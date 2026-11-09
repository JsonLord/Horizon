# Fork Actions optimization acceptance — 2026-11-09

Implementation commit: `9332c2d717ba9d2ba3c6ab7e3de31a4be2050ccb` on
`feature/technical-radar-fleet`, additive to draft PR #8. No main/parent branch,
Actions setting, production archive or remote radar data was changed.

| Phase | Result | Evidence |
|---|---|---|
| Audit | PASS | All four current stacked refs and all seven registered workflows inspected; inventory records main availability, triggers, jobs, runners, timeouts, installs, APIs, secrets, writes and retention. |
| Inherited automation | PASS locally | Weekly legacy collection becomes manual; multilingual posts/feeds retained; docs changes still deploy; duplicate push tests/collection and repeated qualification pytest removed. Remote enable/disable states unchanged. |
| Radar optimization | PASS locally | Content/ETag source snapshots, semantic model cache, per-radar due/backoff/backlog, hard shared/technical budgets, runtime/token/cost telemetry, sealed handoffs, no-change suppression. Actual local source checks and not-due repeats pass. |
| Schedule policy | PASS locally | Existing daily world cron unchanged; disabled radar/funding cron absent; renderer/check tests cover daily pilot, optional second slot, Friday and mismatch rejection. No gate-only scheduled jobs. |
| Reactivation preparation | PASS | FORK_ACTIONS_REACTIVATION.md contains workflow policy, estimates, bounds, owner-controlled activation, smoke, verification and rollback. No activation performed. |
| Hosted readiness | UNVERIFIED | No new hosted run dispatched for this task. Past 42548115014 failed pytest before inference; its cause is unknown because logs were unavailable. No model-key, billing or account diagnosis inferred. |

## Verification

- `uv run --extra dev pytest`: **499 passed in 5.00s**.
- Twelve new optimization tests cover disabled/approved cron transitions,
  optional fresh runner, separate publisher permissions, conditional 304 reuse,
  failed-source isolation, hash corruption rejection, zero calls when not due,
  unchanged checkpoint/handoff suppression, request/token/cost caps, excess
  reported usage stopping further calls, semantic cache reuse across operational
  tuning and late-Friday/daily cadence semantics. Existing tests additionally
  confirm source/policy/SHA-bound recovery and original EN/DE/FR evidence.
- Both MCP smokes pass: legacy config/sources/metrics and real stdio discovery
  with **24 tools / 15 profiles**.
- Funding deterministic check passes. Funding acceptance: **43 local links**,
  three ELIGIBILITY_UNKNOWN records, four pending nominations, zero new pending;
  authored seed hash stays
  `5a509f585d1e05eb996ab13bdff83064ea708f08db03ea4bfd79c22fe0d5ee65`.
- Funding starting-point check: valid, 100 seed candidates, no queue refresh needed.
- `uv run python -m scripts.actions_schedule --check`: pass.
- `/tmp/shared-tools/actionlint -color=false`: pass, no diagnostics.
- Schema regeneration and `git diff --check`: pass.
- All eight candidate workflow hashes match WORKFLOW_INVENTORY_AFTER.json.
- Actual local collection through the optimized adapter: **five source routes
  per radar**, 8 training / 30 RAG / 30 agent-control-plane findings retained.
  Immediate repeat for each returned **not_due**, zero model requests, identical
  sealed data snapshot. Proofs: `docs/actions-optimization-local/*.json`.
  These are local credential-free checks, not hosted model or publication proof.

Routine collection and optional fresh validation have read-only job tokens.
Separate publisher still verifies source revision, file hashes, schema, approved
radar branch and data paths before a non-force update. No Paperclip push call,
webhook, consumer client, credential or secret was introduced. The existing intel
and funding publication/eligibility boundaries remain in place.

## Estimated before/after exposure

Eight workflow YAML files remain; job definitions **19 → 18**. This is distinct
from seven remote registrations (including stale and GitHub-managed entries).
Actual main still has four YAML files until an authorized merge.

Unoptimized PR #8, if merged with disabled subsystem flags, would schedule about
**31 jobs/week**, including gate-only runs. Optimized candidate as submitted:
**14 world jobs/week**. Current main separately estimates **15/week** including
its inherited briefing. Routine expanded radar jobs/controller event **10 → at
most 6**; daily pilot plus Friday **48 radar jobs/week**, rather than 150 under
the prior twice-daily/fresh-validation design. These are estimates, not measured
savings. Full scenario tables and timeout/budget assumptions are in the inventory
and reactivation runbook; no production schedules were enabled to measure them.

## Remaining limits

The fork banner, permission settings, registration and past execution are separate
observations. The user reports enabled/all; this integration's permission read is
403. No fresh execution restoration or live inference was inferred from either.
A future authorized job must establish provider success and cross-runner behavior
on this code. Reviewed multilingual quality labels, further primary-source
qualification and complete real weekly digest publication remain the separate
fleet acceptance gates from the prior report. No current deadline, technical
claim, quality metric, cost invoice or deployment success was invented.

A due refresh may publish meaningful freshness/due-time checkpoint changes even
if findings are unchanged. Identical/not-due snapshots skip publication. Failed
sources keep last-good evidence without advancing successful coverage; source
configuration changes reset coverage qualification. Unknown cost remains null;
configured token-rate costs are explicitly labeled estimates. Retention/file
bounds remain fail-closed rather than silently deleting history.

## Preserved concurrent compatibility fix

The remote PR #8 branch advanced to `b95ab064c7ec7371f970a7272d4ca3007536ed6a`
while delivery was in progress. Its Python 3.11 f-string quoting fix was preserved;
the two unpublished optimization commits were replayed onto that commit. Code
commit above is the resulting `9332c2d717ba9d2ba3c6ab7e3de31a4be2050ccb`.
No remote history was rewritten.

An isolated real CPython 3.11.16 interpreter reproduces the old `5582bde` provider
SyntaxError (`f-string: unmatched '('`, line 76). The preserved fix compiles.
This is a demonstrated compatibility defect consistent with the earlier pytest
import failure; the actual hosted error log remains unavailable. It is not a
provider-key or billing diagnosis. Full post-integration regressions pass on both
Python **3.11: 499 passed in 6.66s** and **3.12: 499 passed in 5.00s**. Both MCP
smokes additionally pass under 3.11. The temporary interpreter/environment were
installed under /tmp; the repository's original environment was preserved.
