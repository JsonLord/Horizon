# Technical radar fleet acceptance — 2026-11-08 UTC

Implementation source: `93596431508915f97dcfdacf01536654c99e1347`, based on PR #7
`05ab6d80ffb3f1e7e9a7c3336c2e4c086727b9bb`. Branch
`feature/technical-radar-fleet` is stacked on `feature/shared-intelligence-filtering`.
PR #5 and PR #7 remain draft and unmerged. This records implementation and
measured limits; it is not production qualification.

## Gate results

| Area | Result | Evidence / remaining work |
|---|---|---|
| 0 Audit / isolation | PASS | Existing contracts reused; architecture report; separate implementation/data branches. |
| 1 Live model readiness | BLOCKED | Registered qualification dispatch 422 Actions disabled; metadata 403; no provider calls or actual model identity. New workflow lookups 404. See DECISION_MODEL_LIVE_ACCEPTANCE.md. |
| 1 Hosted durability | BLOCKED | No new hosted runner/run/artifact. Local SQLite and portable JSON recovery checks pass, including source/policy/hash mismatch rejection. |
| 2 Three domains | PASS | Three schema-valid profiles/policies/registers; three data-only remote branches, manifests retrieved at pinned commits. |
| 3 Ingestion | PARTIAL | All three multilingual query sets and all six official repository-release endpoints retrieved successfully locally. New sample: 30 agent, 8 training, 30 RAG review candidates. Other source families still require approved sources/adapters. |
| 3 Multilingual support | PARTIAL | EN/DE/FR original text/provenance tests pass. Real sample contains DE/EN/FR and explicit unknowns; training's DE/FR queries returned no items in this sample. No fabricated coverage. |
| 4 Scheduling | PARTIAL | Trusted controller/reusable per-radar worker, independent concurrency, 12-hour due state, retries/backlog/catch-up and separate permissions implemented/linted. Both registry flags false; no hosted execution. |
| 5 Deduplication quality | PARTIAL | DOI/arXiv/release-version identities, hashes, shared same-story model gate, separate language sources and within-digest canonical events tested. Actual multilingual semantic matching quality unmeasured. |
| 6 Pedagogical scoring | PARTIAL | 1–10 bounded component rubric, quote/citation support, measured-result requirement, primary-evidence guard, model and policy provenance implemented. Deterministic fallback = review/score 1. Actual model quality unqualified. |
| 7 Technical distillation | PARTIAL | Attributed Markdown reports, source-language evidence, limitations/prerequisites and optional validated original pseudocode/code excerpts implemented. Live source claims are all review, not confirmed technical facts. |
| 8 Weekly digest | PARTIAL | Friday/ISO-year/boundary/catch-up tests pass, immutable snapshots and explicit corrections implemented. All actual local candidates partial; no complete real weekly digest yet. |
| 9 Pull contract | PARTIAL | Public manifest reads and pinned tree validation pass for all three actual branches. Complete digest/history/schema/read-only retrieval paths pass local contract tests. Actual digest/history reads await a qualified publication. |
| 10 Quality evaluation | PARTIAL | Real public-source sample projected into radar benchmark with per-radar/language metrics. No independent reviewed labels; all unsupported quality/latency/cost metrics remain null. |
| 11 Permissions / isolation | PASS locally | Read-only collection/validation, main-only allowlisted data writer, non-force updates, source-bound artifacts, history/latest guards; no external delivery client/credentials/webhooks. Live automatic-token publication unverified. |
| 12 Production readiness | BLOCKED | Requires actual provider/hosted qualification, reviewed labels/source expansion, authorized schedule/publication enablement and first complete weekly publication. No merge/activation performed. |

## Commands and exact measured results

- `uv run --extra dev pytest`: **487 passed in 5.22s**.
- Latest targeted `uv run --extra dev pytest tests/test_radar.py`: **29 passed
  in 0.36s**; covers EN/DE/FR provenance, semantic-event links, release versions,
  technical budget reservation, rubric support, original code pattern citations,
  provider strict/nonstrict JSON, UTC windows, immutable corrections, repeated
  publication, missed schedules, pinned reads, narrow paths and cache recovery.
- `uv run python -m scripts.check_research_mcp`: **PASS**, 24 tools, 15 profiles,
  real local stdio transport.
- `uv run python -m scripts.check_mcp`: **PASS**, legacy config/sources/metrics.
- `uv run python -m scripts.research_funding check`: **valid and deterministic**.
- `uv run python -m scripts.check_funding_acceptance`: **PASS**, 3 opportunities,
  all ELIGIBILITY_UNKNOWN; 43 local links; 4 pending nominations; 0 new pending;
  authored seed unchanged at
  `5a509f585d1e05eb996ab13bdff83064ea708f08db03ea4bfd79c22fe0d5ee65`.
- `/tmp/shared-tools/actionlint -color=false`: **PASS**, no diagnostics.
- `git diff --check`: **PASS**, no whitespace errors.
- `uv run python -m scripts.radar_schemas`: regenerated model schemas.
- Actual credential-free local `run_collection()` for all three radars: all 15
  query/release checks **ok**. Latest bounded retained counts **30/8/30**. Evidence
  files: `docs/radar-local-collection/*.json`. These are developer collection
  smokes, not GitHub-hosted acceptance runs, and contain no model inference.
- `uv run python -m scripts.benchmark_radar --root /tmp/radar-live-final --output
  data/shared-benchmark/radar-benchmark.json`: **68 real public-source cases**;
  unreviewed labels; metrics null. No claim of improved quality.
- Existing registered `horizon-intel.yml` shared-filter qualification dispatch:
  **422**; no run. New direct workflow lookups **404**; no run. Variable/secret
  metadata **403**. Exact safe evidence in `docs/radar-hosted-blocker.json`.

## Actual GitHub data branches and consumer checks

| Branch | Verified pinned initialization commit |
|---|---|
| radar/agent-control-planes | d9d88dc5bfd82b8fb40cabd6ebc283db01980325 |
| radar/distributed-training | 0f7a702cd4e8b75acb39cf659b6b24c69c9572c8 |
| radar/rag-memory | 09efe2f6f4a18213545ba00ef507fd5afa0bf0d4 |

Each currently contains only `README.md` and schema-valid `radar-manifest.json`:
`digest_status=uninitialized`, latest path/week and success timestamps null.
Actual GitHub contents API reads at those immutable SHAs succeeded. The new public
reader also fetched each pinned tree/blob set without a bearer token and validated
its data allowlist/schema. Proof: `docs/radar-branch-initialization.json`.

`weekly-digest.json` and historical weekly paths are deliberately **not yet
present**. Do not advertise these as working live digests: real collection did
not establish full weekly historical coverage or confirmed concepts. Initializing
empty manifests was an operator-authorized branch setup, not automatic-token
publication acceptance. Existing `intel` and funding archives were not published
or changed by this work. No server, HTTP port, hosted MCP or HF Space is used.
The existing local stdio MCP remains the agent interface; public GitHub repository
APIs are the pull interface documented in RADAR_PULL_CONTRACT.md.

## Remaining qualification

Owner must resolve repository Actions availability, accounting for existing cron,
without Horizon silently enabling it. Use the existing registered workflow's
read-only shared-filter qualification on `feature/technical-radar-fleet` to run
all 18 command/profile cells and a separate runner recovery. Retain actual run
URLs, hashes, source/policy versions, model identity, validated decisions and
usage/latency evidence. Then qualify the new radar worker read-only on hosted
runners. Do not infer those results from local fixtures.

Expand reviewed primary papers/blog/lab/conference/benchmark sources and trusted
source-language evidence. Review the real corpus and assign independent labels
before reporting quality. Evaluate multilingual same-story recall, especially
non-English follow-ups. Do not promote unknown-language, unsupported benchmark or
marketing-only content to HIGH_SIGNAL.

After separately authorized activation, observe consecutive collections covering
a full fixed weekly interval and an actual automatic-token publication to each
radar branch. Verify root/history/manifest consistency via a separate read-only
consumer at the resulting SHA; recover a missed Friday with retained evidence;
repeat to verify zero duplicate writes. Reports are retained, portable state is
bounded (80 recent findings/150 KB decision cache), and the publisher fails closed
at its overall 5,000-file/20 MB tree bounds rather than silently pruning history.
Long-term archive scaling needs review before those bounds are reached.

No external consumer integration, push delivery mechanism, wakeup, authentication
or pull client exists in Horizon. No production schedule or merge is authorized
by this acceptance report.

## Files created and modified

Complete implementation inventory (A = added, M = modified):

```text
M	.github/workflows/horizon-intel.yml
A	.github/workflows/radar-fleet.yml
A	.github/workflows/radar-worker.yml
M	AGENTS.md
M	config/filtering/bindings.json
A	config/filtering/policies/radar-agent-control-planes.yaml
A	config/filtering/policies/radar-distributed-training.yaml
A	config/filtering/policies/radar-rag-memory.yaml
A	config/radar/registry.json
A	config/radar/sources/agent-control-planes.json
A	config/radar/sources/distributed-training.json
A	config/radar/sources/rag-memory.json
A	data/shared-benchmark/radar-benchmark.json
A	docs/DECISION_MODEL_LIVE_ACCEPTANCE.md
A	docs/RADAR_PULL_CONTRACT.md
A	docs/TECHNICAL_RADAR_ARCHITECTURE.md
A	docs/radar-branch-initialization.json
A	docs/radar-hosted-blocker.json
A	docs/radar-local-collection/agent-control-planes.json
A	docs/radar-local-collection/distributed-training.json
A	docs/radar-local-collection/rag-memory.json
A	profiles/radars/agent-control-planes.json
A	profiles/radars/distributed-training.json
A	profiles/radars/rag-memory.json
A	schemas/radar-digest.schema.json
A	schemas/radar-finding.schema.json
A	schemas/radar-manifest.schema.json
A	schemas/radar-state.schema.json
A	scripts/benchmark_radar.py
M	scripts/check_research_mcp.py
A	scripts/radar_fleet.py
A	scripts/radar_schemas.py
M	scripts/shared_filtering.py
M	spec.md
M	src/research/filtering/provider.py
A	src/research/radar/__init__.py
A	src/research/radar/contracts.py
A	src/research/radar/pipeline.py
A	src/research/radar/publisher.py
A	src/research/radar/storage.py
A	tests/test_radar.py
M	tests/test_research.py
A	docs/TECHNICAL_RADAR_FLEET_ACCEPTANCE.md
M	docs/agent-research.md
```

Final review: draft PR #8 (https://github.com/JsonLord/Horizon/pull/8), base
`feature/shared-intelligence-filtering`, head `feature/technical-radar-fleet`.
A final dispatch of the registered horizon-intel shared qualification against the
fleet ref also returned 422 Actions disabled; no run was created. Final full
suite at the pushed implementation: 487 passed in 5.22s.

## 2026-11-09 optimization addendum

The newer fork-aware configuration and measured local checks are recorded in
ACTIONS_OPTIMIZATION_ACCEPTANCE.md and WORKFLOW_INVENTORY.md. Routine fresh-runner
validation is now optional; disabled subsystem cron events are absent, not gated.
The 24-hour pilot, conditional source/model reuse, metering and schedule renderer
preserve this digest contract. The past hosted run 42548115014 did execute but
failed pytest before inference; do not treat earlier 422 observations as a
complete diagnosis of the fork's current state. Live provider/digest publication
still require separate actual evidence; no production activation occurred.

## Authorized hosted follow-up after reactivation

See ACTIONS_LIVE_VALIDATION_2026-11-09.md: actual hosted PR validation, funding
collection, all three radar collections and fresh artifact validations pass.
Shared checkpoint recovery also passes without inference. Radar controller testing
used an isolated registered-path alias because its standalone workflow is not
registered on main. Provider readiness is still unqualified: HTTP 404, 0/18 live
cells validated. No production publisher ran; PR #8 remains draft.
