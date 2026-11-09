# Fresh seven-domain test rerun — 9 November 2026

The requested attachment matches the previous real-findings milestone. Reran the
full local suite and fresh hosted collection using saved SystemOne/alias-clef
settings, with no provider overrides or implementation changes. The tested
implementation branch was ef9996e; runtime source/config matches hosted57c4165.
Collection started at23:14 CET (Europe/Berlin),9November2026.

## Exact outcomes

- Local Python3.11: **544 passed,0failed in5.95s**.
- Legacy MCP configuration/metrics and real stdio smoke: PASS,24tools/15profiles.
- Funding deterministic projection,43-link/history audit and authored-seed queue:
  PASS. Three stored opportunities remain ELIGIBILITY_UNKNOWN; four nominations
  remain pending. The authored seed is unchanged.
- Exact review schema, seven typed packs, seven unlabelled feedback templates,
  23 content hashes and all four existing radar schemas: PASS.
- actionlint, schedule consistency and git diff checks: PASS.
- Fresh [hosted regression, attempt2](https://github.com/JsonLord/Horizon/actions/runs/42574191998/attempts/2): PASS.
- Fresh [real-source collection42710013748](https://github.com/JsonLord/Horizon/actions/runs/42710013748): PASS.
- Separate [validated artifact delivery42710566016](https://github.com/JsonLord/Horizon/actions/runs/42710566016): PASS, public reports only on the draft PR.
- Separate read-only GitHub Contents API requests verified all14 domain Markdown/
  JSON files at the immutable report commit below. Actual per-command returned
  identity alias-clef was checked, not inferred from job success.

## Fresh results

476 source observations,371 bounded review candidates;29 fully model-evaluated
and5 partially evaluated. **14 candidates qualified for human review**,11 rejected,
4 duplicates.194 provider requests,135240 known tokens; monetary cost unknown.
All seven six-command replay probes returned6 cache hits with **zero new provider
requests**,42 cache hits in total. These are model judgments, not verified facts.

| Report | Candidates | Review worthy | Rejected | Duplicates | Status |
| --- | --- | --- | --- | --- | --- |
| [agent-control-planes](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/agent-control-planes/REVIEW.md) | 72 | 4 | 0 | 0 | REVIEW_READY |
| [aux](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/aux/REVIEW.md) | 41 | 3 | 2 | 1 | REVIEW_READY |
| [distributed-training](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/distributed-training/REVIEW.md) | 11 | 3 | 2 | 0 | REVIEW_READY |
| [funding-de-eu](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/funding-de-eu/REVIEW.md) | 3 | 0 | 0 | 0 | PARTIAL |
| [incubators](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/incubators/REVIEW.md) | 5 | 0 | 0 | 0 | PARTIAL |
| [rag-memory](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/rag-memory/REVIEW.md) | 39 | 2 | 4 | 0 | REVIEW_READY |
| [world-intelligence](https://github.com/JsonLord/Horizon/blob/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review/world-intelligence/REVIEW.md) | 200 | 2 | 3 | 3 | REVIEW_READY |

Report commit: `beeb72d80714cc91bf64de050da271e130dbb941`.
Each folder contains findings.json, REVIEW.md and review-labels.json.
Precision@10, recall and technical-significance values remain null; independently
confirmed factual findings remain0. No reviewer labels were fabricated.

## Unresolved research limitations, not hidden test failures

- Funding and incubators remain PARTIAL because eligibility/current terms are not
  established. EIC's known2026-11-04 deadline is historical; no open round is invented.
- Two incubator application checks remain blocked: Entrepreneur First HTTP403,
  and YCombinator's application query/fragment rejected by the existing URL guard.
  The aggregate program-coverage warning is not counted as another source failure.
- Training's German/French queries now returned2/1 items, but their actual source
  language remains unverified. Query locale is not language evidence. Current
  heuristic detections: agent radar EN3/FR5/unknown64; training EN1/unknown10;
  RAG DE1/unknown38. Weak coverage is preserved explicitly.
- 105 collected observations fall outside the world inventory cap. Most admitted
  candidates remain unassessed within the unchanged model budget; no full-corpus
  precision/recall or global novelty claim is made.
- Full text, primary benchmarks and verified technical explanations remain limited.
  Native choice classification does not provide free-form technical-learning output.

No source/policy/code changes were needed for this rerun. No merge, schedule
activation, production intel/radar write, weekly digest or Paperclip integration.
PR8 remains draft. Previous results remain pinned in historical commits.
Machine-readable outcomes and artifact metadata are in the adjacent JSON file.

## Hosted artifacts

- [live-review-seven-domains](https://github.com/JsonLord/Horizon/actions/runs/42710013748/artifacts/13714374806) — expires 2026-11-23T22:16:44Z (machine-recorded UTC).
- [validated-live-review](https://github.com/JsonLord/Horizon/actions/runs/42710566016/artifacts/13716285253) — expires 2026-11-23T22:18:03Z (machine-recorded UTC).
