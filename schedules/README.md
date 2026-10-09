# Research schedule registry

Edit `registry.json` through a reviewed PR or the `hz_create_schedule`, `hz_update_schedule`, `hz_pause_schedule`, `hz_resume_schedule`, and `hz_delete_schedule` MCP tools. The tools return a PR and pending state; they do not merge. See [the controller reference](../docs/mcp-controller.md) for authentication, all arguments and activation checks.

Each entry has a unique `schedule_id`, descriptive `name`, approved enabled `profile_id`, five-field `cron`, IANA `timezone`, `lookback_hours` (1–168), `enabled`, and optional `description`. The [JSON Schema](../schemas/schedule-registry.schema.json) defines structural constraints; Python validation additionally checks cron spacing, calendar feasibility, time zones, profile assignments and limits (16 enabled, 64 total). Minimum interval is 15 minutes. A weekday Berlin example is `30 8 * * 1-5` with `Europe/Berlin` and 24 hours lookback.

After edits, run:

```sh
uv run python -m src.control.schedules
uv run python scripts/check_control.py
```

Commit the registry together with generated `.github/workflows/horizon-sched-*.yml` files. Generation removes owned files for paused/deleted entries and never changes archive history. CI rejects drift. Every enabled entry calls `horizon-research.yml`; do not add separate collection implementations or a polling daemon.

The five initial entries replace the original 06:23 UTC batch cron with one native daily workflow per previously scheduled profile. The manual dispatcher has no cron, preventing duplicate daily execution after merge. Different schedules may share a cron expression while retaining distinct IDs and time zones. UTC is rendered as `Etc/UTC` for GitHub validation.

Only merged default-branch workflows execute native schedules. Confirm registry/workflow agreement and GitHub workflow activation with `hz_get_schedule`; an open PR is pending. GitHub delivery is best effort, including DST transitions and inactivity suspension. Displayed future times are estimates; observed runs are authoritative. Reports preserve schedule/run identity and actual collection timestamps, and leave an unavailable nominal occurrence timestamp null.
