# Horizon quality-calibration pilot — shadow replay (2026-11-09)

**Status: completed as a read-only retrospective screening experiment; not a live deployed two-stage filter or human-labelled benchmark.**
Source: [immutable live-review commit](https://github.com/JsonLord/Horizon/tree/beeb72d80714cc91bf64de050da271e130dbb941/data/live-review) and [hosted live run](https://github.com/JsonLord/Horizon/actions/runs/42710013748). Provider requests: **0 new** during this shadow replay.

## Inputs and sample
- 371 bounded candidates across seven domains; historical live run used 194 HTTP provider calls and 135,240 reported tokens, with no priced cost estimate.
- 54 stratified annotated candidates: all 14 shortlisted and 40 non-shortlisted. Technical/AUX/World subtotal 47; 7 funding/incubator candidates remain behind hard evidence and eligibility gates.
- Initial editorial triage (not independent human ground truth): 12 news items merit further investigation, 10 of which the existing pipeline had shortlisted; 2 were not shortlisted. **Do not report these as precision/recall.**

## Two clear missed-priority cases
- **agent-control-planes**: [langgraph-cli==0.4.42](https://github.com/langchain-ai/langgraph/releases/tag/cli%3D%3D0.4.42) — classified `UNASSESSED` in the source run; verified release/API announcement warrants review.
- **rag-memory**: [AWS ajoute à Bedrock le RAG en un seul appel et un mode de récupération seule - Unite.AI](https://aws.amazon.com/blogs/machine-learning/single-shot-and-agentic-retrieval-with-amazon-bedrock-managed-knowledge-base/) — classified `UNASSESSED` in the source run; verified release/API announcement warrants review.

## Selected primary evidence checks
- **LangGraph SDK 0.4.14**: official release documents `strict_resume` and StreamMode tools/lifecycle changes. Its `langgraph-cli 0.4.42` release introduces `deploy metrics`; the CLI item was unassessed.
- **NVIDIA Recovery**: first-party Nov 2 technical article documents a detect→attribute→isolate→restart control loop and describes operational monitoring (not a controlled throughput benchmark).
- **Google Pathways**: first-party Nov 9 announcement explains a single-controller distributed-training architecture. Distinguish product availability from measured training gains.
- **Anthropic agent memory**: Nov 6 primary research post documents dreaming/offline memory consolidation and illustrative evaluations; the sampled secondary headline is not by itself supporting evidence.
- **Amazon Bedrock**: first-party Nov 9 technical article describes `AgenticRetrieveStream` with zero/one/multiple iteration modes; the French secondary report was left unassessed.
- **Jemima Abu / CAIS**: source talk supports an observed 58% cost difference in one **uncontrolled** experiment; it explicitly does not establish a generalizable performance advantage.

## Exploratory lexical pre-screen (shadow only, NOT a hard gate)
| Domain | Candidates | Would route | Current shortlist preserved |
|---|---:|---:|---:|
| agent-control-planes | 72 | 54 | 4/4 |
| distributed-training | 11 | 8 | 3/3 |
| rag-memory | 39 | 14 | 2/2 |
| aux | 41 | 17 | 3/3 |
| world-intelligence | 200 | 138 | 2/2 |
| funding-de-eu | 3 | 3 | not applicable |
| incubators | 5 | 5 | not applicable |

The rough screen would route **239/371**, excluding **132** candidate records. All 14 current shortlist entries and all 12 sampled editorial-investigate entries pass in this **nonrepresentative** calibration sample. These are routing simulations, not measured provider savings or generalization evidence.
**Serious failure discovered in separate excluded examples:** the screen would omit an Iran–US peace-talk development and a COP31 fossil-fuel policy story. Both warrant source review. Therefore **do not deploy lexical hard rejection**, especially for world intelligence.

## Recommended controlled two-stage experiment
1. **Stage 0**: safety/source gates, exact-identity dedup and no-change cache only. Do not hard-reject based on a vocabulary shortlist.
2. **Stage 1**: deterministic priority routing (positive scores for first-party technical release/API changes and domain terms), with reserved random/long-tail exploration **per domain and language**, including items that failed keyword matches.
3. **Stage 2**: native `systemone` choice-classification on routed candidates; explore combining relevance and importance in one bounded native request after contract tests, then reserve claim-support/same-story/HFS for genuine survivors with better primary excerpts. Keep per-domain budgets and telemetry.
4. Keep funding/program hard eligibility independent of relevance, with missing official evidence routed to review rather than promoted.
5. Next: a separate held-out labelled week and human review of this manifest; measure high-significance recall, precision@10, especially language and world-tail recall, and actual calls/tokens; do not tune thresholds on this same calibration sample and report it as test accuracy.

## Evidence limitations
- Most source review-pack excerpts contain only titles, not full article content; verdict `claim-support: yes` can mean title supports itself, not that a technical claim was checked.
- Native SystemOne scores are ordinal choices, not calibrated probabilities. Original article claims and first-party claims are not necessarily independently replicated.
- All labels in the JSON are **AI-assisted editorial triage**, not the user's reviewed judgments. `uncertain` means abstain; unknown funding eligibility is a hard gate.
- The experiment uses a stratified selection enriched for existing shortlisted records; selection metrics are descriptive and cannot estimate population precision or recall.
- No GitHub Actions dispatch, production publication, model-key access, external consumer integration or workflow edit was performed.

## Saved sample
[Full 54-item triage manifest](../../data/quality-calibration/2026-11-09/triage-labels.json) (review this file before use as benchmark ground truth).
