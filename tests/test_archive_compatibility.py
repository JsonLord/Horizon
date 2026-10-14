"""An older deployed runner must restore archives written by newer runners."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.research.history import restore
from src.research.publisher import publish, validate
from src.research.reporting import Archive, Report, atomic, dumps


def mixed_archive(root):
    fixture = Path(__file__).parent / "fixtures/research"
    legacy = json.loads((fixture / "report.json").read_text())
    modern = copy.deepcopy(legacy)
    modern.update(
        report_id="f" * 32,
        run_id="f" * 32,
        created_at="2026-10-10T08:30:00+00:00",
        schedule={
            "schedule_id": "world-mornings",
            "scheduled_execution_time": None,
            "collection_started_at": "2026-10-10T08:29:00+00:00",
        },
        workflow={"run_id": "38000215123", "schedule_id": "world-mornings"},
    )
    modern["links"] = {
        kind: f"intel/reports/world/2026/10/10/{modern['report_id']}/report.{suffix}"
        for kind, suffix in (("json", "json"), ("markdown", "md"))
    }
    rows = []
    for report in (modern, legacy):
        folder = Path(report["links"]["json"]).parent
        manifest = json.loads((fixture / "manifest.json").read_text())
        artifacts = []
        for name, data, mime in (
            ("report.json", dumps(report).encode(), "application/json"),
            ("report.md", (fixture / "report.md").read_bytes(), "text/markdown"),
        ):
            atomic(root / folder / name, data)
            artifacts.append(
                {
                    "path": str(folder / name),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "content_type": mime,
                }
            )
        manifest.update(
            report_id=report["report_id"],
            profile_id=report["profile_id"],
            generated_at=report["created_at"],
            artifacts=artifacts,
            snapshot_id=hashlib.sha256(dumps(artifacts).encode()).hexdigest(),
        )
        if "schedule" in report:
            manifest.update(schedule=report["schedule"], workflow=report["workflow"])
        atomic(root / folder / "manifest.json", dumps(manifest))
        rows.append(
            {
                **{
                    key: report[key]
                    for key in ("report_id", "profile_id", "created_at", "status")
                },
                "path": report["links"]["json"],
            }
        )
    atomic(
        root / "intel/manifest.json", dumps({"schema_version": "1.0", "reports": rows})
    )
    return legacy, modern


def test_restore_mixed_provenance_archive_without_rewriting_evidence(tmp_path):
    source = tmp_path / "source"
    legacy, modern = mixed_archive(source)
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    publication = publish(source, str(remote))
    consumer = tmp_path / "fresh-runner"
    history = restore(consumer, str(remote))
    assert history == {
        "state": "restored",
        "previous_snapshot_commit": publication["commit"],
    }
    assert validate(consumer)
    archive = Archive(consumer)
    assert archive.get(modern["report_id"])["schedule"] == modern["schedule"]
    assert archive.get(legacy["report_id"])["schedule"] == {}
    assert archive.latest(legacy["profile_id"])["report_id"] == modern["report_id"]
    for report in (legacy, modern):
        folder = Path(report["links"]["json"]).parent
        for name in ("report.json", "report.md", "manifest.json"):
            assert (consumer / folder / name).read_bytes() == (
                source / folder / name
            ).read_bytes()


@pytest.mark.parametrize("artifact", ["report.json", "report.md"])
def test_provenance_compatibility_keeps_checksum_validation(tmp_path, artifact):
    _, modern = mixed_archive(tmp_path)
    assert validate(tmp_path)
    path = tmp_path / Path(modern["links"]["json"]).with_name(artifact)
    with path.open("ab") as output:
        output.write(b" ")
    with pytest.raises(ValueError, match="Checksum"):
        validate(tmp_path)


def test_compatibility_does_not_accept_arbitrary_report_fields():
    data = json.loads(
        (Path(__file__).parent / "fixtures/research/report.json").read_text()
    )
    data["unexpected_execution_input"] = "must remain forbidden"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Report.model_validate(data)
