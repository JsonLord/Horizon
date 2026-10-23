"""Read-only runner and verified staging-artifact restoration; no GitHub writes."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

import httpx

from ..branches import resolve
from ..history import restore
from ..profiles import ROOT
from ..publisher import git, validate
from ..reporting import Archive, atomic, dumps, markdown
from ..service import ResearchService
from .models import Dataset
from .render import render_dataset, render_report


async def verify_previous(run_id, source_sha, repository, client=None):
    if not re.fullmatch(r"[1-9][0-9]{0,19}", str(run_id)):
        raise ValueError("Invalid previous qualification run ID")
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        response = await client.get(f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", headers=headers)
        response.raise_for_status()
        run = response.json()
        if run.get("repository", {}).get("full_name") != repository or run.get("head_sha") != source_sha or run.get("conclusion") != "success" or run.get("event") != "workflow_dispatch" or run.get("path", "").split("@")[0] not in {".github/workflows/horizon-intel.yml", ".github/workflows/program-intelligence.yml"}:
            raise ValueError("Previous artifact must come from successful same-code same-repository qualification")
        return run
    finally:
        if own:
            await client.aclose()


def overlay_staging(root, prior, source_sha, expected_run_id):
    root, prior = Path(root), Path(prior)
    validate(prior)
    meta_path = prior / "execution.json"
    if meta_path.stat().st_size > 50000:
        raise ValueError("Oversized staging metadata")
    metadata = json.loads(meta_path.read_text())
    if metadata.get("source_sha") != source_sha or metadata.get("workflow_run_id") != str(expected_run_id) or metadata.get("read_only") is not True or metadata.get("profile_id") != "programs/incubators":
        raise ValueError("Staging provenance mismatch")
    if metadata.get("archive_index_sha256") != hashlib.sha256((prior / "intel/manifest.json").read_bytes()).hexdigest():
        raise ValueError("Staging index checksum mismatch")
    current, previous = Archive(root), Archive(prior)
    rows = {r["report_id"]: r for r in current.list(limit=100)}
    for row in previous.list("programs/incubators", limit=100):
        folder = Path(row["path"]).parent
        if row["report_id"] in rows and (root / rows[row["report_id"]]["path"]).read_bytes() != (prior / row["path"]).read_bytes():
            raise ValueError("Immutable staging report collision")
        (root / folder).mkdir(parents=True, exist_ok=True)
        for name in ("report.json", "report.md", "manifest.json"):
            shutil.copy2(prior / folder / name, root / folder / name)
        rows[row["report_id"]] = row
    atomic(root / "intel/manifest.json", dumps({"schema_version": "1.0", "reports": sorted(rows.values(), key=lambda r: r["created_at"], reverse=True)[:100]}))
    report = current.latest("programs/incubators")
    if report:
        atomic(root / "intel/latest/programs/incubators.json", dumps(report))
        atomic(root / "intel/latest/programs/incubators.md", markdown(report))
    validate(root)
    return {"previous_qualification_run_id": str(expected_run_id), "previous_qualification_index_sha256": metadata["archive_index_sha256"], "comparison_source": "verified_actions_artifact"}


def write_generated(root, report):
    dataset = Dataset.model_validate(report["statistics"]["programs"])
    date = dataset.observed_at[:10]
    files = {
        "Incubator and Programs.md": render_dataset(dataset),
        "data/programs/incubators.json": dumps(dataset.model_dump(mode="json")),
        f"reports/programs/{date}.md": render_report(report),
        f"reports/programs/{date}.json": dumps(report),
    }
    for name, content in files.items():
        atomic(Path(root) / "generated" / name, content)
    return files


async def run(root="data/program-qualification", previous_dir=None):
    repository = os.environ["GITHUB_REPOSITORY"]
    source_sha = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    selected = await resolve(os.environ["RESEARCH_REF"], repository)
    if source_sha != selected["sha"]:
        raise ValueError("Checked-out source must equal the approved immutable revision")
    history = restore(root, "https://github.com/" + repository + ".git")
    previous_id = os.getenv("PREVIOUS_RUN_ID")
    if previous_id:
        await verify_previous(previous_id, source_sha, repository)
        if not previous_dir:
            raise ValueError("Verified previous-run artifact is required")
        history.update(overlay_staging(root, previous_dir, source_sha, previous_id))
    os.environ["HORIZON_SOURCE_SHA"] = source_sha
    service = ResearchService(root)
    service.history = history
    run_id = os.environ["GITHUB_RUN_ID"]
    logical_id = hashlib.sha256((repository + "|programs/incubators|" + run_id).encode()).hexdigest()[:32]
    try:
        report = service.archive.get(logical_id)
        reused = True
    except KeyError:
        job = await service.submit({"profile_id": "programs/incubators", "depth": 20}, requested_by="github_actions")
        done = await service.wait(job["job_id"])
        if not done["report_id"]:
            raise RuntimeError("Program watch failed before producing validated artifacts")
        report = service.archive.get(done["report_id"])
        reused = False
    validate(root)
    generated = write_generated(root, report)
    index_hash = hashlib.sha256((Path(root) / "intel/manifest.json").read_bytes()).hexdigest()
    metadata = {"read_only": True, "profile_id": "programs/incubators", "source_sha": source_sha, "selected_ref": selected["ref"],
                "workflow_run_id": run_id, "workflow_ref": os.getenv("GITHUB_WORKFLOW_REF"), "report_id": report["report_id"],
                "archive_index_sha256": index_hash, "canonical_archive_base": history["previous_snapshot_commit"], "history": history,
                "reused": reused, "generated_paths": sorted(generated), "report_sha256": hashlib.sha256((Path(root) / report["links"]["json"]).read_bytes()).hexdigest()}
    atomic(Path(root) / "execution.json", dumps(metadata))
    return report, metadata
