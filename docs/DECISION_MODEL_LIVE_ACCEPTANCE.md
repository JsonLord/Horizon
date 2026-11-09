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
