# SPEC — Horizon Global News & Institutional Intelligence

**Repository:** https://github.com/JsonLord/Horizon  
**Target:** Existing Horizon codebase plus its Hugging Face Docker Space deployment, if a Space is already configured  
**Status:** Implementation specification (not a claim that these features are already implemented)  
**Date:** 2026-10-09  
**Primary objective:** Turn Horizon into a credential-free-by-default world-news and institutional-research service that external agents can control and whose published results other agents can read directly from GitHub.

## 0. Non-negotiable constraints

1. **Work on the existing repo, not a rewrite.** Preserve the native fetch → cross-source dedup → AI score → filter → enrich → summarize pipeline, existing CLI, MCP tools, setup wizard, and legacy config compatibility.
2. **No new external news or commercial LLM credentials are required for baseline functionality.** Default source set: public RSS/Atom, GDELT DOC, Google News RSS, official institution feeds/pages where legitimately accessible, and public GitHub metadata subject to limits. External-key-dependent sources are optional and OFF by default.
3. **No LLM must be available for successful baseline execution.** In `ai.mode=auto`, use a configured reachable existing OpenAI-compatible endpoint if available; otherwise use deterministic extraction, transparent keyword/rule ranking, and extractive summaries. Never fabricate facts, sources, model judgments, or confidence.
4. **GitHub publication must really work without a manually provisioned GitHub token when the job runs inside GitHub Actions** using its job-scoped `GITHUB_TOKEN` and `permissions: contents: write`, subject to repository rules. **A Hugging Face Space does not receive that token** and MUST NOT pretend it can push to GitHub without configured write authorization.
5. **Remote mutation must never be anonymous.** A Space without `HORIZON_AGENT_TOKEN` can serve public read endpoints and local/demo functionality but MUST reject remote job-submission/configuration mutations (`403`, feature-disabled) rather than expose an abuse-prone public research worker. Authorized GitHub users can trigger workflows using their existing GitHub authorization; this does not require a new third-party API account.
6. **No new public ports** beyond the normal Hugging Face Space container interface (HTTP port 7860). Do not expose Debian gateways or Tailscale services publicly. Do not embed private hostnames or credentials in public client responses.
7. **Do not assume a Hugging Face Space ID.** Discover the real target from the existing git remotes, deployment files, and environment. If it cannot be positively established, make the repository Space-ready, test locally, and report the exact missing deployment binding; do not create or push to an invented Space.
8. **Keep operations compatible with resource-constrained HF CPU Basic deployments.** Bound workers, fetches, requests, file sizes, and concurrency; no heavyweight local inference dependency. The Space filesystem is ephemeral; GitHub-published artifacts are the durable system of record.
9. **Keep previous Horizon behavior.** Existing `uv run horizon --hours 24`, `uv run horizon-mcp`, `horizon-wizard`, relevant tests, and current manually configured data sources must continue to work.
10. **Do not claim the Space or external systems were tested unless an actual end-to-end deployed check was performed.** Always distinguish local, mocked, integration, and live deployment results.

## 1. Verified existing foundation / observed gaps

Inspect and reuse these files before editing:

- `src/orchestrator.py`: native parallel scrapers, cross-source/topic dedup, AI processing, summary generation. GDELT, Google News, and OSS Insight are imported and called when enabled.
- `src/models.py`: `ContentItem`, `SourcesConfig`, `GDELTConfig`, `GoogleNewsConfig`, existing `SourceType` values.
- `src/scrapers/{rss,gdelt,google_news,github,reddit,telegram,hackernews,openbb}.py`: source adapters.
- `src/mcp/server.py`, `src/mcp/service.py`, `src/mcp/run_store.py`, `src/mcp/horizon_adapter.py`: existing MCP interface and stage persistence; `hz_run_pipeline`, `hz_get_run_stage`, and `hz_get_run_summary` already exist.
- `src/mcp/horizon_adapter.py`: `VALID_SOURCES` currently omits `gdelt`, `google_news`, and `ossinsight`, even though the orchestrator knows them. Extend the allowlist, filtering logic, and diagnostics consistently.
- `data/mcp-runs/` is ignored by `.gitignore`; a run artifact there is NOT a GitHub-published research report.
- `src/ai/client.py` requires a configured model/API key in common paths; introduce an explicit optional/offline analyzer pathway rather than fabricating a token or silently treating an unreachable model as successful.
- `Dockerfile` currently runs the CLI, not an HTTP app. Space deployment requires a web entrypoint while retaining the existing CLI through explicit invocation.
- `.github/workflows/daily-summary.yml` currently runs weekly. Add new workflows rather than breaking that legacy one before replacement is validated.

## 2. Architecture and execution contracts

### 2.1 Component boundaries

- **Profiles:** versioned JSON configs defining *what* to monitor; they never hold secrets.
- **Collector:** adapt existing scrapers with bounded multi-query collection and provenance normalization.
- **Research pipeline:** fetch → normalize → dedup → profile relevance → optional model enrichment → verify/attribute → report → change detection.
- **Job service:** asynchronous job IDs, status, progress, cancellation/timeouts, quotas, idempotency, structured errors.
- **Archive publisher:** local, validated, versioned Markdown+JSON artifacts; GitHub Actions commits successful outputs to an `intel` branch (or documented equivalent read-only artifact branch).
- **HF Space HTTP app:** lightweight FastAPI UI/API on port 7860; public read-only data discovery and authenticated optional ephemeral job execution. It can read published reports from public GitHub without secrets.
- **MCP interface:** retain existing stdio MCP and add high-level profile/job/report tools without duplicating the business logic.

### 2.2 Modes

**`world_radar`:** broad global news across regions and subjects, multiple bounded GDELT/Google News queries, primary RSS, region/source diversity, dated snapshots.

**`institution_watch`:** named persistent institution entity, aliases, domains, official primary sources, publication tracking, official-vs-media classification, change timeline, profile-specific relevance.

**`research_job`:** constrained agent-specified question, permitted sources, time range, target institutions, depth; produces a self-contained report and can optionally become a saved profile through an authorized operation.

### 2.3 Deployment split and credential boundary

**Credential-free default:** GitHub Actions is the scheduler/executor/publisher and uses the automatic short-lived `GITHUB_TOKEN`. HF Space provides HTTP dashboard, public read access, and non-persistent local/demo analysis. No third-party news key, GitHub PAT, paid LLM key, or HF token is required for this basic mode **assuming normal repository Actions write permissions and an existing authorized Space deployment mechanism**.

**Optional enhanced mode:** A Space with a user-generated `HORIZON_AGENT_TOKEN` can accept authenticated remote job submissions and return ephemeral results. Durable publication of Space-originated jobs requires a *separately configured* write-capable GitHub identity or a pre-existing authenticated GitHub Actions dispatch path. Do NOT imply an HF Space process can obtain GitHub Actions' job token. If not configured, return `publication_status: "local_only"` and provide export/download endpoints.

**Optional model inference:** `HORIZON_LLM_BASE_URL`, `HORIZON_LLM_MODEL`, and optional `HORIZON_LLM_API_KEY` are runtime secrets/variables. If absent or unreachable, fall back locally. The initial release should not depend on a private Debian/Tailscale endpoint being reachable from GitHub-hosted runners.

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

## 7. HTTP API (Hugging Face Space, FastAPI)

Implement a minimal web UI plus JSON API in `src/api/app.py` (or another clearly named module), with OpenAPI `/api-docs` or `/openapi.json`; build a single container serving on `0.0.0.0:7860`.

**Read-only public endpoints** (no new secrets):

- `GET /health` — liveness; never network-blocking.
- `GET /ready` — readiness, dependency mode, archive connectivity separately reported; don't fail readiness solely because GitHub is temporarily unavailable.
- `GET /v1/info` — current version, supported modes/sources, analysis mode, publication mode, capabilities with no credentials or private endpoints exposed.
- `GET /v1/profiles` and `GET /v1/profiles/{profile_id}` — approved, sanitized profiles.
- `GET /v1/reports` — paged/filterable list from published manifest, with local fallback if no remote archive.
- `GET /v1/reports/{report_id}` — bounded structured JSON and alternate Markdown rendering.
- `GET /v1/changes?profile_id=...&since=...` — bounded change summaries and links.
- `GET /v1/jobs/{job_id}` — only statuses/results authorized to the caller; avoid leaking submitted private prompts, tokens, or logs.
- `GET /` — simple functional dashboard: world latest, profiles, selected institution latest, source coverage, report links, job status, and an explicit read-only/authorized mode indicator.

**Write endpoints** (disabled without `HORIZON_AGENT_TOKEN`):

- `POST /v1/jobs` — validated profile + question + bounded lookback/depth, `202 Accepted`, job ID, idempotency key, status URL; bounded queue.
- `POST /v1/profiles` or `PUT /v1/profiles/{profile_id}` — optional authorized profile mutation, with strict validation and safe persistence rules; no arbitrary feed URL crawling from untrusted requests.
- Do not expose generic shell commands, unrestricted remote URL fetch, arbitrary local config file paths, private local network requests, or unrestricted GitHub write operations.

Error responses use a stable `{ "ok": false, "error": { "code": ..., "message": ... } }` schema, proper HTTP status, no stack traces/secrets.

Without authenticated remote writes, allow UI search/browsing and published-result reading. **Do not advertise fully authenticated remote triggering when it is disabled.**

## 8. MCP tools: reuse existing server

Preserve all existing `hz_*` calls. Add thin service facades sharing the same pipeline/profile/report implementation:

- `hz_list_profiles`, `hz_get_profile`
- `hz_submit_research`, `hz_get_job`, `hz_list_jobs`
- `hz_list_reports`, `hz_get_report`, `hz_search_archive`, `hz_get_changes`
- `hz_register_institution` (local/trusted-authorized only, validates and persists safe profile)
- `hz_subscribe` optional in second phase (persist approved subscriptions; no secrets or unbounded callbacks)

Expose useful MCP resources such as `horizon://profiles`, `horizon://reports`, and `horizon://reports/{report_id}`. Maintain current stage-based tools for backwards compatibility. Stdio MCP is local/trusted, not a public unauthenticated internet endpoint. The model should discover profiles/reports using listing/search tools before loading entire archives.

## 9. Jobs, scheduling, and agent consumption

- Job fields: `job_id`, `idempotency_key`, `requested_by`, `profile_id`, `question`, `mode`, `status`, `submitted_at`, `started_at`, `completed_at`, `stage`, `counts`, `warnings`, `error`, `report_id`, `artifact_manifest`, `publication_status`.
- States: `queued`, `running`, `completed`, `partial`, `failed`, `cancelled`. Enforce state transitions. An empty but valid collection is `completed` with `no_new_items` result or `partial` if source coverage failed; not an invented success summary.
- Constrain concurrency and queue sizes in HF CPU Basic; timeouts per stage and total job. On restart, detect persisted/local interrupted jobs and mark them explicitly rather than leaving them `running` forever.
- For scheduled durable reports, create `.github/workflows/horizon-intel.yml` with scheduled global/institution collection and validated `workflow_dispatch` inputs (`profile_id`, optional safe lookback). Avoid arbitrary shell interpolation from user-supplied inputs.
- GitHub Actions should run `uv sync --frozen`, execute the same research service, validate output, and publish to `intel` branch using the workflow-scoped token. Keep run logs/artifacts for debugging. `permissions: contents: write` on the publishing job only.
- Document that GitHub scheduled jobs may be delayed or disabled through inactivity; an HF free Space may sleep/restart. Don't promise guaranteed always-on operation.
- Remote agents may read published public GitHub files without a token; invoking `workflow_dispatch` still requires an identity authorized by GitHub. If no authorization is available, that control path must be shown as unavailable, not silently bypassed.

## 10. HF Space packaging

- Adapt the existing Dockerfile or provide an unambiguous build artifact copied to the actual Space repository. For a Docker Space, actual Space README YAML frontmatter should contain `sdk: docker` and `app_port: 7860`; do not blindly prepend HF-only metadata to the GitHub source repository README.
- Install `fastapi`, `uvicorn` and other **lightweight** required dependencies, pin through existing `uv.lock` (with reproducible build). Preserve `uv run horizon`, `uv run horizon-mcp` and their CLI tests.
- Run as unprivileged UID 1000; bind server `0.0.0.0:7860`; reasonable startup without external network dependencies; deterministic health checks.
- Configure default `HORIZON_CREDENTIAL_FREE=true`, `HORIZON_AI_MODE=auto`, `HORIZON_ARCHIVE_REPO=JsonLord/Horizon`, `HORIZON_ARCHIVE_REF=intel`, `HORIZON_MAX_JOBS=2`, etc. All private values via runtime environment, never tracked `.env` or in public API.
- No persistent filesystem assumptions: ephemeral Space jobs/reports may disappear. Source of truth for cross-session research is Git-published archive. Make the UI reflect this distinction.
- Do not expose additional ports, and do not install a heavyweight DB or unrelated agent framework. No requirement for paid HF hardware.
- Preserve or repair local Docker Compose CLI behavior if replacing the Dockerfile entrypoint.

## 11. Safety, provenance, correctness

- **SSRF/network:** only allow HTTPS (or explicitly approved safe HTTP public feeds), DNS/IP safeguards against localhost, link-local, RFC1918, cloud metadata and internal tailnet endpoints for *untrusted submitted URLs*, redirect re-validation, hostname allow/deny rules, strict timeouts and response sizes.
- **Authorization:** constant-time bearer comparison, authorization on writes, and rate limiting and job quotas. No public job-spawning without configured authentication.
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
9. HTTP: `/health`, `/ready`, `/v1/info`, profiles, reports, pagination, errors; unauthorized POST rejected; authorized POST creates bounded job; no accidental side effects in GET.
10. MCP: old tools still work; high-level profile/job/report tools work and do not expose secret-bearing effective config.
11. Restart and crash-recovery conditions; protect against path traversal and SSRF/redirect to private targets.
12. Regression: all preexisting `tests/` pass; smoke check `scripts/check_mcp.py` passes.

### Local integration / Docker acceptance

- `uv sync --frozen --extra dev && uv run pytest` is green (or explicitly report unavailable offline dependencies).
- `uv run python scripts/check_mcp.py` passes.
- `docker build ...` works in Docker-capable environments; container on port 7860 serves `/health`, `/ready`, `/v1/info`, `/api-docs`, and read-only archive view without any new secret.
- `uv run horizon --hours 24` and `uv run horizon-mcp` remain invokable.
- Credential-free end-to-end fixture job: create/load profile → fetch stubbed sources → grounded report JSON/Markdown → update latest manifest → second agent/read client resolves a report.
- GitHub Actions workflow passes syntax/static validation; actual publish success is asserted only after a genuine workflow run with authorized repository permissions.

### Live acceptance where access is available

- Actual HF Space build succeeds; endpoint health/ready/info returns accurate modes.
- GitHub Actions dispatch or schedule produces committed report and manifest on configured archive ref using the automatically generated job token, and the Space can read it.
- A separate read-only client retrieves published `intel/latest/world.json` or institution report without needing a GitHub API key (public repo).
- If HF Space ID, repository authorization, Docker daemon, or remote runner access is missing, complete local code/tests and explicitly document the blocked live check and exact action needed—never invent success.

## 13. Implementation order and deliverables

Work in implementation-ready increments, with tests after each:

1. **Audit & plan:** inspect current branch/status, remotes, Space target if present, config/tests, current HF packaging, and source filter. Update `spec.md` only if a proven technical correction is required; preserve product goals.
2. **Profiles and source fixes:** implement Pydantic profile definitions, initial examples, multi-query GDELT/Google collection, source allowlist fixes, and offline fixtures.
3. **Research analysis:** transparent deterministic fallback; institution attribution; evidence-preserving report schema; comparisons and change events.
4. **Artifact archive:** write/report/manifest validator, `intel/latest` pointer, archive consumption API, GitHub Actions publishing (test with local git sandbox and mock auth).
5. **Agent APIs:** higher-level MCP facade and FastAPI read/write endpoints, auth/quotas/idempotency and simple dashboard.
6. **Deployment:** Space Docker image, runtime config, CLI preservation, GitHub Actions workflows and docs.
7. **Validation:** full tests, local smoke, Docker where available, real GitHub/Space smoke only when access is available; repair defects until green or clearly blocked.

Deliver/update these artifacts:

- Root `spec.md` (this specification), implementation notes/checklist in `docs/agent-research.md`.
- `profiles/`, `src/research/`, `schemas/`, `src/api/` as appropriate; minimal necessary edits to existing `src/mcp/`, `src/orchestrator.py`, `src/models.py`, `Dockerfile`, `pyproject.toml`, `uv.lock`.
- `.github/workflows/horizon-intel.yml` and documented manual dispatch/profile setup.
- Tests for new and regression functionality and documented local build/health check commands.
- Human- and machine-readable sample report fixtures under `tests/fixtures/`; no fabricated real-time news passed off as observed news.
- Final handoff: files changed, architectural choices, test results with exact commands, working endpoints, real published artifact links if any, commits/PRs, remaining limitations, and any credentials/permissions needed for optional features.

## 14. Explicit non-goals for the initial release

- No fine-tuning, no training a new LLM, no mandatory vector database or knowledge graph.
- No paid news service integration or bypass of restricted services.
- No public anonymous arbitrary crawl/agent execution endpoint.
- No promises of complete worldwide event coverage or 24/7 uptime from a free HF Space.
- No independent authoritative truth-qualification engine; Horizon records evidence, while downstream systems such as Nodepad may decide qualification.
- No separate redesigned multi-agent orchestration system inside Horizon; external agents retain responsibility for planning and use Horizon as their news/research worker.

## 15. Reference implementation links

- Source repo: https://github.com/JsonLord/Horizon
- Hugging Face Docker Spaces: https://huggingface.co/docs/hub/spaces-sdks-docker
- HF Space configuration: https://huggingface.co/docs/hub/spaces-config-reference
- GitHub Actions `GITHUB_TOKEN`: https://docs.github.com/en/actions/concepts/security/github_token
- Workflow permissions: https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
