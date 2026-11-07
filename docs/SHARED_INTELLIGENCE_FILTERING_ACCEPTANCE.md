# Shared intelligence filtering acceptance — 7 November 2026

Implementation branch: `feature/shared-intelligence-filtering`, stacked on the
existing funding implementation at `44e6e1b`. Existing PR #5 remains untouched.
The provider correction overrides the attachment's native-provider alternatives:
**one configurable OpenAI-compatible endpoint only**, shared by AUX, Funding and
World. Legacy Laya code is preserved; no new native adapter/dependency was added.

| Gate | Status | Evidence / remaining limit |
| --- | --- | --- |
| 0 Audit/base | PASS | Inspected profiles, service, funding/program models, state and workflows; inspected Pi Durable MIT revision 273b79b, jev-classify.ts and news/hfs.ts. Remote branches had no AUX equivalent. Independent Python adaptation; attribution in PI_DURABLE_ATTRIBUTION.md. |
| 1 Shared engine | PASS locally | Executable gates, normalized audited decisions, deterministic ranking, cache, feedback and checkpoints integrated into shared service. Source/eligibility hard gates always win. |
| 2 Initial policies | PASS locally | Three inherited/versioned policies enabled; dedicated examples/ai-usability added; existing funding/world/institution profiles reused. All share runtime HORIZON_DECISION_* config. MCP discovers 12 profiles. |
| 3 Decision concepts | PARTIAL qualification | All six structured commands, event linkage, within-batch coverage/development detection, contradiction review and separate HFS fields implemented/tested. Real semantic quality remains unverified without provider/labels. |
| 4 Provider | BLOCKED live qualification | Contract tests cover strict JSON, validated parsing fallback, model mismatch, invalid citations, rate cooldown and funding invariants. Local configuration absent; GitHub variable/secret metadata reads 403. No successful real inference is claimed. |
| 5 Durability | PARTIAL | Transactional SQLite/cache, backups, manifests, normal-workflow artifact restore and fresh-runner qualification job installed. Local restore, corrupted checkpoint rejection and atomic cache installation tested. Hosted runner boundary is unverified because Actions is disabled. Same-code automatic restore only; release feedback migration remains manual. |
| 6 Feedback | PASS locally | Three commands, profile isolation, bounded topic/source/item adjustments, curated public examples, free-text exclusion and auditable notes tested. Larger changes require a reviewed policy-version PR. |
| 7 Benchmark | PARTIAL | 200 cases: 195 archived world findings, two genuinely collected AUX findings and three explicitly marked historical funding-record projections. Compared under all three policies; the three projections have no fabricated baseline score. Balanced coverage and reviewed labels are still required. Quality metrics remain null rather than fabricated ground truth. |
| 8 Integration | PASS locally | Shared service, local collection/feedback/benchmark CLI, explicit read-only Actions dispatch, reviewed branch refs and profile locations installed. Decisions remain staging metadata; no production filtering rollout or publication. |
| 9 Hosted qualification | BLOCKED | Explicit dispatch returned HTTP 422: Actions has been disabled for this repository. No shared-filtering run ID or real inference result exists. Do not reuse earlier funding runs as proof. |

## Actual checks

- Full regression suite: **458 passed in 5.23s**, zero failing. Includes provider contracts, story deduplication, feedback,
  cache/eligibility invalidation, spend caps, checkpoint/corruption recovery and
  existing legacy/funding/program/news regressions.
- Local public-fixture smoke exercised AUX, Funding and World policies. Provider
  requests: **0**, live inference **false**, model **null**, fallback **unavailable**.
  This verifies deterministic execution only, not provider integration.
- Local restore validated the checkpoint and recovered deliberately interrupted
  working state; `restored_prior_runner_checkpoint` describes the CLI scenario,
  not an actual hosted runner result when run locally.
- Stdio MCP smoke: PASS, **24 tools / 12 profiles**. Legacy MCP smoke: PASS.
- Existing funding projection/43-link audit: PASS; original authored funding
  document unchanged. The historical funding fixture clock was fixed before its
  November 4 cutoff; real expiry rules were not relaxed.
- actionlint 1.7.7: PASS; official download checksum verified.
- Offline corpus/evaluation: `data/shared-benchmark/corpus.json` and
  `benchmark.json`. Zero model requests/spend; precision@10, important-item recall,
  development recall and unsupported-finding rate are null without reviewed
  labels. No duplicate publication rate exists because no publication occurred.
- An actual local AUX collection completed with two findings, two sources and two
  staged shared decisions; live inference remained false. See
  shared-filtering-local-collection.json. This is real news collection, not the
  disclosed inference fixture. No result was published to intel.

## Exact live blocker

Attempted:

```bash
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/shared-intelligence-filtering -f shared_filtering_qualification=true
```

GitHub responded **HTTP 422: Actions has been disabled for this repository**.
Push-triggered qualification also produced no run. Existing workflow listings
being active does not establish that repository Actions execution is enabled.
Repository variables and secrets metadata requests independently returned **403
Resource not accessible by integration**. Their configured values are unknown to
this actor. No endpoint was guessed and no credential was inspected or printed.

The reusable qualification is wired to the four requested repository settings,
requests real inference on a disclosed public fixture, exercises all three
policies, and restores its artifact on a fresh hosted runner. It is ready to run
in an authorized environment, but has **not** run. Enabling repository Actions
could resume existing schedules; it was not changed under this task's prohibition
on production activation. Alternatively an authorized local environment can bind
the same four settings securely and run the smoke; never paste keys into chat.

## Readiness and scope

The code is reviewable staging infrastructure. **Provider integration success,
semantic quality and hosted durability are not certified.** Production findings,
funding eligibility, source approval and main-only publishing remain authoritative.
No merge, force-push, schedule activation, intel publication, permission/secret or
network configuration change occurred.

All three policies select the same OpenAI chat adapter. Endpoints, model IDs and
keys are runtime configuration, never research-profile constants. No OpenRouter
or TypeSafe API dependency was introduced. There is no server, external database,
daemon, hosted container or self-hosted runner.

See SHARED_INTELLIGENCE_FILTERING.md for operation, limits, per-profile controls,
feedback, future-profile registration and reviewed-label evaluation. The existing
funding/program acceptance blockers are not claimed resolved by this work.


Machine evidence: shared-filtering-hosted-blocker.json records the actual failed
dispatch and absence of local provider configuration; shared-filtering-local-
collection.json records the real two-finding AUX collection. Benchmark manifest
and source provenance are in data/shared-benchmark. No hosted run link exists
because dispatch was refused before a run was created.
