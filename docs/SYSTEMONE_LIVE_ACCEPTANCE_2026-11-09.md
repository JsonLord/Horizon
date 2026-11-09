# SystemOne protocol and live acceptance — 2026-11-09

The operator supplied a native model/state/questions request and model/answers/usage
response. This supersedes the earlier OpenAI-chat assumption for this operation.
Application source: db68178fceffa30005188dd3e676aad3a8c4cd8a. PR #8 remains draft.

## Implementation and checks

An explicit systemone mode uses the complete configured operation URL without
suffixes. OpenAI chat remains the default, and legacy program Laya stays separate.
All six semantic commands use typed choices with validated evidence/event IDs,
model identity, probability distributions and usage. Native probabilities remain
uncalibrated metadata; ranking uses documented ordinal mappings. Funding eligibility
hard rules are unchanged. Unsupported free-text technical-learning generation
makes no request and falls back to deterministic review.

Local Python 3.11 suite: 524 passed in 5.18s, including 19 native-protocol tests.
Both MCP smoke checks passed (24 tools, 15 profiles); funding consistency,
actionlint, schedule consistency and diff checks passed. Hosted application CI:
https://github.com/JsonLord/Horizon/actions/runs/42558554176 — success.

## Actual runner observations

| Run | Scope | Result |
| --- | --- | --- |
| [42558670374](https://github.com/JsonLord/Horizon/actions/runs/42558670374) | Native six-command/three-policy qualification | HTTP 404, 0/18 validated cells; independent fresh-runner checkpoint recovery passed |
| [42559142256](https://github.com/JsonLord/Horizon/actions/runs/42559142256) | Exact operator sample through HTTPX | HTTP 404, model_not_found_hint |
| [42559911506](https://github.com/JsonLord/Horizon/actions/runs/42559911506) | Same exact sample/token through HTTPX and literal curl | Both HTTP 404, model_not_found_hint; curl HTTP/2, zero redirects |

Sample diagnostics completed successfully because they captured the failure;
that green status is **not successful inference**. The token was present, without
a Bearer prefix or whitespace; its value and the response body were never logged.
The request alias was alias-laya. The expected response identity laya-rl-agent is
from the operator example and has not been observed in a successful hosted response.

The operator reports that the exact curl works in their environment. The runner
comparison rules out a Python-only client issue in this test. It does not establish
that the key is invalid, valid, identical to the operator's effective credential,
or entitled to this alias. Credential/access, runner-origin routing and server-side
alias availability remain unresolved. No access restrictions were bypassed.

## Owner configuration and next check

No repository setting was changed: the integration's previous variable-write
attempt returned 403. An authorized owner should compare the known-working token
with the repository secret through the settings UI, without posting it in chat or
logs, and confirm model access from GitHub-hosted runners with the provider.
A secret can be replaced from the known-working credential without exposing it.
Do not guess another alias or endpoint from this diagnostic.

For the explicitly selected native protocol, configure global variables:

- HORIZON_DECISION_API_MODE=systemone
- HORIZON_DECISION_BASE_URL: the approved complete operation URL
- HORIZON_DECISION_MODEL=alias-laya
- HORIZON_DECISION_RESPONSE_MODEL=laya-rl-agent (identity from operator example)
- Optional HORIZON_DECISION_CHAT_URL overrides BASE_URL; clear any stale override.
- HORIZON_DECISION_API_KEY: the existing repository secret, raw token only.

No endpoint or identity is placed in research profiles. Qualification supplied
instance-only overrides; it did not persist global configuration. After access is
resolved, rerun read-only qualification and require all 18 validated cells plus
independent restore before calling shared inference qualified. Native classification
does not qualify technical explanation/code generation or digest quality.

Safe job annotations and exact source/run metadata are retained in the adjacent
JSON file. Isolated qualification branches changed only a registered workflow wrapper.
No production data, schedules, merge state or Paperclip integration was changed.
