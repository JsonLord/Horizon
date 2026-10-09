# Agent research implementation and operator guide

Acceptance contract: repository-root `spec.md`. Existing CLI, native AI pipeline and MCP stage tools remain in place; the credential-free research service is additive.

## Progress

- [x] Clean checkout inspected on `work`; implementation branch `feat/agent-research`.
- [x] Existing Docker, source adapters, MCP stage service, providers, manifests and workflows inspected.
- [x] Nine validated JSON profiles; canonical serialization; bounded multi-query collection and MCP source allowlist correction.
- [x] Deterministic title extraction, independent source references, official-domain classification, transparent relevance and query-region coverage.
- [x] Versioned reports, checksummed manifests, latest pointers, bounded events, atomic writes and separate archive consumer.
- [x] Shared asynchronous job service; HTTP auth, quotas, idempotency and restart recovery; additive MCP research tools/resources.
- [x] Single-port CPU Docker packaging and CLI Compose override.
- [x] Scheduled/dispatch Actions collection and separate publishing job using automatic job token.
- [x] Final regression, source fixtures, live Google collection, Docker/API, workflow static validation and real Git archive publication (results below).
- [ ] Actual Space deployment: no Space ID identified in remote/deployment configuration so far.

## Run

Use the existing checkout; tasks already have isolated environments. Do not create a Git worktree unless explicitly requested.

```
uv sync --frozen --extra dev
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 7860
uv run python -m src.research.cli --profile-id world/global
uv run horizon --hours 24
uv run horizon-mcp
```

The legacy CLI still uses its existing `data/config.json`. Native `ai.mode=auto` falls back to transparent deterministic title/recency scoring when the model key is absent; `local`/`off` never call a model. Configured model behavior remains available. Research execution does not require a model or news API key. Empty/unavailable collectors are explicitly distinguished from observed findings.

HTTP read interfaces: `/health`, `/ready`, `/v1/info`, `/v1/profiles`, `/v1/profiles/world/global`, `/v1/reports`, `/v1/reports/{report_id}?format=markdown`, `/v1/changes`, `/api-docs`, `/openapi.json`, `/`. Job submission and job status require `Authorization: Bearer <HORIZON_AGENT_TOKEN>`; absence of the token disables remote execution with 403. No token belongs in a profile or artifact. Profile registration is authenticated; feed additions require operator-reviewed repository profiles.

MCP adds `hz_list_profiles`, `hz_get_profile`, `hz_submit_research`, `hz_get_job`, `hz_list_jobs`, `hz_list_reports`, `hz_get_report`, `hz_search_archive`, `hz_get_changes`, `hz_register_institution` to the existing trusted stdio server. Resources: `horizon://profiles`, `horizon://reports`, `horizon://reports/{report_id}`.

## Archive and publication

Actions schedule runs daily at 06:23 UTC (schedules may be delayed or disabled after inactivity). Dispatch `horizon-intel.yml` with an approved profile ID and lookback 1–168. Inputs pass through environment variables and schema validation, never shell interpolation. Collection has read permission; publication alone has `contents: write`. Branch rules can still deny writes. Space authentication is unrelated to Actions authentication.

The `intel` branch contains `intel/manifest.json`, `intel/latest/world.json` and `.md`, `intel/latest/institutions/ecb.json`, versioned `intel/reports/.../<run_id>/report.json`, `.md`, `manifest.json`, and `intel/events/YYYY/MM/DD/events.jsonl`. Schemas live at `schemas/`. An initially absent branch bootstraps automatically; publication retries boundedly without force pushes. Reports max 1 MB each; index retains 100 reports. Local stage storage remains separate.

Once publication is verified, consumers can use:

```
git fetch origin intel
git show origin/intel:intel/latest/world.json
curl -f https://raw.githubusercontent.com/JsonLord/Horizon/intel/intel/manifest.json
```

These paths were verified on the actual `intel` branch, including anonymous raw HTTP retrieval.

Space-originated research is `local_only` and ephemeral. Public GitHub archive reading uses no API key. Dispatching Actions requires existing authorized GitHub access. This release does not automatically dispatch from the Space or pretend it has Actions' token.

Optional model configuration: `HORIZON_AI_MODE=auto|local|off`, `HORIZON_LLM_BASE_URL`, `HORIZON_LLM_MODEL`, optional `HORIZON_LLM_API_KEY`. `off` makes no model call. Unavailable/invalid model output falls back to extractive analysis. Model enrichment selects evidence IDs only; summaries remain source-grounded titles.

## Space deployment

Build this Dockerfile in the **actual** Docker Space repository; its README frontmatter must contain `sdk: docker` and `app_port: 7860`. GitHub README is unchanged. UID 1000, one port, two bounded workers, no database or local inference runtime. A free Space may sleep/restart; live tasks do not persist. No private endpoints are returned by the info interface.

No official institution feed URL is invented. Seed institutions use news searches and reviewed official-domain attribution with empty feed lists. Operators can add verified public HTTPS feeds to repository profiles. Query region is explicitly not event geography. Headline-only extraction cannot infer contradictions/resolutions or verify truth; these remain surfaced limitations rather than fabricated classifications.

## Verified acceptance results

- `UV_CACHE_DIR=/tmp/horizon-uv uv sync --frozen --extra dev`: passed. The custom cache is required because this cloud machine's default home cache is read-only.
- `UV_CACHE_DIR=/tmp/horizon-uv uv run pytest`: **314 passed**, no skipped/expected-failure tests (final run 3.52 seconds; subsequent runs recorded in the handoff if changed).
- `uv run python scripts/check_mcp.py`: passed after seeding the existing ignored `data/config.json` from the repository example without overwriting a user config.
- `uv run python scripts/check_research_mcp.py`: passed over the real stdio transport; **24 tools, 9 profiles**; original stage tools and new research resources discovered.
- `uv run horizon --hours 24`: initial missing-key failure diagnosed and fixed by the native deterministic fallback; rerun exited **0**, saved its summary and completed. The repository-supported optional sources still report their own unavailable endpoints.
- `actionlint 1.7.7 .github/workflows/horizon-intel.yml`: passed. The downloaded binary was checked against the upstream release checksum. No actual Actions run is claimed.
- Docker: build succeeded with frozen lockfile and TLS verification. This cloud's proxy required a DNS host binding and an optional build-only CA secret. No proxy endpoint or CA is baked into the image. Runtime smoke returned **200** for health, ready, info, docs, OpenAPI, profiles, reports and dashboard. With the existing cloud proxy and CA trust supplied to the test container, its archive API returned **published**, two reports, and 15 ECB findings. Standard HF networking does not require this cloud-specific proxy configuration.
- Fixture E2E: shared job request → multi-source collection fixtures → grounded report → atomic archive → Git branch bootstrap/push → separate clone reader. Tests include zero items followed by findings, checksums, denied pushes with three bounded retries/no force, safe URL/DNS checks, gzip responses, auth/privacy, request/queue bounds, cancellation, restart recovery, model fallback and strict schemas.

### Real archive publication

Published from this cloud machine using its existing HTTPS Git proxy authorization, **not** a manually provisioned token or a claimed Actions token:

- Archive commit: `5bb6a2bba62641c62ebaf5d2b777fa58c2929e82` on `intel`.
- World report: `7b63820cbc8d4083b2c13ccb150d3f89`, **60 findings / 60 sources**.
- ECB report: `65452eb59f454da3884b3e3583d57207`, **15 findings / 15 sources**.
- Both reports are **partial**: live Google News succeeded; GDELT returned **503**, and the existing public Simon Willison feed returned **403** in this cloud environment.
- All five requested world search regions produced selected sources. These are **search locales**, not verified event locations or a claim of worldwide completeness.
- A separate clone and a separate raw-HTTP client with no Authorization header retrieved the real manifest and both reports successfully.

Verified public paths:

- https://raw.githubusercontent.com/JsonLord/Horizon/intel/intel/manifest.json
- https://raw.githubusercontent.com/JsonLord/Horizon/intel/intel/latest/world.json
- https://raw.githubusercontent.com/JsonLord/Horizon/intel/intel/latest/world.md
- https://raw.githubusercontent.com/JsonLord/Horizon/intel/intel/latest/institutions/ecb.json
- https://github.com/JsonLord/Horizon/tree/intel/intel/reports

### Remaining external checks and limits

No actual Hugging Face Space ID was found in the original remotes, tracked deployment files or available environment binding names. Initial HF discovery was blocked with **403**; later API access succeeded, found no Spaces under the matching GitHub author, and a similarly named public candidate had no repository binding. GitHub deployment records list only GitHub Pages. No Space was invented, created or deployed. Supply the actual Space binding and an authorized deployment mechanism; then copy the tested image inputs and `deploy/huggingface/README.md` into that Space and verify its real endpoint.

Initial GitHub REST requests returned **Forbidden**; later authenticated access succeeded and PR **https://github.com/JsonLord/Horizon/pull/1** was created on `feat/agent-research`. An actual workflow dispatch attempt returned **404** because the new workflow is not yet present on the default branch. Merge/review the PR, then dispatch `horizon-intel.yml` to validate a real Actions `GITHUB_TOKEN` publication. The live cloud Git push does not prove that scheduled path ran.

Profiles initially leave official institution feed lists empty; no feed was fabricated. The world profiles reuse Simon Willison's public feed already present in Horizon's example config. Unreviewed submitted feeds are rejected. Query-country metadata never masquerades as event geography. Deterministic dedup handles normalized/near-identical titles and public URL IDs; it cannot reliably recognize every translation or syndication. Contradiction/resolution labels use explicit source wording on a previously observed event and require review. Model enrichment validates evidence selections and preserves extractive summaries; it never invents free-form model facts. Optional subscriptions remain a second-phase non-goal.

Space-originated questions remain private to authenticated local-report/job access and are export-only. The publisher rejects ad hoc/private question reports; approved scheduled profiles are the durable public path. Public profile registration is an authorized operation. Jobs retain at most 100 local records; archive retains at most 100 indexed reports and 30 dated event files, with a 1 MB artifact ceiling. Failed/no-new-items runs do not overwrite successful latest pointers.

## Files created and modified

- Created: `.github/workflows/horizon-intel.yml`
- Modified: `.gitignore`
- Modified: `Dockerfile`
- Modified: `README.md`
- Created: `deploy/huggingface/README.md`
- Modified: `docker-compose.yml`
- Created: `docs/agent-research.md`
- Created: `profiles/examples/custom-research.json`
- Created: `profiles/institutions/cern.json`
- Created: `profiles/institutions/ecb.json`
- Created: `profiles/institutions/helmholtz.json`
- Created: `profiles/institutions/who.json`
- Created: `profiles/world/economy.json`
- Created: `profiles/world/geopolitics.json`
- Created: `profiles/world/global.json`
- Created: `profiles/world/science-technology.json`
- Modified: `pyproject.toml`
- Created: `schemas/manifest.schema.json`
- Created: `schemas/profile.schema.json`
- Created: `schemas/research-report.schema.json`
- Created: `scripts/check_research_mcp.py`
- Created: `src/ai/local.py`
- Created: `src/api/__init__.py`
- Created: `src/api/app.py`
- Modified: `src/mcp/horizon_adapter.py`
- Modified: `src/mcp/server.py`
- Modified: `src/mcp/service.py`
- Modified: `src/models.py`
- Modified: `src/orchestrator.py`
- Created: `src/research/__init__.py`
- Created: `src/research/analyzers.py`
- Created: `src/research/cli.py`
- Created: `src/research/collector.py`
- Created: `src/research/profiles.py`
- Created: `src/research/publisher.py`
- Created: `src/research/remote.py`
- Created: `src/research/reporting.py`
- Created: `src/research/service.py`
- Created: `tests/fixtures/research/manifest.json`
- Created: `tests/fixtures/research/report.json`
- Created: `tests/fixtures/research/report.md`
- Created: `tests/test_local_analyzer.py`
- Modified: `tests/test_mcp_adapter.py`
- Created: `tests/test_research.py`
- Created: `tests/test_research_collection.py`
- Created: `tests/test_research_http.py`
- Created: `tests/test_research_model.py`
- Created: `tests/test_research_publisher.py`
- Modified: `uv.lock`

### Final environment handoff

The HTTP service was left running on port 7860. Its `/ready` reports `archive_connectivity: connected`, deterministic fallback available, no configured model and nine profiles. Real MCP archive reads returned two reports, 15 ECB findings, five matches for a Central Bank search and 15 ECB change events.

After network access changed, the existing public RSS feed was retried: **7 items, valid Atom feed, no error**. The initial published reports correctly retain their historical source-failure observations. A final world refresh/publish is recorded below when completed.

Saved environment draft fields: `install_script`, `start_skill`, `UV_CACHE_DIR` runtime variable and additive custom network domains (existing package-manager presets preserved). This persists instructions and requirements; it does not itself publish a snapshot. Review/save the draft in environment settings and publish the environment for future tasks. No new secret requirement was added for the baseline.
