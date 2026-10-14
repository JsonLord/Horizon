"""Validate fixed workflow inputs and run the existing research implementation."""

import asyncio
import os
import re
from argparse import Namespace

from src.research.cli import run
from src.research.profiles import ROOT, load_profiles
from .schedules import REGISTRY_PATH, ScheduleRegistry


def inputs():
    profile = os.getenv("PROFILE_ID") or None
    hours = int(os.getenv("LOOKBACK_HOURS", "48"))
    request_id = os.getenv("REQUEST_ID", "")
    schedule_id = os.getenv("SCHEDULE_ID", "")
    if not 1 <= hours <= 168:
        raise ValueError("Lookback must be 1–168 hours")
    if request_id and not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", request_id):
        raise ValueError("Invalid request_id")
    profiles = load_profiles()
    if profile and profile not in profiles:
        raise ValueError("Profile is absent or disabled")
    if schedule_id:
        registry = ScheduleRegistry.model_validate_json(
            (ROOT / REGISTRY_PATH).read_text()
        ).validate_profiles(profiles)
        schedule = next(
            (s for s in registry.schedules if s.schedule_id == schedule_id), None
        )
        if (
            not schedule
            or not schedule.enabled
            or (schedule.profile_id, schedule.lookback_hours) != (profile, hours)
        ):
            raise ValueError(
                "Schedule inputs must exactly match its enabled approved registry entry"
            )
        if request_id:
            raise ValueError(
                "Scheduled runs use native run occurrence identity, not manual request IDs"
            )
    os.environ["HORIZON_REQUEST_ID"] = request_id
    os.environ["HORIZON_SCHEDULE_ID"] = schedule_id
    return Namespace(
        profile_id=profile,
        lookback_hours=hours,
        output="data/research",
        publish=False,
        remote="https://github.com/" + os.environ["ARCHIVE_REPO"] + ".git",
    )


def main():
    raise SystemExit(asyncio.run(run(inputs())))


if __name__ == "__main__":
    main()
