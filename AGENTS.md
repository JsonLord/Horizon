# Working on Horizon research

Use the existing checkout and preserve unrelated changes. Funding Gate 1 is on
`feature/program-intelligence-implementation`; it does not activate production.
Read `spec.md` and the relevant task before changing deployment or automation.
Do not merge, enable schedules, publish private inputs or change credentials as
part of a source-list update.

## Change the sites Horizon examines

The authored starting point is now
`research/funding-de-eu/Funding DK (DE missing).md`. Preserve it byte for byte;
do not replace it with generated output. It contains historic deadlines and
personal planning context, not authoritative current funding evidence.
`RESEARCH_QUEUE.json` / `RESEARCH_UPDATES.md` derive nominations and source-line
references from that file without copying its narrative into outbound queries or
generated facts. The repository-root file with the same basename is a generated
navigational dashboard, not the authored source.

- Funding's URL register is `config/funding-sources.json`. Each entry has a stable
  `opportunity_id`, canonical provider/program labels, a public HTTPS `url`, and
  reviewed `official_domains`. Add a domain only after confirming ownership.
  Registered URLs are candidates until retrieved; registration proves no facts.
- Incubator sources are `config/program-sources.json`; bounded discovery sites
  and page/candidate/concurrency limits are `config/program-discovery.json`.
- News queries, language, country, topics, regions, feeds, lookback and limits
  live in `profiles/**/*.json`. Public URLs must satisfy
  `src/research/profiles.py:safe_url`. Never add credentials or private URLs.
- Funding documents, application URLs, guidelines, contacts and FAQs belong in
  each opportunity's `resources/links.json`, generated from its structured
  `resources` records. Include title, URL, kind, retrieval timestamp, verification
  flag, short quotation and response SHA-256. External links are preferred to
  redistributing documents. No full copyrighted pages or private documents.

## Funding records and hard filters

`research/funding-de-eu/opportunities/*/opportunity.json` is the source of truth.
Do not edit generated Markdown, indexes or folder names. `Opportunity` in
`src/research/funding/models.py` defines the complete contract; its JSON schema is
`schemas/funding-opportunity.schema.json`.

1. Collect official pages with
   `uv run python -m scripts.research_funding collect`. This obeys robots, public
   DNS, redirect, MIME and response-size restrictions. It does not infer terms
   from snippets or turn an available page into an open application.
   `uv run python -m scripts.research_funding diagnose` makes read-only HEAD
   checks and distinguishes proxy CONNECT failures, unknown-origin HTTP failures
   and local DNS limitations. It logs only a header allowlist and no credentials;
   it does not replace Horizon's public-DNS, robots or SSRF checks. A successful
   HEAD request alone proves no funding terms. Do not change network settings
   without explicit operator authorization.
2. Review official terms and import a JSON **array** of complete records with
   `uv run python -m scripts.research_funding sync --records /path/to/reviewed.json`.
   Claims cite verified official resource IDs. Quotes must actually support the
   claim. Do not mark a resource verified just to satisfy validation.
3. Set application status separately from eligibility. Date deadlines require
   a matching `deadline` claim (`YYYY-MM-DD`); other verified tokens are `ROLLING`,
   `CLOSED` (permanently discontinued) or `NEXT-ROUND-UNKNOWN`. Missing evidence
   stays `UNKNOWN`. An ordinary closed round is not permanent discontinuation.
4. Express each hard restriction as a `conditions` item: applicant fact `key`,
   description, accepted values and evidence IDs. A documented achievable
   prerequisite may have a `milestone`; otherwise a known mismatch is a hard
   exclusion. Set `eligibility_complete` only after checking the complete
   official requirements, with its own supporting claim.
5. Public, confirmed applicant facts go in `config/funding-applicant.json`.
   It intentionally defaults to no facts. Interests are research targets, not
   evidence of citizenship, residence, company status, financing or eligibility.
   Never commit private applicant details. Change `evidence_max_age_days` there
   to control the maximum evidence age (default 30).
6. Rebuild with `uv run python -m scripts.research_funding sync`; check generated
   output with `uv run python -m scripts.research_funding check`. Stable IDs must
   survive provider label and deadline changes. Never create a new ID for a round
   change. Mark `archived: true` to retain a record outside active counts.

Keep historical resources/events. Unknown legal or geographic conditions require
review. Scores are explained heuristics, never probabilities or eligibility.
The collector verifies page availability only; human/agent review of primary
terms is necessary to populate funding amounts, deadlines and restrictions.

## How an agent steers research

The document-driven workflow is `.github/workflows/funding-research.yml`.
Its policy is `config/funding-research.json`: DK/Berlin/DE/EU coverage, reviewed
public search queries, candidate/search limits, scheduling and review-PR flags.
Run `uv run python -m scripts.funding_research index` after edits to the starting
file to refresh its offline queue. `index --check` validates without rewriting.
Run `uv run python -m scripts.funding_research run --output /tmp/funding-proposal`
to collect approved sources and discover new nominations into a fresh proposal
directory. The source document is never used as an executable instruction or
sent verbatim to a search/model provider.

New nominations require review of the official program identity and domain. Add
an approved entry to `config/funding-sources.json` with a stable opportunity ID;
the next refresh creates its folder through the common storage adapter. Names
without URLs remain source-discovery tasks; do not invent a URL or copy a dated
seed claim into a verified fact. Existing opportunity IDs survive deadline changes.

`schedule_enabled` and `review_pr_enabled` start false. After explicit production
review, scheduling can run Monday 07:17 UTC. The optional PR job runs only from
reviewed main-branch workflow code, validates the source SHA and seed fingerprint,
re-renders structured artifacts, and creates a new data-only draft PR using the
automatic GITHUB_TOKEN. It never force-updates a ref, edits the authored document,
merges, or publishes the production intel branch. An owned, marked funding draft PR is updated through a non-force fast-forward after checking its head SHA and data-only diff. Identical content causes zero writes. Unmarked/legacy proposals remain pending manual reconciliation; they are never adopted or duplicated.
Use manual dispatch for branch qualification; obsolete feature-branch push
collection triggers were removed. The privileged proposal job cannot run there.

Use the existing authorized MCP tools `hz_list_profiles`, `hz_submit_research`,
`hz_get_job`, `hz_list_reports`, `hz_search_archive`, and `hz_get_report`. Inspect
their live input schemas rather than inventing tool arguments. A funding request
uses `profile_id: "funding/de-eu"`, a bounded `depth`, optional `lookback_hours`
and `idempotency_key`. Funding/program requests reject free-text questions,
institution overrides and source overrides: adjust the reviewed repository
configuration instead. Ordinary research profiles retain their existing query
controls. Anonymous public execution must stay disabled.

The funding adapter uses the bounded official URL register, not the profile's
news-discovery query. Search text alone cannot verify an opportunity. Its current
maximum is 40 registered opportunities/pages; change limits only with tests.
For funding, `depth` bounds the selected registered sources; `lookback_hours`
describes the common report window and does not filter official program pages.
`max_items`, `max_queries` and `lookback_hours` control normal news profiles.
Program fit weights, thresholds and optional model endpoint are in
`config/program-relevance.yaml`; model unavailability must retain deterministic
fallback and unknown eligibility. Do not route private data through that endpoint.

## Storage, publication and verification

Profiles choose `output.storage: "report"` (default) or
`"opportunity_folders"`. `src/research/output_storage.py` accepts a reusable
entity adapter (`sync(records)`); funding supplies `OpportunityFolderStorage`.
Folder projections accompany the existing checksummed intel archive, which stays
the MCP report contract. Service projections are under its configured data root;
the CLI's default projection is the repository's `research/funding-de-eu`.
Publication remains explicit; local folder generation does not publish to GitHub.

Run `uv sync --frozen --extra dev`, `uv run --extra dev pytest`,
`uv run python -m scripts.check_research_mcp` and
`uv run python -m scripts.research_funding check`. The legacy MCP smoke command
also needs its existing example/local config. Regenerate affected JSON schemas
from their Pydantic models after changing contracts. Record progress, actual
verification dates, test results and access blockers in `docs/agent-research.md`.

## Funding acceptance qualification

Use `funding_qualification=true` plus `funding_acceptance=true` when dispatching
horizon-intel on the implementation branch. Dispatch again at the same source
revision with `previous_run_id` to restore its validated snapshot on a fresh
hosted runner. Both production collect/publish jobs stay skipped. Snapshot
artifacts exclude the authored narrative; public notices contain bounded official
quotations and checksum proof. Recovery simulates a partial working-tree write,
not process-kill atomicity. See scripts/qualify_funding_acceptance.py.

`scripts/qualify_funding_review.py --live` is an explicit authorized sandbox
PR qualification: isolated automation/funding-acceptance-base-* target, never
main/intel, data-only rendered queues and a draft PR marked DO NOT MERGE. When run locally it uses
the existing operator identity. Explicit hosted qualification uses the automatic
job token as described below. Production
PR creation remains disabled and default-branch guarded.

`research/funding-de-eu/NOMINATION_REVIEWS.json` records manual nomination
qualification, reason codes and unknown official sources. Unverified/rejected
nominations never authorize crawling or eligibility. Resolve official ownership
and primary conditions before approving a source in the normal URL register.
`uv run python -m scripts.check_funding_acceptance` checks local navigation,
required folder contents, immutable IDs, checksummed history and classifications.

An explicit `funding_review_qualification=true` dispatch of horizon-intel on the
implementation branch tests a new isolated sandbox using the automatic job token.
It is disabled by default, rejects main/fork/scheduled execution, suppresses normal
collection/publication, and changes only generated queue JSON/Markdown through
the same guarded writer. The proof notice reports success or the exact bounded
GitHub permission failure; a completed qualification job with `status: blocked`
is not successful PR publication. No token or repository setting is changed.

## Shared decision filtering

Read docs/SHARED_INTELLIGENCE_FILTERING.md before editing the new subsystem.
Its default inference adapter is OpenAI-compatible chat, using global
HORIZON_DECISION_BASE_URL / MODEL / API_MODE repository variables and
HORIZON_DECISION_API_KEY repository secret. The operator's 2026-11-09 state/questions example authorizes an additional explicit
`systemone` mode, independent of the old native Laya adapter. Do not auto-detect
protocols or add OpenRouter/TypeSafe dependencies; old program Laya stays separate.
Policies inherit config/filtering/defaults.yaml; bind reviewed profile IDs in
config/filtering/bindings.json. Bump versions for tuning, keep source/eligibility
hard rules independent, and keep decisions staged until qualification. A model,
feedback or cache must never promote unknown funding eligibility. No endpoint,
model ID or secret belongs in a research profile. Use the explicit shared-filtering
qualification flag only in an authorized read-only Actions execution. Repository
Actions currently refuses execution; do not enable it without authorization that
accounts for existing schedules. Never claim live inference from mock/fallback
results. Benchmark labels are unreviewed, not ground truth.

## Technical radar fleet and source changes

Read `docs/RADAR_PULL_CONTRACT.md` and `docs/TECHNICAL_RADAR_ARCHITECTURE.md`.
Trusted controller code lives on the reviewed application branch. The three
`radar/*` branches contain only isolated research data; never execute their code.
Implementation is stacked on PR #7. Leave PR #5/#7 and all schedules unmerged and
inactive until explicitly authorized. `config/radar/registry.json` has separate
false scheduling/publication flags; enabling Actions itself can resume existing
production cron and is not an innocuous qualification step.

To change monitored subjects, edit the radar's profile in `profiles/radars/` and
its policy in `config/filtering/policies/radar-*.yaml`, then bump the policy
version and matching registry version. `config/radar/sources/<radar>.json` is the
URL/repository register: approved project repository seeds, en/de/fr discovery
queries and links requiring review. Profile queries drive collection; keep their
mirrored source-register queries consistent. Do not add guessed feeds, assumed
source language or private URLs. New source families need explicit bounded
adapters and official ownership/source review. A query match is only a nomination.

Steering controls: query text/language/country, topics, lookback (max 168h),
max_items/max_queries live in the profile. The policy controls shared attention
weights and threshold. Registry controls independent radar IDs/branches, candidate
cap (30), model request/token budgets (36/200000), and 24-hour pilot eligibility (12 hours with the optional second daily run).
The runner reserves technical distillation/support budget before shared scoring;
overflow stays in review. Unknown source language or semantic relevance is not an
exclusion. Primary evidence, bounded verbatim supporting quotations, separately
validated distillation support and explicit source language are required for
HIGH_SIGNAL. Marketing text and a large model score cannot override these gates.

Use `uv run python -m scripts.radar_fleet collect --radar rag-memory --restore`
for read-only development/qualification (repeat for other registered IDs).
`digest --radar rag-memory --week-end 2026-11-06T18:00:00Z` demonstrates an explicit
cutoff recovery; use the intended Friday, never fabricate historical coverage.
`--correction <review-id>` creates a traceable correction while retaining the
original snapshot; it requires explicit review, never an automatic rerun.
Generation is local/artifact-only. The publisher refuses non-main execution and
disabled publication, validates allowlisted data paths and never touches `intel`.

All model calls use the same four global HORIZON_DECISION_* settings as shared
filtering. No external delivery credentials, webhook, notification or consumer
pull client belongs in Horizon. Consumers use read-only GitHub APIs and pin the
branch head SHA before reading. Do not put a commit's own SHA inside its files.

Run `uv run --extra dev pytest`, `uv run python -m scripts.radar_schemas`, MCP
smokes and actionlint. Record actual live/hosted results independently of fixtures
in `docs/TECHNICAL_RADAR_FLEET_ACCEPTANCE.md` and `docs/agent-research.md`.
A live model remains unqualified until a real authorized Actions job validates it.


## Fork Actions optimization and reactivation

Read docs/WORKFLOW_INVENTORY.md and docs/FORK_ACTIONS_REACTIVATION.md before
changing Actions. Registration state, repository permissions and fork execution
activation are different observations. Do not diagnose billing, suspension or a
provider key from a fork-disable banner. Do not enable Actions or merge this work.

config/actions-schedules.json is the reviewed schedule plan. Disabled radar and
funding controllers have no actual cron event, avoiding scheduled gate-only runs.
After explicit approval, update the matching registry flags and render YAML with
`uv run python -m scripts.actions_schedule --render`; review the diff and merge
through normal authorization. CI runs `--check` to detect drift. Existing world
intelligence stays daily. Legacy Pages briefing is manual; preserve its historical
posts/feeds and keep_files behavior. Docs deployment stays docs-change-only.

Routine radar collection validates its sealed artifact in the same read-only
job. A separate publisher revalidates source revision/hashes/schema with write
permissions. `durability=true` adds a fresh-runner acceptance check; do not run a
full regression suite inside model qualification. PR validation owns regression
tests. All uv jobs cache dependencies by uv.lock; caches are not evidence stores.

Normalized source checkpoints store short attributed references, body hashes and
ETags, never raw pages. Unchanged content retains original evidence timestamps.
Changed queries invalidate their source checkpoint, and changed source coverage
resets coverage qualification. Changed analysis/provider identity invalidates
model decisions; documentation-only commits can reuse decisions. Retry/backlog
state is bounded and per radar. Runtime/request/token/cost telemetry is in safe
collection proof artifacts/logs. Unknown billing remains null; explicit dollar
caps without prices fail closed. No-change snapshots skip artifact/publication.
A due refresh may still update checkpoint timestamps even with no new findings.


For gateways exposing chat JSON at a custom operation path, the optional global
repository variable HORIZON_DECISION_CHAT_URL selects the complete POST URL
verbatim. It overrides base expansion; do not append v1/chat/completions to it.
BASE_URL compatibility remains the default when the override is absent. All shared
policies and radars use the same setting, public-HTTPS validation, no redirects,
strict response/citation checks and deterministic fallback. Never put an endpoint
in a profile or infer that endpoint HTTP success proves structured inference.


## Explicit SystemOne choice contract (operator amendment, 2026-11-09)

The supplied API example uses model/state/questions and answers, not OpenAI chat
messages/choices. Set HORIZON_DECISION_API_MODE=systemone explicitly; BASE_URL is
then the complete operation URL (CHAT_URL can still override it). Request alias
is HORIZON_DECISION_MODEL; pin the actual returned identity separately through
HORIZON_DECISION_RESPONSE_MODEL. No endpoint or identity belongs in profiles.
The user's example supersedes the earlier OpenAI-only protocol assumption for
this endpoint; keep openai_chat as the unchanged default and keep legacy program
Laya code unselected by shared filtering.

Native responses are schema-validated: exact question and choice IDs, bounded
probabilities/confidence/action, approved response identity and numeric usage.
Probabilities/confidence are uncalibrated metadata, never importance/eligibility
probabilities. The selected class maps to documented ordinal heuristic scores.
Only supplied citations/event IDs can be selected; missing support or zero action
abstains. Funding hard eligibility is independent. No free-text finding, benchmark
or pseudocode may be invented from a choice response. Technical-learning generation
is explicitly unsupported in this mode and falls back to deterministic review.
