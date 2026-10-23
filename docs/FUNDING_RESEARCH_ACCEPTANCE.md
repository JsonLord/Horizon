# Funding research acceptance — 23 October 2026

Funding changes on `feature/program-intelligence-implementation`, draft PR #5.
Baseline independently confirmed at `a549be157816aa3b4b582ec279bf06aed00c6702`.
The two independent hosted qualifications execute the same immutable revision
`b30b6b66ac182e0ac30f10df9ca5bb9778b11518`. Subsequent changes add reviewed
observations, navigation auditing and the separately qualified PR transport.
This report distinguishes successful software execution from complete research.

| Gate | Result | Evidence and practical limit |
| --- | --- | --- |
| A — IBB/EIC source verification | PARTIAL | Both official pages fetched successfully on 23 October; every prior page quotation still present. Changed full-page hashes caused `official_terms_need_reverification`, not a 403. Current cited evidence and founder scenarios updated; uncited terms/full eligibility remain unresolved. |
| B — four nominations | PARTIAL | All four rechecked on both hosted runs; Google News article robots rules refused access. Official providers/canonical program URLs and terms remain unverified. Four pending, zero accepted/rejected/promoted. Four permitted public-feed alternative queries returned 200, but no verified official program identities/terms. |
| C — folder storage/navigation | PASS | Required files present, immutable IDs/history checksums valid, one correctly named overview per folder, 43 internal links checked. Deadline rename/history and failed-transaction tests pass. Original authored source bytes unchanged. |
| D — independent-run durability | PASS | Two successful dispatches, different hosted runner instances, same code revision; second restored artifact 12433950391 and verified ZIP/manifest hashes. Prior report restored; each history appended once. Simulated partial working-tree write rejected and exact sealed checkpoint restored. This is not SIGKILL atomicity testing. |
| E — guarded draft PR | PARTIAL | Operator-only isolated PR #6 created/updated/reused safely. Real automatic GITHUB_TOKEN test reached POST /pulls but GitHub refused HTTP 403 `actions_pr_creation_disabled`. No PR created by that job; permissions were not changed. |
| F — optional model | PARTIAL | Configured native Laya contract discovered; actual structured inference unavailable after three bounded attempts on each hosted run. Deterministic fallback executed. 429/500/502/503, timeout, invalid identity/schema and hard-filter protection tested. No probability or successful inference claimed. |
| G — acceptance evidence/regressions | PASS | 439 tests passed; MCP, funding consistency, 43-link audit, source-index and workflow lint passed. Independent durability runs, final code regressions and the explicit job-token permission result are recorded below. PASS here means acceptance checks/reporting completed, not that partial/blocked research or publication gates became successful. |

## Sources, deadlines and founder scenario

All times below are actual observation timestamps in UTC; Berlin was UTC+2.
Evidence, bounded quotations and response hashes are preserved in each opportunity
folder and [run 2 proof](funding-acceptance-run-2.json).

| Program and canonical source | Observation | Verified fields and unresolved conditions |
| --- | --- | --- |
| [IBB GründungsBONUS Plus](https://www.ibb.de/de/foerderprogramme/gruendungsbonus-plus.html) | 2026-10-23 09:48:15 UTC | Current page says applications can again be submitted. Fixed/rolling deadline UNKNOWN. Official guideline requires completed establishment at application, Berlin headquarters and age within 18 months. An unincorporated founder must first complete eligible establishment and meet the remaining requirements. No full eligibility determination. |
| [EIC Accelerator](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en) | 2026-10-23 09:48:17 UTC | Full-proposal cutoff **4 November 2026, 17:00 Europe/Brussels**, requiring short-proposal GO. Short proposals can be submitted at any time, with monthly batching. Natural persons intending to establish an SME are listed; a Berlin AI software idea alone establishes neither TRL 6–8 readiness nor eligibility. Global application status remains UNKNOWN to avoid conflating stages. |
| [KfW ERP-Gründerkredit StartGeld](https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/F%C3%B6rderprodukte/ERP-Gr%C3%BCnderkredit-Startgeld-(067)/) | 2026-10-23 09:48:16 UTC | Loan, not grant; previous guideline evidence retained with original timestamp. Deadline/application status UNKNOWN. Run 2 also detected a changed raw page hash; all cited page quotations remained present. No automatic eligibility promotion. |

IBB's official guideline is linked from its folder's resource register. It was
not re-downloaded during these two qualifications; its original 22 October
retrieval is preserved and remains within the 30-day policy. EIC Work Programme
and full applicant/project conditions are not completely verified. Cited quotes
remaining present do not prove that all uncited terms are unchanged. Conservative
review flags remain; no network or evidence guard was weakened.

Counts: **3 programs with official evidence, 0 verified eligible now,
3 ELIGIBILITY_UNKNOWN, 0 verified ineligible, 0 active, 3 review-required,
0 archived**. The public founder scenario is documented as a scenario, not a
private applicant profile; `config/funding-applicant.json` still contains no facts.

## Four nomination outcomes

[Machine register](../research/funding-de-eu/NOMINATION_REVIEWS.json) and
[readable review](../research/funding-de-eu/NOMINATION_REVIEWS.md).

| Nomination | Outcome | Rationale, without treating headlines as evidence |
| --- | --- | --- |
| SoundInvest Fund II / Bang & Olufsen headline | Pending | Fund-fundraising headline; a distinct current founder application has not been established. |
| IDA Startup Grant 2026–2027 | Pending | Potential prize; official provider, geography, instrument/conditions and current deadline unverified. |
| 77 projects / EUR 3.4 billion net-zero funding | Pending | Award-selection headline does not establish a distinct current application call. |
| Turning Business Potential into Progress | Pending | Roundup; no distinct official program established. |

Each article path returned `robots_disallowed`; no restriction was bypassed.
[Four alternative public-feed searches](funding-nomination-alternatives.json)
returned HTTP 200 at 10:04 UTC on 23 October (2/2/5/5 bounded results), but
yielded only news/aggregator references, not verified official program sources.
Official canonical program URLs remain null rather than guessed. Hard filters
return review-required for missing primary evidence. Semantic scores are null;
none can override that result. Deduplication cannot be established conclusively
without official identities; no new opportunity ID or folder was created.

## Hosted durability evidence

1. [Run 1 — 39795621057](https://github.com/JsonLord/Horizon/actions/runs/39795621057),
   runner `GitHub Actions 1000002783`; [public proof](funding-acceptance-run-1.json).
2. [Run 2 — 39934478478](https://github.com/JsonLord/Horizon/actions/runs/39934478478),
   runner `GitHub Actions 1000002796`; [public proof](funding-acceptance-run-2.json).

Snapshot artifact: `funding-acceptance-snapshot`, run 1 artifact ID `12433950391`.
ZIP SHA-256 `22391859a8ffcc5c0e386ffe846d05cd1b48a6051f408cc332c15a2110ae3dac`.
Snapshot manifest SHA-256
`63c11c297ddd7390bc09d265a28e64bcec4b10053dfd05d5d8b2ec54b1109a75`.
Run 2 verified both values before analysis, using its automatic read-only job token.
Its comparison report ID matches run 1's report. History counts EIC 4→5,
IBB 3→4, KfW 4→5; no duplicate record IDs/events, claims or deadlines lost.
[Machine comparison](funding-durability-qualification.json).

Every official page was rechecked. Old terms retain their original provenance;
failed/changed-page refreshes do not silently become fresh verified claims.
An HTTP 503 fallback test separately verifies failed-network preservation; the
live runs tested changed-page preservation, not an invented live network failure.
The sealed checkpoint is restored into a clean tree after deliberately corrupting
a working manifest. Artifact retention is 14 days; expired/missing/tampered or
wrong-revision artifacts fail closed. No authored narrative is in the snapshot.
The local environment did **not** download the full artifacts. It retrieved and
decoded bounded public notices through GitHub's check-run annotations API; run 2's
hosted runner did download and validate the real prior artifact.

Dispatch commands (same approved revision must remain selected for both runs):

```bash
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/program-intelligence-implementation \
  -f funding_qualification=true -f funding_acceptance=true \
  -f research_ref=feature/program-intelligence-implementation
# After the first run succeeds, repeat with:
# -f previous_run_id=FIRST_RUN_ID
```

## Guarded publication evidence

[Draft PR #6](https://github.com/JsonLord/Horizon/pull/6) targets isolated branch
`automation/funding-acceptance-base-b30b6b66ac18`, not main. Only
`RESEARCH_QUEUE.json` and `RESEARCH_UPDATES.md` differ. The fixture deliberately
reduces the existing public nomination list; it invents no program or fact.
Do not merge that qualification PR or its sandbox base.
[Creation, update and repetition proof](funding-review-qualification.json).

The shared writer checks reviewed source/base SHA, generated path allowlist,
PR ownership marker/repository, prior head SHA and existing branch diff. It uses
non-force fast-forward updates only. Identical Git blobs cause zero writes; an
unmarked/legacy proposal is not adopted or duplicated. Full projections remove
obsolete deadline folders without duplicating an opportunity. Tests cover
permission/protection HTTP 403/422 and racing heads, without exposing response
bodies or credentials. The main-branch API reports `protected: false`; this does not establish future
job-token permission. No branch protection was changed or protected production
write attempted.

The historical `propose` job was skipped because `review_pr_enabled=false` and
the implementation workflow is not the reviewed main workflow; these conditions
fail before any API permission check. It was not evidence of a permission failure
or a no-change optimization. The initial live sandbox writes used the existing operator identity. A separate
explicit `funding_review_qualification=true` dispatch now tests the same isolated
writer with automatic Actions GITHUB_TOKEN. Its branch/event/source guards reject main before network access.
[Run 39990565222](https://github.com/JsonLord/Horizon/actions/runs/39990565222)
reached `POST /pulls` and GitHub refused **HTTP 403**, with the specifically
recognized policy message that Actions cannot create or approve pull requests.
[Public token proof](funding-review-token-qualification.json) records
`status: blocked`, `reason_code: actions_pr_creation_disabled`. The qualification
job completed after recording that expected permission outcome; this is **not**
successful PR publication. Normal collect/publish and other research jobs skipped.

The job token did create an isolated base and a generated-data head before PR
creation was refused. Both sandbox refs remain, with only queue JSON/Markdown
changes; no PR exists for that head. The writer refuses to adopt an unassociated
ref or force-update it. The retained refs and SHAs are in the token proof for
manual reconciliation. The operator's attempt to read Actions workflow permission
settings also returned HTTP 403 `Resource not accessible by integration`, so the
repository-versus-organization enforcement location cannot be proven here. Owner
permission/policy review is required; no setting was changed. Production flags
remain disabled and no production token publication is claimed.

## Optional model evidence

Configured public service: `https://leon4gr45-needle-router.hf.space/v1/system-one`,
model `receptron/laya-onnx`, policy `1.0-provisional`, in
`config/program-relevance.yaml`. Its inspected interface is a native structured
classifier, not an assumed OpenAI chat endpoint. A real public EIC quotation was
used; authored notes, applicant facts and private preferences were excluded.
Both hosted runs discovered the native contract but ended with
`inference_succeeded=false`, `attempts=3`, deterministic fallback. The sanitized
error was `invalid_or_unavailable_inference`; its precise upstream cause is not
proven by that code. Routing/health discovery is not successful inference.

429/500/502/503 and transport failures retry at most three times, with bounded
backoff and the same input/request hash. Schema/identity/citation failures fall
back without speculative repair. Timeout is capped at 15 seconds per configured
attempt. Tests verify high semantic scores cannot override verified closed-round
hard filters. All scores remain uncalibrated heuristics; probability is null.
No model is mandatory; funding eligibility remains deterministic and separate.

The separate OpenAI-compatible evidence selector in `src/research/analyzers.py`
uses `HORIZON_LLM_BASE_URL`, `HORIZON_LLM_MODEL` and optional
`HORIZON_LLM_API_KEY`; none is configured in this execution environment. A local
`enrich([])` call returned `(None, "deterministic", [])`, without inference.
Its `/chat/completions` contract is tested with mock providers (not a claim of a
configured live OpenAI model). It now also retries 429/500/502/503/transport errors
at most three times with bounded backoff; four transient-error regressions verify
identical requests, unchanged findings on fallback and no provider-body leakage.
Invalid/oversized replies are not retried, and only existing evidence IDs may be
selected; extractive text and eligibility are never replaced with model claims.


Artifact restore errors now omit signed redirect URLs and raw upstream text; a
transport-failure regression verifies that sensitive exception context is hidden.

## Commands and exact results

- Baseline full suite: **407 passed in 3.98s**.
- Final implementation suite: `uv run --extra dev pytest -o addopts='' -q` —
  **439 passed in 5.06s**, zero failures. Intermediate test defects in the new
  qualification harness (mock argument binding and snapshot path allowlist) were
  fixed before the successful focused/full/hosted checks; no failing test hidden.
- `uv run python -m scripts.check_research_mcp` — PASS, 24 tools / 11 profiles.
- `uv run python -m scripts.check_mcp` — PASS, legacy validation/metrics.
- `uv run python -m scripts.research_funding check` — PASS, deterministic.
- `uv run python -m scripts.check_funding_acceptance` — PASS, 43 local links,
  required folders/history/IDs, three unknown opportunities, four pending reviews.
- `uv run python -m scripts.funding_research index --check` — PASS, 100 authored
  references, queue fingerprint current; total queue 104 including search results.
- `actionlint` 1.7.7 — PASS. The resumed environment lacked the prior temporary
  binary; the official release was downloaded and its SHA-256 verified before use.
- `uv run python -m scripts.qualify_funding_review --live` — PASS, isolated draft
  PR creation, non-force update, no empty PR and zero-write repetition.
- Authored document SHA-256 unchanged:
  `5a509f585d1e05eb996ab13bdff83064ea708f08db03ea4bfd79c22fe0d5ee65`.

## Readiness and remaining blockers

**Technical readiness:** funding changes are ready for technical review, with
real independent-run restoration and a separately tested data-only draft-PR path.
Final hosted push/PR regressions passed on 805028e; URLs are below. PR #5 stays draft; unrelated
program-intelligence production gates are not claimed complete by this report.

**Research completeness:** partial. Three evidence-backed programs are not three
verified eligible applications. Complete applicant/project eligibility and uncited
terms remain unresolved; IBB's fixed deadline is unknown; four official nomination
identities/conditions remain unverified under robots restrictions; actual semantic
inference is unavailable. No fabricated current terms, canonical URLs or scores.

**Production authorization:** absent for this milestone. No PR merged, schedule
enabled, production intel published, network/secrets settings changed or force
push performed. GitHub Actions PR creation is blocked by the observed policy. The existing
integration also cannot read that permission setting. Resolving it requires owner
policy authorization and reconciliation of the retained sandbox refs; default-
branch production token/branch-rule behavior still needs its own authorized test. Artifact expiry and source/model outages remain
operational risks, handled with explicit unknowns, fail-closed restoration and
retained evidence rather than promotion into the active shortlist.

## Final hosted checks

Final tested code: `805028e569079feaacab672dfeeaa4cdc224d789`.
The automatic-token sandbox ran on `bdf7d832f2b86051017e05805088e2042811fbe2`;
subsequent generic-model retry changes do not change that publication path.

- [Push regression 39991873667](https://github.com/JsonLord/Horizon/actions/runs/39991873667): success on final code.
- [PR regression 39991878771](https://github.com/JsonLord/Horizon/actions/runs/39991878771): success on final code.
- [Earlier push regression 39990560292](https://github.com/JsonLord/Horizon/actions/runs/39990560292): success.
- [PR regression 39990570621](https://github.com/JsonLord/Horizon/actions/runs/39990570621): success.
- [Automatic-token sandbox 39990565222](https://github.com/JsonLord/Horizon/actions/runs/39990565222): qualification job completed; **PR publication BLOCKED (403)**, normal production jobs skipped.
- [Read-only funding maintenance 39937114312](https://github.com/JsonLord/Horizon/actions/runs/39937114312): success on preceding source/data audit code `1f91795`.
- Signed-URL hardening regressions [39989900641](https://github.com/JsonLord/Horizon/actions/runs/39989900641) / [39989909381](https://github.com/JsonLord/Horizon/actions/runs/39989909381): success.

There are no failing local or regression tests. Successful qualification execution
must not be confused with successful automatic PR creation: that API operation
was attempted and refused, with exact evidence retained. PR #5 remains draft and
is ready for technical review of the funding changes, with A/B/E/F explicitly
partial and production activation unauthorized.

## Changed files

- Workflow/agent controls: `.github/workflows/horizon-intel.yml`,
  `.github/workflows/research-validation.yml`, `AGENTS.md`.
- Funding/runtime code: `src/research/funding/review.py`,
  `src/research/funding/storage.py`, `src/research/programs/laya.py`,
  `src/research/programs/review.py`, `src/research/analyzers.py`.
- Commands: `scripts/funding_research.py`, `scripts/qualify_funding_acceptance.py`,
  `scripts/qualify_funding_review.py`, `scripts/check_funding_acceptance.py`.
- Funding data: nomination review JSON/Markdown, KB navigation, and the three
  opportunity folders' records, evidence, resource registers, overviews and history.
  The authored starting document was not modified.
- Tests: funding acceptance/review/research tests, native model relevance tests,
  OpenAI-compatible model tests. Existing funding tests remain passing.
- Documentation: this report, `docs/agent-research.md`, workflow guide, two hosted
  proof JSON files, durability/PR/token proof JSON files and alternative-search
  metadata. `git diff --name-only a549be1..HEAD` gives the exact tracked inventory.
