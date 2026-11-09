# Temporary test-server qualification — 2026-11-09

The operator authorized a temporary test against the supplied test-d host with
alias-clef. No repository variables or secrets were changed. Qualification ran
on an isolated branch with read-only permissions; production profiles and defaults
were untouched. The approved test origin was bound in the temporary wrapper only,
without weakening the application's same-origin endpoint guard.

## Results

- Root `/`: [42565188435](https://github.com/JsonLord/Horizon/actions/runs/42565188435),
  HTTP404 from both HTTPX and curl, no model-not-found hint.
- Existing native operation `/v1/systemone` on that host:
  [42565240340](https://github.com/JsonLord/Horizon/actions/runs/42565240340),
  HTTP200 through both clients, response identity alias-clef, heavy_tier selected,
  182 input tokens and zero output tokens per sample. Curl used HTTP/2, zero redirects.
- Full native qualification:
  [42565325280](https://github.com/JsonLord/Horizon/actions/runs/42565325280),
  **PASS, 18/18 schema-validated command/profile cells**: relevance,
  worth-attention, same-story, importance, claim-support and HFS across AUX,
  Funding DE/EU and World Intelligence. Expected and returned identity alias-clef.
- Independent fresh-runner recovery: **PASS**, source/policy/checkpoint/command-cache
  verification, zero provider requests during restoration.

The full qualification issued 37 provider requests including its initial probe,
policy exercises and 18-cell matrix. Its initial validated decision reported
340 input tokens, zero output tokens, latency1036ms; these are **one decision's**
usage/latency, not whole-run totals. Cost remains null (no invented pricing).
Qualification and restore jobs took40s and13s respectively as recorded by GitHub.
Temporary workflow changes passed actionlint and diff checks. Application code
was unchanged from the previously tested524-test implementation.

## Effective temporary configuration

- API_MODE: systemone
- BASE_URL/CHAT_URL: the operator-approved test host's complete `/v1/systemone` operation
- MODEL: alias-clef
- RESPONSE_MODEL: alias-clef (observed and validated)
- API_KEY: the existing repository secret; value never read or logged by the agent

The supplied root alone is not a working native POST route. No suffix is appended
by systemone mode: configure the complete operation explicitly. No endpoint/model
is stored in a research profile. The temporary workflow is not production configuration.

This establishes live native structured classification and durable restoration on
the test host with the configured credential. It does not diagnose why the original
host/alias-laya failed, prove arbitrary generated explanations/code, multilingual
research quality or production publication. Native technical-learning generation
remains unsupported and falls back to deterministic review. Hard eligibility and
all evidence/security gates are unchanged. No merge, schedule activation, Paperclip
push or production archive publication occurred. PR #8 remains draft.

Machine-readable safe run annotations/source SHAs are in the adjacent JSON file.
