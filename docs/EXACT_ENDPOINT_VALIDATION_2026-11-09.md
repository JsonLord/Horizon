# Exact inference operation URL — 2026-11-09

Implemented on draft PR #8, source `19d586e5211d0429e66a650ed4e9d52ce2c98af8`.
The operator corrected the target to a complete POST operation URL, not an API
base. `HORIZON_DECISION_CHAT_URL` now overrides base expansion and is used
verbatim: no added `/v1` or `/chat/completions`, including preserving a supplied
trailing slash. When absent, existing BASE_URL behavior remains compatible.

OpenAI chat request/response JSON, model identity, citations, schema validation,
redirect refusal, public HTTPS rules and deterministic fallback are unchanged.
No native provider API or profile-specific endpoint was introduced. All shared
AUX/Funding/World and radar workflows receive the same optional repository
variable. Cache identity binds the effective operation URL, model and API mode.

## Actual hosted results

- [504-test PR regression](https://github.com/JsonLord/Horizon/actions/runs/42554215566): PASS.
- [Exact URL qualification](https://github.com/JsonLord/Horizon/actions/runs/42554237210):
  routing explicitly `exact_endpoint`, but HTTP 404; 0/18 cells validated.
  Independent fresh-runner checkpoint recovery: PASS, zero inference calls.
- [Sanitized error diagnostic](https://github.com/JsonLord/Horizon/actions/runs/42554666728):
  one additional direct request to that same exact operation returned HTTP 404,
  `application/json`, with `model_not_found_hint`. No error body was logged.
  This narrows investigation to model mapping; it does not independently prove
  the exact rejected identifier or token validity. Current configured alias is
  `alias-laya`; no successful server-reported model identity was obtained.

The smoke ran through an isolated registered-path wrapper because the shared
workflow is not registered on main. Its custom URL input is restricted to the
currently configured provider origin before the API key can be sent. No endpoint
is hardcoded in application code or profiles. The chosen URL was supplied only
as the authorized Actions dispatch input; it is omitted from this public report.
Safe check annotations and actual source SHAs are in the accompanying JSON.

## Remaining configuration and validation

Saving the optional repository variable through this integration returned
**403 Resource not accessible by integration**. It was not saved. An authorized
owner must configure `HORIZON_DECISION_CHAT_URL` to select the exact route for
normal shared/radar runs. The API key is unchanged. A qualification-only override
was used for these tests, not a persistent configuration bypass.

The owner was asked which exact model identifier this operation supports. Do not
invent an ID from the URL, silently change the model or loosen identity/schema
validation. A successful real inference is still required before provider
readiness can pass. No schedule was enabled, branch merged, production archive
published or unknown finding promoted.

Local Python 3.11 regression: **504 passed in 5.12s**; targeted routing/security
checks and workflow lint pass. Cases include exact URL preservation, base
compatibility, private URL refusal, same-origin qualification, cache separation,
and successful technical-schema parsing with no BASE_URL configured.
