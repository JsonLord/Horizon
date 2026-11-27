# Two-stage held-out filtering experiment

Run ID: `46049318049`. Attempt: `1`. Created: `2026-11-27T18:27:01.864037+00:00`.

All human labels remain blank. Precision and recall are not calculated.

| Domain | Status | Fresh unseen candidates | Control requests / decisions | Treatment requests / decisions | Screened out |
|---|---|---:|---:|---:|---:|
| agent-control-planes | COMPLETE | 8/8 | 9 / 0 | 9 / 0 | 2 |
| distributed-training | COMPLETE | 8/8 | 9 / 0 | 9 / 0 | 2 |
| rag-memory | COMPLETE | 8/8 | 9 / 0 | 9 / 0 | 2 |
| aux | COMPLETE | 8/8 | 9 / 0 | 9 / 0 | 2 |
| world-intelligence | INCOMPLETE | 8/8 | — | — | — |

## Method and coverage

Each complete domain is deterministically divided into four control and four treatment candidates, balancing recorded language and source type. The control requests all six existing decision commands for every candidate. The treatment routes the top priority candidate and one seeded exploration candidate; each remaining candidate is marked `SCREENED_OUT_FOR_BUDGET` and receives zero provider calls.

Actual HTTP attempts include retries and are capped at 27 per arm and domain. Token ceilings inherit the existing domain policy. Model request, token, latency and cache observations are recorded in `experiment.json`; no production policy limits were changed.

## Human review

Review all rows in `review-labels.json`, including screen-outs. Until labels are entered, precision and recall remain null.

## Limitations

- Human review labels are blank; precision and recall are not computed.
- Model decisions are uncalibrated editorial judgments, not verified facts.
- Source language comes from evidence metadata or the existing lexical heuristic; discovery locale is not treated as source language.
- An incomplete domain is reported without reusing prior candidates.
