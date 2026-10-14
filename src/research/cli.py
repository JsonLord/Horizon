"""Shared scheduled research execution; no shell interpolation from inputs."""

import argparse
import asyncio
import os

from .publisher import publish, validate
from .service import ResearchService


async def run(args):
    from .history import restore
    from .profiles import load_profiles

    profiles = load_profiles()
    if args.profile_id and args.profile_id not in profiles:
        raise ValueError("Only repository-reviewed profiles are allowed")
    if args.lookback_hours is not None and not 1 <= args.lookback_hours <= 168:
        raise ValueError("Lookback must be 1–168 hours")
    history = restore(
        args.output, getattr(args, "remote", "https://github.com/JsonLord/Horizon.git")
    )
    service = ResearchService(args.output)
    service.history = history
    ids = (
        [args.profile_id]
        if args.profile_id
        else [
            "world/global",
            "institutions/ecb",
            "institutions/who",
            "institutions/cern",
            "institutions/helmholtz",
        ]
    )
    failed = False
    new_reports = 0
    for pid in ids:
        if os.getenv("GITHUB_ACTIONS") == "true" and os.getenv("GITHUB_RUN_ID"):
            import hashlib

            logical = os.getenv("HORIZON_REQUEST_ID") or os.environ["GITHUB_RUN_ID"]
            identity = "|".join(
                (
                    os.getenv("GITHUB_REPOSITORY", ""),
                    os.getenv("HORIZON_SCHEDULE_ID", ""),
                    logical,
                    pid,
                )
            )
            rid = hashlib.sha256(identity.encode()).hexdigest()[:32]
            try:
                previous = service.archive.get(rid)
            except KeyError:
                previous = None
            if previous:
                hours = args.lookback_hours or profiles[pid].lookback_hours
                if previous["workflow"].get("effective_lookback_hours") != hours:
                    raise ValueError(
                        "Logical request already published with a different lookback"
                    )
                if os.getenv("HORIZON_REQUEST_ID") and previous["workflow"].get(
                    "ref"
                ) != os.getenv("GITHUB_REF_NAME"):
                    raise ValueError(
                        "Logical request already published from a different ref"
                    )
                print(
                    pid,
                    "already_published",
                    previous["report_id"],
                    "original_run",
                    previous["workflow"].get("run_id"),
                )
                continue
        job = await service.submit(
            {
                "profile_id": pid,
                "lookback_hours": args.lookback_hours,
                "depth": profiles[pid].max_items,
            },
            requested_by="github_actions"
            if os.getenv("GITHUB_ACTIONS") == "true"
            else "local_cli",
        )
        done = await service.wait(job["job_id"])
        print(pid, done["status"], done["report_id"])
        failed |= done["status"] == "failed"
        new_reports += bool(done["report_id"])
    validate(args.output)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"new_reports={new_reports}\n")
    if args.publish:
        print(publish(args.output, args.remote))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id")
    parser.add_argument("--lookback-hours", type=int)
    parser.add_argument("--output", default="data/research")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--remote", default="https://github.com/JsonLord/Horizon.git")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
