import asyncio
import subprocess
from argparse import Namespace

import pytest

from src.control.runner import inputs
from src.research import cli
from src.research.reporting import Archive
from src.research.service import ResearchService
from tests.test_research import fixture_item


def test_runtime_schedule_inputs_are_exact_and_bounded(monkeypatch):
    monkeypatch.setenv("PROFILE_ID", "institutions/ecb")
    monkeypatch.setenv("LOOKBACK_HOURS", "48")
    monkeypatch.setenv("SCHEDULE_ID", "daily-ecb")
    monkeypatch.setenv("REQUEST_ID", "")
    monkeypatch.setenv("ARCHIVE_REPO", "JsonLord/Horizon")
    assert inputs().profile_id == "institutions/ecb"
    monkeypatch.setenv("LOOKBACK_HOURS", "24")
    with pytest.raises(ValueError):
        inputs()
    monkeypatch.setenv("LOOKBACK_HOURS", "48")
    monkeypatch.setenv("REQUEST_ID", "untrusted-command$")
    with pytest.raises(ValueError):
        inputs()
    monkeypatch.setenv("REQUEST_ID", "id")
    with pytest.raises(ValueError):
        inputs()


def test_independent_runner_retry_reuses_exact_publication(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    calls = []

    async def collect(p, q):
        calls.append(p.profile_id)
        return [fixture_item()], [{"source": "rss", "status": "ok", "items": 1}]

    monkeypatch.setattr(
        cli, "ResearchService", lambda root: ResearchService(root, collector=collect)
    )
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "GITHUB_RUN_ID": "901",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REPOSITORY": "JsonLord/Horizon",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_REF_NAME": "main",
        "HORIZON_REQUEST_ID": "manual-id",
        "HORIZON_SCHEDULE_ID": "",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "outputs"))

    def execute(day):
        return asyncio.run(
            cli.run(
                Namespace(
                    profile_id="institutions/ecb",
                    lookback_hours=48,
                    output=str(tmp_path / day),
                    remote=str(remote),
                    publish=True,
                )
            )
        )

    assert execute("day1") == 0
    one = Archive(tmp_path / "day1").latest("institutions/ecb")
    monkeypatch.setenv("GITHUB_RUN_ID", "902")
    assert execute("retry-other-run") == 0
    assert calls == ["institutions/ecb"]
    assert len(Archive(tmp_path / "retry-other-run").list()) == 1
    assert (
        Archive(tmp_path / "retry-other-run").latest("institutions/ecb")["workflow"][
            "run_id"
        ]
        == "901"
    )
    monkeypatch.setenv("HORIZON_REQUEST_ID", "")
    monkeypatch.setenv("HORIZON_SCHEDULE_ID", "daily-ecb")
    monkeypatch.setenv("GITHUB_RUN_ID", "903")
    assert execute("schedule1") == 0
    scheduled = Archive(tmp_path / "schedule1").latest("institutions/ecb")
    assert scheduled["report_id"] != one["report_id"]
    assert scheduled["schedule"]["occurrence_key"] == "daily-ecb:903"
    assert scheduled["schedule"]["scheduled_execution_time"] is None
    assert scheduled["history"]["previous_report_id"] == one["report_id"]
    assert scheduled["findings"][0]["change_type"] == "unchanged"
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    assert execute("schedule-retry") == 0
    assert len(calls) == 2
    assert len(Archive(tmp_path / "schedule-retry").list()) == 2
    assert "new_reports=0" in (tmp_path / "outputs").read_text()
