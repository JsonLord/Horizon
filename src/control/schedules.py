"""Validated schedule configuration and reproducible native Actions workflows."""

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from pydantic import Field, field_validator, model_validator

from src.research.profiles import ROOT, Short, Strict, load_profiles
from src.research.reporting import atomic

REGISTRY_PATH = "schedules/registry.json"
WORKFLOW_PREFIX = ".github/workflows/horizon-sched-"
SHARED_WORKFLOW = ".github/workflows/horizon-research.yml"
MAX_ACTIVE = 16
MIN_INTERVAL_MINUTES = 15


def cron_fields(expression):
    fields = expression.upper().split()
    if len(fields) != 5 or len(expression) > 120:
        raise ValueError("Use a standard five-field cron expression")
    names = [
        {},
        {},
        {},
        {
            n: i + 1
            for i, n in enumerate(
                "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
            )
        },
        {n: i for i, n in enumerate("SUN MON TUE WED THU FRI SAT".split())},
    ]
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    values = []
    for field, aliases, (low, high) in zip(fields, names, bounds):
        for name, number in aliases.items():
            field = field.replace(name, str(number))
        if not re.fullmatch(r"[0-9*,/\-]+", field):
            raise ValueError(
                "Unsupported cron syntax; use numeric fields or standard month/day names"
            )
        selected = set()
        for part in field.split(","):
            pieces = part.split("/")
            if len(pieces) > 2:
                raise ValueError("Invalid cron step")
            step = int(pieces[1]) if len(pieces) == 2 else 1
            if not 1 <= step <= high - low + 1:
                raise ValueError("Invalid cron step")
            base = pieces[0]
            if base == "*":
                first, last = low, high
            elif "-" in base:
                first, last = map(int, base.split("-"))
            else:
                first = int(base)
                last = high if len(pieces) == 2 else first
            if not low <= first <= last <= high:
                raise ValueError("Cron value outside its field bounds")
            selected.update(range(first, last + 1, step))
        values.append(selected)
    if not croniter.is_valid(expression):
        raise ValueError("Invalid cron expression")
    # Conservatively bound all daily clock slots, including across midnight.
    slots = sorted(h * 60 + m for h in values[1] for m in values[0])
    gaps = [b - a for a, b in zip(slots, slots[1:] + [slots[0] + 1440])]
    if min(gaps) < MIN_INTERVAL_MINUTES:
        raise ValueError("Horizon schedules must be at least 15 minutes apart")
    try:
        croniter(
            expression, datetime(2024, 1, 1), max_years_between_matches=8
        ).get_next(datetime)
    except Exception as exc:
        raise ValueError(
            "Cron has no supported calendar occurrence within eight years"
        ) from exc
    return " ".join(fields)


class Schedule(Strict):
    schedule_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    name: Short
    profile_id: str = Field(pattern=r"^(world|institutions|examples)/[a-z0-9-]{1,64}$")
    cron: str = Field(max_length=120)
    timezone: str = Field(default="UTC", max_length=80)
    lookback_hours: int = Field(default=48, ge=1, le=168)
    enabled: bool = True
    description: str = Field(default="", max_length=1000)

    @field_validator("cron")
    @classmethod
    def cron_expression(cls, value):
        return cron_fields(value)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        if value != "UTC" and (
            "/" not in value or value.startswith(("posix/", "right/"))
        ):
            raise ValueError("Use an IANA Area/City timezone or UTC")
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(
                "Use a valid IANA timezone, such as Europe/Berlin"
            ) from exc
        return value


class ScheduleRegistry(Strict):
    schema_version: Literal["1.0"] = "1.0"
    schedules: list[Schedule] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def limits(self):
        if len({s.schedule_id for s in self.schedules}) != len(self.schedules):
            raise ValueError("Duplicate schedule IDs")
        if sum(s.enabled for s in self.schedules) > MAX_ACTIVE:
            raise ValueError("At most 16 schedules may be active")
        return self

    def validate_profiles(self, profiles):
        if any(s.profile_id not in profiles for s in self.schedules):
            raise ValueError("Schedules require existing enabled research profiles")
        return self


def next_expected(schedule, now=None):
    """An estimate, not a guarantee of delivery by GitHub's best-effort scheduler.

    Resolve spring gaps at the first valid wall minute (GitHub's documented
    policy), and expose real UTC offsets across DST. Ambiguous fall times may
    have two possible instants; actual execution is established only by runs.
    """
    now = now or datetime.now(UTC)
    zone = ZoneInfo(schedule.timezone)
    start = now.astimezone(zone).replace(tzinfo=None) - timedelta(days=1)
    iterator = croniter(schedule.cron, start, max_years_between_matches=8)
    options = []
    for _ in range(256):
        wall = iterator.get_next(datetime)
        valid = []
        for offset in range(181):
            candidate = wall + timedelta(minutes=offset)
            for fold in (0, 1):
                instant = candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                if instant.astimezone(zone).replace(tzinfo=None) == candidate:
                    valid.append(instant)
            if valid:
                break
        options += [v for v in valid if v > now]
        if options:
            return min(options).isoformat()
    raise ValueError("Unable to estimate next execution within supported bounds")


def workflow_path(schedule_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", schedule_id):
        raise ValueError("Invalid schedule ID")
    return f"{WORKFLOW_PREFIX}{schedule_id}.yml"


def render_workflows(registry):
    result = {}
    for schedule in sorted(registry.schedules, key=lambda s: s.schedule_id):
        if not schedule.enabled:
            continue
        # JSON strings are valid YAML scalars; user values never become expressions.
        scalar = lambda value: json.dumps(value, ensure_ascii=True)
        result[workflow_path(schedule.schedule_id)] = (
            "# Generated by python -m src.control.schedules; edit schedules/registry.json.\n"
            f"name: {scalar('Horizon schedule ' + schedule.schedule_id)}\n"
            f"run-name: {scalar('Horizon schedule ' + schedule.schedule_id + ' [' + schedule.profile_id + ']')}\n"
            "on:\n  schedule:\n"
            f"    - cron: {scalar(schedule.cron)}\n      timezone: {scalar('Etc/UTC' if schedule.timezone == 'UTC' else schedule.timezone)}\n"
            "permissions:\n  contents: read\n"
            "jobs:\n  research:\n    permissions:\n      contents: write\n"
            f"    uses: ./{SHARED_WORKFLOW}\n    with:\n"
            f"      schedule_id: {scalar(schedule.schedule_id)}\n"
            f"      profile_id: {scalar(schedule.profile_id)}\n"
            f"      lookback_hours: {scalar(str(schedule.lookback_hours))}\n"
        )
    return result


def synchronize(root=ROOT, check=False):
    root = Path(root)
    registry = ScheduleRegistry.model_validate_json((root / REGISTRY_PATH).read_text())
    registry.validate_profiles(
        load_profiles(root / "profiles", root / "sources/registry.json")
    )
    expected = render_workflows(registry)
    actual = {
        str(p.relative_to(root)): p.read_text()
        for p in (root / ".github/workflows").glob("horizon-sched-*.yml")
    }
    if check:
        if expected != actual:
            raise ValueError(
                "Generated schedule workflows differ; run python -m src.control.schedules"
            )
    else:
        for path, content in expected.items():
            atomic(root / path, content)
        for path in set(actual) - set(expected):
            (root / path).unlink()
    return {"valid": True, "active_schedules": len(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(synchronize(check=args.check)))


if __name__ == "__main__":
    main()
