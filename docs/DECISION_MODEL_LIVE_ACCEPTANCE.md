# Decision-model live acceptance — 2026-11-08

Result: **BLOCKED**. Rechecked the newly configured repository, rather than
assuming the previous access result persisted.

- Base source `05ab6d80ffb3f1e7e9a7c3336c2e4c086727b9bb`, PR #7 remains draft,
  stacked on draft PR #5. Both remain open/unmerged.
- `gh workflow run horizon-intel.yml --repo JsonLord/Horizon --ref
  feature/shared-intelligence-filtering -f shared_filtering_qualification=true`
  returned **HTTP 422: Actions has been disabled for this repository**. No run ID,
  run URL, runner or artifact was created by that dispatch.
- Variable-name and secret-name metadata endpoints returned **403 Resource not
  accessible by integration**. This does not establish whether the operator's
  new settings exist or whether a job could use them.
- The managed execution environment exposes none of the four decision settings.
  Local qualification made **zero provider HTTP requests**. No endpoint, secret
  value, model identity, live latency, usage or cost was obtained or disclosed.
- Local checkpoint/SQLite restoration succeeds; this is **not hosted durability**.

`scripts/shared_filtering.py` now explicitly qualifies all six commands across AUX,
Funding DE/EU and World Intelligence (18 public-fixture command cells), recording
individual validated decisions/usage and `all_commands_live_validated`. Genuine
successes are cached separately for restoration; fallback cells remain incomplete.
The fixture is disclosed and never published as a research finding. The original
policy test and funding hard eligibility guard remain intact. Strict nested JSON
schemas and validated non-strict parsing use the same shared OpenAI chat adapter.
Legacy Laya is untouched and is not selected for the shared pipeline.

Retry the authorized read-only dispatch after the repository owner resolves the
Actions availability issue. Enabling Actions may resume existing production
schedules, so this task did not change that setting. Collect the actual run URLs,
18-cell results, reported model identity, usage, latency, schema/citation checks
and fresh-runner restoration proof before changing this gate to PASS. A successful
HTTP response or fixture schema alone cannot certify multilingual research quality.

After pushing the fleet branch, direct lookup/dispatch by the new workflow names
`shared-filtering.yml` and `radar-fleet.yml` returned **404 Not Found**; no run was
created. This is distinct from the registered horizon-intel workflow's 422. The
existing read-only shared-filtering qualification allowlist now also permits
`feature/technical-radar-fleet`, without changing its production collect/publish
guards. Once Actions is available, qualify the new 18-cell implementation with:

```sh
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/technical-radar-fleet -f shared_filtering_qualification=true
```

Do not use a successful workflow dispatch response as inference proof; inspect
both runners' actual artifacts and `all_commands_live_validated`. Checkpoint
restoration now verifies the application source revision, three policy versions,
SQLite checkpoint hash and separate command-cache hash before opening restored
state. No hosted run currently exists for these changes.

## 2026-11-09 — Fork execution restored; endpoint returns 404

Actual authorized run 42552497344 reached the configured provider. All settings
are present, but three requests returned 404 and 0/18 cells validated. The
configured alias is alias-laya; no successful server-reported model identity.
Shared checkpoint recovery passed independently on a fresh runner with zero
inference requests. The old Actions-disabled blocker is superseded by these
observations; provider readiness remains FAIL/unqualified. Full safe evidence,
run links and the unresolved endpoint/model-routing question are in
ACTIONS_LIVE_VALIDATION_2026-11-09.md. No credentials or private endpoint exposed.

## Exact-operation follow-up

The operator's complete POST URL is now supported through the optional global
HORIZON_DECISION_CHAT_URL. Live exact-mode tests still return404; a bounded safe
JSON error classifier reports model_not_found_hint. The currently requested model
is alias-laya; its supported mapping remains to be confirmed by the owner.
See EXACT_ENDPOINT_VALIDATION_2026-11-09.md for source/run evidence and the403
blocker saving the repository variable. Inference remains unqualified.

## Latest operator selection: alias-laya

The temporary alias-clef test selection was retracted by the owner. The latest
bounded exact-URL alias-laya request (42556922702) still returns JSON404 with a
model-not-found hint referencing that alias. No valid inference was obtained.
See ALIAS_LAYA_RECHECK_2026-11-09.md; global MODEL was not changed by this task.

## 2026-11-09 — Explicit native SystemOne contract; runner comparison

Operator supplied the actual state/questions choice protocol and corrected the
request alias to alias-laya. Source db68178 adds explicit systemone mode, strict
answer/identity/citation/usage validation, six semantic classifications and
uncalibrated metadata. OpenAI default and legacy Laya remain separate; free-text
technical-learning generation is explicitly unsupported, with deterministic review.
524 local Python3.11 tests pass (19 native tests); both MCP smokes, funding
consistency, actionlint and schedule checks pass; hosted CI42558554176 succeeds.

Actual native qualification42558670374 fails HTTP404/0 of18 cells; independent
restore passes. Exact operator sample42559142256 also returns404. Comparison
42559911506 sends the same token/payload through HTTPX and literal curl: both404
with model_not_found_hint, curl HTTP/2 and zero redirects. Diagnostic green is not
inference success. Operator reports their exact curl succeeds; the effective
credential/access or runner/server routing difference remains unresolved. Do not
infer a bad key, bypass restrictions or guess other aliases. No settings changed;
repository variable writes remain403. PR8 stays draft, no merge, production
publication or new schedule activation. Full evidence and owner configuration:
docs/SYSTEMONE_LIVE_ACCEPTANCE_2026-11-09.md/.json.

## 2026-11-09 — Temporary test host: live native qualification PASS

Operator authorized test-d plus alias-clef. Exact root probe42565188435 returns404,
but the existing /v1/systemone operation42565240340 returns200 through both curl
and HTTPX, response identity alias-clef. Full read-only qualification42565325280
passes all18 command/profile cells; independent fresh-runner source/policy/hash/
SQLite command-cache restoration passes with zero inference calls. The full
qualification uses37 provider requests including policy exercises. Cost unknown.
No persistent provider settings, production data or schedules changed; PR8 draft.
This supersedes the inference-unqualified status only for these native public
fixture checks on the temporary host. Original host/laya failure and generative
technical-learning limitations remain. Evidence and configuration:
docs/SYSTEMONE_TEST_SERVER_ACCEPTANCE_2026-11-09.md/.json.

## 2026-11-09 — Saved production globals qualified without overrides

Owner added the missing response identity and URL override. Read-only dispatch
42566477893 on3832608 now PASSES all18 native command/profile cells using only
repository variables/secret; verified alias-clef response, systemone exact route.
37requests across probe/policy/matrix; no pricing invented. Independent hosted
restore PASSES source/policies/checkpoint/command-cache integrity with zero
provider calls. Hosted full regression42566366763 also PASS. Direct variable API
access is still403, but runtime configuration is verified and no longer blocked.
No merge, new schedule or production publication; PR8 draft. Evidence:
docs/PRODUCTION_DECISION_CONFIGURATION.md/.json. Native generative limitations
and original host/laya failure remain separate unresolved items.
