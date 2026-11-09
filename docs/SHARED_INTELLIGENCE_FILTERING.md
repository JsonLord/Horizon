# Shared filtering operations

The new pipeline uses only `DecisionModelProvider` (`openai_chat`). Existing
Laya/native program code is retained for legacy program research and is never
selected by the shared engine. Bound news profiles bypass legacy model selection;
all new semantic decisions use the same global settings:

| Actions configuration | Kind |
| --- | --- |
| HORIZON_DECISION_BASE_URL | Repository variable: API base URL (default routing) |
| HORIZON_DECISION_CHAT_URL | Optional repository variable: complete POST URL; used verbatim, overrides base |
| HORIZON_DECISION_MODEL | Repository variable: exact model identifier |
| HORIZON_DECISION_API_KEY | Repository secret: optional authentication token |
| HORIZON_DECISION_API_MODE | Repository variable: `openai_chat` |

When HORIZON_DECISION_CHAT_URL is set, the client POSTs to that exact public HTTPS
operation URL without appending a path. The OpenAI chat JSON body, model check,
schema/citation checks, redirect policy and fallback are unchanged. No endpoint
belongs in a profile. When the override is absent, the client appends `/v1/chat/completions` (or `/chat/completions` to a base already
ending in `/v1`). It requires public HTTPS, does not follow redirects with the
key, verifies response model identity, validates JSON/citations/event references,
and falls back deterministically. Unsupported strict response formats retry with
ordinary JSON parsing plus the same schema validation. No native API or vendor
SDK is selected. No OpenRouter/TypeSafe credentials are required.

## Profiles and policies

`config/filtering/defaults.yaml` and `policies/*.yaml` use JSON, a YAML 1.2 subset,
without adding a parser dependency. Defaults are merged before strict validation.
`config/filtering/bindings.json` maps profile IDs to policy filenames. World and
institution profiles inherit world-radar unless explicitly overridden. A null
binding disables shared filtering for that profile. Other approved profiles can
be bound explicitly without implementing a new provider.

- `examples/ai-usability`: dedicated AUX profile and ai-usability policy.
- `funding/de-eu`: existing funding profile, funding-de-eu policy.
- `world/global` and other world/institution profiles: world-radar policy.

Edit topics, exclusions, provisional weights, threshold, concurrency (1–4),
request/token caps and optional USD cap in policy files. Bump the policy version
and review larger changes through a PR. Never put endpoint URLs, model names,
credentials or private founder preferences into profiles/policies.

Each model decision uses bounded public summary/excerpts, public topic labels,
reviewed-public examples and at most three prior candidate summaries. It never
receives the authored funding narrative, raw private questions or applicant facts.
HFS dimensions are editorial estimates; a facts score does not verify truth.
Funding acceptance additionally requires the existing deterministic ELIGIBLE_NOW
assessment; unknown, future-round, milestone and ineligible categories cannot be
promoted by a model, feedback or cached decisions. Original research findings and
eligibility records remain authoritative. Shared decisions are staging metadata
under `statistics.shared_filtering`, not automatic publication selection.

## Run and review

```bash
# Real collection, no publication (uses existing shared service and archive reader):
uv run python -m src.research.cli --profile-id examples/ai-usability --output data/aux-staging
uv run python -m src.research.cli --profile-id funding/de-eu --output data/funding-staging
uv run python -m src.research.cli --profile-id world/global --output data/world-staging

# Disclosed public inference fixture plus three-policy qualification:
uv run python -m scripts.shared_filtering --output data/shared-filtering
uv run python -m scripts.shared_filtering --output data/shared-filtering --restore

# Bounded, profile-scoped feedback (state stays outside intel):
uv run python -m scripts.shared_filtering --output data/aux-staging/filtering \
  --feedback more_like_this --profile examples/ai-usability --item FINDING_ID \
  --topics accessibility --sources SOURCE_ID --reason 'Reviewed public evidence'
```

Other feedback commands: `less_like_this`, `important_but_not_actionable`.
Topic/source and item adjustments are capped; important/nonactionable feedback
separately adjusts editorial dimensions. Free-text audit notes are not sent to the
model. Curated examples come only from already collected public summaries.
Keep feedback audit notes public-safe before exporting artifacts. Feedback never
edits security, source approval or eligibility policy.

Every result records stable item/event IDs, policy version, content fingerprint,
individual gate outcomes, citation IDs, provider status/model/family, fallback,
request latency and token usage when supplied. Scores are not probabilities.
Same stories retain coverage, developments link to the earlier event, distinct
events remain separate, contradictions/insufficient support require review.
Funding opportunity IDs cannot be merged by semantic story matching.

## Bounds and state

Each provider call has a 15-second timeout, 6 KB request bound, 64 KB response
bound and 500 output-token request. There are at most three attempts, with bounded
backoff and Retry-After respected; long cooldowns cause fallback instead of early
retry. Three failed decisions open a per-provider circuit. Policies reserve a
conservative 19,500 tokens / three HTTP attempts before each decision, including
format fallback. Completed decisions and successful partial gate calls are cached
using policy, provider fingerprint, evidence content, previous context, feedback
and hard-status bindings. Current hard gates are rechecked on completed-cache use.

Dollar costs remain unknown when the provider supplies no prices. Optional
`max_cost_usd` with `usd_per_million_tokens` bounds reserved estimated spend; an
explicit dollar cap without pricing fails closed to fallback. No hardcoded vendor
prices or statistical probabilities are invented.

SQLite is embedded local state, not a service. Transactions commit individual
checkpoints. Consistent backups have SHA-256 manifests and integrity checks.
Normal Actions collection optionally restores `shared-filter-cache` from a
successful same-branch, same-source-revision run before collecting, and uploads
its new bounded snapshot afterward (14-day retention). Invalid/expired caches
cold-start with a warning; they do not replace the intel last-good archive.
Code-revision changes intentionally cold-start this automatic cache; reviewed
feedback migration across releases remains an operator task.

The staging workflow has a separate fresh-runner restore job: it deliberately
corrupts working state, validates the retained backup and recovers from it.
This tests checkpoint recovery, not arbitrary SIGKILL atomicity. Missing or
unverified hosted execution must not be described as demonstrated durability.

## Hosted qualification and benchmark

```bash
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/shared-intelligence-filtering -f shared_filtering_qualification=true

# Read archived findings without publishing; offline evaluation is the default:
uv run python -m scripts.benchmark_shared_filtering --revision intel \
  --output data/shared-benchmark
# Optional actual local report supplements, reviewed labels and explicit spend:
# --extra-report PATH/TO/AUX/report.json
# --labels reviewed-labels.json --live-model
```

The explicit Actions qualification calls the read-only reusable workflow;
production collection/publication stays skipped for this flag. Existing production
schedules are unchanged. The provider variables and secret are wired into normal
collection too, without changing main-only publication guards.

Reviewed labels are keyed by profile then item ID, with `reviewed: true`,
`relevant`, `important`, `new_development` and `supported`. Unreviewed or incomplete
labels produce null quality metrics. Empty feeds cannot claim good precision or
recall. The corpus includes explicitly marked historical opportunity views, not fabricated
news findings; optional local reports retain their provenance. Benchmark excerpts are short/attributed; original archive scores provide
a baseline, not proof of a controlled quality improvement. Live benchmark spend
requires the explicit flag. Do not claim provider success without a real smoke.


2026-11-09 fork optimization: provider qualification is manual/reusable only, no
feature push or full pytest duplication. PR validation owns the regression suite.
Select `durability=true` for fresh-runner restoration; a smoke can use one runner.
The registered horizon-intel entry point exposes `shared_filtering_durability`
(default false) with the existing shared qualification flag. Hosted qualification
now requires all live command/profile cells; deterministic fallback retains safe
artifacts but does not return successful live qualification.

The read-only staging qualification accepts an optional `model` input (or CLI
`--model`) so an operator can test a specific identifier without modifying global
repository settings. It is validated and binds the decision cache identity.
This override applies to all three fixture profiles in that qualification; normal
collectors continue to use HORIZON_DECISION_MODEL. The latest operator-selected
identifier is alias-laya; live status is recorded in the dated acceptance reports.
