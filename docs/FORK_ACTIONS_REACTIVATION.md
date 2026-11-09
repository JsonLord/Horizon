# Safe fork Actions reactivation

Prepared 2026-11-09 for `JsonLord/Horizon`, draft PR #8 on
`feature/technical-radar-fleet`. This document is an operator runbook, not
permission to enable Actions, merge, activate schedules or publish production.
No such changes were made while preparing it.

## Interpret the current evidence

The fork banner says "Workflows on this fork have been disabled." The operator
reports the repository permission API says `enabled=true, allowed_actions=all`.
Those permissions allow Actions in principle; they do not prove the additional
fork execution gate has been lifted. This integration receives 403 from that
permission endpoint. Registered workflows with `state=active` also do not prove
runnable jobs. Do not infer billing, account suspension or a provider-key error.

Read `WORKFLOW_INVENTORY.md` and both inventory JSON files. A past real run,
42548115014, reached a hosted runner and failed pytest before model inference.
Its logs were unavailable to this integration. That result neither certifies
live inference nor establishes the fork's present activation state. No new
workflow was dispatched during optimization.

## Workflows to retain

- **KEEP:** horizon-intel.yml, daily world/institution research with its existing
  main-only intel publisher. Its five scheduled profiles and daily 06:23 UTC
  cadence remain unchanged.
- **KEEP:** research-validation.yml, relevant pull-request changes only. It owns
  the full regression suite, MCP, funding checks and schedule-policy validation.
  Obsolete feature/research/automation push triggers are removed.
- **KEEP:** deploy-docs.yml, relevant main documentation/workflow changes only.
  No collection or dependency installation; five-minute bound; existing Pages
  history preserved.
- **MANUAL_ONLY:** daily-summary.yml, legacy multilingual Jekyll briefing. Its
  weekly recurring collector is removed. Manual collection has a read-only token;
  Pages publication is a separate reviewed-main job and default-false input.
  Do not delete historical posts or language feeds.
- **MANUAL_ONLY initially:** shared-filtering.yml, read-only live provider smoke
  and optional fresh-runner restoration. It no longer repeats pytest or triggers
  on feature pushes. Both artifact sets retain 14 days.
- **MANUAL_ONLY initially:** radar-fleet.yml and reusable radar-worker.yml. Three
  independent radars remain; no actual cron exists while disabled.
- **MANUAL_ONLY initially:** funding-research.yml. No feature push or cron while
  disabled. Weekly scheduling and data-PR publication require separate approval.
- **DISABLE after operator review:** stale registered "Horizon control validation"
  (380087226), absent from main and all inspected implementation refs. Do not
  recreate it just because its registration is active.
- **KEEP if Pages remains in use:** GitHub-managed pages-build-deployment. Its
  definition is service-managed, not a YAML file to edit. Pages currently reports
  `built` from `gh-pages:/`; actual reader traffic was not verified.

The current main branch still contains inherited schedules until reviewed changes
are merged. Pushing PR #8 does not alter main. If a safe merge has not been
approved, an operator must keep the fork disabled or explicitly disable unwanted
registered workflows before restoring execution. Do not push older stacked
branches with their old automation and assume the optimized trigger files apply
to those refs.

## Expected execution and budgets

All values below are **configuration estimates**, not measured savings or bills.
PR, manual, documentation and GitHub-managed Pages build frequency is excluded.
All scheduled jobs are GitHub-hosted; there are no servers, ports or self-hosted
runners.

| Reviewed configuration | Scheduled jobs/week (upper estimate) | Sum of job timeout bounds/week |
|---|---:|---:|
| Candidate as submitted: daily world; radar/funding absent | 14 | 210 runner-minutes |
| Daily radar pilot + Friday, world retained | 62 | 1,050 runner-minutes |
| Above + weekly funding collect and approved proposal | 64 | 1,075 runner-minutes |
| Optional second radar run + Friday + funding/proposal | 106 | 1,810 runner-minutes |

The current main definitions would schedule about 15 jobs/week. Unoptimized PR #8
with disabled subsystem flags would schedule about 31, because its gate jobs
still start. Optimized candidate has 8 workflow files / 18 job definitions,
compared with 8 / 19 on the previous PR #8 head. Routine radar expansion drops
from 10 to at most 6 jobs/controller event; cadence drops from 15 to 8 events/week.
Actual skipped publishers reduce these numbers. They are not measured execution.

Routine per radar: one 25-minute read-only collection/validation job and at most
one 10-minute write job. A `durability=true` acceptance adds a separate 10-minute
read job per radar. A provider smoke is one 15-minute job; full provider durability
can use two (30 total). PR CI is 10 minutes; docs deployment 5; manual legacy
briefing up to 20 + 5. Optional manual funding collect/proposal is 15 + 10.
These are runner-minute sums, not wall-clock duration; concurrent jobs add up.
GitHub-managed Pages builds have their own service-controlled limits and are
additional exposure, not bounded by these YAML jobs.

Per radar per collection: **36 HTTP model-attempt reservations, 200,000 token
reservations**, covering shared filtering, technical-learning and distillation
support together. Cache hits do not spend these budgets. Explicit prices and
`max_cost_usd` may be configured per radar in `config/radar/registry.json`; an
explicit dollar cap without a price blocks inference. No price/model endpoint
is invented. Usage/cost can be unknown after failures/retries; do not treat null
as free inference or infer an actual invoice from a configured-price estimate.

With three radars, daily pilot plus Friday has a conservative upper budget of
**864 attempts and 4.8 million reserved tokens/week**. Optional twice-daily plus
Friday: **1,620 attempts / 9 million reserved tokens/week**. These are ceilings,
not expected use. The existing world job's five profiles each retain their own
shared caps (currently at most 36 attempts / 120,000 reserved tokens/profile/run):
a loose upper bound of 1,260 attempts / 4.2 million reserved tokens/week. Actual
request bounds are usually lower because token caps bind first. Model-unavailable
execution uses deterministic review without calling a provider.

Dedicated public-fixture qualification is separate from routine budgets. Its
three policy caps plus 19 direct three-attempt decision cells give a loose upper
bound of 165 HTTP attempts per smoke runner, or 330 if two runners must retry
all uncached failures. It is manual and must not run on every push. The existing
legacy manual CLI uses its own source/model configuration; it is not part of the
new shared budget and is deliberately excluded from routine schedules.

## Schedule configuration after explicit approval

The reviewed plan is `config/actions-schedules.json`. The candidate currently
contains only the existing world cron. Radar/funding disabled flags agree with
**absent YAML schedule events**; there are no scheduled no-op gate runners.

For a separately approved deployment change:

1. Review the desired subsystem, provider readiness, budgets and source quality.
2. Set the matching enabled flag in the schedule plan and registry/policy. Radar
   also needs its separate publication flag for actual branch writes; funding
   data-PR publication remains a separately reviewed flag.
3. Render locally with `uv run python -m scripts.actions_schedule --render`.
   Review and commit the YAML diff. CI's `--check` rejects drift and flag mismatch.
4. Merge only after authorization. Scheduled events run from the default branch;
   do not schedule branch-supplied executable code.

Pilot: 02:13 UTC daily. Optional second: 14:13 UTC, enabled in both schedule plan
and radar registry. Friday digest: **18:00 UTC**, fixed previous-Friday 18:00
inclusive to current-Friday 18:00 exclusive. Weekly funding: Monday 07:17 UTC
only after approval. UTC does not shift for daylight saving; Friday 18:00 UTC is
19:00 Europe/Berlin during November 2026.

Independent due timestamps align to intended collection slots so a delayed start
does not suppress tomorrow's run. A missing Friday window triggers one bounded
final source refresh on the Friday event even when ordinary collection is not
due; repeated already-published Friday events do not repeat that refresh. Daily
runs recover missed weeks from retained evidence oldest-first. They never invent
missing historical coverage or silently replace a newer pointer with an older one.

## Operator-controlled fork reactivation

After authorization and review of **actual main**:

1. Save the workflow inventory, main revision and current workflow states.
2. Disable unwanted inherited/stale workflows first using the Actions UI or
   authorized `gh workflow disable <id> --repo JsonLord/Horizon`. In particular,
   do not leave the old weekly summary scheduled on unoptimized main. If the fork
   UI prevents this preparation, keep execution disabled until reviewed main is
   safe. This task did not run any disable/enable command.
3. Confirm main has no radar/funding `schedule` blocks while their flags are false;
   keep full legacy generation and qualification manual-only. Inspect the actual
   registered source files, not only `state=active`.
4. Use the fork's Actions banner/Enable workflows control to lift the fork gate.
   `enabled=true` from the permissions endpoint is not a substitute for this step.
   Do not broaden `GITHUB_TOKEN` defaults; job-level write permissions suffice.
5. Run one explicitly authorized read-only smoke and inspect actual job steps,
   artifacts, provider decisions and runner evidence. A dispatch acknowledgement
   alone is insufficient. Do not dispatch normal world publication as a smoke.
6. Inspect the next scheduled run list: only the intended daily world route should
   execute until additional subsystem approval. Check for inherited Monday
   briefing, funding gate or radar gate runs; none belong in the optimized policy.

Do not enable or merge anything solely to make a qualification error disappear.

## Read-only smoke and recovery

Once authorized execution is available, the already registered entry point can
select the reviewed PR #8 implementation:

```sh
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/technical-radar-fleet \
  -f shared_filtering_qualification=true \
  -f shared_filtering_durability=false
```

Other qualification flags must remain false. This skips ordinary collection and
production publishing. On reviewed main with the new workflow registered,
`gh workflow run shared-filtering.yml --repo JsonLord/Horizon --ref main
-f durability=false` is also read-only.

The approved provider now uses explicit `systemone` mode with the verified
`alias-clef` request/response identity. Apply/check the five global variables with
`scripts/configure-production-decisions.sh`; the existing
`HORIZON_DECISION_API_KEY` secret is unchanged. See
[production configuration status](PRODUCTION_DECISION_CONFIGURATION.md).
Do not print their values. Inspect all 18 command/profile cells,
`all_commands_live_validated`, actual reported model/usage and funding hard-gate
results. `--require-live` makes an incomplete/fallback-only qualification fail,
while retaining safe proof artifacts. Passing offline schema tests is not live
model or multilingual quality acceptance.

For dedicated fresh-runner acceptance, select `shared_filtering_durability=true`,
or radar-fleet's `durability=true` for three isolated radar snapshot checks. The
routine radar path already validates its sealed data before upload; the separate
writer rechecks source SHA, file hashes, data schemas and branch/path allowlists.
The optional fresh runner tests portability additionally; no write token or model
credential is needed for snapshot validation. Periodic durability may be scheduled
only after separate review; no periodic acceptance cron is enabled here.

Collection proofs/logs expose each radar's runtime, attempts, known token usage,
usage completeness, cost basis, cache/source changes and backlog. Source
checkpoints retain attributed bounded references, original languages, hashes and
ETags, never raw pages. Documentation-only code revisions can reuse valid model
decisions; changed analysis/policy/provider invalidates them. Candidate/source
failures have separate bounded backoff and do not block other radars. No-change
snapshots skip uploads and publication; due-time/freshness changes are meaningful
checkpoint writes even without new findings.

## Rollback

If activation behaves unexpectedly, the authorized operator should disable the
specific controller (or keep the fork globally disabled), retain logs/artifacts
and stop further dispatches. Revert the approved schedule/flag change through a
reviewed commit; render/check policy again so disabled cron blocks disappear.
Do not restore the inherited weekly collector as an automatic rollback, force
push research refs, delete historical digests or clear last-good pointers. Data
branches are independent from `intel` and retain readable pinned history. Revert
code separately through normal review if required. This task performed no
reactivation, merge, schedule enablement, production publish or rollback action.

Compatibility verification during delivery: an independent remote Python 3.11
quoting fix was retained in PR #8. The pre-fix provider fails local compilation
under a real 3.11 interpreter; full optimized regressions now pass under 3.11
and 3.12. Keep this fix when reviewing/merging. Hosted provider readiness still
requires the separate authorized smoke; local tests do not prove it.

Live follow-up: after the owner re-enabled execution, authorized runs confirmed
CI/funding/radar execution and independent shared/radar checkpoint recovery.
Provider requests currently return HTTP 404, so inference is not qualified.
Use ACTIONS_LIVE_VALIDATION_2026-11-09.md for actual run IDs and evidence. This
does not activate the proposed radar/funding schedules or authorize publication.
