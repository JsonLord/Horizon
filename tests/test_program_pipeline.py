import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from src.research.profiles import load_profiles
from src.research.programs.fetch import Page
from src.research.programs.models import Dataset
from src.research.programs.pipeline import build_report
from src.research.programs.review import allowed_path, bundle
from src.research.programs.runner import overlay_staging, write_generated
from src.research.publisher import publish, validate
from src.research.reporting import Archive, atomic, dumps


class FakeFetcher:
    def __init__(self, failed=False):
        self.requests = 0
        self.failed = failed

    async def fetch(self, url, observed_at):
        self.requests += 1
        if self.failed:
            return Page(url, url, observed_at, error="HTTP_503")
        title = url.split('/')[2] + " software AI startup accelerator"
        html = f'<h1>{title}</h1><p>Applications are open</p><p>Application deadline: 2027-01-31</p><a href="/apply">Apply</a><p>Eligibility: software founders and entrepreneurs.</p><p>Equity-free grant funding, mentoring, networking, workspace and inclusive UX innovation. No fee.</p>'
        return Page(url, url, observed_at, html)


async def search(profile):
    return [], [{"source": "google_news", "status": "ok", "items": 0}]


def create_report(root, rid="a" * 32, previous=None, failed=False):
    report = asyncio.run(build_report(load_profiles()["programs/incubators"], rid, previous, collector=search, fetcher=FakeFetcher(failed), contract={}))
    report["workflow"] = {"source_commit": "b" * 40}
    Archive(root).write(report)
    return Archive(root).get(rid)


def execution(root, report, run="101"):
    metadata = {"read_only": True, "source_sha": "b" * 40, "selected_ref": "main", "profile_id": "programs/incubators", "workflow_run_id": run, "report_id": report["report_id"],
                "archive_index_sha256": hashlib.sha256((root / "intel/manifest.json").read_bytes()).hexdigest(), "canonical_archive_base": None,
                "report_sha256": hashlib.sha256((root / report["links"]["json"]).read_bytes()).hexdigest()}
    atomic(root / "execution.json", dumps(metadata))
    return metadata


def test_common_archive_render_schema_and_dry_run_publisher(tmp_path):
    report = create_report(tmp_path)
    dataset = Dataset.model_validate(report["statistics"]["programs"])
    assert len(dataset.programs) >= 5
    assert {p.name for p in dataset.programs if p.legacy} == {"Kilo Health", "Kaospilots"}
    assert all(p.fit.probability_relevant is None for p in dataset.programs)
    assert validate(tmp_path)
    execution(tmp_path, report)
    files = write_generated(tmp_path, report)
    assert len(files) == 4 and all(allowed_path(path) for path in files)
    assert "2025-02-01" in files["Incubator and Programs.md"]
    assert "historical" in files["Incubator and Programs.md"]
    assert "scores" in files["Incubator and Programs.md"].lower()
    # Real publisher against a bare Git remote, with no push/publication.
    import subprocess
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    assert publish(tmp_path, str(remote), dry_run=True)["publication_status"] == "dry_run"
    with pytest.raises(ValueError, match="explicit authorization"):
        publish(tmp_path, str(remote))


def test_fresh_state_restoration_change_tracking_and_last_good(tmp_path):
    first_root, second_root = tmp_path / "first", tmp_path / "second"
    first = create_report(first_root)
    execution(first_root, first)
    proof = overlay_staging(second_root, first_root, "b" * 40, "101")
    assert proof["comparison_source"] == "verified_actions_artifact"
    old = Archive(second_root).latest("programs/incubators")
    second = create_report(second_root, "c" * 32, old)
    assert second["statistics"]["programs"]["previous_dataset_sha256"] == hashlib.sha256(dumps(first["statistics"]["programs"]).encode()).hexdigest()
    assert any(c["type"] == "unchanged" for p in second["statistics"]["programs"]["programs"] for c in p["material_changes"])
    useful = Archive(second_root).latest("programs/incubators")["report_id"]
    failed = create_report(second_root, "d" * 32, second, failed=True)
    assert not failed["findings"]
    assert Archive(second_root).latest("programs/incubators")["report_id"] == useful
    pointer = json.loads((second_root / "intel/latest/programs/incubators.json").read_text())
    assert pointer["report_id"] == useful
    assert validate(second_root)


def test_artifact_restrictions_and_untrusted_markdown_are_recomputed(tmp_path):
    report = create_report(tmp_path)
    execution(tmp_path, report)
    atomic(tmp_path / "generated/.github/workflows/pwn.yml", "untrusted executable")
    metadata, files, digest, meaningful = bundle(tmp_path)
    assert all(allowed_path(p) for p in files)
    assert not any(".github" in p for p in files)
    assert meaningful and len(digest) == 64
    assert not allowed_path("../README.md") and not allowed_path("src/main.py")
    assert not allowed_path("reports/programs/../../scripts/x.py")


def test_staging_rejects_wrong_code_run_and_tampering(tmp_path):
    root = tmp_path / "source"
    report = create_report(root)
    execution(root, report)
    with pytest.raises(ValueError, match="provenance"):
        overlay_staging(tmp_path / "bad", root, "0" * 40, "101")
    path = root / report["links"]["json"]
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="Checksum"):
        overlay_staging(tmp_path / "bad2", root, "b" * 40, "101")
