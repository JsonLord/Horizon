import asyncio
import subprocess

from src.research.publisher import publish, validate
from src.research.reporting import Archive
from src.research.service import ResearchService


def test_bootstrap_and_second_consumer(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )

    async def collect(p, q):
        return [], [{"source": "google_news", "status": "ok", "items": 0}]

    async def job():
        s = ResearchService(tmp_path / "source", collector=collect)
        j = await s.submit({"profile_id": "world/global"})
        await s.wait(j["job_id"])
        return j

    j = asyncio.run(job())
    assert (
        publish(tmp_path / "source", str(remote), dry_run=True)["publication_status"]
        == "dry_run"
    )
    assert (
        publish(tmp_path / "source", str(remote))["publication_status"] == "published"
    )
    reader = tmp_path / "consumer"
    subprocess.run(
        ["git", "clone", "--branch", "intel", str(remote), str(reader)],
        check=True,
        capture_output=True,
    )
    assert Archive(reader).get(j["job_id"])["status"] == "no_new_items"
    assert validate(reader)
    assert (
        publish(tmp_path / "source", str(remote))["publication_status"] == "published"
    )


def test_denied_publication(tmp_path):
    import pytest

    with pytest.raises(RuntimeError):
        publish(tmp_path, str(tmp_path / "nonexistent.git"))


def test_checksum_failure_prevents_push(tmp_path):
    from pathlib import Path
    import pytest
    from src.research.reporting import atomic, dumps
    from src.research.publisher import validate
    import shutil, json

    fixture = Path("tests/fixtures/research")
    report = json.loads((fixture / "report.json").read_text())
    report_root = tmp_path / Path(report["links"]["json"]).parent
    report_root.mkdir(parents=True)
    for name in ["report.json", "report.md", "manifest.json"]:
        shutil.copyfile(fixture / name, report_root / name)
    atomic(
        tmp_path / "intel/manifest.json",
        dumps(
            {
                "schema_version": "1.0",
                "reports": [
                    {
                        "report_id": report["report_id"],
                        "profile_id": report["profile_id"],
                        "status": report["status"],
                        "created_at": report["created_at"],
                        "path": report["links"]["json"],
                    }
                ],
            }
        ),
    )
    assert validate(tmp_path)
    (report_root / "report.md").write_text("tampered")
    with pytest.raises(ValueError, match="Checksum"):
        validate(tmp_path)


def test_push_retries_and_no_force(tmp_path, monkeypatch):
    from src.research import publisher
    import pytest

    original = publisher.git
    pushes = []
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )

    def denied(root, *args, **kw):
        if args[0] == "push":
            pushes.append(args)
            return subprocess.CompletedProcess(args, 1, "", "permission denied")
        return original(root, *args, **kw)

    monkeypatch.setattr(publisher, "git", denied)
    with pytest.raises(RuntimeError, match="denied"):
        publisher.publish(tmp_path / "source", str(remote))
    assert len(pushes) == 3
    assert all("--force" not in args for args in pushes)
