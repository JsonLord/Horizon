"""Independent ephemeral runner simulations against a durable Git archive."""

import asyncio
import subprocess
import json
import pytest
from src.research.history import restore
from src.research.publisher import publish, git
from src.research.reporting import Archive
from src.research.service import ResearchService
from tests.test_research import fixture_item


def execute(root, history, titles):
    async def collect(p, q):
        return [
            fixture_item(t, "https://ecb.europa.eu/press/" + str(i))
            for i, t in enumerate(titles)
        ], [
            {"source": "google_news", "status": "ok", "items": len(titles)},
            {
                "source": "gdelt",
                "status": "failed",
                "items": 0,
                "error_code": "HTTP_503",
            },
        ]

    async def run():
        s = ResearchService(root, collector=collect)
        s.history = history
        j = await s.submit({"profile_id": "institutions/ecb"})
        await s.wait(j["job_id"])
        return Archive(root).get(j["job_id"])

    return asyncio.run(run())


def test_two_fresh_runners_and_meaningful_change(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    a = tmp_path / "day1"
    b = tmp_path / "day2"
    c = tmp_path / "day3"
    h = restore(a, str(remote))
    assert h["state"] == "bootstrap"
    first = execute(a, h, ["European Central Bank announces decision"])
    commit = publish(a, str(remote))["commit"]
    h = restore(b, str(remote))
    assert h["previous_snapshot_commit"] == commit
    second = execute(b, h, ["European Central Bank announces decision"])
    assert second["status"] == "partial"
    assert second["findings"][0]["change_type"] == "unchanged"
    assert second["findings"][0]["finding_id"] == first["findings"][0]["finding_id"]
    assert second["sources"][0]["source_id"] == first["sources"][0]["source_id"]
    publish(b, str(remote))
    third = execute(
        c,
        restore(c, str(remote)),
        [
            "European Central Bank announces revised decision",
            "European Central Bank announces new research",
        ],
    )
    assert {f["change_type"] for f in third["findings"]} == {"updated", "new"}
    assert third["history"]["previous_report_id"] == second["report_id"]
    publish(c, str(remote))
    consumer = tmp_path / "consumer"
    restore(consumer, str(remote))
    assert (
        Archive(consumer).latest("institutions/ecb")["report_id"] == third["report_id"]
    )


def test_corrupt_history_is_not_bootstrap(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    git(work, "init")
    git(work, "checkout", "--orphan", "intel")
    (work / "intel").mkdir()
    (work / "intel/manifest.json").write_text(
        '{"schema_version":"broken","reports":[]}'
    )
    git(work, "add", ".")
    git(
        work,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "corrupt",
    )
    git(work, "push", str(remote), "intel")
    with pytest.raises(ValueError, match="Malformed"):
        restore(tmp_path / "fresh", str(remote))


def test_failed_and_empty_runs_preserve_last_good(tmp_path):
    root = tmp_path / "archive"
    first = execute(
        root, {"state": "local"}, ["European Central Bank announces decision"]
    )
    empty = execute(root, {"state": "local"}, [])
    assert empty["status"] == "partial"
    assert Archive(root).latest("institutions/ecb")["report_id"] == first["report_id"]
    pointer = json.loads((root / "intel/latest/institutions/ecb.json").read_text())
    assert pointer["report_id"] == first["report_id"]


def test_concurrent_push_preserves_both_reports(tmp_path, monkeypatch):
    from src.research import publisher

    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    a = tmp_path / "a"
    b = tmp_path / "b"
    one = execute(
        a, restore(a, str(remote)), ["European Central Bank announces decision"]
    )
    two = execute(
        b, restore(b, str(remote)), ["European Central Bank announces new research"]
    )
    original = publisher.git
    pushed = False

    def collide(root, *args, **kwargs):
        nonlocal pushed
        if args[0] == "push" and not pushed:
            pushed = True
            publisher.publish(b, str(remote))
        return original(root, *args, **kwargs)

    monkeypatch.setattr(publisher, "git", collide)
    publisher.publish(a, str(remote))
    consumer = tmp_path / "consumer"
    restore(consumer, str(remote))
    assert {r["report_id"] for r in Archive(consumer).list()} == {
        one["report_id"],
        two["report_id"],
    }


def test_institution_primary_and_photo_filter():
    from src.research.analyzers import analyze
    from src.research.profiles import load_profiles

    items = [
        fixture_item("European Central Bank official decision"),
        fixture_item(
            "FILE PHOTO European Central Bank building", "https://example.com/photo"
        ),
        fixture_item(
            "European Central Bank economy monetary policy Europe decision",
            "https://example.com/story",
        ),
    ]
    findings, sources = analyze(load_profiles()["institutions/ecb"], items, None)
    assert len(findings) == 2
    lookup = {s["source_id"]: s for s in sources}
    assert lookup[findings[0]["source_ids"][0]]["source_kind"] == "primary"


def test_workflow_provenance_and_validated_inputs(tmp_path, monkeypatch):
    from argparse import Namespace
    from src.research.cli import run

    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    report = execute(
        tmp_path / "valid",
        {"state": "restored", "previous_snapshot_commit": "b" * 40},
        ["European Central Bank announces decision"],
    )
    assert report["workflow"]["run_id"] == "12345"
    assert report["workflow"]["source_commit"] == "a" * 40
    assert (
        Archive(tmp_path / "valid").index()["reports"][0]["workflow"]["run_id"]
        == "12345"
    )
    for pid, hours in [("world/global", 169), ("unreviewed/target", 24)]:
        with pytest.raises(ValueError):
            asyncio.run(
                run(
                    Namespace(
                        profile_id=pid,
                        lookback_hours=hours,
                        output=str(tmp_path / "unused"),
                    )
                )
            )
    assert not (tmp_path / "unused").exists()
