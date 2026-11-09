# Fork workflow inventory — 2026-11-09 UTC

This is a read-only audit of `JsonLord/Horizon` and a proposed optimization on
PR #8. No fork setting, workflow enablement, production data or schedule was
activated. Machine evidence: `WORKFLOW_INVENTORY_BEFORE.json`,
`WORKFLOW_INVENTORY_AFTER.json`, `actions-optimization-observations.json`.

## Availability and execution are distinct

| Source inspected | Exact revision | Workflow YAML files | Job definitions |
|---|---|---:|---:|
| main | c9dcef30a10ffe67b8e399baea5c2a6787c7dfd2 | 4 | 5 |
| feature/program-intelligence-implementation | 44e6e1b1d10d5915c0b1090a1db6f243fbe38dad | 5 | 11 |
| feature/shared-intelligence-filtering | 05ab6d80ffb3f1e7e9a7c3336c2e4c086727b9bb | 6 | 14 |
| feature/technical-radar-fleet before optimization | 5582bdea8e1bc715816e7e881acde8afb5516624 | 8 | 19 |
| proposed optimized working tree | PR #8 additive changes | 8 | 18 |

Counts are YAML definitions, not expanded reusable/matrix jobs and not executed
jobs. No source files were edited on main or the two parent implementation refs.

GitHub lists **seven registered workflows**, each with `state=active`:

| Registered name / ID | Default-branch source available? | Interpretation |
|---|---|---|
| Weekly Horizon Summary / 306842636 | yes, daily-summary.yml | inherited recurring collector |
| Deploy Docs / 306842637 | yes | meaningful existing Pages feature |
| Funding document research and enhancement / 392967451 | no | present only on stacked branches |
| Horizon control validation / 380087226 | no on any of four inspected refs | stale registration; recommend DISABLE after operator review |
| Horizon intelligence archive / 380057296 | yes | current daily world/institution collector |
| Research archive regression / 383881388 | yes | current PR validation |
| pages-build-deployment / 306847616 | GitHub-managed dynamic workflow | Pages service owns definition; not a repository YAML |

Shared filtering, radar fleet and radar worker YAML files exist on implementation
refs but are absent from the current main tree/registered list. Workflow
registration, file availability, repository Actions permissions and the fork
execution gate are separate states. The operator reports `enabled=true` and
`allowed_actions=all`; this integration's permissions read is 403, not independent
confirmation. The fork banner is not evidence of suspension, billing trouble or
an invalid inference key.

Run **42548115014** at 2026-11-09 01:55:48 UTC (02:55:48 Europe/Berlin) did reach
GitHub-hosted runner `GitHub Actions 1000003292` at source `5582bde`. Dependency
setup succeeded; pytest failed; inference and restoration were skipped. Logs
could not be retrieved, so the test failure's cause is unknown. This is actual
past execution evidence, not proof of current fork reactivation or model success.
No new run was dispatched for this audit.

## Per-workflow function, cost and recommendation

All proposed runners are GitHub-hosted `ubuntu-24.04`, Python jobs use 3.11,
`uv sync --frozen` and explicit uv.lock-keyed dependency caching. A cache miss
still downloads/builds dependencies; timing savings have not been measured.

| Workflow | Before triggers / cron UTC | Main? | Function / duplication | Before → proposed jobs | Recommendation |
|---|---|---|---|---:|---|
| daily-summary.yml | manual + Monday 00:17 | yes | Legacy multilingual summarization, Jekyll posts/Pages; overlaps routine news collection but unique presentation | 1 → 2 manual read/publish | MANUAL_ONLY; consolidate recurring collection into existing intel |
| deploy-docs.yml | main push docs/** | yes | Deploy static documentation without collection | 1 → 1 | KEEP; also match own workflow changes, explicit timeout/concurrency |
| horizon-intel.yml | daily 06:23 + manual qualification inputs | yes | World/institutions + guarded qualification paths, independent intel archive | 6 → 6 definitions; daily uses 2 | KEEP; cache dependencies; single-job provider smoke or explicit two-runner durability |
| research-validation.yml | relevant PR + broad main/feature/research/automation pushes | yes, main has narrower old paths | Full offline regression, funding consistency, MCP | 1 → 1 | CONSOLIDATE on relevant PR changes; remove all push duplicates |
| funding-research.yml | manual, feature-branch push, Monday 07:17 gate even when disabled | no | Funding refresh/discovery/proposal | 3 → 2; manual collect, conditional reviewed-main proposal | MANUAL_ONLY until weekly approval; remove push and actual disabled cron |
| shared-filtering.yml | reusable/manual + shared feature push; repeats full pytest | no | Live provider/portable-state acceptance | 2 → 2 definitions, smoke 1, durability 2 | MANUAL_ONLY; remove full-suite duplication and push trigger |
| radar-fleet.yml | manual + 02:13/14:13 daily + Friday 18:00; gate runner always starts | no | Fixed three-radar controller | 2 → 1 definition plus matrix worker expansion | CONSOLIDATE; no gate runner, no disabled cron; daily pilot after approval |
| radar-worker.yml | reusable call only | no | Per-radar collection, always-fresh validation, privileged publisher | 3 → 3 definitions; routine uses 1 read + at most 1 write | KEEP; fresh validation only with durability=true |

The legacy generator in `src/orchestrator.py` writes language-specific
`data/summaries/` and `docs/_posts/`; docs/index.md exposes language post lists and
feeds. Pages API reports `built`, source `gh-pages:/`; its current tree has seven
post path entries and `feed-en.xml` / `feed-zh.xml`. The README demo link points to
the upstream site; traffic and actual fork readership are unknown. Evidence does
not justify deleting these unique outputs. No history or feed was removed.
Both Pages writers retain `keep_files: true`. Legacy generation is now explicit
manual-only with a default-false Pages publication input. Documentation changes
still deploy without another news collection.

## Runner, dependency, API, permission and retention details

| Workflow | Proposed timeout minutes | Installs | Network/model work | Secrets / token | Writes | Artifact retention |
|---|---|---|---|---|---|---|
| legacy briefing | 20 read + 5 publish | one cached runtime sync | legacy sources/model only when manually requested; old config preserved | existing OPENAI_API_KEY, APIFY_TOKEN in read job; built-in job token in writer | only separate reviewed-main Pages job | 7 days |
| docs | 5 | none | Pages action; no model/source collection | built-in job token | gh-pages, preserve historical files | no workflow artifact |
| world intel | 20 collect + 10 publish; qualification jobs 10–15 | cached runtime sync/job | bounded credential-free queries/feeds and optional shared OpenAI inference | global HORIZON_DECISION_* vars and API_KEY secret in collector; built-in token for archive/cache operations | existing main-only intel writer; separate explicit sandbox proposal qualification | archive 7d, cache/qualification 14d |
| PR regression | 10 | one cached dev sync | offline tests/MCP; no production model credential | no model secrets | none | none |
| funding | 15 collect + 10 conditional propose | cached runtime sync/job | official source checks and nominations; no additional inference dependency | built-in token only for proposal | contents + pull-requests only in reviewed-main proposal job | 14d |
| shared qualification | 15 smoke + optional 15 restore | cached runtime sync/job, no repeated pytest | explicit public-fixture six-command/provider/profile matrix; require live success | four global decision settings; token/actions read | none | both proofs/checkpoint 14d |
| radar | 25 collect + optional 10 durability + conditional 10 publish per radar | cached runtime sync/job | up to 3 news queries + 2 registered release endpoints, ETag/hash reuse, bounded shared inference | four global decision settings only in collector; built-in token for read/write GitHub data | only separate main-only per-radar data publisher | 14d when changed or explicit durability |

Before optimization, legacy/docs used ubuntu-latest and had no explicit timeout;
funding's gate also had no timeout (GitHub's normal job ceiling applies). Most
Python jobs repeated full dependency setup with no explicit uv cache configuration.
Shared qualification repeated the full suite already owned by PR CI. Its restored
proof had repository-default retention. All have explicit bounds/cache/retention
where applicable now. The legacy write-capable collection was split into read
and publication jobs. Existing intel/funding publication guards remain intact.

## Estimated execution exposure, not measured savings

These estimates assume successful scheduled events, all three radars, and a write
for every changed collection. Skipped publishers lower the count. Matrix/reusable
jobs are expanded; GitHub-managed Pages builds, manual jobs, PR CI and docs pushes
are excluded from weekly scheduled totals because their frequency is unknown.
The fork banner and lack of new qualification mean these are not measured runs.

| Scenario if reviewed configuration were allowed to execute | Scheduled jobs/week estimate | Configured runner-minute upper bound/week |
|---|---:|---:|
| actual main definitions now: world + inherited weekly briefing | 15 | 570 (legacy lacks explicit timeout) |
| pre-optimization PR #8 merged with radar/funding flags false | 31 | 975, including 15 radar gates and one unbounded funding gate |
| optimized candidate as submitted: world only, disabled crons absent | 14 | 210 |
| approved daily radar pilot + Friday refresh, funding still off | at most 62 (14 world + 8×6 radar) | 1,050 |
| pilot + approved weekly funding collection and proposal | at most 64 | 1,075 |
| optional second daily radar + Friday + weekly funding/proposal | at most 106 | 1,810 |

Prior radar design at full publication: **10 jobs/controller event** (gate +
3×read/validate/write), twice daily plus Friday = 150 radar jobs/week. Optimized
routine design: **at most 6/event**, daily plus Friday = 48 radar jobs/week.
Fresh durability adds three 10-minute jobs only when explicitly selected.
No-change/not-due snapshots suppress both artifact upload and the writer. A due
source refresh can legitimately change its checkpoint timestamps even if no new
technical finding exists; that operational state must persist to avoid duplicate
collection and false freshness claims. It does not create new digest snapshots.
