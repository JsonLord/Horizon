# Funding research driven by the authored starting document

`research/funding-de-eu/Funding DK (DE missing).md` is the human-authored starting
point. The workflow preserves its text, historical context and line references.
The repository-root file of the same name remains a generated navigation page.

The new source file was available publicly on
`feature/program-intelligence-implementation` but not in this checkout. It was
read through the normal public raw GitHub URL and restored byte for byte. SHA-256:
`5a509f585d1e05eb996ab13bdff83064ea708f08db03ea4bfd79c22fe0d5ee65`.
Git/API authentication initially returned 401 but recovered on resume. The remote
authored-file commit is `4176ea47617bda64a789da31e77f8da78452da87`; its source bytes
match the preserved copy. Preserve that parent when integrating these changes.

## Data flow

1. Parse program-row references and public URLs from the authored file. Reject
   HTTP, private hosts, authentication URLs and unreviewed query parameters;
   remove known analytics tracking and harmless presentation fragments only.
   Do not infer a current deadline from historical notes or a yearless date.
2. Refresh the official programs approved in `config/funding-sources.json` using
   the existing ResearchService, collector protections and opportunity storage.
   Changed content requires review; failed refreshes retain previous evidence.
3. Search reviewed generic public queries from `config/funding-research.json`,
   using existing Horizon collectors without news/model credentials. Never send
   the authored narrative or personal planning context as a query or prompt.
4. Keep new candidates in `RESEARCH_QUEUE.json` and `RESEARCH_UPDATES.md`. The
   initial deduplicated queue contains 100 research references: 36 needing
   official-source review, 57 needing a source, and 7 references to existing
   tracked programs. These counts are not counts of verified funding offers.
5. Approve a new program identity/domain in the source register before it can
   enter a self-contained opportunity folder. Current deadlines, amounts and
   eligibility need direct official evidence. Applicant facts remain separately
   reviewed and no nomination can promote eligibility.
6. Save a structured proposal artifact. On explicitly enabled, reviewed main
   code, validate its source SHA and source-document fingerprint and re-render
   the generated data; ignore artifact Markdown or executable files. The writer
   can change only generated dashboards, the queue and opportunity data. It
   cannot edit the authored source, configuration, workflow or application code.
7. Optionally create a **draft data PR** with the automatic job GITHUB_TOKEN.
   Never update existing refs, force-push, auto-merge or publish the intel archive.
   If a funding data PR is already open, preserve it for review. If main advances,
   collect again rather than propose stale data.

Source nomination entries use host labels or opaque line references; personal
row notes are not duplicated into the queue. Search/seed nominations do not carry
verified amounts, deadlines, application status or eligibility fields. Old search
nominations survive temporary outages subject to the bounded candidate limit;
authored entries removed from the current document stop being current seeds.

## Commands and controls

```bash
uv run python -m scripts.funding_research index
uv run python -m scripts.funding_research index --check
uv run python -m scripts.funding_research run --output /tmp/funding-proposal
uv run python -m scripts.research_funding check
```

`run` creates a fresh proposal directory; it does not modify the committed
research store or publish. Its summary reports collection failures explicitly,
even if a useful discovery proposal could still be produced. `apply` / `propose`
are reserved for enabled default-branch workflow execution. The writer validates
typed records, approved entity/domain bindings and source provenance before any
GitHub writes. Git objects and new refs are created through the API; refs are
never PATCHed or force-updated. API authorization errors stop the job.

Configure `max_candidates` (1–200), `max_search_results` (1–40), `regions` and
`queries` in `config/funding-research.json`. The official refresh remains limited
to at most 40 approved programs. Current discovery adds review tasks; it does not
automatically establish domain ownership or extract verified terms from snippets.

The workflow declares Monday 07:17 UTC (09:17 summer / 08:17 winter Berlin), but
`schedule_enabled: false` prevents scheduled research. `review_pr_enabled: false`
prevents automated PR writes. Manual collection remains read-only. A new manual
workflow normally must exist on the default branch before GitHub permits dispatch.
For development validation without merging, relevant pushes on the existing
`feature/program-intelligence-implementation` branch trigger read-only collection;
its privileged proposal job is always skipped. This allows the new workflow to
be tested through a regular branch push, without merging or enabling the
production schedule. No external/fork PR trigger executes public research jobs.
No merge, schedule activation or production publication is included here.

## Current limitations

Local live discovery succeeded for all three reviewed Google News queries and
added four unverified funding-related nominations (104 total references). The
local official-source refresh failed closed because public DNS was unavailable;
existing verified records were preserved. Hosted Actions validation must be
reported separately. No credential values were inspected or replaced. A robots-file request to the
seed's Innobooster operator returned proxy CONNECT 403, so it remains a nomination,
not an approved/verified funding opportunity. No network settings were changed.
The earlier source-verification milestone and its live qualification proof remain
in `docs/funding-source-verification.md`; they do not validate this new workflow.

## Hosted verification without artifact-host access

Each hosted `run` emits a bounded `funding-maintenance-proof` notice: workflow ID,
source/seed hashes, report status, nomination counts, sanitized search statuses
and approved program refresh/deadline metadata. Read it through the collect job's
check-run annotations API. It contains no authored narrative, search headlines,
transport errors or credentials. The full proposal remains a same-run artifact;
the current execution environment denies its external download host (403).
A successful job with a failed refresh is explicitly incomplete evidence, not a
verified-current funding report.
