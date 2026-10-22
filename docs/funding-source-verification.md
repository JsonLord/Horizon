# Funding source verification — 22 October 2026

All times stored in records are UTC; this review date is Europe/Berlin. Work is
on `feature/program-intelligence-implementation`, draft PR #5. No network setting,
production schedule, secret, default branch or production archive was changed.

## What failed, and what is now observable

The historical operator check recorded `Tunnel connection failed: 403 Forbidden`
for all three URLs. This identifies a failure in the proxy CONNECT path; no
destination response, redirect or original headers were retained. The exact
denying component and policy rule cannot be reconstructed. It is **not** evidence
that any funding provider refused access. The previous generic Horizon
`network_unavailable` error also obscured a separate local DNS failure.

On 22 October, all three original URLs returned successful CONNECT 200 and HEAD
200 through the inherited proxy, with no redirects. Robots files returned 200
and permitted the program URLs. Operator GET checks then returned 200 with the
official program content. Dated, allowlisted response headers and access checks
are embedded in each `opportunity.json`, `sources.json` and generated `evidence.md`.
No authorization headers, cookies, proxy addresses, credentials or full pages are
included. The `server: envoy` header alone does not identify an original refusal.

Local `socket.getaddrinfo` still fails for all three hosts. Horizon's bounded
collector stops **before HTTP**, now reporting `local_dns_unavailable`. Its DNS,
SSRF, redirects, robots, MIME and size protections remain in force. Operator
verification of these fixed official URLs through the existing authorized proxy
does not add a proxy-DNS exception to Horizon or a new general crawler.

The runtime policy observation says `state: unknown` and its effective host list
does not include these sites, despite the successful proxy responses. The reason
for the changed proxy behavior is therefore unknown. No claim is made that the
saved draft was applied, that the policy is enforced, or that an unapproved
network change is needed to explain current access.

## Programs and official alternatives

| Program | Original official URL | Authoritative material retrieved | Final classification |
| --- | --- | --- | --- |
| IBB GründungsBONUS Plus | https://www.ibb.de/de/foerderprogramme/gruendungsbonus-plus.html | Program page and linked Berlin funding guideline (16 January 2026), 175,995-byte PDF | Official terms verified; applicant `ELIGIBILITY_UNKNOWN` |
| KfW ERP-Gründerkredit – StartGeld (067) | https://www.kfw.de/inlandsfoerderung/Unternehmen/Gr%C3%BCnden-Nachfolgen/F%C3%B6rderprodukte/ERP-Gr%C3%BCnderkredit-Startgeld-(067)/ | Program page and linked Merkblatt 6000002258 (18 June 2026), 78,814-byte PDF | Official terms verified; applicant `ELIGIBILITY_UNKNOWN` |
| EU EIC Accelerator | https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en | Official program, eligibility, financing and 2026 full-proposal schedule on the Commission page | Official terms and scoped cutoff verified; applicant `ELIGIBILITY_UNKNOWN` |

Official alternative links discovered on those pages:

- [IBB funding guideline](https://www.ibb.de/media/dokumente/foerderprogramme/wirtschaftsfoerderung/gruendungsbonus-plus/richtlinie-gruendungsbonus-plus.pdf): robots permitted; HEAD/GET 200; SHA-256
  `57f3fc2de79cf66c81bf5fce008358d028e24d61a3fee90e563a655c1a486a37`.
  This explicitly describes a **conditionally repayable**, purpose-bound grant;
  it must not be advertised as unconditionally non-repayable funding.
- [IBB Business Team application information](https://www.ibb-business-team.de/gruendungsbonus-plus): robots permitted; HEAD 301 to the same URL with a trailing slash.
  The application resource remains unverified; no submission was attempted.
- [KfW Merkblatt](https://www.kfw.de/PDF/Download-Center/F%C3%B6rderprogramme-(Inlandsf%C3%B6rderung)/PDF-Dokumente/6000002258_M_067_StartGeld.pdf): robots permitted; HEAD/GET 200; SHA-256
  `3e4aa0b2b99f60f9354f8410f490db57fc14a3a431f5dec9cdf13e5453229e6e`.
  It documents a loan up to EUR 200,000, not a grant. Linked SME/de-minimis forms,
  business-plan template and required-facts checklist are registered as links;
  their document contents were not separately verified.
- [EIC Work Programme 2026](https://eic.ec.europa.eu/document/download/52598755-1351-4b54-b46b-e2682d0a3aec_en): official linked document route; robots permitted; HEAD 200/PDF.
  Download stopped at the existing 2,000,000-byte ceiling. The document is linked
  as **unverified content**; its contents are not used for funding claims.
- [Official EIC application portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-EIC-2026-ACCELERATOR-01): robots permitted; HEAD 200. Optional navigation query parameters from the source link were omitted and the resulting route was checked. Portal content/submission eligibility is unverified; no login or application occurred.

PDFs were examined only in temporary storage. The repository retains short
quotations, URLs, dates and hashes, not redistributed documents or full pages.

## Funding decisions and deadlines

All three applicant classifications remain `ELIGIBILITY_UNKNOWN`; verified
shortlist count remains zero. Applicant facts are still empty and complete
eligibility is not asserted. IBB's explicit current notice supports application
status `OPEN`; its fixed/rolling deadline is unknown. KfW's deadline and current
application status remain unknown; lack of a deadline is not evidence of rolling
availability.

EIC's **4 November 2026 at 17:00 Europe/Brussels** cutoff is explicitly scoped to
the **2026 full proposal (Step 2), after a short-proposal GO decision**. Short
proposals are a separate rolling step. The scope is included in the record,
overview and aggregate index. Renaming `EU__EIC-Accelerator__UNKNOWN` to
`EU__EIC-Accelerator__2026-11-04` preserved stable ID `eu-eic-accelerator`, earlier
events and prior source references. No deadline was inferred for IBB or KfW.

## Saved network draft: inspected, not modified

Read-only inspection found draft revision 6, ID
`493f88d7-09ca-41d8-9aee-4c505bd70eb1~cecfgdraft_6ad93640f34481a18c3fc83be7365910`.
It keeps restricted mode and the `package_managers` preset. Compared with the
reported effective runtime host list, it proposes five additional destinations:

1. `www.ibb.de`
2. `www.ibb-business-team.de`
3. `www.kfw.de`
4. `eic.ec.europa.eu`
5. `ec.europa.eu`

It removes no existing custom host. It has 162 custom entries versus nine in the
reported runtime configuration: the other 148 added custom entries are already
allowed effectively, including 116 preset hosts and 32 other effective aliases.
Those are redundant explicit copies, not additional effective destinations under
the observed preset expansion. Future preset changes could make that redundancy
material. A minimal reviewed proposal would preserve the nine custom entries and
add only the five needed destinations; **no rewrite or activation was performed**.
No network change is requested based solely on the current successful responses.

## Verification and next milestone

`research_funding diagnose` is read-only and publishes only bounded, non-sensitive
headers. Unknown-origin HTTP failures stay unknown. New tests cover attribution,
header rejection, historical hash compatibility, failed-refresh staleness and
consecutive service restoration. A failed collection no longer republishes old
quotes with a fresh timestamp. Changed official page content requires terms
review and cannot promote eligibility.

The manual-only `funding_qualification` input on `horizon-intel.yml` skips legacy
collection/publication and invokes the same service twice in a GitHub-hosted job.
The second fresh service restores the first execution's intel and opportunity
trees. It checks three freshly retrieved official pages, stable IDs/folder paths,
deadline history growth, one overview per folder, deterministic regeneration and
zero promotions. It uploads local artifacts and emits a compact public proof;
the job has contents-read permission and no publisher call. This is two executions
inside one hosted job, not two separate workflow runs or runners.

Live run IDs, exact test outcomes and remaining limitations are recorded in
`docs/agent-research.md` after execution. PR #5 must remain in draft.
