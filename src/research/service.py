"""Shared bounded research jobs for trusted local MCP and GitHub Actions."""

import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Annotated

from .analyzers import analyze, enrich
from .collector import collect
from .profiles import Profile, load_profiles
from .reporting import Archive, atomic, dumps, make_report


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(pattern=r"^(world|institutions|examples)/[a-z0-9-]{1,64}$")
    question: str = Field(default="", max_length=1000, pattern=r"^[^\x00-\x08]*$")
    lookback_hours: int | None = Field(default=None, ge=1, le=168)
    depth: int = Field(default=60, ge=1, le=200)
    sources: list[Literal["gdelt", "google_news", "rss"]] | None = Field(
        default=None, min_length=1, max_length=3
    )
    institution_ids: list[Annotated[str, Field(pattern=r"^[a-z0-9-]{1,64}$")]] = Field(
        default_factory=list, max_length=4
    )
    idempotency_key: str | None = Field(
        default=None, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )


class ResearchService:
    def __init__(self, root=None, profiles_dir=None, collector=collect):
        self.root = Path(root or os.getenv("HORIZON_RESEARCH_DIR", "data/research"))
        self.archive = Archive(self.root)
        self.history = {"state": "local", "previous_snapshot_commit": None}
        self.profiles = load_profiles(profiles_dir)
        for f in (self.root / "profiles").glob("*.json"):
            p = Profile.model_validate_json(f.read_text())
            self.profiles[p.profile_id] = p
        self.collector = collector
        self.jobs = {}
        self.tasks = {}
        self.max_jobs = min(2, max(1, int(os.getenv("HORIZON_MAX_JOBS", "2"))))
        self.semaphore = asyncio.Semaphore(self.max_jobs)
        for p in (self.root / "jobs").glob("*.json"):
            try:
                job = json.loads(p.read_text())
                if job["status"] in ("running", "queued"):
                    job.update(
                        status="failed",
                        stage="interrupted",
                        completed_at=datetime.now(UTC).isoformat(),
                        error={
                            "code": "INTERRUPTED",
                            "message": "Process restarted before completion.",
                        },
                    )
                    atomic(p, dumps(job))
                self.jobs[job["job_id"]] = job
            except (ValueError, KeyError):
                continue

    def persist(self, job):
        atomic(self.root / "jobs" / f"{job['job_id']}.json", dumps(job))

    def profile(self, pid):
        if pid not in self.profiles:
            raise KeyError("Profile not found")
        return self.profiles[pid]

    def get_job(self, jid):
        if jid not in self.jobs:
            raise KeyError("Job not found")
        return dict(self.jobs[jid])

    def register(self, payload):
        p = Profile.model_validate(payload)
        # Trusted registration still refuses arbitrary submitted feed crawling.
        if p.feeds or (p.institution and p.institution.official_feeds):
            raise ValueError("Feeds require operator-reviewed repository configuration")
        atomic(
            self.root / "profiles" / f"{p.profile_id.replace('/', '-')}.json",
            p.canonical(),
        )
        self.profiles[p.profile_id] = p
        return p.model_dump(by_alias=True)

    async def submit(self, request, requested_by="trusted_stdio"):
        req = Request.model_validate(request)
        self.profile(req.profile_id)
        for iid in req.institution_ids:
            p = self.profile("institutions/" + iid)
            if not p.institution:
                raise ValueError("Institution profile required")
        import hashlib

        fingerprint = hashlib.sha256(
            req.model_dump_json(exclude={"idempotency_key"}).encode()
        ).hexdigest()
        if req.idempotency_key:
            for j in self.jobs.values():
                if (
                    j["idempotency_key"] == req.idempotency_key
                    and j["requested_by"] == requested_by
                ):
                    if j.get("request_fingerprint") != fingerprint:
                        raise ValueError("Idempotency key conflict")
                    return dict(j)
        if (
            sum(j["status"] in ("queued", "running") for j in self.jobs.values())
            >= self.max_jobs + 4
        ):
            raise OverflowError("Job queue full")
        while len(self.jobs) >= 100:
            old_id = next(
                (
                    k
                    for k, j in self.jobs.items()
                    if j["status"] not in ("queued", "running")
                ),
                None,
            )
            if old_id is None:
                raise OverflowError("Job history full")
            self.jobs.pop(old_id)
            self.tasks.pop(old_id, None)
            (self.root / "jobs" / f"{old_id}.json").unlink(missing_ok=True)
        jid = uuid.uuid4().hex
        job = {
            "job_id": jid,
            "idempotency_key": req.idempotency_key,
            "request_fingerprint": fingerprint,
            "requested_by": requested_by,
            "profile_id": req.profile_id,
            "question": req.question,
            "mode": self.profile(req.profile_id).mode,
            "status": "queued",
            "submitted_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
            "stage": "queued",
            "counts": {},
            "warnings": [],
            "error": None,
            "report_id": None,
            "artifact_manifest": None,
            "publication_status": "local_only",
        }
        self.jobs[jid] = job
        self.persist(job)
        self.tasks[jid] = asyncio.create_task(self.execute(jid, req))
        return dict(job)

    async def execute(self, jid, req):
        job = self.jobs[jid]
        try:
            async with self.semaphore:
                job.update(
                    status="running",
                    stage="collecting",
                    started_at=datetime.now(UTC).isoformat(),
                )
                self.persist(job)
                async with asyncio.timeout(180):
                    profile = self.profile(req.profile_id).model_copy(deep=True)
                    profile.max_items = min(req.depth, profile.max_items)
                    if req.lookback_hours:
                        profile.lookback_hours = req.lookback_hours
                    # Agent questions are bounded search input, never shell/configuration instructions.
                    if req.sources:
                        profile.sources = req.sources
                        profile.queries = [
                            q for q in profile.queries if q.source in req.sources
                        ]
                    if req.question or req.institution_ids:
                        from .profiles import Query

                        selected = [
                            self.profile("institutions/" + iid).institution
                            for iid in req.institution_ids
                        ]
                        texts = (
                            [
                                (
                                    " ".join(req.question.split())[:150]
                                    + ' "'
                                    + i.names[0][:80]
                                    + '"'
                                ).strip()
                                for i in selected
                            ]
                            if selected
                            else [" ".join(req.question.split())[:240]]
                        )
                        profile.queries = [
                            Query(
                                source=source,
                                text=text,
                                language="english" if source == "gdelt" else "en",
                                region="unknown",
                            )
                            for text in texts
                            for source in profile.sources
                            if source != "rss"
                        ][: profile.max_queries]
                    items, metrics = await self.collector(profile, req.question)
                    job["stage"] = "analyzing"
                    self.persist(job)
                    findings, sources = analyze(
                        profile, items, self.archive.latest(profile.profile_id)
                    )
                    if req.institution_ids:
                        from .analyzers import mentions

                        for finding in findings:
                            for iid in req.institution_ids:
                                institution = self.profile(
                                    "institutions/" + iid
                                ).institution
                                if (
                                    mentions(institution, finding["summary"])
                                    and iid not in finding["institutions"]
                                ):
                                    finding["institutions"].append(iid)
                    model, mode, warnings = await enrich(
                        findings, os.getenv("HORIZON_AI_MODE", "auto")
                    )
                    report_id = jid
                    if job["requested_by"] == "github_actions" and os.getenv(
                        "GITHUB_RUN_ID"
                    ):
                        import hashlib

                        logical = (
                            os.getenv("HORIZON_REQUEST_ID")
                            or os.environ["GITHUB_RUN_ID"]
                        )
                        identity = "|".join(
                            (
                                os.getenv("GITHUB_REPOSITORY", ""),
                                os.getenv("HORIZON_SCHEDULE_ID", ""),
                                logical,
                                profile.profile_id,
                            )
                        )
                        report_id = hashlib.sha256(identity.encode()).hexdigest()[:32]
                    report = make_report(
                        profile,
                        report_id,
                        req.question,
                        findings,
                        sources,
                        metrics,
                        model,
                        mode,
                        warnings,
                    )
                    report["history"] = dict(self.history)
                    previous = self.archive.latest(profile.profile_id)
                    report["history"]["previous_report_id"] = (
                        previous["report_id"] if previous else None
                    )
                    if previous:
                        import hashlib

                        report["history"]["previous_report_sha256"] = hashlib.sha256(
                            (self.root / previous["links"]["json"]).read_bytes()
                        ).hexdigest()
                        report["history"]["previous_created_at"] = previous[
                            "created_at"
                        ]
                        report["history"]["stale_last_good"] = (
                            datetime.now(UTC)
                            - datetime.fromisoformat(previous["created_at"])
                        ).total_seconds() > profile.lookback_hours * 3600
                    report["history"]["comparison"] = (
                        "last_good" if previous else "first_profile_snapshot"
                    )
                    report["workflow"] = {
                        "run_id": os.getenv("GITHUB_RUN_ID"),
                        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
                        "source_commit": os.getenv("GITHUB_SHA"),
                        "repository": os.getenv("GITHUB_REPOSITORY"),
                        "name": os.getenv("GITHUB_WORKFLOW"),
                        "workflow_ref": os.getenv("GITHUB_WORKFLOW_REF"),
                        "ref": os.getenv("GITHUB_REF_NAME"),
                        "request_id": os.getenv("HORIZON_REQUEST_ID") or None,
                        "schedule_id": os.getenv("HORIZON_SCHEDULE_ID") or None,
                        "effective_lookback_hours": profile.lookback_hours,
                    }
                    if os.getenv("HORIZON_SCHEDULE_ID"):
                        report["schedule"] = {
                            "schedule_id": os.environ["HORIZON_SCHEDULE_ID"],
                            "occurrence_key": os.environ["HORIZON_SCHEDULE_ID"]
                            + ":"
                            + os.environ.get("GITHUB_RUN_ID", jid),
                            "scheduled_execution_time": os.getenv(
                                "HORIZON_SCHEDULED_AT"
                            )
                            or None,
                            "scheduled_time_basis": "event_timestamp"
                            if os.getenv("HORIZON_SCHEDULED_AT")
                            else "not_provided_by_github",
                            "collection_started_at": job["started_at"],
                            "actual_collection_timestamp": report["created_at"],
                            "lookback_hours": profile.lookback_hours,
                        }
                    job["stage"] = "archiving"
                    self.persist(job)
                    manifest = self.archive.write(report)
                    job.update(
                        status="failed"
                        if manifest["status"] == "failed"
                        else "partial"
                        if manifest["status"] == "partial"
                        else "completed",
                        stage="done",
                        report_id=report_id,
                        artifact_manifest=manifest,
                        counts=report["statistics"],
                        warnings=warnings,
                    )
        except asyncio.CancelledError:
            job.update(status="cancelled", stage="cancelled")
            raise
        except Exception:
            job.update(
                status="failed",
                stage="failed",
                error={
                    "code": "RESEARCH_FAILED",
                    "message": "Research failed; inspect operator logs without exposing source payloads.",
                },
            )
        finally:
            job["completed_at"] = datetime.now(UTC).isoformat()
            self.persist(job)

    def cancel(self, jid):
        job = self.get_job(jid)
        if job["status"] not in ("queued", "running"):
            raise ValueError("Job is already terminal")
        task = self.tasks.get(jid)
        if task:
            task.cancel()
        self.jobs[jid].update(
            status="cancelled",
            stage="cancelled",
            completed_at=datetime.now(UTC).isoformat(),
        )
        self.persist(self.jobs[jid])
        return self.get_job(jid)

    async def wait(self, jid):
        await self.tasks[jid]
        return self.get_job(jid)

    def changes(self, profile_id=None, since=None):
        result = []
        for row in self.archive.list(profile_id, limit=100):
            if since and row["created_at"] < since:
                continue
            result.extend(
                dict(c, report_id=row["report_id"])
                for c in self.archive.get(row["report_id"])["changes"]
            )
        return result[:200]

    def search(self, query, limit=20):
        query = query[:200].lower()
        results = []
        for row in self.archive.list(limit=100):
            for finding in self.archive.get(row["report_id"])["findings"]:
                if query in finding["summary"].lower():
                    results.append(dict(finding, report_id=row["report_id"]))
        return results[: min(100, max(1, limit))]
