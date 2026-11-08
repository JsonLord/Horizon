# Technical radar implementation audit

Base: shared-filtering `05ab6d8`, PR #7 → funding branch PR #5 → main. Both PRs
were open and draft at the 2026-11-08 audit. Work is isolated on
`feature/technical-radar-fleet`; no merge or production schedule activation.

Reused without modifying their behavior: credential-free Google News collector,
public URL canonicalization/redirect/response bounds, profile validation, atomic
report writer, shared six-command filtering/budgets, transactional SQLite working
cache and existing CLI/MCP. Existing publishers still exclusively target `intel`.
Funding eligibility, authored funding document, Laya and original workflows remain
independent. Three new profiles use the existing approved `examples/` namespace;
there are now 15 discoverable profiles and still 24 MCP tools.

New `src/research/radar/` layers provide typed technical evidence/rubric contracts,
per-radar state, conservative distillation, fixed Friday windows, immutable history,
data-tree validation and a GitHub REST publisher. The shared provider adds one
technical-learning response contract without replacing its six existing commands.
All provider settings remain global Actions variables/secret. No endpoint/model
is embedded in profiles. Source text is untrusted evidence, never instructions.

A controller workflow uses a fixed three-radar matrix and an isolated reusable
worker per radar: read-only collection, separate read-only artifact validation,
then a main-only disabled-by-default data publisher. This isolates a failed radar
from the other two. No branch-supplied code, pickle or database is executed.
Portable JSON caches are bounded and revision/policy/model scoped. Reports are
content-addressed; retained snapshots are immutable; publication uses non-force
optimistic ref updates and bounded conflict retries. No delivery infrastructure.

Each source register has balanced en/de/fr queries and reviewed official project
repository seeds. Public API retrieval verified all six registered repositories
and release endpoints during the local smoke. No invented institutional feeds.
Other source families (papers/labs/conferences/blogs/benchmarks) remain explicit
review tasks rather than being misrepresented as verified feeds. Search results
are nominations, not authoritative technical verification.

Limitations to retain in review: live inference/hosted recovery are blocked by
Actions availability; source-language heuristics alone cannot qualify a concept;
conservative fallback retains review entries at score 1; cross-language same-story
classification needs actual multilingual provider evaluation; complete historical
coverage and reviewer labels are not established by the local collection smoke.
