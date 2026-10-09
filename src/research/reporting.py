"""Versioned, bounded atomic artifacts and checksummed manifests."""

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    source_id: str
    location: str
    snippet: str = Field(max_length=500)


class Geography(BaseModel):
    event_region: str = "unknown"
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    original_url: str = Field(max_length=2048)
    canonical_url: str = Field(max_length=2048)
    publisher: str = Field(max_length=300)
    source_kind: Literal["primary", "secondary", "social", "unknown"]
    published_at: str | None
    source_seen_at: str | None = None
    fetched_at: str
    origin_collector: str
    source_country: str = "unknown"
    language: str = "unknown"
    search_query: str | None = None
    profile_id: str
    institution_id: str | None = None
    content_fingerprint: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    event_id: str
    summary: str = Field(max_length=500)
    classification: str
    institutions: list[str]
    regions: list[str]
    topics: list[str]
    source_ids: list[str] = Field(min_length=1, max_length=200)
    importance: float | None = None
    profile_relevance: float
    ranking_explanation: str
    verification: Literal[
        "unverified",
        "single_primary_source",
        "multiple_secondary_sources",
        "single_secondary_source",
    ]
    corroboration: int
    published_at: str | None
    observed_at: str
    evidence: list[Evidence]
    limitations: list[str]
    provenance: str
    geography: Geography
    change_type: Literal["new", "updated", "contradicted", "resolved", "unchanged"]
    model_selected: bool | None = None


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    report_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    run_id: str
    profile_id: str = Field(pattern=r"^(world|institutions|examples)/[a-z0-9-]{1,64}$")
    question: str = Field(max_length=1000)
    created_at: str
    time_window: dict
    status: Literal["complete", "partial", "failed", "no_new_items"]
    model_used: str | None
    analysis_mode: str
    coverage: dict
    statistics: dict
    findings: list[Finding] = Field(max_length=200)
    sources: list[Source] = Field(max_length=3200)
    limitations: list[str]
    changes: list[dict]
    errors: list[dict]
    links: dict


class Manifest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    report_id: str
    profile_id: str
    generated_at: str
    status: str
    snapshot_id: str
    commit: str | None = None
    artifacts: list[dict]


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = data if isinstance(data, bytes) else data.encode()
    if len(data) > 1_000_000:
        raise ValueError("Artifact exceeds 1 MB")
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def markdown(report):
    lines = [
        f"# Horizon: {report['profile_id']}",
        f"Status: {report['status']} | Analysis: {report['analysis_mode']}",
        f"Observed: {report['created_at']}",
        "",
        "Search-region coverage (not event geography): "
        + ", ".join(report["coverage"]["regions"]),
        "",
    ]
    sources = {s["source_id"]: s for s in report["sources"]}
    for f in report["findings"]:
        # Escape HTML and markdown control syntax from untrusted titles.
        import html

        title = (
            html.escape(f["summary"])
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("#", "\\#")
        )
        lines += [f"- {title} ({f['verification']}; {f['change_type']})"]
        for sid in f["source_ids"]:
            source = sources[sid]
            lines += [
                f"  - <{source['canonical_url']}> — {html.escape(str(source['publisher']))}"
            ]
    lines += ["", "## Limitations"] + ["- " + x for x in report["limitations"]]
    return "\n".join(lines) + "\n"


def make_report(
    profile, run_id, question, findings, sources, metrics, model, mode, warnings
):
    now = datetime.now(UTC)
    failures = [m for m in metrics if m["status"] != "ok"]
    status = "partial" if failures else "complete" if findings else "no_new_items"
    if metrics and all(m["status"] == "failed" for m in metrics):
        status = "failed"
    regions = sorted({r for f in findings for r in f["regions"] if r != "unknown"})
    report = Report(
        report_id=run_id,
        run_id=run_id,
        profile_id=profile.profile_id,
        question=question,
        created_at=now.isoformat(),
        time_window={
            "since": (now - timedelta(hours=profile.lookback_hours)).isoformat(),
            "until": now.isoformat(),
        },
        status=status,
        model_used=model,
        analysis_mode=mode,
        coverage={
            "regions": regions,
            "missing_regions": sorted(set(profile.regions) - set(regions)),
            "basis": "search query region; event geography unknown",
        },
        statistics={
            "items": len(findings),
            "sources": len(sources),
            "collectors": metrics,
        },
        findings=findings,
        sources=sources,
        limitations=[
            "Bounded queries do not provide exhaustive global coverage.",
            "GDELT seen time is an observation timestamp, not verified publication time.",
            "Contradiction/resolution labels require explicit source wording and review; no automatic truth adjudication.",
        ]
        + warnings,
        changes=[
            {
                "finding_id": f["finding_id"],
                "type": f["change_type"],
                "institution_ids": f["institutions"],
                "observed_at": now.isoformat(),
            }
            for f in findings
            if f["change_type"] != "unchanged"
        ],
        errors=[{"code": "SOURCE_INCOMPLETE", "source": m["source"]} for m in failures],
        links={},
    ).model_dump()
    return report


class Archive:
    def __init__(self, root):
        self.root = Path(root)

    def index(self):
        p = self.root / "intel/manifest.json"
        return (
            json.loads(p.read_text())
            if p.exists()
            else {"schema_version": "1.0", "reports": []}
        )

    def list(self, profile_id=None, limit=20, offset=0):
        rows = self.index()["reports"]
        return [r for r in rows if not profile_id or r["profile_id"] == profile_id][
            max(0, offset) : max(0, offset) + min(100, max(1, limit))
        ]

    def get(self, report_id):
        if not re.fullmatch(r"[a-f0-9]{32}", report_id):
            raise ValueError("Invalid report ID")
        row = next(
            (r for r in self.list(limit=100) if r["report_id"] == report_id), None
        )
        if not row:
            raise KeyError("Report not found")
        path = (self.root / row["path"]).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Unsafe archive path")
        return Report.model_validate_json(path.read_text()).model_dump()

    def latest(self, profile_id):
        rows = self.list(profile_id, limit=100)
        for row in rows:
            if row["status"] in ("complete", "partial"):
                return self.get(row["report_id"])
        return None

    def write(self, report):
        report = Report.model_validate(report).model_dump()
        ids = {s["source_id"] for s in report["sources"]}
        if any(not set(f["source_ids"]) <= ids for f in report["findings"]):
            raise ValueError("Dangling evidence")
        for s in report["sources"]:
            from .analyzers import canonical

            if canonical(s["canonical_url"]) != s["canonical_url"]:
                raise ValueError("Unsafe source URL")
        # Bound the serialized public artifact, preserving complete retained evidence sets.
        trimmed = False
        while len(dumps(report).encode()) > 900_000 and report["findings"]:
            trimmed = True
            report["findings"].pop()
            used = {sid for f in report["findings"] for sid in f["source_ids"]}
            report["sources"] = [s for s in report["sources"] if s["source_id"] in used]
            kept = {f["finding_id"] for f in report["findings"]}
            report["changes"] = [
                c for c in report["changes"] if c["finding_id"] in kept
            ]
        if trimmed:
            report["limitations"].append(
                "Findings truncated to the 1 MB artifact ceiling."
            )
            report["status"] = "partial"
            report["statistics"].update(
                items=len(report["findings"]), sources=len(report["sources"])
            )
        date = datetime.fromisoformat(report["created_at"]).strftime("%Y/%m/%d")
        group = (
            "world" if report["profile_id"] == "world/global" else report["profile_id"]
        )
        base = f"intel/reports/{group}/{date}/{report['report_id']}"
        report["links"] = {
            "json": base + "/report.json",
            "markdown": base + "/report.md",
        }
        artifacts = []
        for filename, content, mime in [
            ("report.json", dumps(report), "application/json"),
            ("report.md", markdown(report), "text/markdown"),
        ]:
            data = content.encode()
            path = base + "/" + filename
            atomic(self.root / path, data)
            artifacts.append(
                {
                    "path": path,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                    "content_type": mime,
                }
            )
        manifest = Manifest(
            report_id=report["report_id"],
            profile_id=report["profile_id"],
            generated_at=report["created_at"],
            status=report["status"],
            snapshot_id=hashlib.sha256(dumps(artifacts).encode()).hexdigest(),
            artifacts=artifacts,
        ).model_dump()
        atomic(self.root / base / "manifest.json", dumps(manifest))
        index = self.index()
        index["reports"] = [
            r for r in index["reports"] if r["report_id"] != report["report_id"]
        ]
        index["reports"].insert(
            0,
            {
                "report_id": report["report_id"],
                "profile_id": report["profile_id"],
                "status": report["status"],
                "created_at": report["created_at"],
                "path": base + "/report.json",
            },
        )
        removed = index["reports"][100:]
        index["reports"] = index["reports"][:100]
        atomic(self.root / "intel/manifest.json", dumps(index))
        if report["status"] in ("complete", "partial"):
            latest = (
                "world"
                if report["profile_id"] == "world/global"
                else report["profile_id"]
            )
            for ext, content in [("json", dumps(report)), ("md", markdown(report))]:
                atomic(self.root / f"intel/latest/{latest}.{ext}", content)
        eventfile = self.root / f"intel/events/{date}/events.jsonl"
        events = eventfile.read_text().splitlines() if eventfile.exists() else []
        events = [
            e
            for e in events
            if e.strip() and json.loads(e).get("report_id") != report["report_id"]
        ]
        events += [
            json.dumps(dict(c, report_id=report["report_id"]))
            for c in report["changes"]
        ]
        atomic(eventfile, "\n".join(events[-1000:]) + "\n")
        import shutil

        for row in removed:
            folder = (self.root / row["path"]).parent
            if folder.is_relative_to(self.root / "intel/reports"):
                shutil.rmtree(folder, ignore_errors=True)
        for old_event in sorted((self.root / "intel/events").rglob("events.jsonl"))[
            :-30
        ]:
            old_event.unlink()
        return manifest
