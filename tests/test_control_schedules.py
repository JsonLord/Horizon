from datetime import UTC, datetime
from pathlib import Path

import pytest
from src.control.schedules import (
    Schedule,
    ScheduleRegistry,
    next_expected,
    render_workflows,
    synchronize,
)
from src.research.profiles import load_profiles


def schedule(**kwargs):
    return Schedule(
        schedule_id="ecb-weekday",
        name="ECB weekday",
        profile_id="institutions/ecb",
        cron="30 8 * * 1-5",
        timezone="Europe/Berlin",
        lookback_hours=24,
        **kwargs,
    )


@pytest.mark.parametrize(
    "cron",
    ["30 8 * * 1-5", "15 7 * * MON", "0 */6 * * *", "0 0 1 JAN *", "0,30 * * * *"],
)
def test_valid_cron(cron):
    assert Schedule.model_validate({**schedule().model_dump(), "cron": cron}).cron


@pytest.mark.parametrize(
    "cron",
    [
        "* * * * *",
        "*/5 * * * *",
        "0 25 * * *",
        "0 0 * *",
        "@daily",
        "0 0 31 2 *",
        "0 0 ? * *",
        "0 0 L * *",
        "0 0 * * 9",
        "60 0 * * *",
        "0 0 * * 1#2",
    ],
)
def test_invalid_or_unsupported_cron(cron):
    with pytest.raises(ValueError):
        Schedule.model_validate({**schedule().model_dump(), "cron": cron})


def test_invalid_zones_profiles_and_duplicates():
    with pytest.raises(ValueError):
        Schedule.model_validate({**schedule().model_dump(), "timezone": "Mars/City"})
    with pytest.raises(ValueError):
        ScheduleRegistry(schedules=[schedule(), schedule()])
    with pytest.raises(ValueError):
        ScheduleRegistry(schedules=[schedule()]).validate_profiles({})
    with pytest.raises(ValueError):
        Schedule.model_validate({**schedule().model_dump(), "lookback_hours": 169})


def test_next_expected_berlin_daylight_changes():
    s = schedule()
    assert (
        next_expected(s, datetime(2026, 3, 27, 12, tzinfo=UTC))
        == "2026-03-30T06:30:00+00:00"
    )
    assert (
        next_expected(s, datetime(2026, 10, 23, 12, tzinfo=UTC))
        == "2026-10-26T07:30:00+00:00"
    )
    gap = Schedule.model_validate({**s.model_dump(), "cron": "30 2 * * *"})
    assert (
        next_expected(gap, datetime(2026, 3, 28, 12, tzinfo=UTC))
        == "2026-03-29T01:00:00+00:00"
    )


def test_same_cron_different_zones_have_distinct_workflows():
    one = schedule()
    two = Schedule.model_validate(
        {**one.model_dump(), "schedule_id": "ecb-utc", "timezone": "UTC"}
    )
    files = render_workflows(ScheduleRegistry(schedules=[one, two]))
    assert len(files) == 2
    assert "Europe/Berlin" in files[".github/workflows/horizon-sched-ecb-weekday.yml"]
    assert "Etc/UTC" in files[".github/workflows/horizon-sched-ecb-utc.yml"]
    assert (
        len(
            render_workflows(
                ScheduleRegistry(
                    schedules=[one.model_copy(update={"enabled": False}), two]
                )
            )
        )
        == 1
    )


def test_generated_workflows_match_checked_in_registry():
    assert synchronize(check=True)["active_schedules"] == 5
    registry = ScheduleRegistry.model_validate_json(
        Path("schedules/registry.json").read_text()
    )
    assert {s.profile_id for s in registry.schedules} == {
        "world/global",
        "institutions/ecb",
        "institutions/who",
        "institutions/cern",
        "institutions/helmholtz",
    }
    registry.validate_profiles(load_profiles())
    assert "schedule:" not in Path(".github/workflows/horizon-intel.yml").read_text()


def test_registry_active_bound():
    with pytest.raises(ValueError):
        ScheduleRegistry(
            schedules=[
                schedule().model_copy(update={"schedule_id": f"schedule-{i}"})
                for i in range(17)
            ]
        )
