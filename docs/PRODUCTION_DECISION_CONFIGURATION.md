# Production decision provider configuration

Status: **saved GitHub configuration verified by live qualification, without overrides**.

[Run42566477893](https://github.com/JsonLord/Horizon/actions/runs/42566477893) passed
18/18 native command/profile cells and independent fresh-runner recovery. The
owner applied the settings. Direct variable administration remains unavailable to
the integration, but that no longer blocks runtime qualification. This verifies
the feature-branch implementation; PR8 remains draft and main was not deployed.

Historical configuration attempt:
The operator approved production use on2026-11-09 after successful live native
classification and independent recovery. All five repository-variable writes were
attempted at05:09UTC and rejected403 Resource not accessible by integration. No
value was saved by this attempt; current values cannot be read with this identity.
The automatic Actions GITHUB_TOKEN does not grant repository-variable administration.

## Exact approved repository settings

| Repository variable | Value |
| --- | --- |
| HORIZON_DECISION_BASE_URL | https://test-d.blablador.fz-juelich.de/v1/systemone |
| HORIZON_DECISION_CHAT_URL | https://test-d.blablador.fz-juelich.de/v1/systemone |
| HORIZON_DECISION_MODEL | alias-clef |
| HORIZON_DECISION_RESPONSE_MODEL | alias-clef |
| HORIZON_DECISION_API_MODE | systemone |

Use the existing HORIZON_DECISION_API_KEY repository secret unchanged. Do not put
its value in the script, command line, documentation or research profiles. Both
URL variables deliberately agree so an older CHAT_URL override cannot reroute
requests. Runtime code remains configurable and has no baked-in endpoint or alias.

An owner with repository Variables read/write permission can apply exactly this
reviewable configuration from the feature branch:

```sh
bash scripts/configure-production-decisions.sh --apply
bash scripts/configure-production-decisions.sh --check
```

Alternatively enter the table in repository Settings → Secrets and variables →
Actions → Variables. The helper fails before mutation when variable read access
is denied, writes API_MODE last, and verifies every value without printing it.
The five API updates are not transactional; a later failure may leave earlier
writes applied, and the helper reports that limitation. Inspect settings if one
fails. It neither changes the API key nor touches workflows or research branches.

## Production-setting acceptance

After readback succeeds, run the registered read-only qualification with no model,
URL or API-mode overrides:

```sh
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref feature/technical-radar-fleet \
  -f shared_filtering_qualification=true \
  -f shared_filtering_durability=true
```

Require all18 command/profile cells and the independent fresh-runner recovery
check to pass. This dispatch skips regular collection and publishing. A branch
with the SystemOne implementation is required; changing variables does not deploy
unmerged code to main. PR8 remains draft and no merge is authorized by this step.
No production schedule is enabled or data published.

## Verification completed

- Full local Python3.11 suite: **524 passed in5.17s**.
- Legacy MCP configuration/metrics smoke: PASS.
- Real stdio MCP: PASS,24 tools,15 profiles.
- Funding audit: PASS,3 opportunities remain ELIGIBILITY_UNKNOWN,4 nominations
  pending,43 local links valid; authored funding seed SHA unchanged.
- Deterministic funding projections: PASS.
- Workflow actionlint and schedule consistency: PASS.
- Configuration helper Bash syntax: PASS; real --check fails closed on403 before
  any mutation, as intended for this identity.
- Live temporary-configuration qualification:18/18 cells PASS and independent
  recovery PASS, [run42565325280](https://github.com/JsonLord/Horizon/actions/runs/42565325280).
  See SYSTEMONE_TEST_SERVER_ACCEPTANCE_2026-11-09.md/.json for safe detailed proof.

Direct variable-API readback remains denied to this integration. The owner has
applied the settings, and override-free live qualification now passes (see below). Native choices cannot
produce arbitrary technical explanations/code: that capability retains deterministic
review fallback. No model scores can override evidence or funding eligibility.

Hosted regression for c73505e: [42565881811](https://github.com/JsonLord/Horizon/actions/runs/42565881811)
**PASS**: full pytest suite, schedule checks, deterministic funding projections,
funding audit, authored-seed/research policy check and both MCP smokes. This does
not change the403 production-variable authorization blocker.

## Saved-settings check — 05:15 UTC

Override-free dispatch [42566264433](https://github.com/JsonLord/Horizon/actions/runs/42566264433)
selected systemone and alias-clef from the repository settings. BASE_URL and key
were present, CHAT_URL absent (no stale override), but RESPONSE_MODEL was absent.
Inference correctly stopped locally: zero provider requests and0/18 validated
cells. Independent checkpoint recovery passed. Owner must add repository variable
HORIZON_DECISION_RESPONSE_MODEL=alias-clef, then repeat override-free qualification.
CHAT_URL is optional here because native mode uses the exact BASE_URL. No secret,
settings, production data, merge or schedule was changed by this check.

## Saved-settings acceptance PASS — 05:17 UTC

[42566477893](https://github.com/JsonLord/Horizon/actions/runs/42566477893), application
source3832608795b7a670227c8899121b583b0f2a782e, used only repository variables and
the existing secret: no mode/model/URL/identity overrides. It reports systemone,
request and verified response alias-clef, and18/18 schema-valid command/profile
cells across AUX, Funding DE/EU and World Intelligence. Both URL variables were
present and the exact-operation route was used. The job made37 provider requests
including probe/policy exercises; initial decision340input/0output tokens,1178ms;
whole-run cost unknown. Initial decision usage is not aggregate usage.

Independent fresh-runner restoration verified source revision, policy versions,
checkpoint and command-cache integrity, using zero provider requests. Hosted full
regression42566366763 also passed for this source. No application changes required
a new local suite after the prior524passing tests. Data collection and all
publishers were skipped. No merge, schedule change or production publication.
Original host/alias-laya availability remains unexplained, and native technical
free-text generation remains unsupported; those limitations do not negate the
verified choice-classification interface.
