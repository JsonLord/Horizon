"""Research orchestration through GitHub APIs, without local production jobs."""

import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from src.research.profiles import Profile
from src.research.registry import Registry, apply_registry
from src.research.reporting import atomic, dumps

from .archive import PublishedArchive
from .github import ControlError, GitHub
from .schedules import (
    REGISTRY_PATH,
    SHARED_WORKFLOW,
    WORKFLOW_PREFIX,
    Schedule,
    ScheduleRegistry,
    next_expected,
    render_workflows,
    workflow_path,
)

DISPATCH_WORKFLOW = "horizon-intel.yml"
REQUEST_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"


def run_identity(run):
    title = run.get("display_title", "")
    manual = re.fullmatch(
        r"Horizon ((?:world|institutions|examples)/[a-z0-9-]+|default) \[request=([a-zA-Z0-9_-]+)\](?: \[hours=([0-9]+)\])?",
        title,
    )
    scheduled = re.fullmatch(
        r"Horizon schedule ([a-z0-9-]+) \[((?:world|institutions|examples)/[a-z0-9-]+)\]",
        title,
    )
    if manual:
        return {
            "profile_id": manual[1],
            "request_id": manual[2],
            "lookback_hours": int(manual[3]) if manual[3] else None,
            "schedule_id": None,
        }
    if scheduled:
        return {
            "profile_id": scheduled[2],
            "request_id": None,
            "lookback_hours": None,
            "schedule_id": scheduled[1],
        }
    return {
        "profile_id": None,
        "request_id": None,
        "lookback_hours": None,
        "schedule_id": None,
    }


class Controller:
    def __init__(
        self, github=None, default_ref=None, allowed_refs=None, state_dir=None
    ):
        self.github = github or GitHub()
        self.default_ref = default_ref or os.getenv(
            "HORIZON_GITHUB_DEFAULT_REF", "main"
        )
        self.allowed_refs = set(
            allowed_refs
            or os.getenv("HORIZON_GITHUB_ALLOWED_REFS", self.default_ref).split(",")
        )
        self.allowed_refs.add(self.default_ref)
        self.archive = PublishedArchive(self.github)
        self.state_dir = Path(
            state_dir or os.getenv("HORIZON_CONTROL_STATE_DIR", "data/control")
        )
        self.dispatch_lock = asyncio.Lock()

    async def snapshot(self, ref=None):
        commit = await self.github.commit(ref or self.default_ref)
        sha = commit["sha"]
        tree = await self.github.get(
            "git/trees/" + commit["commit"]["tree"]["sha"], {"recursive": "1"}
        )
        if tree.get("truncated"):
            raise ControlError(
                "REPOSITORY_TOO_LARGE",
                "Repository tree is truncated; cannot validate approved configuration.",
            )
        paths = [
            r["path"]
            for r in tree["tree"]
            if r["type"] == "blob"
            and re.fullmatch(
                r"profiles/(world|institutions|examples)/[a-z0-9-]+\.json", r["path"]
            )
        ]
        if len(paths) > 64:
            raise ControlError(
                "TOO_MANY_PROFILES", "At most 64 reviewed profiles are supported."
            )
        semaphore = asyncio.Semaphore(4)

        async def read(path):
            async with semaphore:
                return Profile.model_validate_json(await self.github.file(path, sha))

        parsed = await asyncio.gather(*(read(path) for path in paths))
        if len({p.profile_id for p in parsed}) != len(parsed):
            raise ControlError(
                "PROFILE_CONFLICT", "Duplicate profile IDs in chosen revision."
            )
        profiles = {p.profile_id: p for p in parsed if p.enabled}
        source_raw = await self.github.file("sources/registry.json", sha, missing=True)
        sources = Registry.model_validate_json(source_raw) if source_raw else Registry()
        apply_registry(profiles, sources)
        raw = await self.github.file(REGISTRY_PATH, sha, missing=True)
        schedules = (
            ScheduleRegistry.model_validate_json(raw) if raw else ScheduleRegistry()
        )
        schedules.validate_profiles(profiles)
        return {
            "commit": commit,
            "sha": sha,
            "profiles": profiles,
            "sources": sources,
            "schedules": schedules,
            "paths": {r["path"] for r in tree["tree"]},
        }

    async def profiles(self, ref=None):
        ref = ref or self.default_ref
        if ref not in self.allowed_refs:
            raise ControlError(
                "REF_NOT_AUTHORIZED",
                "Select a ref explicitly listed in HORIZON_GITHUB_ALLOWED_REFS.",
            )
        snapshot = await self.snapshot(ref)
        return {
            "ref": ref,
            "source_commit": snapshot["sha"],
            "profiles": [
                p.model_dump(mode="json", by_alias=True)
                for p in snapshot["profiles"].values()
            ],
            "institutions": [
                p.institution.model_dump()
                for p in snapshot["profiles"].values()
                if p.institution
            ],
        }

    async def recent(self, workflow=DISPATCH_WORKFLOW, limit=100, status=None, pages=1):
        if status and status not in {
            "queued",
            "in_progress",
            "completed",
            "requested",
            "waiting",
            "pending",
            "success",
            "failure",
            "cancelled",
            "timed_out",
            "action_required",
            "neutral",
            "skipped",
            "stale",
        }:
            raise ValueError("Unsupported GitHub run status/conclusion")
        result = []
        for page in range(1, pages + 1):
            params = {"per_page": min(100, limit), "page": page}
            if status:
                params["status"] = status
            batch = await self.github.get(
                "actions/workflows/" + workflow + "/runs", params, missing=True
            )
            if batch is None:
                return result
            rows = batch["workflow_runs"]
            result += rows
            if len(rows) < min(100, limit):
                break
        return result

    def request_file(self, request_id):
        return self.state_dir / (
            hashlib.sha256(request_id.encode()).hexdigest() + ".json"
        )

    async def dispatch(self, profile_id, lookback_hours=48, request_id=None, ref=None):
        ref = ref or self.default_ref
        if ref not in self.allowed_refs:
            raise ControlError(
                "REF_NOT_AUTHORIZED", "Ref is not explicitly authorized for dispatch."
            )
        if (
            not isinstance(lookback_hours, int)
            or isinstance(lookback_hours, bool)
            or not 1 <= lookback_hours <= 168
        ):
            raise ValueError("Lookback must be 1–168 hours")
        supplied_id = request_id is not None
        request_id = request_id or uuid.uuid4().hex
        if not re.fullmatch(REQUEST_PATTERN, request_id):
            raise ValueError(
                "request_id must contain 1–64 ASCII letters, digits, underscores or hyphens"
            )
        submitted = {
            "profile_id": profile_id,
            "lookback_hours": str(lookback_hours),
            "request_id": request_id,
        }
        fingerprint = {"ref": ref, "inputs": submitted}
        async with self.dispatch_lock:
            snapshot = await self.snapshot(ref)
            if profile_id not in snapshot["profiles"]:
                raise ControlError(
                    "PROFILE_NOT_APPROVED",
                    "Profile is absent or disabled at the selected GitHub revision.",
                )
            await self.github.authenticate(required=True)
            path = self.request_file(request_id)
            saved = json.loads(path.read_text()) if path.exists() else None
            if saved and saved["fingerprint"] != fingerprint:
                raise ControlError(
                    "IDEMPOTENCY_CONFLICT",
                    "request_id was previously used with different inputs/ref.",
                )
            if saved and saved.get("run_id"):
                return {**saved["result"], "reused": True}
            if supplied_id or saved:
                # Reconcile across controller restarts/hosts using GitHub's own
                # correlation title. Do not infer a run from 'most recent'.
                for run in await self.recent(pages=3):
                    identity = run_identity(run)
                    if identity["request_id"] == request_id:
                        if (
                            identity["profile_id"] != profile_id
                            or identity["lookback_hours"] not in (None, lookback_hours)
                            or run.get("head_branch") != ref
                        ):
                            raise ControlError(
                                "IDEMPOTENCY_CONFLICT",
                                "request_id already identifies a run with different parameters.",
                            )
                        result = self.dispatched_result(run, submitted, ref)
                        atomic(
                            path,
                            dumps(
                                {
                                    "fingerprint": fingerprint,
                                    "run_id": result["run_id"],
                                    "result": result,
                                }
                            ),
                        )
                        return {**result, "reused": True}
                _, rows = await self.archive.index()
                for row in rows:
                    wf = row.get("workflow", {})
                    if wf.get("request_id") == request_id:
                        if (
                            row["profile_id"] != profile_id
                            or wf.get("effective_lookback_hours") != lookback_hours
                            or wf.get("ref") != ref
                        ):
                            raise ControlError(
                                "IDEMPOTENCY_CONFLICT",
                                "Published request_id has different parameters.",
                            )
                        run = await self.github.get(
                            "actions/runs/" + str(int(wf["run_id"]))
                        )
                        result = self.dispatched_result(run, submitted, ref)
                        atomic(
                            path,
                            dumps(
                                {
                                    "fingerprint": fingerprint,
                                    "run_id": result["run_id"],
                                    "result": result,
                                }
                            ),
                        )
                        return {**result, "reused": True}
            if saved:
                return {
                    "request_id": request_id,
                    "run_id": None,
                    "status": "dispatch_uncertain",
                    "inputs": submitted,
                    "ref": ref,
                    "message": "An earlier submission is still uncorrelated. Inspect workflow runs; this request will not dispatch a duplicate.",
                }
            workflow_raw = await self.github.file(
                ".github/workflows/" + DISPATCH_WORKFLOW, snapshot["sha"]
            )
            if b"request_id:" not in workflow_raw:
                raise ControlError(
                    "CONTROLLER_NOT_ACTIVATED",
                    "Merge the controller workflow before dispatching correlated requests at this ref.",
                )
            # A local journal is recovery metadata, never a background scheduler.
            # Record intent before POST; a transport timeout is not retried.
            path.parent.mkdir(parents=True, exist_ok=True)
            if len(list(path.parent.glob("*.json"))) >= 1000:
                raise ControlError(
                    "REQUEST_JOURNAL_FULL",
                    "Local request recovery journal is full; archive completed entries before submitting new requests.",
                )
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                return {
                    "request_id": request_id,
                    "run_id": None,
                    "status": "dispatch_uncertain",
                    "inputs": submitted,
                    "ref": ref,
                    "message": "Another local controller reserved this request. Reconcile its run before retrying.",
                }
            with os.fdopen(descriptor, "w") as journal:
                journal.write(
                    dumps(
                        {
                            "fingerprint": fingerprint,
                            "run_id": None,
                            "submitted_at": datetime.now(UTC).isoformat(),
                        }
                    )
                )
                journal.flush()
                os.fsync(journal.fileno())
            try:
                response = await self.github.write(
                    "POST",
                    "actions/workflows/" + DISPATCH_WORKFLOW + "/dispatches",
                    {"ref": ref, "inputs": submitted, "return_run_details": True},
                )
            except ControlError as exc:
                if exc.code != "GITHUB_WRITE_UNCERTAIN":
                    path.unlink(missing_ok=True)
                raise
            rid = (
                response.get("workflow_run_id")
                or response.get("run_id")
                or response.get("id")
            )
            if rid:
                if isinstance(rid, bool) or not str(rid).isdigit() or int(rid) <= 0:
                    raise ControlError(
                        "GITHUB_INVALID_RESPONSE",
                        "Run-details response contains no valid GitHub run ID.",
                    )
                try:
                    run = await self.github.get("actions/runs/" + str(int(rid)))
                    result = self.dispatched_result(run, submitted, ref)
                except ControlError as exc:
                    if exc.code != "GITHUB_NOT_FOUND":
                        raise
                    # The API's positive returned ID is authoritative even when
                    # its run metadata has not propagated to GET yet.
                    result = {
                        "run_id": int(rid),
                        "run_url": f"https://github.com/{self.github.repo}/actions/runs/{int(rid)}",
                        "request_id": request_id,
                        "inputs": submitted,
                        "ref": ref,
                        "status": "submitted",
                        "source_commit": None,
                        "validated_source_commit": snapshot["sha"],
                        "reused": False,
                    }
                atomic(
                    path,
                    dumps(
                        {
                            "fingerprint": fingerprint,
                            "run_id": result["run_id"],
                            "result": result,
                        }
                    ),
                )
                return result
            for attempt in range(4):
                for run in await self.recent(limit=100):
                    identity = run_identity(run)
                    if (
                        identity["request_id"] == request_id
                        and identity["profile_id"] == profile_id
                        and run.get("head_branch") == ref
                    ):
                        result = self.dispatched_result(run, submitted, ref)
                        atomic(
                            path,
                            dumps(
                                {
                                    "fingerprint": fingerprint,
                                    "run_id": result["run_id"],
                                    "result": result,
                                }
                            ),
                        )
                        return result
                if attempt < 3:
                    await asyncio.sleep(1)
            return {
                "request_id": request_id,
                "run_id": None,
                "status": "acknowledged_waiting_for_run",
                "inputs": submitted,
                "ref": ref,
                "message": "GitHub acknowledged dispatch without run details. List runs and match request_id; do not dispatch again.",
            }

    def dispatched_result(self, run, inputs, ref):
        if (
            not isinstance(run.get("id"), int)
            or run["id"] <= 0
            or run.get("head_branch") != ref
        ):
            raise ControlError(
                "GITHUB_INVALID_RESPONSE",
                "Dispatch response did not identify a real run on the requested ref.",
            )
        identity = run_identity(run)
        if identity["request_id"] and (
            identity["request_id"] != inputs["request_id"]
            or identity["profile_id"] != inputs["profile_id"]
        ):
            raise ControlError(
                "GITHUB_INVALID_RESPONSE",
                "Run correlation differs from submitted request.",
            )
        return {
            "run_id": run["id"],
            "run_url": run["html_url"],
            "request_id": inputs["request_id"],
            "inputs": inputs,
            "ref": ref,
            "status": run["status"],
            "source_commit": run["head_sha"],
            "reused": False,
        }

    async def workflow_run(self, run_id):
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise ValueError("run_id must be a positive GitHub run ID")
        run = await self.github.get("actions/runs/" + str(run_id))
        path = run.get("path", "").split("@")[0]
        if path != ".github/workflows/horizon-intel.yml" and not re.fullmatch(
            r"\.github/workflows/horizon-sched-[a-z0-9-]+\.yml", path
        ):
            raise ControlError(
                "UNRELATED_WORKFLOW", "This run is not a Horizon research workflow."
            )
        jobs = (
            await self.github.get(f"actions/runs/{run_id}/jobs", {"per_page": 100})
        )["jobs"]
        identity = run_identity(run)
        collection = next(
            (j for j in jobs if j["name"].split(" / ")[-1] == "collect"), None
        )
        publication = next(
            (j for j in jobs if j["name"].split(" / ")[-1] == "publish"), None
        )
        _, rows = await self.archive.index()
        matched = [
            r for r in rows if str(r.get("workflow", {}).get("run_id")) == str(run_id)
        ]
        verified = []
        for row in matched:
            result = await self.archive.report(run_id, row["profile_id"], "summary")
            report = result["report"]
            if report["workflow"].get("source_commit") != run["head_sha"]:
                raise ControlError(
                    "ARCHIVE_IDENTITY_MISMATCH",
                    "Report code SHA differs from the workflow run.",
                )
            verified.append(
                {
                    k: result[k]
                    for k in ("report_id", "profile_id", "publication_commit", "links")
                }
            )
        requested = identity["profile_id"]
        requested_present = (
            bool(verified)
            if requested in (None, "default")
            else any(r["profile_id"] == requested for r in verified)
        )
        failures = [
            {
                "job": j["name"],
                "conclusion": j["conclusion"],
                "steps": [
                    s["name"]
                    for s in j.get("steps", [])
                    if s.get("conclusion") in ("failure", "cancelled", "timed_out")
                ],
            }
            for j in jobs
            if j.get("conclusion") in ("failure", "cancelled", "timed_out")
        ]
        compact = lambda j: (
            {
                k: j.get(k)
                for k in (
                    "id",
                    "name",
                    "status",
                    "conclusion",
                    "started_at",
                    "completed_at",
                )
            }
            if j
            else None
        )
        return {
            "run_id": run_id,
            "run_url": run["html_url"],
            "requested_profile": requested,
            "request_id": identity["request_id"],
            "schedule_id": identity["schedule_id"],
            "status": run["status"],
            "conclusion": run.get("conclusion"),
            "source_commit": run["head_sha"],
            "started_at": run.get("run_started_at"),
            "completed_at": max(
                (j["completed_at"] for j in jobs if j.get("completed_at")), default=None
            )
            if run["status"] == "completed"
            else None,
            "collection": compact(collection),
            "publication": compact(publication),
            "runner_completed": run["status"] == "completed",
            "collection_succeeded": bool(
                collection and collection["conclusion"] == "success"
            ),
            "publication_job_succeeded": bool(
                publication and publication["conclusion"] == "success"
            ),
            "publication_status": "verified" if requested_present else "not_observed",
            "reports": verified,
            "failure_reason": failures or None,
        }

    async def workflow_report(self, run_id, profile_id=None, format="json"):
        result = await self.archive.report(run_id, profile_id, format)
        run = await self.github.get("actions/runs/" + str(int(run_id)))
        if result["source_commit"] != run["head_sha"]:
            raise ControlError(
                "ARCHIVE_IDENTITY_MISMATCH",
                "Published source SHA differs from requested run.",
            )
        return result

    async def list_runs(self, profile_id=None, status=None, limit=20):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1–50")
        runs = await self.github.get(
            "actions/runs", {"per_page": 100, **({"status": status} if status else {})}
        )
        _, rows = await self.archive.index()
        result = []
        for run in runs["workflow_runs"]:
            path = run.get("path", "").split("@")[0]
            if path != ".github/workflows/horizon-intel.yml" and not re.fullmatch(
                r"\.github/workflows/horizon-sched-[a-z0-9-]+\.yml", path
            ):
                continue
            identity = run_identity(run)
            matched = [
                r
                for r in rows
                if str(r.get("workflow", {}).get("run_id")) == str(run["id"])
            ]
            if (
                profile_id
                and identity["profile_id"] != profile_id
                and not any(r["profile_id"] == profile_id for r in matched)
            ):
                continue
            result.append(
                {
                    "run_id": run["id"],
                    "run_url": run["html_url"],
                    "status": run["status"],
                    "conclusion": run.get("conclusion"),
                    "source_commit": run["head_sha"],
                    "created_at": run["created_at"],
                    **identity,
                    "publication_status": "indexed_unverified"
                    if matched
                    else "not_observed",
                    "report_ids": [r["report_id"] for r in matched],
                }
            )
        return {
            "runs": result[:limit],
            "scan_limit": 100,
            "message": "Publication is checksum-verified by hz_get_workflow_run/report; missing rows can also indicate retention.",
        }

    async def propose(self, kind, resource_id, files, title, metadata, snapshot):
        await self.github.authenticate(required=True)
        if SHARED_WORKFLOW not in snapshot["paths"]:
            raise ControlError(
                "CONTROLLER_NOT_ACTIVATED",
                "Merge the integration PR before opening lifecycle proposals from the default branch.",
            )
        allowed = lambda p: (
            p in (REGISTRY_PATH, "sources/registry.json")
            or re.fullmatch(
                r"profiles/(world|institutions|examples)/[a-z0-9-]+\.json", p
            )
            or re.fullmatch(r"\.github/workflows/horizon-sched-[a-z0-9-]+\.yml", p)
        )
        if not files or any(not allowed(path) for path in files):
            raise ValueError("Proposal contains no changes or unauthorized paths")
        digest = hashlib.sha256(
            dumps(
                {"files": files, "operation": metadata, "base": snapshot["sha"]}
            ).encode()
        ).hexdigest()[:12]
        resource_id = re.sub(r"[^a-z0-9-]", "-", resource_id.lower())[:64]
        branch = f"horizon-proposal/{kind}-{resource_id}-{digest}"
        existing = await self.github.get(
            "pulls",
            {
                "state": "open",
                "head": self.github.repo.split("/")[0] + ":" + branch,
                "base": self.default_ref,
                "per_page": 10,
            },
        )
        current = await self.github.commit(self.default_ref)
        if current["sha"] != snapshot["sha"]:
            raise ControlError(
                "PROPOSAL_CONFLICT",
                "Default branch changed during validation; reload and propose again.",
            )
        ref_suffix = "git/ref/heads/" + quote(branch, safe="")
        branch_ref = await self.github.get(ref_suffix, missing=True)
        if branch_ref:
            # Recover only our exact proposal marker. Never overwrite an edited branch.
            head = await self.github.get("git/commits/" + branch_ref["object"]["sha"])
            if (
                head["message"] != title + "\n\nHorizon proposal " + digest
                or len(head["parents"]) != 1
                or head["parents"][0]["sha"] != snapshot["sha"]
            ):
                raise ControlError(
                    "PROPOSAL_CONFLICT",
                    "Proposal branch exists with unexpected changes; it will not be overwritten.",
                )
            for path, content in files.items():
                actual = await self.github.file(
                    path, branch_ref["object"]["sha"], missing=True
                )
                if actual != (content.encode() if content is not None else None):
                    raise ControlError(
                        "PROPOSAL_CONFLICT",
                        "Proposal files were edited; existing work will not be overwritten or claimed as validated.",
                    )
            if existing:
                return {
                    "pull_request_url": existing[0]["html_url"],
                    "branch": branch,
                    "activation_state": "pending_review",
                    "reused": True,
                    **metadata,
                }
        else:
            tree = []
            for path, content in sorted(files.items()):
                sha = None
                if content is not None:
                    sha = (
                        await self.github.write(
                            "POST",
                            "git/blobs",
                            {"content": content, "encoding": "utf-8"},
                        )
                    )["sha"]
                tree.append(
                    {"path": path, "mode": "100644", "type": "blob", "sha": sha}
                )
            built = await self.github.write(
                "POST",
                "git/trees",
                {
                    "base_tree": snapshot["commit"]["commit"]["tree"]["sha"],
                    "tree": tree,
                },
            )
            commit = await self.github.write(
                "POST",
                "git/commits",
                {
                    "message": title + "\n\nHorizon proposal " + digest,
                    "tree": built["sha"],
                    "parents": [snapshot["sha"]],
                },
            )
            if (await self.github.commit(self.default_ref))["sha"] != snapshot["sha"]:
                raise ControlError(
                    "PROPOSAL_CONFLICT",
                    "Default branch changed before branch creation; no branch/PR was published.",
                )
            await self.github.write(
                "POST",
                "git/refs",
                {"ref": "refs/heads/" + branch, "sha": commit["sha"]},
            )
        body = (
            title
            + "\n\nConfiguration was validated against "
            + snapshot["sha"]
            + ". Activation requires review and merge; historical research is preserved.\n\n<!-- horizon-proposal:"
            + json.dumps(metadata, sort_keys=True)
            + " -->"
        )
        try:
            pr = await self.github.write(
                "POST",
                "pulls",
                {
                    "title": title,
                    "head": branch,
                    "base": self.default_ref,
                    "body": body,
                },
            )
        except ControlError as exc:
            # Recover a racing or response-lost PR creation by exact head/base.
            matches = await self.github.get(
                "pulls",
                {
                    "state": "open",
                    "head": self.github.repo.split("/")[0] + ":" + branch,
                    "base": self.default_ref,
                    "per_page": 10,
                },
            )
            if not matches:
                raise exc
            pr = matches[0]
        return {
            "pull_request_url": pr["html_url"],
            "branch": branch,
            "activation_state": "pending_review",
            "reused": False,
            **metadata,
        }

    async def change_schedule(self, operation, schedule_id=None, **fields):
        snapshot = await self.snapshot()
        registry = snapshot["schedules"]
        old = next(
            (s for s in registry.schedules if s.schedule_id == schedule_id), None
        )
        if operation == "create":
            name = fields.get("name", "")
            slug = (
                re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "research"
            )
            schedule_id = (
                slug + "-" + hashlib.sha256(dumps(fields).encode()).hexdigest()[:8]
            )
            old = next(
                (s for s in registry.schedules if s.schedule_id == schedule_id), None
            )
            if old:
                raise ControlError(
                    "SCHEDULE_ALREADY_EXISTS",
                    "A schedule with these creation parameters exists; use update/get.",
                )
            proposed = Schedule(schedule_id=schedule_id, **fields)
        else:
            if not old:
                raise ControlError(
                    "SCHEDULE_NOT_FOUND",
                    "Schedule does not exist on the default branch.",
                )
            if operation in ("pause", "resume"):
                fields = {"enabled": operation == "resume"}
            if any(
                k
                not in {
                    "name",
                    "profile_id",
                    "cron",
                    "timezone",
                    "lookback_hours",
                    "description",
                    "enabled",
                }
                for k in fields
            ):
                raise ValueError("Unsupported schedule update field")
            proposed = (
                None
                if operation == "delete"
                else Schedule.model_validate({**old.model_dump(), **fields})
            )
        updated = ScheduleRegistry(
            schedules=[s for s in registry.schedules if s.schedule_id != schedule_id]
            + ([proposed] if proposed else [])
        )
        updated.validate_profiles(snapshot["profiles"])
        expected = render_workflows(updated)
        actual_paths = {
            p
            for p in snapshot["paths"]
            if p.startswith(WORKFLOW_PREFIX) and p.endswith(".yml")
        }
        files = {REGISTRY_PATH: dumps(updated.model_dump(mode="json")), **expected}
        files.update({p: None for p in actual_paths - set(expected)})
        metadata = {
            "kind": "schedule",
            "schedule_id": schedule_id,
            "operation": operation,
            "proposed": proposed.model_dump(mode="json") if proposed else None,
        }
        return await self.propose(
            "schedule",
            schedule_id,
            files,
            f"{operation.capitalize()} Horizon schedule {schedule_id}",
            metadata,
            snapshot,
        )

    async def pending_schedules(self):
        pulls = await self.github.get(
            "pulls", {"state": "open", "base": self.default_ref, "per_page": 50}
        )
        results = []
        for pr in pulls:
            if "<!-- horizon-integration -->" in (pr.get("body") or ""):
                branch = pr.get("head", {}).get("sha")
                if branch:
                    proposed = await self.snapshot(branch)
                    results.extend(
                        {
                            "kind": "schedule",
                            "schedule_id": s.schedule_id,
                            "operation": "migrate",
                            "proposed": s.model_dump(mode="json"),
                            "pull_request_url": pr["html_url"],
                            "activation_state": "pending_review",
                        }
                        for s in proposed["schedules"].schedules
                    )
                continue
            match = re.search(
                r"<!-- horizon-proposal:(\{.*?\}) -->", pr.get("body") or ""
            )
            if not match:
                continue
            try:
                metadata = json.loads(match[1])
                if metadata.get("kind") != "schedule":
                    continue
                if metadata.get("proposed"):
                    Schedule.model_validate(metadata["proposed"])
                results.append(
                    {
                        **metadata,
                        "pull_request_url": pr["html_url"],
                        "activation_state": "pending_review",
                    }
                )
            except (ValueError, KeyError):
                continue
        return results

    async def list_schedules(self):
        snapshot = await self.snapshot()
        _, rows = await self.archive.index()
        result = []
        for schedule in snapshot["schedules"].schedules:
            path = workflow_path(schedule.schedule_id)
            if not schedule.enabled:
                activation = (
                    "paused" if path not in snapshot["paths"] else "configuration_drift"
                )
                workflow = None
            else:
                actual = await self.github.file(path, snapshot["sha"], missing=True)
                expected = render_workflows(ScheduleRegistry(schedules=[schedule]))[
                    path
                ]
                workflow = await self.github.get(
                    "actions/workflows/" + path.split("/")[-1], missing=True
                )
                activation = (
                    "active"
                    if actual
                    and actual.decode() == expected
                    and workflow
                    and workflow.get("state") == "active"
                    else "configuration_drift"
                    if actual
                    else "not_installed"
                )
            matches = [
                r
                for r in rows
                if r.get("schedule", {}).get("schedule_id") == schedule.schedule_id
                or r.get("workflow", {}).get("schedule_id") == schedule.schedule_id
            ]
            latest = next(
                (r for r in matches if r["status"] in ("complete", "partial")), None
            )
            runs = await self.recent(path.split("/")[-1], limit=1)
            last = runs[0] if runs else None
            result.append(
                {
                    **schedule.model_dump(mode="json"),
                    "activation_state": activation,
                    "next_expected_execution": next_expected(schedule)
                    if schedule.enabled
                    else None,
                    "next_execution_is_estimate": True,
                    "last_known_execution": {
                        "run_id": last["id"],
                        "status": last["status"],
                        "conclusion": last.get("conclusion"),
                        "created_at": last["created_at"],
                    }
                    if last
                    else None,
                    "latest_report_link": f"https://raw.githubusercontent.com/{self.github.repo}/intel/{latest['path']}"
                    if latest
                    else None,
                    "workflow_state": workflow.get("state") if workflow else None,
                }
            )
        return {
            "ref": self.default_ref,
            "source_commit": snapshot["sha"],
            "schedules": result,
            "pending_changes": await self.pending_schedules(),
            "message": "Only default-branch registry/workflow matches are active. Next times are estimates; GitHub may delay or disable inactive schedules.",
        }

    async def schedule_runs(self, schedule_id, limit=20):
        path = workflow_path(schedule_id)
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1–50")
        runs = await self.recent(path.split("/")[-1], limit=min(100, limit))
        _, rows = await self.archive.index()
        reports = [
            r
            for r in rows
            if r.get("schedule", {}).get("schedule_id") == schedule_id
            or r.get("workflow", {}).get("schedule_id") == schedule_id
        ]
        return {
            "schedule_id": schedule_id,
            "runs": [
                {
                    "run_id": r["id"],
                    "run_url": r["html_url"],
                    "status": r["status"],
                    "conclusion": r.get("conclusion"),
                    "created_at": r["created_at"],
                    "reports": [
                        p
                        for p in reports
                        if str(p.get("workflow", {}).get("run_id")) == str(r["id"])
                    ],
                }
                for r in runs[:limit]
            ],
            "reports": reports[:limit],
            "missed_execution_status": "unknown",
            "message": "No run is not proof of a missed occurrence; GitHub can delay delivery and history is bounded.",
        }

    async def get_schedule(self, schedule_id):
        listed = await self.list_schedules()
        active = next(
            (s for s in listed["schedules"] if s["schedule_id"] == schedule_id), None
        )
        pending = [
            p for p in listed["pending_changes"] if p["schedule_id"] == schedule_id
        ]
        if active is None and not pending:
            raise ControlError(
                "SCHEDULE_NOT_FOUND",
                "No active/paused schedule or pending proposal is known.",
            )
        return {
            "schedule": active,
            "pending_changes": pending,
            "history": await self.schedule_runs(schedule_id),
        }

    async def propose_profile(self, profile):
        proposed = Profile.model_validate(profile)
        snapshot = await self.snapshot()
        # Validate every declared feed as data, not as an instruction to GitHub.
        from src.research.registry import discover
        from urllib.parse import urlsplit

        feeds = [f.url for f in proposed.feeds]
        if proposed.institution:
            for url in proposed.institution.official_feeds:
                host = urlsplit(url).hostname
                if not any(
                    host == d or host.endswith("." + d)
                    for d in proposed.institution.official_domains
                ):
                    raise ValueError(
                        "Official feeds must use a reviewed official domain"
                    )
            feeds += proposed.institution.official_feeds
        for url in feeds:
            await asyncio.wait_for(discover(url, feed_url=url), 60)
        profiles = dict(snapshot["profiles"])
        if proposed.enabled:
            profiles[proposed.profile_id] = proposed
        else:
            profiles.pop(proposed.profile_id, None)
        apply_registry(profiles, snapshot["sources"])
        snapshot["schedules"].validate_profiles(profiles)
        return await self.propose(
            "profile",
            proposed.profile_id,
            {
                "profiles/" + proposed.profile_id + ".json": dumps(
                    proposed.model_dump(mode="json", by_alias=True)
                )
            },
            "Propose Horizon profile " + proposed.profile_id,
            {"kind": "profile", "profile_id": proposed.profile_id},
            snapshot,
        )

    async def propose_source(
        self, url, name, profile_ids, topic="general", region="unknown", feed_url=None
    ):
        import tempfile
        from src.research.registry import register

        snapshot = await self.snapshot()
        with tempfile.TemporaryDirectory(prefix="horizon-source-proposal-") as tmp:
            path = Path(tmp) / "registry.json"
            atomic(path, dumps(snapshot["sources"].model_dump(mode="json")))
            source = await register(
                url,
                name,
                profile_ids,
                topic,
                region,
                feed_url,
                path,
                profiles=dict(snapshot["profiles"]),
            )
            updated = Registry.model_validate_json(path.read_text())
        return await self.propose(
            "source",
            source["source_id"],
            {"sources/registry.json": dumps(updated.model_dump(mode="json"))},
            "Propose Horizon source " + source["source_id"],
            {
                "kind": "source",
                "source_id": source["source_id"],
                "profile_ids": source["profile_ids"],
                "verified_feed_url": source["feed_url"],
            },
            snapshot,
        )
