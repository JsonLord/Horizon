"""Data-only review PRs; canonical intel publication stays in the existing publisher."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re

import httpx

from ..branches import policy
from ..publisher import validate
from ..reporting import Archive, dumps
from .models import Dataset
from .pipeline import material
from .runner import write_generated


def allowed_path(path):
    return path in {"Incubator and Programs.md", "data/programs/incubators.json"} or bool(re.fullmatch(r"reports/programs/\d{4}-\d{2}-\d{2}\.(md|json)", path))


def bundle(root):
    root = Path(root)
    validate(root)
    metadata = json.loads((root / "execution.json").read_text())
    if metadata.get("archive_index_sha256") != hashlib.sha256((root / "intel/manifest.json").read_bytes()).hexdigest():
        raise ValueError("Collected archive index changed")
    report = Archive(root).get(metadata["report_id"])
    if report["profile_id"] != "programs/incubators" or report["question"] or report["workflow"].get("source_commit") != metadata["source_sha"]:
        raise ValueError("Program artifact identity mismatch")
    if metadata.get("report_sha256") != hashlib.sha256((root / report["links"]["json"]).read_bytes()).hexdigest():
        raise ValueError("Collected report changed")
    dataset = Dataset.model_validate(report["statistics"]["programs"])
    # Re-render with trusted checked-out code. Ignore all collected Markdown,
    # paths and other files, including any executable files in the artifact.
    files = write_generated(root, report)
    if len(files) != 4 or any(not allowed_path(p) or len(text.encode()) > 1_000_000 for p, text in files.items()):
        raise ValueError("Generated proposal escaped the data-only path policy")
    digest = hashlib.sha256(dumps({"source_sha": metadata["source_sha"], "programs": [{"program_id": p.program_id, **material(p)} for p in dataset.programs]}).encode()).hexdigest()
    meaningful = any(c["type"] in ("added", "changed", "expired") for p in dataset.programs for c in p.material_changes)
    return metadata, files, digest, meaningful


class ReviewAPI:
    def __init__(self, repository, client=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.repository, self.client = repository, client

    async def call(self, method, path, payload=None, missing=False):
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if method != "GET" and not token:
            raise PermissionError("Existing GitHub contents/pull-requests write identity is required")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        own = self.client is None
        client = self.client or httpx.AsyncClient(timeout=20)
        try:
            response = await client.request(method, f"https://api.github.com/repos/{self.repository}/{path}", json=payload, headers=headers)
            if missing and response.status_code == 404:
                return None
            if response.status_code >= 400:
                # Do not expose raw GitHub bodies, request headers or token values.
                reason = ""
                if len(response.content) < 10000:
                    try:
                        message = response.json().get("message")
                    except (ValueError, AttributeError):
                        message = None
                    reason = {"GitHub Actions is not permitted to create or approve pull requests.": "actions_pr_creation_disabled",
                              "Resource not accessible by integration": "integration_permission_denied"}.get(message, "")
                raise RuntimeError(f"GitHub {method} failed with HTTP {response.status_code}; {reason or 'permission_or_api_rejection'}; reconcile PR/ref state before retrying writes")
            if len(response.content) > 2_000_000:
                raise ValueError("Oversized GitHub response")
            return response.json() if response.content else {}
        except httpx.TransportError as exc:
            raise RuntimeError("GitHub response unavailable; reconcile PR/ref state before retrying") from None
        finally:
            if own:
                await client.aclose()


async def propose(root, api):
    metadata, files, digest, meaningful = bundle(root)
    if not meaningful:
        return {"status": "no_change", "writes": 0}
    if not policy()["review_pr_enabled"]:
        return {"status": "disabled_pending_review", "writes": 0, "digest": digest, "paths": sorted(files)}
    if os.getenv("GITHUB_REF") != "refs/heads/main" or not os.getenv("GITHUB_WORKFLOW_REF", "").endswith("/.github/workflows/program-intelligence.yml@refs/heads/main") or metadata["source_sha"] != os.getenv("GITHUB_SHA") or metadata.get("selected_ref") != "main":
        raise PermissionError("Only reviewed default-branch code and its own collected artifacts may propose production data")
    base = await api.call("GET", "commits/main")
    if base["sha"] != metadata["source_sha"]:
        raise ValueError("Default branch advanced; collect/re-evaluate before proposing stale data")
    archive = await api.call("GET", "commits/intel", missing=True)
    if (archive["sha"] if archive else None) != metadata["canonical_archive_base"]:
        raise ValueError("Archive advanced; restore and re-evaluate changes before proposing")
    branch = policy()["generated_branch"] + "-" + digest[:12]
    marker = "<!-- horizon-program-update:" + digest + " -->"
    opened = await api.call("GET", "pulls?state=open&base=main&per_page=100")
    for pr in opened:
        if pr.get("head", {}).get("ref") == branch and marker in (pr.get("body") or ""):
            return {"status": "pending_review", "reused": True, "pull_request_url": pr["html_url"], "paths": sorted(files)}
        if pr.get("head", {}).get("ref", "").startswith(policy()["generated_branch"] + "-"):
            return {"status": "conflict_pending_review", "writes": 0, "pull_request_url": pr["html_url"]}
    prior = await api.call("GET", "git/ref/heads/" + branch, missing=True)
    if prior:
        commit = await api.call("GET", "git/commits/" + prior["object"]["sha"])
        if commit.get("message") != "Horizon program data " + digest or [p["sha"] for p in commit.get("parents", [])] != [base["sha"]]:
            raise ValueError("Generated branch was edited or has a stale base; no overwrite attempted")
        for name, content in files.items():
            from urllib.parse import quote
            remote = await api.call("GET", "contents/" + quote(name, safe="/") + "?ref=" + branch)
            if base64.b64decode(remote["content"]) != content.encode():
                raise ValueError("Existing generated branch data differs; no overwrite attempted")
    else:
        entries = []
        for name, content in files.items():
            blob = await api.call("POST", "git/blobs", {"content": content, "encoding": "utf-8"})
            entries.append({"path": name, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = await api.call("POST", "git/trees", {"base_tree": base["commit"]["tree"]["sha"], "tree": entries})
        commit = await api.call("POST", "git/commits", {"message": "Horizon program data " + digest, "tree": tree["sha"], "parents": [base["sha"]]})
        current = await api.call("GET", "commits/main")
        if current["sha"] != base["sha"]:
            raise ValueError("Concurrent base update; generated ref was not created")
        # Create only. Never update an existing ref and never force push.
        await api.call("POST", "git/refs", {"ref": "refs/heads/" + branch, "sha": commit["sha"]})
    body = "Generated public program data only. Review primary evidence and unknowns before approval. No auto-merge.\n\n" + marker + "\n\nSource revision: " + metadata["source_sha"]
    pr = await api.call("POST", "pulls", {"title": "Review weekly program intelligence", "head": branch, "base": "main", "body": body})
    return {"status": "pending_review", "reused": False, "pull_request_url": pr["html_url"], "paths": sorted(files)}
