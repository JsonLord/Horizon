"""Commit-pinned, checksummed research retrieval by exact workflow identity."""

import hashlib
import json
import re
from pathlib import PurePosixPath

from src.research.reporting import Manifest, Report, dumps
from .github import ControlError


class PublishedArchive:
    def __init__(self, github):
        self.github = github

    async def index(self):
        head = await self.github.get("commits/intel", missing=True)
        if head is None:
            return None, []
        sha = head["sha"]
        raw = await self.github.file("intel/manifest.json", sha)
        index = json.loads(raw)
        if (
            index.get("schema_version") != "1.0"
            or not isinstance(index.get("reports"), list)
            or len(index["reports"]) > 100
        ):
            raise ControlError(
                "ARCHIVE_INVALID",
                "Archive index is malformed or exceeds retention bounds.",
            )
        rows = index["reports"]
        if len({r["report_id"] for r in rows}) != len(rows):
            raise ControlError("ARCHIVE_INVALID", "Duplicate archive report IDs.")
        for row in rows:
            if (
                not re.fullmatch(r"[a-f0-9]{32}", row["report_id"])
                or not row["path"].startswith("intel/reports/")
                or ".." in row["path"].split("/")
            ):
                raise ControlError(
                    "ARCHIVE_INVALID", "Unsafe report identity/path in archive index."
                )
        return sha, rows

    async def report(self, run_id, profile_id=None, format="json"):
        if format not in ("json", "markdown", "summary"):
            raise ValueError("Format must be json, markdown or summary")
        sha, rows = await self.index()
        matches = [
            r
            for r in rows
            if str(r.get("workflow", {}).get("run_id")) == str(run_id)
            and (not profile_id or r["profile_id"] == profile_id)
        ]
        if not matches:
            raise ControlError(
                "REPORT_NOT_PUBLISHED",
                "No matching report for this workflow run is retained in intel. It may be pending, failed, skipped or outside archive retention; latest is not substituted.",
            )
        if len(matches) > 1:
            raise ControlError(
                "PROFILE_REQUIRED",
                "This run published multiple profiles; select profile_id.",
                {"profiles": [r["profile_id"] for r in matches]},
            )
        row = matches[0]
        parent = str(PurePosixPath(row["path"]).parent)
        raw = await self.github.file(row["path"], sha)
        report = Report.model_validate_json(raw).model_dump()
        if (
            str(report["workflow"].get("run_id")) != str(run_id)
            or any(
                report[k] != row[k]
                for k in ("report_id", "profile_id", "status", "created_at")
            )
            or report["links"]["json"] != row["path"]
        ):
            raise ControlError(
                "ARCHIVE_IDENTITY_MISMATCH",
                "Report identity does not match the requested workflow and index.",
            )
        manifest = Manifest.model_validate_json(
            await self.github.file(parent + "/manifest.json", sha)
        )
        if (
            manifest.report_id != report["report_id"]
            or manifest.profile_id != report["profile_id"]
            or manifest.status != report["status"]
            or manifest.snapshot_id
            != hashlib.sha256(dumps(manifest.artifacts).encode()).hexdigest()
        ):
            raise ControlError(
                "ARCHIVE_IDENTITY_MISMATCH",
                "Snapshot manifest identity/checksum differs.",
            )
        if (manifest.workflow and manifest.workflow != report["workflow"]) or (
            manifest.schedule and manifest.schedule != report["schedule"]
        ):
            raise ControlError(
                "ARCHIVE_IDENTITY_MISMATCH",
                "Snapshot provenance differs from the report.",
            )
        source_ids = {s["source_id"] for s in report["sources"]}
        if any(not set(f["source_ids"]) <= source_ids for f in report["findings"]):
            raise ControlError(
                "ARCHIVE_INVALID", "Report has dangling source evidence."
            )
        if len(manifest.artifacts) != 2 or {a["path"] for a in manifest.artifacts} != {
            row["path"],
            parent + "/report.md",
        }:
            raise ControlError(
                "ARCHIVE_INVALID",
                "Snapshot must contain its JSON and Markdown artifacts.",
            )
        artifacts = {row["path"]: raw}
        for artifact in manifest.artifacts:
            data = artifacts.get(artifact["path"])
            if data is None:
                data = await self.github.file(artifact["path"], sha)
                artifacts[artifact["path"]] = data
            if (
                len(data) != artifact["bytes"]
                or hashlib.sha256(data).hexdigest() != artifact["sha256"]
            ):
                raise ControlError(
                    "ARCHIVE_CHECKSUM_MISMATCH",
                    "Published artifact failed checksum/length validation.",
                )
        # Reports are immutable; this API returns the commit that introduced the
        # versioned JSON, rather than pretending a commit can contain its own SHA.
        commits = await self.github.get(
            "commits", {"sha": sha, "path": row["path"], "per_page": 1}
        )
        publication_commit = commits[0]["sha"] if commits else None
        links = {
            "json": f"https://raw.githubusercontent.com/{self.github.repo}/{sha}/{row['path']}",
            "markdown": f"https://raw.githubusercontent.com/{self.github.repo}/{sha}/{parent}/report.md",
            "manifest": f"https://raw.githubusercontent.com/{self.github.repo}/{sha}/{parent}/manifest.json",
            "github": f"https://github.com/{self.github.repo}/blob/{sha}/{row['path']}",
        }
        value = report
        if format == "markdown":
            value = artifacts[parent + "/report.md"].decode()
        elif format == "summary":
            findings = report["findings"][:20]
            ids = {sid for f in findings for sid in f["source_ids"]}
            value = {
                k: report[k]
                for k in (
                    "report_id",
                    "profile_id",
                    "status",
                    "statistics",
                    "coverage",
                    "limitations",
                    "changes",
                    "history",
                    "workflow",
                )
            }
            value.update(
                findings=findings,
                sources=[s for s in report["sources"] if s["source_id"] in ids],
                truncated=len(report["findings"]) > 20,
            )
        return {
            "run_id": int(run_id),
            "profile_id": report["profile_id"],
            "report_id": report["report_id"],
            "source_commit": report["workflow"].get("source_commit"),
            "research_status": report["status"],
            "publication_status": "verified",
            "archive_commit": sha,
            "publication_commit": publication_commit,
            "links": links,
            "format": format,
            "report": value,
        }
