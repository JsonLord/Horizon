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


# GitHub MCP controller and recurring schedule extension

The following approved task extends this acceptance contract. Its production controller and schedule requirements supersede earlier limits that described MCP only as a local research facade. Existing source/evidence/archive requirements remain in force.

# Codex Task — Horizon GitHub Actions MCP Controller & Scheduled Research

**Repository:** https://github.com/JsonLord/Horizon

**Existing work:**
- PR #1: GitHub Actions-based research engine, merged.
- PR #2: Agent instructions and source registry, commit `fcfc71c`, awaiting merge.
- Existing MCP server: `src/mcp/server.py`
- Existing workflow: `.github/workflows/horizon-intel.yml`
- Persistent research archive: GitHub branch `intel`

## Objective

Extend Horizon so external agents can fully manage **on-demand and recurring research through MCP**, while all production research execution happens exclusively on GitHub-hosted Actions runners.

An agent must be able to:

1. Discover available research profiles and institutions.
2. Trigger an approved research profile immediately.
3. Retrieve the resulting GitHub Actions run ID.
4. Monitor execution and publication status.
5. Retrieve the corresponding published research report.
6. Register a recurring cron schedule for a research profile.
7. Inspect, update, pause, resume and delete schedules.
8. Propose new research profiles and public source assignments through reviewable GitHub pull requests.

Implement real functionality, not documentation-only placeholders.

## 1. Architecture constraints

Horizon must remain GitHub-native and serverless.

**Allowed:**
- GitHub Actions runners for all production research.
- GitHub REST API and existing GitHub authentication for orchestration.
- GitHub branches, pull requests and workflow files for persistent configuration.
- The existing stdio MCP server running as a lightweight local interface within an external agent environment.
- The existing `intel` branch for research history.
- Existing news collectors and deterministic fallback.

**Not allowed:**
- Hugging Face Spaces.
- Always-on Horizon servers.
- Hosted HTTP/MCP endpoints.
- Background processes outside GitHub Actions for scheduled research.
- Additional paid APIs or mandatory external provider credentials.
- Arbitrary public workflow inputs that bypass source/profile approval.
- Committing credentials or secrets.

The MCP process must function primarily as a GitHub controller and research reader. It must not need to perform production scraping or analysis locally.

Keep existing local MCP research tools available for development and backward compatibility, but clearly label their jobs `local_only`.

## 2. Add GitHub Actions control tools to MCP

Implement the following tools, with explicit schemas, actionable error responses and appropriate authentication.

### `hz_dispatch_research`

Inputs:
- `profile_id` — approved profile
- `lookback_hours` — 1–168
- `request_id` — optional unique correlation identifier
- `ref` — default `main`, restricted to explicitly authorized branches

Actions:
- Verify the profile exists and is enabled in the chosen GitHub revision.
- Dispatch `.github/workflows/horizon-intel.yml`.
- Use GitHub's workflow-dispatch API with `return_run_details=true` when available.
- Return the actual GitHub run ID, run URL, submitted inputs and status.
- Fall back safely when the API returns only a 204 acknowledgement; never invent a run ID.
- Include bounded retries, timeouts and useful API error handling.
- Avoid duplicate dispatches when a valid idempotency key is supplied.

### `hz_get_workflow_run`

Inputs:
- `run_id`

Return:
- Workflow run ID and URL
- Requested profile
- Current status and conclusion
- Source commit
- Start and completion timestamps
- Collect and publish job states
- Failure reason when retrievable
- Archive publication status, if known

Distinguish:
- Runner completed
- Collection succeeded
- Publication succeeded
- Report appeared in `intel`

A successful Actions run must not automatically be treated as proof that the requested report was published.

### `hz_get_workflow_report`

Inputs:
- `run_id`
- Optional `profile_id`
- Optional response format (`json`, `markdown`, `summary`)

Actions:
- Locate the matching entry in `intel/manifest.json`.
- Match the recorded `workflow.run_id` and profile.
- Validate report identity and artifact checksums.
- Return findings, sources, historical changes, coverage and limitations.
- Provide versioned GitHub/raw links.

Never substitute a stale `latest` report when the requested run has no corresponding publication.

### `hz_list_workflow_runs`

Inputs:
- Optional profile
- Optional status
- Limit

Return recent relevant workflow executions and publication status.

Preserve the existing read-only research tools and resources.

## 3. Add recurring research schedules

This is a first-class requirement, not an optional future feature.

Agents must be able to create and manage cron schedules through MCP.

Examples:

- Monitor the ECB every weekday at 08:30 Europe/Berlin.
- Monitor CERN every Monday at 07:15 UTC.
- Research worldwide AI policy developments every six hours.
- Disable an institution watch temporarily.
- Increase a schedule's lookback from 24 to 72 hours.
- List upcoming research schedules and their most recent reports.

### Persistent schedule registry

Create:

`schedules/registry.json`

And a corresponding JSON Schema.

Example:

```json
{
  "schema_version": "1.0",
  "schedules": [
    {
      "schedule_id": "ecb-weekday-monitor",
      "name": "ECB weekday intelligence",
      "profile_id": "institutions/ecb",
      "cron": "30 8 * * 1-5",
      "timezone": "Europe/Berlin",
      "lookback_hours": 24,
      "enabled": true,
      "description": "Monitor ECB institutional developments each weekday"
    },
    {
      "schedule_id": "cern-weekly",
      "name": "CERN weekly research",
      "profile_id": "institutions/cern",
      "cron": "15 7 * * 1",
      "timezone": "UTC",
      "lookback_hours": 168,
      "enabled": true
    }
  ]
}
```

Validate:
- Unique, stable schedule IDs.
- Existing enabled profile IDs.
- Standard five-field cron expressions.
- Valid IANA time zones.
- Supported scheduling frequency.
- Lookback limits.
- Bounded number of active schedules.
- No arbitrary URLs, commands, scripts or additional workflow permissions.

### Native GitHub scheduling

**Prefer native GitHub Actions `on.schedule`, rather than a continuously polling scheduler.**

Implement a deterministic workflow-generation or synchronization mechanism that transforms the approved schedule registry into GitHub Actions schedules.

A robust approach is to generate a small workflow file per active schedule, with its native `cron` and `timezone`, calling a shared reusable Horizon research workflow.

For example:

`.github/workflows/horizon-sched-ecb-weekday-monitor.yml`

The generated workflow should invoke the existing shared research implementation with:
- Schedule ID
- Profile ID
- Lookback hours
- GitHub run provenance

Ensure that two schedules sharing the same cron expression but using different time zones remain distinguishable.

Avoid duplicating the entire research implementation across generated workflow files.

Migrate the existing default daily scheduled run into the new registry without accidentally creating duplicate runs.

### Schedule lifecycle

Adding a schedule should produce a proposed configuration change.

Updating a schedule should modify its registry entry and generated workflow.

Pausing should disable future scheduled execution without deleting historical reports.

Resuming should reactivate scheduling.

Deleting should remove the active workflow configuration while preserving research history.

Generated workflows must be reproducible from the registry.

Use CI to verify that the generated workflow files and schedule registry remain synchronized.

## 4. Schedule-management MCP tools

Implement:

### `hz_list_schedules`

Return registered schedules, including:
- ID
- Name
- Profile
- Cron expression
- Time zone
- Enabled/paused state
- Activation state
- Next expected execution
- Last known execution
- Latest report link

Clearly identify whether a schedule is active on `main` or pending PR approval.

### `hz_get_schedule`

Return the full schedule configuration, current activation state and available run history.

### `hz_create_schedule`

Inputs:
- `name`
- `profile_id`
- `cron`
- `timezone`
- `lookback_hours`
- Optional description

Validate the schedule, then create a Git branch and pull request containing the schedule registry and generated workflow changes.

Return:
- Schedule ID
- Proposed cron and time zone
- Pull request URL
- Activation state: `pending_review`

**Do not claim a schedule is active until its PR has been merged and the workflow is present on the default branch.**

### `hz_update_schedule`

Modify an existing schedule through a reviewable PR.

Support changing:
- Cron expression
- Time zone
- Lookback period
- Profile
- Description
- Enabled state

### `hz_pause_schedule`

Submit the configuration change needed to prevent future scheduled executions.

### `hz_resume_schedule`

Submit the configuration change needed to restore recurring execution.

### `hz_delete_schedule`

Submit a PR removing the schedule from active configuration.

Do not delete historical intelligence.

### `hz_get_schedule_runs`

Return runs and reports associated with a particular schedule ID, including missed, failed, partial and successful observations where that status can be established.

## 5. GitHub authentication and PR safety

Reuse the GitHub authentication already available to the agent, for example an authenticated GitHub CLI or appropriately scoped GitHub API credentials.

Do not introduce a separate Horizon API-key system.

Read-only MCP operations should continue working against public GitHub research artifacts without authentication whenever possible.

Writing operations require authorized GitHub access.

Schedule creation and updates should use reviewable pull requests by default.

Implement:
- Branch creation
- File updates
- PR creation
- Existing-PR reuse when appropriate
- Conflict detection
- Safe retry behavior
- Clear missing-permission errors
- No force pushes
- No automated merge without explicit authorization

Validate all changes before opening a PR.

Avoid allowing untrusted scraped content to influence GitHub repository operations.

## 6. Integrate schedules with the research archive

Every scheduled report must retain provenance including:

- `schedule_id`
- GitHub Actions `run_id`
- Workflow name
- Source commit
- Research profile
- Effective lookback window
- Scheduled execution time when available
- Actual collection timestamp
- Publication commit
- Previous comparison snapshot
- Research completion status
- Coverage limitations

Preserve existing JSON/Markdown schemas through backward-compatible additions and schema-version handling where necessary.

Scheduled runs must restore validated prior intelligence from `intel` before determining what changed.

Different schedules for the same profile should not corrupt one another's historical comparisons.

Prevent duplicate archival findings caused by retries or repeated executions of the same logical schedule occurrence.

Preserve last-good report pointers when collection fails.

## 7. Agent-facing workflow

The target experience is:

**User:** "Monitor the European Central Bank every weekday at 8:30 AM Berlin time."

Agent:
1. Calls `hz_list_profiles`.
2. Selects `institutions/ecb`.
3. Calls `hz_create_schedule`.
4. Receives the generated schedule proposal and PR link.
5. Presents the PR for approval.
6. After merge, verifies that the schedule is active.

Later, without manual intervention, GitHub Actions executes the scheduled research and publishes the results.

**User:** "What did Horizon learn from the ECB this week?"

Agent:
1. Calls `hz_list_schedules` or `hz_get_schedule_runs`.
2. Retrieves relevant published reports.
3. Calls `hz_get_changes` or `hz_get_workflow_report`.
4. Summarizes genuinely new findings with source references.

**User:** "Research CERN now."

Agent:
1. Calls `hz_dispatch_research`.
2. Obtains the GitHub run ID.
3. Polls `hz_get_workflow_run`.
4. Calls `hz_get_workflow_report` after publication.
5. Returns the findings.

No Horizon-hosted service is involved.

## 8. Maintain existing source and profile workflows

Preserve PR #2's functionality:
- `horizon-source add`
- `horizon-source list`
- `horizon-source validate`
- `sources/registry.json`
- `AGENTS.md`
- Institution and world research profiles

Ensure the scheduler uses exactly the same approved profiles and source registry as manual research.

The agent may propose additional institutional targets or public feeds, but new source configurations become active only after appropriate review and merge.

If PR #2 remains unmerged, base the implementation on the correct integration branch without losing its changes.

## 9. Testing requirements

Write automated tests for:

- Successful GitHub workflow dispatch.
- GitHub dispatch response containing a real run ID.
- 204-only dispatch fallback.
- Workflow-run polling.
- Failed, cancelled and timed-out workflows.
- Successful collection followed by failed publication.
- Retrieving reports by exact workflow run ID.
- Rejecting stale/unrelated report pointers.
- Valid and invalid cron expressions.
- Unsupported scheduling frequencies.
- Time-zone validation and daylight-saving transitions.
- Multiple schedules with the same cron time.
- Schedule creation, update, pause, resume and deletion.
- Generated workflow consistency.
- Duplicate schedule IDs.
- Invalid or disabled research profiles.
- Unauthorized GitHub operations.
- PR creation conflicts.
- Historical state restoration.
- Duplicate-run and retry handling.
- No mandatory external AI/news credentials.
- Compatibility with existing MCP tools and research archive schemas.

Run the complete existing test suite, both MCP smoke checks, workflow validation with `actionlint`, and repository/schema checks.

Where permissions allow, validate:
1. A real manual GitHub Actions dispatch.
2. Run status retrieval.
3. Actual `intel` publication.
4. Independent retrieval of the published report.

For recurring schedules, verify generated workflows and activation state. Do not claim that a future scheduled occurrence has happened until GitHub actually executes it.

## 10. Documentation and handoff

Update:
- `AGENTS.md`
- `spec.md`
- `docs/agent-research.md`
- README MCP usage
- Example MCP client configuration
- Schedule registry/schema documentation

Document actual arguments, return structures, authentication requirements and how schedule activation works.

Include example instructions for an external agent to register a schedule and trigger an immediate run.

## Deliverables

1. Working GitHub Actions MCP controller.
2. Working schedule-management MCP tools.
3. Persistent schedule registry.
4. Generated or synchronized native GitHub Actions cron workflows.
5. Source-attributed reports linked to workflow and schedule IDs.
6. Backward-compatible research and source management.
7. Passing regression and integration tests.
8. Updated documentation.
9. New PR against `main`, preserving PR #2's work and repository history.

Report:
- Changed files.
- New MCP tools and their schemas.
- Test results.
- Actual GitHub Actions runs verified.
- Example schedule registration.
- Current active versus pending schedules.
- Any remaining permissions or deployment blockers.

**Implement the complete integration. Do not stop after creating a plan or documentation. Keep Horizon production execution exclusively on GitHub Actions runners.**
