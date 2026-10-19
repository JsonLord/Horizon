# Program intelligence implementation and qualification

Authoritative contract: root spec.md, Sections 0–23. Started 2026-10-19 on a clean checkout; new branch `feature/program-intelligence-implementation` derives from specification commit `27eccade5eabff623972ae7372295c360ff9b6f0`, including main hotfix `c9dcef30a10ffe67b8e399baea5c2a6787c7dfd2`. Do not merge, activate cron, change secrets or publish to intel during qualification.

## G0 — baseline (complete)

- Baseline frozen install and full regression: **322 passed in 9.48s** (Python 3.12). Existing nine profiles, local CLI and 24-tool stdio MCP remain the foundation.
- `research-validation.yml`: contents-read, PR source/schema/test/workflow paths; push only `fix/archive-provenance-compat`. Extend coverage without removing that branch.
- `horizon-intel.yml`: daily 06:23 UTC plus manual approved-profile dispatch, read-only collect, separate contents-write publisher using automatic job token. Existing workflow can be dispatched on a branch but lacks a default-branch publisher guard; close that boundary additively.
- `daily-summary.yml`: Monday 00:17 UTC/manual, provider secrets and gh-pages write. `deploy-docs.yml`: only docs pushes to main, gh-pages write. Preserve these triggers; require trusted default-branch identity before privileged manual execution.
- Existing public archive tip observed: `8125ee4505ff42802bfbdb548855744430c98caf`. Restore validates JSON/Markdown identities, sizes and SHA-256; publisher optimistically retries non-force updates, retains at most 100 reports, preserves useful latest pointers. Reuse this publisher and archive layout.
- Open PRs #2 (source registry) and #3 (Actions MCP controller/schedules) remain unmerged. Do not silently import their implementation or assume it is on main.
- The original user spreadsheet/document is not tracked on this specification branch. Preserve the exact legacy fragments recorded by Section 18, with explicit seed attribution; do not invent missing row text or a Kaospilots application URL.

## Gates

- G1 complete: eight ref/security tests pass; genuine read-only push [39188214612](https://github.com/JsonLord/Horizon/actions/runs/39188214612) and PR [39188229440](https://github.com/JsonLord/Horizon/actions/runs/39188229440) validation pass. No branch-push publisher or Pages job is triggered. PR #5 remains draft; production automation remains disabled.
- G2: seed migration, primary verification and live observations — pending.
- G3: bounded discovery, candidate qualification — pending.
- G4: inspect Needle Router contract; optional inference and transparent fallback — pending.
- G5: common archive, generated-data restrictions, fresh-runner history — pending.
- G6: genuine read-only branch execution and final acceptance — pending.

Weekly production activation and privileged Monday-path publication require a separately reviewed merge/authorization; they are not authorized by this implementation task.
