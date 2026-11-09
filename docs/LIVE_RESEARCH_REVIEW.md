# Real-source portfolio review

Run `uv run python -m scripts.live_review --domain all` to collect the seven
approved domains. Each domain can also run independently with `--domain DOMAIN`.
The existing saved HORIZON_DECISION variables select inference; no provider URL,
model ID or secret is added to profiles. The manual/reusable live-review workflow
has contents:read, one bounded45-minute job, no schedule and no publisher.

News uses168hours, within the existing profile bound. Radars reuse registered
multilingual discovery queries and official GitHub release repositories. Funding
reuses official-page verification and existing reviewed records. Incubators reuse
program discovery/verification with legacy contract discovery disabled, then use
shared classification only. Hard eligibility remains independent. Historical and
unrefreshed application statuses do not become currently open rounds.

Outputs under data/live-review/DOMAIN: findings.json, REVIEW.md and unlabelled
review-labels.json. INDEX.md compares all seven domains without pretending their
attention rubrics form a universal significance scale. Confirmed factual findings,
technical significance and precision/recall are never invented: confirmations are
zero, technical significance and review metrics null. Evidence-backed source
statements, model judgments and editorial investigation questions are distinct.

Every observed candidate has six explicit command states. Approved request/token/
cost bounds constrain inference; excess candidates retain budget_limit states.
Only successful decisions cache. A content/policy/context/provider-bound six-command
replay demonstrates unchanged input makes zero additional requests. Cache state
is separate from human labels and raw evidence. No feedback is applied automatically.

GitHub artifacts retain packs and checkpoints14days. Readable step summaries
and seven bounded notices expose actual domain counts. GitHub truncates notice
messages at4096bytes and retains only ten per step, so full report transport
through annotations is intentionally not used.

If artifact storage is unavailable locally, the explicit live-review-recovery
workflow downloads the existing artifact on a runner, verifies the exact prior
source/run, all23 allowlisted reports, schemas, hashes, blank feedback and absence
of configured secret/endpoint echoes. Its separate optional contents:write job
revalidates the sealed handoff and copies only24 public files (23reports plus
hosted provenance) to data/live-review on feature/technical-radar-fleet. No source,
config, cache, deletion, main/intel/radar branch or force update is permitted.
The writer is disabled by default; the operator's milestone authorizes copying
validated public review reports to this draft PR. Ref conflicts fail closed.

This is a dedicated review acceptance path, not routine scheduled publication.
No weekly digest, production archive, merge, schedule or Paperclip functionality
is changed. Keep actual source, language and evidence gaps visible.

## Reproduce the evaluated implementation

The new workflow is not installed on main. The isolated registered-path wrapper
can run the exact reviewed implementation without source/provider overrides:

```sh
gh workflow run horizon-intel.yml --repo JsonLord/Horizon \
  --ref qualification/live-review-final-936d05a
```

The blank recovery inputs select read-only collection, not the optional PR writer.
For one domain locally, use `--domain aux` (or another DOMAINS key). Local inference
requires the same operator-managed environment variables; absent configuration
uses deterministic/explicit-unavailable states without new credentials.

See [the final evaluation](LIVE_RESEARCH_ACCEPTANCE_2026-11-09.md) for seven report
links, actual command budgets, language gaps, source probes, human-review guidance,
validated artifact IDs and exact tested source revisions. Review-qualified is a
human-review queue state, never independent verification or funding eligibility.
