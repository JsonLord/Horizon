# GitHub Actions MCP controller

Horizon exposes a lightweight local stdio MCP controller, `uv run horizon-mcp`. Production collection/analysis/publication executes on GitHub-hosted Actions runners. No HTTP/MCP server, listening port or external background scheduler is deployed. All 24 existing local/read-only MCP tools remain; the 15 additional tools are listed below. See `examples/mcp-client.json` for client setup and `schemas/mcp-controller-tools.json` for exact input/output schemas.

## Authentication and configuration

The controller uses existing `GH_TOKEN`/`GITHUB_TOKEN` bindings or an existing `gh auth token` login. It never logs or writes token values. Public GitHub/profile/archive reads can run anonymously; GitHub applies its normal rate limits. Dispatch needs Actions write permission. Configuration proposals need repository contents and pull-request write permissions, plus permission to edit workflows (classic PAT workflow scope or appropriate existing fine-grained repository permissions). These are GitHub authorization scopes, not new Horizon credentials.

| Setting | Meaning |
| --- | --- |
| `HORIZON_GITHUB_REPO` | Repository binding, default `JsonLord/Horizon` |
| `HORIZON_GITHUB_DEFAULT_REF` | Default branch, normally `main` |
| `HORIZON_GITHUB_ALLOWED_REFS` | Explicit comma-separated dispatch/read allowlist; default branch is always allowed |
| `HORIZON_CONTROL_STATE_DIR` | Local recovery journal, default ignored `data/control`; use a writable directory |

Only approved profile IDs/lookback/request correlation are accepted for remote research. There is no public arbitrary prompt/source URL execution. URLs/profiles/schedules can be proposed through validated PRs. The client example deliberately contains no credential values; use existing secure environment bindings/login.

Controller calls return `{"ok":true,...}` or `{"ok":false,"error":{"code":...,"message":...,"details":...}}`. Schemas bound hours, IDs, formats and list limits. Permission errors explain required GitHub scopes; conflicts preserve existing work. Requests have bounded HTTP timeouts/retries and 1 MB file/5 MB API-response ceilings. Read retries cover temporary rate/network failures. Mutating dispatch is never blindly retried after an uncertain response.

## Production tools

| Tool | Arguments | Result |
| --- | --- | --- |
| `hz_list_github_profiles` | optional `ref` | Approved profiles/institutions at a pinned source commit |
| `hz_dispatch_research` | `profile_id`; `lookback_hours=48`; optional `request_id`, `ref` | Actual run ID/URL, inputs, ref/status/source commit, or explicit uncorrelated acknowledgement |
| `hz_get_workflow_run` | positive `run_id` | Runner status/conclusion, collect/publish jobs, timestamps, failure steps and separately verified publication |
| `hz_get_workflow_report` | `run_id`; optional `profile_id`; `format=json|markdown|summary` | Exact run/profile report with validated artifact checksums and commit-pinned links |
| `hz_list_workflow_runs` | optional `profile_id`, GitHub `status`; `limit=20` (1–50) | Recent relevant runs; indexed publication is marked unverified until exact retrieval |
| `hz_list_schedules` | none | Default-branch state, pending PRs, next estimates, last observed runs and latest report links |
| `hz_get_schedule` | `schedule_id` | Configuration/activation, pending changes and available history |
| `hz_create_schedule` | `name`, `profile_id`, `cron`; `timezone=UTC`, `lookback_hours=48`, `description=""` | Stable schedule ID, proposed configuration, PR URL and `pending_review` |
| `hz_update_schedule` | `schedule_id`; optional name/profile/cron/timezone/hours/description/enabled | Reviewable update PR |
| `hz_pause_schedule` / `hz_resume_schedule` / `hz_delete_schedule` | `schedule_id` | Reviewable lifecycle PR; history preserved |
| `hz_get_schedule_runs` | `schedule_id`, `limit=20` | Observed run states and report statuses; no fabricated missed-occurrence verdict |
| `hz_propose_research_profile` | complete `profile` object | Validated profile/verified-feed PR |
| `hz_propose_source` | `url`, `name`, `profile_ids`; optional `topic`, `region`, `feed_url` | Verified public RSS/Atom registry assignment PR |

`hz_list_profiles` and `hz_get_profile` continue to describe the local checkout; restart local MCP after local changes. `hz_submit_research` and its local job tools are development helpers with `publication_status=local_only`, and never produce a remote GitHub job handle. Archive read tools/resources remain available.

## Immediate research example

1. `hz_list_github_profiles(ref="main")` and choose `institutions/cern`.
2. `hz_dispatch_research(profile_id="institutions/cern", lookback_hours=48, request_id="cern-investigation-20261010-a")`.
3. Poll `hz_get_workflow_run(run_id=<returned ID>)`.
4. Retrieve `hz_get_workflow_report(run_id=<ID>, profile_id="institutions/cern", format="summary")`.

GitHub's dispatch API returns details when `return_run_details=true` is supported. A positive returned ID is authoritative even if run metadata has not propagated yet (status=submitted, source_commit=null until observed). For 204-only responses, correlation uses the exact request identifier in the workflow run title, profile and ref. It scans bounded recent runs; if none is visible it returns run_id=null and an acknowledgement state. Reuse the same request ID to reconcile; do not invent an ID or immediately dispatch a new request.

The local recovery journal reserves an ID before POST, survives process restarts, and uses exclusive file creation for controllers sharing that journal. Known correlated runs and retained archive requests are reused across separate client environments. Uncertain writes remain reserved until reconciled. Request keys must contain 1–64 ASCII letters/digits/underscore/hyphen and must not contain private questions. Conflict detection rejects reuse with different profile/hours/ref. Searches are bounded to 300 recent workflow runs and 100 retained reports; keep recovery journals if longer deduplication is needed. Separate client hosts can race before GitHub exposes a run; runner-side logical report IDs still prevent duplicate archival output under the serialized workflow. This is not an indefinite global API idempotency guarantee.

A successful runner/publisher step is not proof of a published report. Exact report retrieval pins the archive commit, checks the index/report identity, source commit, snapshot metadata, artifact lengths and SHA-256, and resolves the publication commit from Git history. It never substitutes `latest`. Summary format retains evidence-linked findings/sources, changes, coverage and limitations; it marks truncation above 20 findings.

## Register and manage schedules

Example request:

```json
{
  "name": "ECB weekday intelligence",
  "profile_id": "institutions/ecb",
  "cron": "30 8 * * 1-5",
  "timezone": "Europe/Berlin",
  "lookback_hours": 24,
  "description": "Monitor ECB institutional developments each weekday"
}
```

Pass it to `hz_create_schedule`. The returned `schedule_id` is derived from the name/configuration. Present the PR URL for approval; the schedule remains pending until merge. After approved merge, call `hz_get_schedule` and confirm `activation_state=active`, then observe later native GitHub runs. Do not claim a future scheduled run has occurred.

`hz_update_schedule(schedule_id=..., lookback_hours=72)` proposes a lookback change. Pause/resume/delete likewise propose registry/generated-workflow changes; they do not stop current execution before merge. Deletion removes configuration only, never `intel` history. Existing open PRs are reused for identical proposals; edited branches and changed base revisions produce conflicts rather than force updates. All allowed files are constrained to profiles, source/schedule registries and generated schedule workflows. No merge operation is exposed.

Cron validation supports standard five-field POSIX numeric/month/day syntax, at least 15-minute wall-clock spacing, enabled approved profiles, valid IANA area/city zones or UTC, 1–168 hours lookback, at most 16 enabled schedules and 64 total entries. Calendar expressions without a supported occurrence within eight years are rejected. UTC renders as Etc/UTC. Spring-forward skipped times estimate the next valid local minute; ambiguous autumn times are estimates, and actual GitHub runs are authoritative.

`uv run python -m src.control.schedules` generates a small native `on.schedule` workflow per enabled entry, calling shared `horizon-research.yml`. Different IDs/time zones have distinct files even if their cron expressions match. Paused schedules have no generated workflow. CI verifies generated bytes match the registry. The original single 06:23 UTC batch cron is removed and replaced by exactly five profile-specific entries at the same UTC time (08:23 in Berlin during summer time, 07:23 during winter time).

The shared workflow keeps collection read-only and publisher contents-write with the automatic job token. Its global concurrency group serializes history restore through publication using GitHub's native `queue: max` (up to 100 pending runs); a full queue can still cancel additional runs. This avoids the default concurrency behavior that replaces all but one pending run. GitHub schedules run only from the default branch, can be delayed/dropped, and can be disabled after repository inactivity. Absence of a retained run is therefore `unknown`, not proof of a missed occurrence.

Reports record schedule ID, native run/attempt/workflow/ref/code identity, effective lookback, actual collection timestamps and previous comparison commit/report/hash. Native event payloads do not supply exact scheduled execution time, so that field is null unless supplied by a future supported event timestamp. Occurrence identity is schedule ID plus GitHub run ID; reruns reuse the same report ID. Manual request IDs also yield stable logical report IDs. Existing reports are immutable, last-good pointers survive empty/failing collection, and different schedules retain separate snapshots while comparing against the profile's validated last-good evidence.

## Validation and current activation boundary

Run:

```sh
uv sync --frozen --extra dev
uv run --extra dev pytest
uv run python scripts/check_mcp.py
uv run python scripts/check_research_mcp.py
uv run python scripts/check_control.py
uv run python scripts/check_workflows.py --actionlint /path/to/actionlint
```

The wrapper enables all actionlint checks except its exact unknown-concurrency-queue warning: actionlint 1.7.12 understands native timezone but predates documented `queue: max`. The wrapper independently rejects any other queue value/location. Live GitHub execution validates the workflow with GitHub's own parser.

The integration PR includes PR #2's source registry without merging or overwriting it. Until this PR is merged, `main` still has the original daily batch and lacks the controller/schedule registries. Production default-branch schedule mutations return CONTROLLER_NOT_ACTIVATED rather than create workflows that reference a missing shared implementation. A temporary integration ref may be explicitly allowlisted for authorized live smoke testing; it does not activate native schedules on the default branch.
