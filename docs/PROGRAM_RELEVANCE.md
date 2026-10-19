# Program relevance and uncertainty

`config/program-relevance.yaml` is a validated JSON document (valid YAML 1.2), avoiding another dependency. Its public interests are software, AI, innovation, inclusive UX, entrepreneurship, mentoring and founder networking. It contains no personal eligibility data. Initial weights are **provisional**, awaiting user refinement; change them and the policy version in a reviewed PR. They must total one.

| Dimension | Weight | Deterministic evidence |
| --- | ---: | --- |
| Strategic fit | .25 | Founder/startup/venture, accelerator/incubator/grant/fellowship, entrepreneurship |
| Software/AI | .25 | Software/digital, AI, technology/innovation |
| Inclusive innovation | .10 | Accessibility/inclusion, design/UX |
| Mentoring/network | .15 | Mentoring/coaching, network/community, founders |
| Benefits | .15 | Funding/grants, practical support, equity-free/stipend |
| Terms/effort | .10 | Explicit equity-free and no-fee statements; unknown terms earn no points |

Each dimension is the fraction of its documented keyword groups present in fresh, quoted primary evidence. Absence is lack of observed support, not proof of absence. The weighted sum is a **heuristic relevance score**, not a probability. Model dimension scores may contribute at most the configured 35% when genuine inference passes schema, identity, input-hash, policy and citation validation. A router's model-selection result cannot serve as a relevance judgment.

`fit_score`, `hard_eligibility`, `evidence_confidence`, `model_self_reported_confidence` and `probability_relevant` are separate. Evidence confidence is the bounded fraction of supported fresh fact fields, a coverage heuristic rather than statistical confidence. Probability remains null and calibration remains uncalibrated. There are no human holdout labels or measured calibration metrics. Feedback and overrides do not automatically constitute calibration.

Scores >= .75 suggest prioritization, .45–.75 review, and lower scores not prioritized. These bands never bypass the evidence gate. A directly verified closed round or expired current deadline is ineligible. Missing current availability, eligibility or primary evidence forces review regardless of score. A general educational offer is distinguished from an open founder program. Geography, entity, founder stage and residency remain unknown when not stated; no private founder attributes are inferred or transmitted. Benefits, costs, equity and application steps are retained as source quotations; uncertain terms require human review.

Reviewed overrides may choose review/not-prioritized with program ID, reason and review date. They cannot turn unverified offers into prioritized opportunities. Candidate/rejection/change histories remain visible. To revise preferences, edit this policy, review the deterministic fixture results and explicitly assess real outcomes before changing weights or bands.

Kilo Health's old 2025-02-01 date is historical, not a current verified deadline. Kaospilots has no authoritative source in the supplied legacy fragments. No application URL is invented. Root `Incubator and Programs.md` is rendered from typed records in a generated-data review artifact/PR; it never silently modifies main.
