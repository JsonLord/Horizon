# Corrected model selection — 2026-11-09

The operator clarified that the exact operation must use **alias-laya**,
superseding the temporary alias-clef qualification selection. The repository
model setting was never changed by this task. Neither selection nor the API key
was written through a privileged workflow. Repository-variable writes remain
unavailable to this integration (previous403).

[Recheck run 42556922702](https://github.com/JsonLord/Horizon/actions/runs/42556922702)
used an isolated qualification branch and supplied `model=alias-laya`, the
operator-approved exact URL and `diagnose_only=true`. The full matrix/recovery
job was deliberately skipped; only one bounded request was needed.

Actual safe proof:

- Requested model: alias-laya.
- Exact operation routing: true; no URL suffix appended.
- Requests: 1.
- HTTP404, application/json, model_not_found_hint.
- The error references the requested model, not the last operation-path segment.
- Validated inference decision: false.

The diagnostic job itself completed successfully because it captured these
facts. Its green conclusion **does not mean inference passed**. No response body,
API key, signed artifact URL or private endpoint is retained. Full safe check
annotations and source/runner metadata are in the accompanying JSON.

The alias's availability/mapping for this endpoint/account needs provider-side
verification. HTTP404/model-not-found does not independently prove a bad token
or establish that authentication succeeded. Do not silently switch model IDs,
try unrelated inference routes or disable identity/schema validation.

Earlier alias-clef tests were read-only and are superseded as model selection.
They returned HTTP400, including after format fallback; they did not establish
working inference. No further alias-clef requests were made after the correction,
and all earlier jobs had already completed.

Provider qualification now supports an explicit bounded model input in addition
to the same-origin exact URL override. These are test-only inputs; normal shared
and radar runs continue to read global repository configuration. Code source
`a7de1322f265032b4b929db17d4d739d5d35eb4a`, local regression **505 passed in
5.16s**, hosted PR regression42555730120 PASS. New schedules, merges and production
publication remain unactivated.
