# Hosted Actions validation — 2026-11-09

**Execution works. Provider inference remains unqualified (HTTP 404).**
Tests were authorized after the owner reported fork Actions re-enabled. No
repository setting, schedule, merge or production publication was changed.
Implementation tested: `7d714e70ef8c2665283dd0d8d88c327fb52a20d3`, draft PR #8.
Machine evidence includes actual jobs, runner identities, source SHAs, safe
check annotations and artifact metadata in ACTIONS_LIVE_VALIDATION_2026-11-09.json.

| Test | Actual run | Outcome |
|---|---|---|
| PR regression, funding consistency and MCP | [42552489740](https://github.com/JsonLord/Horizon/actions/runs/42552489740) | PASS; all validation steps completed |
| Provider qualification | [42552497344](https://github.com/JsonLord/Horizon/actions/runs/42552497344) | FAIL: HTTP 404, 0/18 live command/profile cells validated |
| Shared checkpoint recovery, separate runner in same provider run | same run, restore job | PASS: source/policy/hashes/SQLite verified, zero inference calls |
| Funding read-only collection | [42552502452](https://github.com/JsonLord/Horizon/actions/runs/42552502452) | PASS; proposal job skipped |
| Three radar collections + three separate fresh validations | [42552509052](https://github.com/JsonLord/Horizon/actions/runs/42552509052) | PASS; all three publication jobs skipped |

## Corrected CI failure

Initial PR run 42551605745 failed pytest. Reproduced locally by setting the real
Actions environment (`GITHUB_SHA` present): the unchanged-snapshot test passed
`local-development` to verification while the CLI correctly sealed the actual
source SHA. The test now explicitly supplies its own fixture SHA. The production
source/hash check is unchanged. All **500 tests passed locally on Python 3.11
under Actions-like environment variables (5.33s)**. The subsequent hosted PR
validation passed. No failed test was disabled or skipped.

## Provider result and configuration visibility

The job confirms base/model/key presence and `API_MODE=openai_chat`. Safe path
classification is `prefix_without_v1`; it does not reveal the hostname or path.
The standard adapter appends `/v1/chat/completions` to such a base. This is a
supported base shape, not proof the configuration is wrong.

Configured model alias: `alias-laya`. No model identity was reported successfully
by the server. Three requests returned 404/non-success; the circuit then stopped
additional network attempts. All 18 AUX/Funding/World command cells remain
unvalidated. First measured failure latency was 602 ms; model token usage and
cost are unknown. There is no evidence establishing an invalid key, account
problem, billing failure or whether the 404 is route/model/intermediary related.
The base/endpoint routing and model mapping need operator review; no settings,
credentials, endpoint paths or native provider API were guessed or changed.

Recovery was separated from inference readiness so a failed provider does not
prevent testing durable state. The fresh recovery job has no inference credential
mapping and makes zero model requests. It checks source SHA, all three policy
versions, both SQLite hashes/structure and restored history. This proves hosted
checkpoint portability, not successful model inference.

## Radar execution evidence

The new radar workflow is still absent from main's workflow registration; direct
dispatch by `radar-fleet.yml` returned 404. Testing used an isolated qualification
branch with the existing radar controller copied to the registered horizon-intel
workflow path. All application/worker code is unchanged from the tested PR head.
No merge or workflow registration change was needed.

Qualification source: `81ebc76d0d738b768fbde7d6df073f6c565ee827`, branch
`qualification/radar-readonly-7d714e7`. Its only difference from implementation
`7d714e7` is that workflow alias file. The manual event and non-main ref prevent
publishing; actual publisher jobs are skipped. An initial equivalent alias run
42551970117 also passed all six read-only jobs at the preceding implementation.

| Radar | Findings retained | Source checks | Collection time | Fresh files verified |
|---|---:|---:|---:|---:|
| agent-control-planes | 30 | 5 | 3.691 s | 63 |
| distributed-training | 8 | 5 | 5.007 s | 19 |
| rag-memory | 30 | 5 | 3.304 s | 63 |

Each radar attempted three model requests and obtained zero validated decisions;
fallback retained review findings. Known reported tokens are zero, **usage is
incomplete and cost remains null**. This is not a claim of free inference or
confirmed technical findings. English/German/unknown source-language values are
preserved as observed; French discovery remains supported without inventing
confirmed French coverage in this particular sample.

Every fresh validation matched its source SHA and file manifest on a different
hosted runner. It used zero model requests. No latest digest, eligibility
classification or production archive was published or promoted.

## Evidence access and remaining gates

The execution environment cannot download the signed artifact storage objects
because its outbound policy denies that host. Network settings were not changed.
Safe proof notices were retrieved from GitHub's check annotations instead; the
hosted fresh runners successfully downloaded and verified the artifacts. Artifact
IDs/digests are retained without signed URLs or credentials.

Actions execution, regression CI, funding workflow execution and hosted radar /
shared-state recovery now have real evidence. Live provider success, reviewed
multilingual model quality and automatic production digest publication remain
unverified. Future production activation still needs separate authorization;
PR #8 remains draft and schedules remain unactivated.
