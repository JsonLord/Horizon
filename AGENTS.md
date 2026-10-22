# Working on Horizon research

Use the existing checkout and preserve unrelated changes. Funding Gate 1 is on
`feature/program-intelligence-implementation`; it does not activate production.
Read `spec.md` and the relevant task before changing deployment or automation.
Do not merge, enable schedules, publish private inputs or change credentials as
part of a source-list update.

## Change the sites Horizon examines

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
