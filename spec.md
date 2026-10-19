# SPEC — Horizon Global News & Institutional Intelligence

**Repository:** https://github.com/JsonLord/Horizon
**Target:** GitHub repository + GitHub-hosted Actions runners ONLY; no other deployment
**Status:** Implementation specification (not a claim that these features are already implemented)
**Date:** 2026-10-09
**Primary objective:** Turn Horizon into a credential-free-by-default world-news and institutional-research service that external agents can control and whose published results other agents can read directly from GitHub.

## 0. Non-negotiable constraints (GitHub-only deployment)

1. **GitHub-hosted Actions runners are the ONLY execution environment for scheduled or remotely triggered research.** No Hugging Face Space, Debian runtime, VM, hosted API, web server, self-hosted runner, public port, database server, or background daemon. Local CLI/test execution for development is permitted, but is NOT deployment.
2. **Preserve the existing Horizon application** (legacy CLI, setup wizard, scrapers, local stdio MCP, existing user configurations, and tests). Existing local Docker CLI use may remain for backward compatibility, but is NOT a deployment target. Revert PR #1 Docker/web-server-specific changes where unnecessary.
3. **Credential-free sources and deterministic offline scoring are the default.** Use public Google News RSS, GDELT, official RSS/Atom and permitted public feeds; do not require news, commercial LLM, Hugging Face, or private network API credentials.
4. **GitHub permissions are different from external service credentials.** GitHub Actions uses its built-in short-lived `GITHUB_TOKEN` to publish. An external agent must already have GitHub authorization to dispatch workflows or open a PR; anonymous agents may only read the public `intel` branch. Do not imply unauthenticated workflow dispatch is supported.
5. **Agent control is GitHub-native.** External agents use `workflow_dispatch` (or optionally approved PRs changing versioned profiles); job state and logs live in Actions workflow runs, durable public results live on the `intel` branch. Do not require any custom FastAPI/HTTP server or API bearer token.
6. **Only approved, bounded targets and inputs can run.** Validate profile IDs, time windows, sources, query bounds, and publication policy. Ad hoc/private questions must never be silently committed to the public intelligence branch; route to authorized Actions artifacts or require profile review.
7. **Load prior published state BEFORE analysis**, even on a newly provisioned runner, so change detection is correct across independent runs. Failed/no-new-item executions must not erase the last successful snapshot.
8. **Actions permission boundary:** collection job receives `contents: read`; only publication job gets `contents: write`, with concurrency controls and safe retries, no force pushes or long-lived PAT. Respect branch rules and explicit authorization failures.
9. **No sensitive artifacts:** avoid private prompts, IPs, credentials, internal URLs, paywalled bodies, copied copyrighted content, and unreviewed raw scraped HTML in commits/logs. Publisher must validate schemas and provenance before pushing.
10. **Actual live acceptance is a GitHub Actions run.** Never claim a scheduled/dispatch workflow or publication is verified solely because local tests or a developer-authorized Git push succeeded.

## 1. Verified existing foundation / observed gaps

Inspect and reuse these files before editing:

- `src/orchestrator.py`: native parallel scrapers, cross-source/topic dedup, AI processing, summary generation. GDELT, Google News, and OSS Insight are imported and called when enabled.
- `src/models.py`: `ContentItem`, `SourcesConfig`, `GDELTConfig`, `GoogleNewsConfig`, existing `SourceType` values.
- `src/scrapers/{rss,gdelt,google_news,github,reddit,telegram,hackernews,openbb}.py`: source adapters.
- `src/mcp/server.py`, `src/mcp/service.py`, `src/mcp/run_store.py`, `src/mcp/horizon_adapter.py`: existing MCP interface and stage persistence; `hz_run_pipeline`, `hz_get_run_stage`, and `hz_get_run_summary` already exist.
- `src/mcp/horizon_adapter.py`: `VALID_SOURCES` currently omits `gdelt`, `google_news`, and `ossinsight`, even though the orchestrator knows them. Extend the allowlist, filtering logic, and diagnostics consistently.
- `data/mcp-runs/` is ignored by `.gitignore`; a run artifact there is NOT a GitHub-published research report.
- `src/ai/client.py` requires a configured model/API key in common paths; introduce an explicit optional/offline analyzer pathway rather than fabricating a token or silently treating an unreachable model as successful.
- Keep any legacy `Dockerfile` / `docker-compose.yml` oriented to the existing CLI only; no container or HTTP application is needed for GitHub-hosted Actions execution.
- `.github/workflows/daily-summary.yml` currently runs weekly. Add new workflows rather than breaking that legacy one before replacement is validated.

## 2. Architecture and execution contracts

### 2.1 Component boundaries

- **Profiles:** versioned JSON configs defining *what* to monitor; they never hold secrets.
- **Collector:** adapt existing scrapers with bounded multi-query collection and provenance normalization.
- **Research pipeline:** fetch → normalize → dedup → profile relevance → optional model enrichment → verify/attribute → report → change detection.
- **Job execution:** one approved Actions workflow run per request; use GitHub run IDs, job conclusions and logs as the authoritative status interface, not an always-on in-process job queue.
- **Archive publisher:** local, validated, versioned Markdown+JSON artifacts; GitHub Actions commits successful outputs to an `intel` branch (or documented equivalent read-only artifact branch).
- **Agent interface:** GitHub workflow dispatch, Actions status/artifacts and public `intel` branch files; GitHub is already the remote API and publication host. No custom hosted HTTP app.
- **MCP interface:** retain existing local stdio MCP for developer/agent clients, with optional GitHub-backed workflow dispatch/read wrappers; no hosted MCP daemon.

### 2.2 Modes

**`world_radar`:** broad global news across regions and subjects, multiple bounded GDELT/Google News queries, primary RSS, region/source diversity, dated snapshots.

**`institution_watch`:** named persistent institution entity, aliases, domains, official primary sources, publication tracking, official-vs-media classification, change timeline, profile-specific relevance.

**`research_job`:** constrained agent-specified question, permitted sources, time range, target institutions, depth; produces a self-contained report and can optionally become a saved profile through an authorized operation.

### 2.3 GitHub-only runtime and credential boundary

**Scheduled route:** `.github/workflows/horizon-intel.yml` checks out the source, installs dependencies using `uv sync --frozen`, restores verified prior `intel` state for comparisons, gathers bounded public information, generates grounded reports, validates output, and publishes to `intel` using its job-scoped `GITHUB_TOKEN`.

**Agent-triggered route:** an authenticated agent dispatches `horizon-intel.yml` with an approved `profile_id` and bounded `lookback_hours` using GitHub's REST Actions API, `gh workflow run`, or an installed GitHub integration. The agent tracks the workflow run via GitHub, then retrieves its published report through `intel/manifest.json` and profile-specific latest pointer. No separate HTTP endpoint or bearer token is required beyond GitHub's own authorization.

**Ad hoc investigations:** use approved profile definitions or a separate bounded `workflow_dispatch` mode that produces access-controlled Actions artifacts without exposing private questions on the public archive. Do not enable arbitrary untrusted crawls or publish free-form private prompts. For persistent research, agent proposes a validated profile as a PR for review.

**Optional models:** no private gateway required; deterministic/no-LLM baseline works in GitHub-hosted runner. Optional OpenAI-compatible endpoints must be externally reachable from Actions and expressly configured; errors fall back to deterministic extraction, never block the baseline.

## 3. Research profile contract

Create `src/research/profiles.py` with Pydantic validation and deterministic canonical serialization. Use JSON files initially to avoid an unnecessary YAML dependency. Store example/active profiles in:

```
profiles/
  world/
    global.json
    geopolitics.json
    science-technology.json
    economy.json
  institutions/
    ecb.json
    who.json
    cern.json
    helmholtz.json
  examples/
    custom-research.json
```

Required schema fields: `schema_version`, `profile_id`, `mode`, `name`, `enabled`, `topics`, `regions`, `languages`, `queries`, `sources`, `schedule_hint`, `lookback_hours`, `max_items`, `max_queries`, `ranking`, `output`, and an optional `institution` object containing stable `id`, official names, aliases, domains, and primary feed URLs.

For query fields require allowed source enum, query text bounded in length, locale, and declared topic/region. Profiles must be validated before scheduling. Ensure no arbitrary local paths, command execution, raw HTTP headers, credentials, or injected workflow expressions enter the profile contract.

Sample `profiles/institutions/ecb.json`:

```json
{
  "schema_version": "1.0",
  "profile_id": "institutions/ecb",
  "mode": "institution_watch",
  "name": "European Central Bank",
  "enabled": true,
  "institution": {
    "id": "ecb",
    "names": ["European Central Bank"],
    "aliases": ["ECB", "Europäische Zentralbank"],
    "official_domains": ["ecb.europa.eu"],
    "official_feeds": []
  },
  "topics": ["monetary_policy", "speeches", "projections"],
  "regions": ["EU"],
  "languages": ["en", "de"],
  "queries": [
    {"source": "gdelt", "text": "\"European Central Bank\"", "language": "english"},
    {"source": "google_news", "text": "\"European Central Bank\" monetary policy", "language": "en", "country": "DE"}
  ],
  "sources": ["gdelt", "google_news", "rss"],
  "schedule_hint": "daily",
  "lookback_hours": 48,
  "max_items": 60,
  "max_queries": 8,
  "ranking": {"mode": "institution_relevance", "minimum_score": 3.0},
  "output": {"languages": ["en"], "markdown": true, "json": true, "changes": true}
}
```

The `official_feeds` example is deliberately empty: discover and validate actual official URLs before adding them; never invent feeds. Provide similarly realistic but bounded seed profiles for world regions/topics and the other institutions. Allow new institutions by validated profile registration, not hard-coded target-specific logic.

## 4. Source collection: global breadth + institutional depth

1. Fix `src/mcp/horizon_adapter.py` source selection for `gdelt`, `google_news`, `ossinsight` and ensure disabling other sources actually disables them in the effective config.
2. Add a profile compiler that maps **multiple** GDELT/Google News query specs to bounded scraper invocations while preserving the existing single-query `SourcesConfig` for older configs. Do not mutate shared config objects in concurrent jobs.
3. Preserve source `publisher`, `source_country`, `language`, `published_at`, `fetched_at`, `search_query`, `profile_id`, `institution_id`, original and canonical URLs, and `source_kind: primary|secondary|social|unknown` in stable metadata fields where available. Mark unknown rather than guessing.
4. Distinguish **publisher geography** from **event geography** and label geographic inference with confidence and evidence.
5. Apply URL canonicalization, normalization, strict URL validation, cross-source and semantic dedup with original source references retained. Dedup must not erase independent corroborating publishers.
6. Add institutional official-domain/source matching; an article mentioning an institution is not automatically an official institutional statement.
7. Favor geographically diverse sources. Define per-region quotas or balancing rules and expose actual `coverage`/`missing_regions` indicators; never promise global exhaustiveness.
8. Use timeouts, bounded concurrency, retries with backoff, response-size ceilings, and per-source metrics; handle 429, malformed RSS, empty pages, stale timestamps, and unavailable feeds gracefully.
9. Never bypass paywalls, authentication, robots restrictions, access controls, or terms. Cite original pages instead of copying copyrighted article bodies into the repository.
10. Validate GDELT query semantics and limits; do not assume unlimited historical coverage or all regions covered by one query.

## 5. Analysis, evidence and no-LLM fallback

Introduce `src/research/analyzers.py` and `src/research/reporting.py` using the existing AI analyzer and summarizer when available.

- `ai.mode: auto | local | off`; `auto` uses a configured available compatible endpoint or deterministic fallback; `off` guarantees no LLM calls.
- Deterministic baseline computes transparent relevance scores using declared profile keywords, source kind, recency, region, and topical matches. Never describe these as probabilistic truth/confidence ratings.
- Extractive summaries may use titles, feed descriptions, and properly attributed excerpts, avoiding generative ungrounded extrapolation.
- Optional model summaries must preserve evidence IDs and produce structured outputs validated against schema; refuse/flag unsupported claims. Avoid prompt injection from article HTML, summaries, or institutional documents.
- Each finding has stable `finding_id`, `event_id` when applicable, institution IDs, topic/region tags, publication and observation timestamps, `source_ids`, evidence snippets or location metadata, verification status, uncertainty/limitations, and provenance.
- Distinguish `importance`, `profile_relevance`, `corroboration`, and `verification` instead of presenting one numerical score as all four.
- A single primary-source announcement can be included as `single_primary_source` when accurately attributed; two secondary reports are not a substitute for a primary source.
- Determine `new`, `updated`, `contradicted`, `resolved`, `unchanged` against prior archived reports. Contradictions are surfaced for review, not automatically resolved by an LLM.
- Mark run status `complete`, `partial`, `failed`, or `no_new_items` based on source/analysis results. No invented content when zero items arrive.

## 6. Versioned Git archive contract

Retain `data/mcp-runs/<run_id>/` as temporary local stage storage. Do **not** make it the published knowledge interface.

Publish a compact data tree on the `intel` branch (or an explicitly justified, deterministic alternative):

```
intel/
  manifest.json
  latest/
    world.json
    world.md
    institutions/
      ecb.json
      ecb.md
      who.json
  reports/
    world/2026/10/09/<run_id>/
      report.json
      report.md
      manifest.json
    institutions/ecb/2026/10/09/<run_id>/
      report.json
      report.md
      manifest.json
  events/
    2026/10/09/events.jsonl
schemas/
  profile.schema.json
  research-report.schema.json
  manifest.schema.json
```

The outer `intel/` prefix is inside the archive branch. Read-only URLs, file paths, and GitHub tree refs returned by the API must refer to the **real** published layout; don't generate non-existent URLs. If an orphan branch is chosen, provide an automated bootstrap without deleting or overwriting existing data.

Report schema (at minimum):

- `schema_version`, `report_id`, `run_id`, `profile_id`, `question`, `created_at`, `time_window`, `status`, `model_used` (`null` for fallback), `analysis_mode`, `coverage`, `statistics`, `findings`, `sources`, `limitations`, `changes`, `errors` (sanitized), and links to canonical reports.
- Every source: stable `source_id`, original URL, canonical URL, publisher, source kind, publication timestamp if known, retrieval timestamp, origin collector, and optional content fingerprint.
- Every finding: stable ID, summary, classification, relevant institutions/regions/topics, source IDs, verification, confidence fields only when supported by actual evidence, and change type.
- A manifest: artifact checksum, SHA/commit or snapshot ID when known, content type, bytes, generated time, status, schema version, and paths.
- `latest` indexes should point to complete/partial reports with clear status; failed runs must never replace a successful latest report silently.
- Write archive outputs atomically locally; validate schema and links before publish. Resolve runs idempotently. Never commit secrets, cookies, binary archives, full article copies, or oversized raw API responses.
- Keep public repository output bounded (retention/pruning policy and an explicit maximum per report); raw large materials stay out of Git.
- GitHub publication job must serialize writes or safely rebase with bounded retries. Report branch-rule permission errors clearly rather than falsely declaring success.
- Provide stable filenames and `README` examples for consumers using GitHub raw URLs and `git show intel:intel/latest/world.json`.

## 7. GitHub-native remote control (NO hosted HTTP API)

GitHub provides the only remote interface. Do NOT deploy FastAPI or a dashboard. For the PR #1 adaptation, remove `deploy/huggingface/`, deployment-only `src/api/` and `fastapi`/`uvicorn` dependencies unless other pre-existing behavior demonstrably requires them. Keep the pre-existing Horizon CLI and local stdio MCP. Preserve any useful pure Python research service functionality and rewire it to the workflow.

**Workflow dispatch interface** via `.github/workflows/horizon-intel.yml`:

- `profile_id`: string, must match an approved enabled versioned profile; empty uses bounded scheduled defaults.
- `lookback_hours`: integer, 1–168; schema-validated after parsing.
- Optional `output_mode`: `public_profile` (publish approved profile results) or `private_artifact` (only if implemented with authorization and privacy protections). Do not log private question text.
- Optional ad hoc question or additional query scope only if tightly validated and kept OUT of public archive and public logs; otherwise omit support and use PR-based profile registration.

**Authenticated agent control:** caller uses existing GitHub authorization to dispatch, list runs, poll conclusion, retrieve artifacts as permitted, or open a profile PR. The workflow must exist on the default branch for `workflow_dispatch` to be recognized. GitHub controls roles and audit trail; do not mint or store new app-level bearer tokens.

**Unauthenticated agent reads:** read public `intel/manifest.json`, `intel/latest/world.json`, and `intel/latest/institutions/<id>.json` from the public `intel` branch. Provide stable paths, raw URLs, checksums and committed snapshot IDs.

**Job status:** GitHub workflow run ID and run URL; report metadata may include `workflow_run_id` and `source_commit` where available. Avoid claiming a local in-process job ID is independently pollable after runner exit.

## 8. MCP tools: preserve local integration without hosting it

Keep the existing `horizon-mcp` stdio command and existing stage-based `hz_*` tools working for developers and local agents. Research-specific profile/report tools may wrap the on-disk or GitHub-published archive. Where possible add thin optional GitHub-backed helpers for listing profiles, reading latest reports, dispatching approved workflows and polling GitHub run status, using **the calling agent's existing GitHub authentication**, never a server-side shared secret.

Do not expose stdio MCP as a network service. Do not build a new hosted MCP endpoint, persistent job queue, FastAPI wrapper, or app-level token system. Remote control works via GitHub Actions' existing API; agents without GitHub write access can read public published results but cannot trigger jobs.

## 9. Scheduled workflows, history and publication

- Keep or extend `.github/workflows/horizon-intel.yml`: `schedule` for world/institution profiles and `workflow_dispatch` for authenticated external agent requests. Scheduled jobs can be late, can be disabled for inactivity, and have timeout/resource limits; do not promise always-on monitoring.
- Prefer **GitHub-hosted** `ubuntu-latest`; no self-hosted runner or third-party compute. Use bounded `timeout-minutes`, source concurrency, retries, size limits, and workflow `concurrency` groups.
- **Restore historical state before collection:** fetch `intel` branch or inspect public raw archive; validate manifests/checksums and hydrate the prior successful per-profile report. Then calculate new/updated/unchanged evidence against that snapshot. Store previous snapshot commit ID in run metadata for reproducibility.
- Use collector `contents: read`, publisher `contents: write` only and the default Actions token. Publisher must safely merge concurrent updates without force-push and keep correct `latest` pointers.
- Expose precise workflow conclusions and report statuses. An Actions run finishing successfully is not equivalent to full source coverage; report `partial` when collectors fail. Failed/empty runs must preserve last successful latest report.
- Keep bounded debugging artifacts and clear logs with no unreviewed source bodies, token echoes or private prompts. Validate workflow input by Pydantic/schema, pass via environment rather than unquoted shell interpolation.
- Publish branch paths that public agents can read anonymously; external workflow dispatch requires a GitHub identity with appropriate permissions.

## 10. GitHub-hosted runner packaging

- GitHub Actions checks out the source, installs Python and `uv`, uses `uv sync --frozen` / locked dependencies, runs the research CLI and publishes outputs. It requires no separate server or container build.
- Keep the repo's historical `Dockerfile` and Compose **only if needed for pre-existing local CLI compatibility**; revert Space-specific `EXPOSE 7860`, `uvicorn` entrypoint and Space build metadata.
- Remove Hugging Face deployment-only files, startup instructions, environment variables and tests. Do not install `fastapi`/`uvicorn` solely for an unused hosted interface.
- No `HORIZON_AGENT_TOKEN`, no Space deployment target, no HTTP listen socket, no external service requiring uptime.
- Defaults: `HORIZON_AI_MODE=off` or deterministic `auto` fallback, `HORIZON_ARCHIVE_REPO=JsonLord/Horizon`, `HORIZON_ARCHIVE_REF=intel`. Protect optional secrets using Actions environment; no new external API secret required for the baseline.
- Every runner has a fresh ephemeral checkout: restore prior branch state before classification, and publish durable results before termination. Keep data volume, minutes and token use bounded.

## 11. Safety, provenance, correctness

- **SSRF/network:** only allow HTTPS (or explicitly approved safe HTTP public feeds), DNS/IP safeguards against localhost, link-local, RFC1918, cloud metadata and internal tailnet endpoints for *untrusted submitted URLs*, redirect re-validation, hostname allow/deny rules, strict timeouts and response sizes.
- **Authorization:** GitHub identity/permissions protect workflow dispatch and repository updates. Never introduce unauthenticated public job triggers or a custom bearer-token-controlled service; use runner timeouts, job concurrency and strict validated inputs.
- **Prompt injection:** scraped pages, RSS descriptions, institutional PDFs/text are untrusted evidence and cannot modify system prompts, file paths, GitHub operations, auth, or tool permissions.
- **Privacy:** do not publish private source URLs containing secrets, IPs, tokens, arbitrary prompts from other users, unredacted error payloads, or proprietary article bodies.
- **Evidence:** keep original source URL, publisher, publication/observation dates, source kind and normalized evidence IDs; never synthesize fake publication dates or misleading corroboration.
- **Source failures:** partial coverage should be visible, retries bounded. Detect duplicates across languages, syndications, reruns and daily snapshots without discarding provenance.
- **Scope:** no paywall or CAPTCHA bypass, credential harvesting, stealth scraping, or protected-source collection.

## 12. Tests and acceptance criteria

### Unit / fixture tests (offline, no credentials)

1. Profile parse, validation, deterministic serialization, old-config compatibility, maximum bounds, invalid IDs and unsafe URL rejection.
2. MCP adapter correctly includes and excludes **all supported sources**, especially GDELT, Google News and OSS Insight.
3. Fake feeds and fake GDELT/Google responses drive multiple queries, correct language/region metadata, dedup and attribution.
4. Rules-only mode produces grounded reports with `model_used: null` and correct `no_new_items`/partial outcomes.
5. Evidence/source links in findings refer to existing source records and have stable IDs across reruns.
6. Institution official source vs secondary media vs mere mentions are classified correctly in fixtures.
7. Versioned report, JSON Schema, Markdown, manifest/checksum and changed-event outputs are valid, including empty and failed runs.
8. Git publication dry-run, branch bootstrap, concurrency-safe publishing, denied permissions, failed push/retry, and no secret in logs/artifacts.
9. Workflow control: input validation, approved profiles, denied/unauthorized dispatch handling, workflow-run status mapping, no public ad hoc prompt publication, and no custom HTTP server dependency.
10. MCP: old tools still work; high-level profile/job/report tools work and do not expose secret-bearing effective config.
11. Fresh-runner history restoration, cancellation/timeout behavior and retriable publication; protect against path traversal and SSRF/redirect to private targets.
12. Regression: all preexisting `tests/` pass; smoke check `scripts/check_mcp.py` passes.

### Local integration / workflow acceptance

- `uv sync --frozen --extra dev && uv run pytest` is green; retain baseline Horizon CLI and existing MCP smoke checks.
- Research CLI completes bounded fixture runs with no model/news API key. Archive artifacts and manifest checksums validate.
- Test a **two-day scenario with separate fresh checkout directories**, restoring the first day's `intel` archive before the second day's analysis, proving unchanged stories are not all mislabeled new.
- `actionlint` (or equivalent) passes; the workflow itself uses only the automatic job token for publication and does not interpolate untrusted workflow inputs into shell source.
- The `intel` branch is consumable by a separate clone and unauthenticated raw-file reader; fresh latest reports preserve previous history and never expose private job questions.
- Explicitly test denied write permissions, concurrent publication collisions, collector 503/429, duplicate item handling and partial coverage.

### Live acceptance where authorized

- The approved workflow exists on the default branch and a genuine `workflow_dispatch` succeeds on a **GitHub-hosted Actions runner**, using its automatic token for publication.
- A committed `intel` update is verified by branch SHA and actual raw URLs; repeat a second run and inspect change classification and persisted historical state.
- Separately verify institutional results and global report access with no credentials for public reading.
- If no authorized merge/dispatch access is available, complete code/tests and state precisely what was not exercised. No Hugging Face or other deployment is part of acceptance.


## 13. Implementation order and deliverables (adapt PR #1)

Work on existing `feat/agent-research` PR #1. Do not recreate existing implemented features merely to match original design; adjust them to the runner-only architecture:

1. **Audit:** inspect the current diff/PR branch, workflows, archive and previous deployed status. Mark all hosted Space/FastAPI requirements as explicitly superseded by this GitHub-only revision.
2. **Prune deployment:** delete `deploy/huggingface/` and Space-specific `src/api/` server code/dependencies if no longer used. Restore pre-existing local CLI Docker/Compose behavior. Keep shared research pipeline, local MCP, profiles and schemas.
3. **Remote control:** standardize `workflow_dispatch` inputs, profile allowlisting, GitHub-based job monitoring, and agent quick-start documentation for `gh workflow run`, Actions REST API and public `intel` reads.
4. **Restore history:** hydrate prior successful `intel` snapshots before analysis on every fresh runner; compare changes and retain correct stable IDs.
5. **Improve sources:** validate official institutional feeds and reduce irrelevant generic headlines without adding third-party credentials.
6. **Validate:** run unit/fixture tests and two-run fresh-checkout integration, static Actions validation, and real workflow dispatch after merge if authorized; verify commit and public archive reads.
7. **Document:** update repo-root `spec.md`, `docs/agent-research.md`, README, workflows and tests. Push fixes to the current PR branch without a force push; never imply deployment is required.

Deliverables: approved profile files, credential-free research CLI, durable `intel` archive, working Actions workflows, developer-friendly local MCP, comprehensive tests, and exact agent instructions. **No Space, FastAPI service, external VM, or self-hosted deployment.**

## 14. Explicit non-goals

- No Hugging Face deployment, HTTP server, FastAPI, hosted dashboard, VM, Debian daemon, self-hosted runner, or public port.
- No new standalone scheduler, hosted agent framework, app-level authentication, mandatory model API, fine-tuning or vector database.
- No bypass of restricted/premium news sources; no free-form unauthenticated research execution.
- No guarantee of uninterrupted coverage or 24/7 uptime from scheduled GitHub Actions.
- No independent authoritative truth qualification; downstream evidence systems may assess reliability.

## 15. Reference implementation links

- Source / PR: https://github.com/JsonLord/Horizon/pull/1
- GitHub Actions workflow dispatch: https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- GitHub Actions permissions: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- GitHub Actions scheduled events: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule


---

# Extension SPEC — Branch-Aware Actions and Weekly Program Intelligence
**Added:** 2026-10-19
**Status:** Implementation requirements; not evidence of deployment.
**Precedence:** This section extends Sections 0–15 above. Existing GitHub-only deployment, credential-free baseline, approved-profile validation, local CLI/MCP compatibility, provenance, \`intel\` archive, publish isolation and live acceptance remain normative. If implementation conflicts, preserve the stricter existing boundary. No new Hugging Face-hosted Horizon runtime or public API.

## 16. Scope and branch architecture
Build an additive \`program_watch\` research profile/mode for incubators, accelerators, founder programs, startup grants, venture studios, fellowships and compatible ecosystem opportunities. Include (a) weekly revalidation of known program URLs, (b) bounded discovery of new offers, (c) evidence-qualified structured records and change tracking, (d) optional Laya semantic fit evaluation, and (e) an audited, Markdown+JSON review/publishing flow.

Branches have **distinct purposes**:
- \`main\`: trusted Actions workflow definitions, existing application, review gate, and scheduling. No experimental data pushed by default.
- \`feature/**\`, \`research/**\`, \`automation/**\`: branch-scoped **read-only validation** via push/PR; no publication, Pages deployment or write token. Preserve existing named-branch coverage.
- \`research/program-intelligence\`: reviewed implementation branch once the feature is merged/activated; workflow dispatch must explicitly and safely select an allowlisted ref.
- \`automation/program-intelligence\`: optional generated-data PR head with no authorization to change executable workflows, code, policies or security controls.
- \`intel\`: retain the canonical externally readable archive contract from Section 6. Publish only validated, approved public program profile data through its existing safe publisher; do not introduce a second competing public archive.
Never remove existing research modes or repurpose the \`intel\` root.

GitHub \`schedule\` executes the workflow from default branch, **not** the feature branch. \`workflow_dispatch\` is recognized only for a workflow present on default branch and can be dispatched with an explicit ref. Implement default-branch scheduled control calling an approved ref (or another rigorously justified mechanism). Until the orchestration workflow is merged into \`main\`, run branch validation and bounded manual qualification; do not claim weekly activation.

## 17. Inventory audit and workflow hardening
Inspect existing \`.github/workflows/horizon-intel.yml\`, \`research-validation.yml\`, \`daily-summary.yml\`, \`deploy-docs.yml\`, archive publisher, profiles, tests and existing PRs before edits. Record baseline behavior and any already-working features.

- Extend \`research-validation.yml\` push filters to \`main\`, \`feature/**\`, \`research/**\`, \`automation/**\` (and preserve currently supported branch), plus PR validation; include new program scripts, configs, schemas, tests and workflows in path coverage. Use \`contents: read\`; no secrets on untrusted PRs and no \`pull_request_target\` execution of untrusted code.
- Preserve the currently live \`horizon-intel.yml\` daily schedule/dispatch and \`daily-summary.yml\` until independently proven safe; avoid broadening existing publish/deploy jobs to every branch.
- Run cross-branch research against checked-out **allowlisted immutable commit SHA/ref**, verified to belong to this repository, not arbitrary user-provided git URLs, shell expressions, or PR heads. Do not pass freeform strings into shell scripts.
- Split collector/classifier (read-only) from publisher (write), with minimal job permissions and artifact boundary; never execute unreviewed research-branch code in a job that holds \`contents: write\` or privileged secrets.
- Protect concurrent runs with per-profile/per-ref collection groups and a serialized publication boundary. Reject stale generated updates or rebase/re-evaluate against the latest archive before committing; no force push.
- Document GitHub Actions self-dispatch limitations, token privileges, branch protection/rulesets and how the scheduler obtains run status; avoid assuming that a \`GITHUB_TOKEN\` push triggers a separate push workflow.
- Prefer a trusted, default-branch controller invoking a reviewed **default-branch** runner after qualification. During experiments, dispatch read-only branch workflows with \`--ref\` for live assessment. If using a staging branch long-term, permit only reviewed/pinned code and no privileged execution.

## 18. Program profile and criteria contract
Add \`program_watch\` to the existing research profile schema, compiler, validators, CLI and (as useful) local MCP, reusing Section 3 conventions. Suggested approved profile ID: \`programs/incubators\`. Profile config declares finite lookback/search window, enabled collectors, source/URL caps, languages, regions, budgets, output policy, target kinds and freshness limits. Every dispatch must validate the approved profile identifier.

Create:
- \`config/program-relevance.yaml\` (or JSON if aligning to existing Pydantic/JSON convention): versioned, validated machine-readable scoring policy; initial **provisional** weights explicitly marked awaiting user refinement.
- \`docs/PROGRAM_RELEVANCE.md\`: transparent plain-language explanation of inclusion/exclusion criteria and uncertainty.
- \`config/program-sources.json\` and \`config/program-discovery.json\` (or equivalent approved versioned profiles): initial known URLs and bounded discovery seeds.

The criteria distinguish (1) deterministic hard eligibility (geography, founder/entity restrictions, stage, deadline and required residency), (2) strategic relevance to AI/software ventures, inclusive UX, entrepreneurship, mentoring, founder networking and relevant innovation projects, (3) benefit, funding/equity tradeoff, application effort and opportunity cost. Unknown eligibility is **review_required**, not automatic rejection. Personal/private profile attributes must remain outside public \`intel\`; a public profile may contain only user-approved non-sensitive interests.

For initial migration, preserve verbatim legacy rows, including the Kilo Health incubator URL \`https://incubator.kilo.health/\`, related \`https://ventures.kilo.health/\`, old \`2025-02-01\` date, and \`Kaospilots\` (which has no authoritative source URL in the uploaded file). Mark the old date as **historical/unverified current deadline** until confirmed from an official source. Do not invent a Kaospilots application URL or treat the old note as an active offer. Discover relevant source pages and distinguish general educational offerings, advisory/project collaboration and actual open programs.

## 19. Data model and verification
Use structured JSON as source of truth and render \`Incubator and Programs.md\` deterministically. If the original file is not already tracked in Horizon, import it as an explicitly attributed user-provided seed without inventing verified claims; never overwrite unrelated documents.

Each record must include: stable \`program_id\`, name, operator, canonical/original/application URLs, program type, target domains, eligible countries, location/remote policy, company/founder stage, application status (\`open|upcoming|closed|unknown\`), deadline + timezone/precision, benefits, funding/grant/equity/cost terms, eligibility, application steps, last_checked UTC, last_verified UTC per fact, source evidence IDs/URLs, extraction status, material change events, and separate program-fit decision and model metadata. Unknowns are explicit null/unknown, not guesses.

Make **each material assertion traceable** to precise retrieved primary-source URL, captured observation timestamp and bounded quotation/snippet or selector/location; record supporting/counterevidence, publication date if available, content fingerprint and snapshot provenance. Prefer the official program/application page for live deadlines and availability. Search results, aggregators and LLM output only nominate candidates. An inaccessible page, redirect, challenge, absent form or stale landing page implies \`unknown\`, never \`open\` or \`closed\` by inference. Avoid copying full third-party page content.

Pipeline: restore last good state → refresh known URLs → bounded discovery via existing RSS/Google News/GDELT/official sites or approved safe search adapter → canonicalize and dedup programs, not just URLs → extract structured fields → primary evidence verify → compare historical state → deterministic eligibility checks → optional Laya score → render and validate → publish/review. Honor robots/terms and SSRF protections on every redirect; budgets/timeouts/mime/size ceilings. On partial runs retain last-known facts with clear staleness and last-check failure; no destructive replacement of good snapshots.

Suggested program paths within **published** \`intel\` branch: \`intel/latest/programs/incubators.json\`, \`intel/latest/programs/incubators.md\`, \`intel/reports/programs/incubators/YYYY/MM/DD/<run_id>/{report.json,report.md,manifest.json}\`. Retain existing manifest semantics, source links, checksums, previous snapshot SHA, run status and statuses \`complete|partial|failed|no_new_items\`. Keep a distinct human-review file \`Incubator and Programs.md\` at repository root in an automation PR, not as a conflicting archive root.

## 20. Laya adapter and numerical decision contract
Laya/Needle Router Space \`https://huggingface.co/spaces/Leon4gr45/needle-router\` is an **optional outbound model dependency**. It is NOT Horizon's deployment or a required runtime. Only GitHub-hosted runners execute this pipeline. Inspect documented/live actual Needle Router endpoint and request/response schema (prefer the verified \`/v1/gates/route\` or supported route contract) and confirm whether this endpoint performs classification versus routes to a downstream generative model. Do not invent an HTTP payload or assume model-generated JSON is exposed by the routing gate. Integrate the verified usable inference path; otherwise log \`model_unavailable\` and run deterministic scoring. Never send sensitive user profile data or non-public content to public model endpoints. Secrets, if ever needed, stay in approved Actions secrets and **only reviewed code** receives them.

Keep \`hard_eligibility\`, \`fit_score\`, \`evidence_confidence\`, \`model_self_reported_confidence\` and \`probability_relevant\` separate. Laya is asked for bounded dimension scores, reason codes, unknowns and cited evidence IDs—not whether a web claim is true. Validate schema, 0..1 ranges, evidence IDs, model identity, policy version, input hash and error/fallback provenance. The default weighted result is a **heuristic relevance score**, not a calibrated probability. Set \`probability_relevant: null\` / \`calibration_status: uncalibrated\` until holdout human labels justify calibration; document metric/method/sample size. Never present an arbitrary model confidence as a statistically valid probability.

Initial review bands (configurable): \`fit_score >= .75\` prioritize; \`.45 <= fit_score < .75\` review; lower archive as not prioritized. A deterministic ineligibility can suppress prioritization even with high model fit. Missing critical eligibility or primary evidence forces review. Preserve candidate and rejection decision history (without personal secrets), allow explicit human overrides, and never treat feedback as automatically improving calibration without measurement.

## 21. Weekly operation and review/promotion
Default weekly trigger: Monday \`07:23 UTC\` (non-hour-boundary), manual dispatch also available; exact local time varies with DST. Schedule belongs on \`main\`. During pre-activation, all workflows operate in no-publish/staging mode.

Produce:
1. A typed updated program dataset and change report listing added/changed/expired/unknown/deadline-soon candidates, evidence links, gaps and failures.
2. Stable rendered \`Incubator and Programs.md\` with columns/name, verified current status/deadline, eligibility, benefit, fit score and **actual** evidence links; mark historical/unverified entries.
3. A weekly Markdown digest \`reports/programs/YYYY-MM-DD.md\` (or equivalent archive report) with top qualified opportunities, review list, rejected reason codes, coverage and counts; do not claim exhaustive discovery.
4. Reviewable generated-data PR targeting \`main\`, with restricted data-only changed paths, no auto-merge, no workflows or executable code modifications, and a no-change skip.
5. After authorized approval, optional \`intel\` publication following existing Section 6 publisher; maintain public approved data and avoid exposing private preference details.

Generated-data branch updates must be resilient to prior open PRs, competing runs, branch rules and untrusted content; safe commit author/token and no \`pull_request_target\`. Report blocked PR creation or denied write permissions as honest partial outcomes. Do not let an unauthenticated or unapproved discovered URL become a dispatch target.

## 22. Deliverables and required tests
Deliver: updated profile/schema/CLI, policy and source registries, collector/refresh/discovery/verification/classifier/render modules under \`src/research/\` or shared equivalents, safe branch validation workflows, weekly trusted controller/workflow, tests, example generated data, updated README and user/agent operating instructions. Keep existing Horizon tests, CLI, local stdio MCP, news/intelligence reports, \`intel\` archive and Pages behavior intact.

Gates:
- **G0 baseline:** document current workflow triggers, branch/write boundaries, current \`spec.md\` contracts and current \`intel\` behavior.
- **G1 branch CI:** demonstrate push + PR test runs from a feature/research branch, read-only token, no Pages/production publication on branch push.
- **G2 seed & verification:** two legacy entries survive migration; live source checks distinguish obsolete deadline and uncertain application state. Tests cover redirect, closed/reopened round, dates with timezones, missing dates, blocked pages, stale facts, dedup and evidence provenance.
- **G3 discovery:** bounded real-web collection discovers and verifies independently sourced candidates; candidate ranking cannot publish unverified offers.
- **G4 Laya:** contract-test actual remote route/inference API, valid/invalid/timeout/fallback behavior, deterministic weight calculation and uncalibrated probability-null semantics. Prove model request sends no private profile contents.
- **G5 archive & PR:** second fresh GitHub runner restores previous state; manifests/checksums, stable IDs and change labels survive; restricted generated PR and idempotent reruns; earlier successful latest pointers retained after failure.
- **G6 LIVE qualification:** run GitHub-hosted Actions against an explicitly selected read-only research ref, confirm run ID, logs, output evidence and no writes. Only after review/merge/authorization test real Monday-path dispatch with controlled publication/PR. Do not equate fixture tests with live website/API validation.

Use \`uv sync --frozen --extra dev && uv run --extra dev pytest\`, legacy MCP smoke scripts, \`actionlint\`, schema checks, dry-run publish and safe remote live tests where authorized. Explicitly test robots/SSRF redirects, unauthorized refs, workflow-on-default-branch semantics, injected webpage text, false positive program status, no-key fallback, concurrency, permissions denied, lack of prior archive, and an inaccessible Laya endpoint.

**Acceptance/reporting:** provide branch and commit SHAs, actual Actions run URLs and conclusions, exact URLs/timestamps for representative independently checked opportunities, whether Laya inference or routing was truly exercised, summary of recorded decisions, source coverage gaps, PR link, and explicit not-done/blocked items. Never claim weekly cron activation or probability calibration without the corresponding evidence.

## 23. Implementation sequencing and non-goals
Implement in two reviewed workstreams: **A. branch/workflow safety**, then **B. program intelligence**. Deliver each gate with tests and commits, no force pushes. Do not merge, activate production cron, auto-merge generated PRs, change repository secrets/settings, or publish private profiles unless separately authorized. Existing recurring news research continues unchanged.

Non-goals: second always-on Horizon deployment; new server/API; self-hosted runner; local background agent; scraping behind access controls; arbitrary public URLs or unchecked query execution; inferred eligibility or deadlines; mandatory Laya; model-created probabilities without calibrated labels.
