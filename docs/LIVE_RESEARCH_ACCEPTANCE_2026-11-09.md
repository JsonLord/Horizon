# Real findings across seven domains — review delivery

Seven real-source review packs are available in draft PR8. This milestone delivers
inspection material, not verified technical facts or production qualification.
The final run collected499 observations, admitted375 candidates to the bounded
review inventory, fully evaluated29 and partially evaluated5 with the native
model, and retained12 model-qualified candidates for human review. The remaining
candidates have explicit non-evaluated/budget/verification states. No precision,
recall, calibrated confidence or independent factual-confirmation claim is made.

## Open the reports

Reports are pinned to immutable commit
`fdcde80d666e2bbf9afadac143b69c4e7a0fbb57`.

| Domain | Inventory | Full model evaluation | Review worthy | Rejected / duplicates | Main limitation | Report |
| --- | --- | --- | --- | --- | --- | --- |
| Agent Control Planes |83|5|3|0 /0|Most languages unresolved; only short release/news excerpts|[REVIEW](../data/live-review/agent-control-planes/REVIEW.md)|
| Distributed Training |9|5|3|1 /0|Zero German/French retrieval; no reproducible measured comparison|[REVIEW](../data/live-review/distributed-training/REVIEW.md)|
| RAG & Memory |37|5|2|4 /0|German/French source language unverified; primary benchmark evidence missing|[REVIEW](../data/live-review/rag-memory/REVIEW.md)|
| AUX |38|5|2|2 /2|Accessibility/AI overlap does not establish usability-testing relevance|[REVIEW](../data/live-review/aux/REVIEW.md)|
| Funding DE/EU |3|3|0|0 /0|Official pages refreshed; complete current terms/applicant facts unresolved|[REVIEW](../data/live-review/funding-de-eu/REVIEW.md)|
| World Intelligence |200|5|2|2 /0|124 additional observations outside inventory cap; mostly discovery headlines|[REVIEW](../data/live-review/world-intelligence/REVIEW.md)|
| Incubators |5|1|0|0 /0|Two application-page checks fail; founder eligibility remains unknown|[REVIEW](../data/live-review/incubators/REVIEW.md)|

Only the first three domains correspond to radar data branches. The other four
are existing research profiles. None of those production branches was published.
Each folder includes findings.json and an unlabelled review-labels.json template.
[Portfolio index](../data/live-review/INDEX.md) compares the domain-specific rubrics.

## Findings worth inspecting

This is a diverse editorial selection, not a universal significance ranking:

1. LangGraph SDK0.4.14: an actual registered GitHub release and quoted changelog
   in the agent pack. Review the diff before inferring an architectural change.
2. NVIDIA's workload-recovery article: distributed-training candidate worth
   investigating for failure handling. The feed headline is not a reproduced
   benchmark or a verified integration recommendation.
3. Zalo accessibility features for older users: potential AUX product-research
   input. Subtitle/translation usefulness needs actual accessibility evaluation;
   this is not evidence of market demand or successful usability testing.
4. A proposed shared AI-agent memory format: RAG investigation candidate. The
   originating specification/implementation remains to be located and verified.
5. European leaders' proposed closer UK ties: world-news candidate. Locate the
   primary statements and distinguish policy proposals from enacted decisions.

Potential false positives or over-interpretations, explicitly **not ground truth**:

- FSDP in an IDEX executive filing: an acronym collision, not training research.
- The Scottish fiscal-budget story: the model rejected it as irrelevant training material.
- AUX's WTM London accessibility/AI event story: possible lexical fit without
  concrete AI-assisted usability-testing evidence, despite positive model judgments.
- The prediction about frontier models learning on the job by2027: a forecast,
  not a measured distributed-training result.
- World opinion about a pre-existing plan for Europe: potentially high-impact
  background coverage rather than a newly established development.

The first two appear in the frozen earlier/probe records; current templates still
contain no fabricated reviewer labels. Read command states and evidence before
labeling a model judgment correct or incorrect.

## Evidenced research gaps and recommendations

- Training's original German/French searches each returned0; broadened native-
  language probes also returned0. Keep that gap visible. RAG's locale-specific
  queries returned items but did not establish their actual source language.
  Only the agent radar has nonzero German/French lexical detections (1 and5);
  these are heuristic, reviewable evidence labels, never inferred from query locale.
- Actual release evidence exists for LangGraph and LangChain, while PyTorch,
  Accelerate and FAISS supplied no releases in this seven-day window. Do not
  fabricate recent activity. Balance release and discovery sampling; source-first
  saturation reduced RAG review candidates to0 in the second experiment.
- Consider reviewed source expansion using public repositories whose metadata
  was actually retrieved: w3c/aria-practices, microsoft/accessibility-insights-web,
  deepspeedai/DeepSpeed and NVIDIA/Megatron-LM. The former Microsoft/DeepSpeed
  lookup resolves to deepspeedai/DeepSpeed. Activity timestamps prove neither a
  relevant release nor institutional affiliation. Review the appropriate event
  adapter and ownership before registering these as primary collectors.
- No approved paper/laboratory/conference/benchmark collector supplied primary
  research here. Register verified sources before collecting them. Do not invent
  institutional RSS URLs, papers, benchmark hardware or measured comparisons.
- Google News links are discovery URLs; the publisher's original full text was
  not independently fetched. Short excerpts cannot establish mechanisms, complete
  benchmark conditions or claim truth. Native classification cannot supply the
  missing technical-learning/generative capability.
- Funding's page headings were refreshed, but changed official content still needs
  terms review. EIC's2026-11-04 deadline is historical: its current review state is
  WATCH_FUTURE_ROUND, not an open round. The other two remain ELIGIBILITY_UNKNOWN.
  No opportunity-folder history or authored funding seed was changed.
- Incubator checks retain unknown eligibility. Entrepreneur First's application
  page returns403; Y Combinator's related application route hits the existing
  query/fragment restriction. No bypass or network-setting change was attempted.
  Distinguish primary-homepage evidence from application availability in a future
  reviewed extraction improvement; do not let model fit establish either eligibility
  or a verified current deadline. Kaospilots still has no verified source URL.
- The bounded world inventory excludes124 observations and model budgets leave
  most candidates unassessed. Evaluate sampling/source/region balance before
  increasing budgets. Label the actual false positives/negatives before tuning
  thresholds; no automatic policy or eligibility override is introduced.

Source experiments and the public repository checks are preserved in
[LIVE_RESEARCH_SOURCE_PROBES_2026-11-09.json](LIVE_RESEARCH_SOURCE_PROBES_2026-11-09.json).
Initial reports remain retrievable at commit17e4ec943d7dfc0407539b4adc711d07c3eb9b77.

## Hosted evidence and independent consumption

- [Final real collection42572214484](https://github.com/JsonLord/Horizon/actions/runs/42572214484): success, source57c41654fdda261ec2168e2e32ba7f1a76567002;
  194 provider requests,134961 known tokens, zero generated output tokens where
  reported by the native classifier. Monetary cost remains unknown, not zero.
- [Collection artifact](https://github.com/JsonLord/Horizon/actions/runs/42572214484/artifacts/13654055653): live-review-seven-domains.
- [Validated delivery42572616009](https://github.com/JsonLord/Horizon/actions/runs/42572616009): source/run/schema/hash/public-safety checks followed by a
  separate automatic-token writer restricted to24 public files under data/live-review
  on feature/technical-radar-fleet. Ref updates are never forced.
- [Validated artifact](https://github.com/JsonLord/Horizon/actions/runs/42572616009/artifacts/13653827904): validated-live-review. Both artifacts have
  real expiration timestamps on2026-11-23; committed reports remain accessible.
- All seven six-command unchanged-input probes recorded6 cache hits and **zero
  new model requests**. This is42 cache hits across seven bounded probes.
- A separate consumer retrieved all14 Markdown/JSON domain reports through the
  GitHub Contents API at the immutable report commit and verified their SHA256s.
  A first-run historical report was also fetched by pinned commit and verified.

Example read (no model credentials required):

```text
GET /repos/JsonLord/Horizon/contents/data/live-review/rag-memory/findings.json?ref=fdcde80d666e2bbf9afadac143b69c4e7a0fbb57
```

## Tests and review feedback

- Full local Python3.11 suite: **544 passed in5.25s** (20 new review tests).
- [Hosted full regression42572192768](https://github.com/JsonLord/Horizon/actions/runs/42572192768): success for implementation936d05a.
- Legacy MCP configuration/metrics smoke and real stdio smoke: PASS,24tools/15profiles.
- Funding deterministic projection,43-link/history audit and authored-seed queue
  check: PASS. Seed SHA remains5a509f585d1e05eb996ab13bdff83064ea708f08db03ea4bfd79c22fe0d5ee65.
- Seven typed review packs, exact review JSON schema, seven blank label templates,
  23 content hashes and all four existing radar schemas: PASS.
- Workflow actionlint, reviewed schedule consistency and git diff checks: PASS.

Copy a domain's template to data/live-review-feedback/DOMAIN/review.json before
labeling it; keep findings_sha256 so feedback stays tied to the original record.
That local feedback directory is ignored by default. Do not overwrite raw findings,
invent labels or automatically apply feedback to source verification/eligibility.
Precision@10 and recall remain null until real reviewed ground truth exists.

Main and all three radar ref SHAs were checked against their prior recorded heads
and remain unchanged. No production intel/radar write, schedule activation, merge,
weekly digest publication, Paperclip push/client, service or new port was introduced.
PR8 remains draft. Machine-readable evidence is in the adjacent acceptance JSON.
