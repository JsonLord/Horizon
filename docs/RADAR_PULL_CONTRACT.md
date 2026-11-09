# Technical radar pull contract — schema 1.0

Horizon publishes data through GitHub. Consumers independently poll; there is no
notification, external API integration, dispatch queue or consumer client here.
Read-only repository access suffices (public unauthenticated requests have lower
GitHub rate limits). Research execution still requires authorized workflow dispatch.

| Radar ID | Data branch |
|---|---|
| agent-control-planes | radar/agent-control-planes |
| distributed-training | radar/distributed-training |
| rag-memory | radar/rag-memory |

All branches have the same paths. `radar-manifest.json` discovers the latest
validated digest. `weekly-digest.json` is present **only after** a complete,
schema-valid publication. History is `weekly/YYYY-Www/weekly-digest.json`, using
the ISO week of the **Friday cutoff**, including ISO year at New Year.
`reports/<content-addressed-id>.json` and `.md` retain attributed technical
research, including review findings. `radar-state.json` is the bounded portable
checkpoint; consumers should use the digest and reports rather than depend on
checkpoint internals. Branches contain data, never executable application clones.

## JSON schemas

Reviewed implementation code carries reproducible schemas:

- `schemas/radar-digest.schema.json`: Digest, Concept, Pattern, Quality, Reference.
- `schemas/radar-manifest.schema.json`: RadarManifest.
- `schemas/radar-finding.schema.json`: TechnicalFinding and scoring support.
- `schemas/radar-state.schema.json`: internal checkpoint, not a consumer API.

Regenerate with `uv run python -m scripts.radar_schemas`. Runtime Pydantic checks
also enforce cross-field constraints beyond JSON Schema: UTC boundaries, rubric
sums, source IDs, language provenance, primary evidence, evidence timestamps,
manifest/history agreement and completeness. Validate these semantics in addition
to the structural schema if building an independent consumer.

Digest fields include `schema_version`, `radar_id`, `week_start_utc`,
`week_end_utc`, `generated_at_utc`, `policy_version`, `source_languages`,
`source_references`, `top_concepts`, `code_patterns`,
`suggested_prerequisites`, `quality`, `status`. Scores are heuristics, not
probabilities; source claims and Horizon interpretation remain distinct.
References retain original title, author (null if absent), publisher, publication
and retrieval timestamps, URL, short original-language excerpt and fingerprint.
Discovery query language is separate from source language. Unknown stays unknown.
No equal-language publication quota or translation of primary evidence is applied.

Manifest fields:

| Field | Meaning |
|---|---|
| schema_version | manifest contract version, currently 1.0 |
| radar_id | fixed radar identity |
| latest_digest_path | weekly-digest.json, or null before first complete digest |
| latest_week | ISO cutoff week, or null |
| digest_status | uninitialized or complete; describes the retained latest digest |
| last_successful_collection_utc | actual successful collection time, or null |
| last_successful_digest_utc | generation time of retained validated digest, or null |

A recent collection timestamp does not mean the digest is current. There is no
self-referential commit SHA inside a digest or manifest.

## GitHub retrieval and commit pinning

The branch form is useful for discovery:

```text
GET /repos/JsonLord/Horizon/contents/radar-manifest.json?ref=radar/rag-memory
GET /repos/JsonLord/Horizon/contents/weekly-digest.json?ref=radar/rag-memory
```

For a consistent snapshot, first obtain the branch head:

```text
GET /repos/JsonLord/Horizon/git/ref/heads/radar/rag-memory
```

Save `object.sha` as the consumer's pinned revision. Use that SHA as `ref` for
**every** subsequent read, rather than resolving the moving branch each time:

```text
GET /repos/JsonLord/Horizon/contents/radar-manifest.json?ref=PINNED_SHA
GET /repos/JsonLord/Horizon/contents/weekly-digest.json?ref=PINNED_SHA
GET /repos/JsonLord/Horizon/contents/weekly/2026-W47/weekly-digest.json?ref=PINNED_SHA
GET /repos/JsonLord/Horizon/contents/reports?ref=PINNED_SHA
```

The week above is illustrative. GitHub contents responses expose Base64 `content`;
the raw media type is also supported. Use standard GitHub API authentication for
private repositories; no Horizon or external delivery secret is involved. Respect
GitHub rate limits, conditional requests/ETags and access failures. A 403 is not
proof that a digest is missing. Historical snapshots remain readable at their
publication SHA even after later branch advances.

## Identity, freshness and incomplete coverage

A digest identity is `(radar_id, week_end_utc, schema_version)`. The interval is
previous Friday 18:00 UTC **inclusive** through current Friday 18:00 UTC
**exclusive**. Delayed execution uses the intended cutoff, never its actual start.
A finding exactly at the cutoff belongs to the next week.

Detect a new digest by comparing this identity after resolving and validating the
manifest at a pinned SHA. A changed branch SHA alone can mean collection or
report updates, not a new weekly digest. Corrections use the same weekly identity
with a distinct, explicit `weekly/YYYY-Www/corrections/<review-id>/` path and
`correction.json` identifying the superseded digest hash; the original is retained.
Consumers that need correction awareness also compare the digest bytes/hash and
inspect correction history at the new pinned commit.

Repeated runs preserve the first validated snapshot for that identity. They do
not silently regenerate it from new inputs. Root updates cannot regress to an
older cutoff. Missing weeks are planned oldest-first in bounded batches (eight by
default); manual `digest --week-end <Friday-UTC>` can recover a specified week
**only from retained historical evidence and adequate collection coverage**.
A delayed collector cannot invent unavailable historical evidence. If it cannot
prove the weekly coverage, the candidate stays partial in Actions artifacts.

The manifest remains at the last-good complete digest during failures. Before the
first successful week it is uninitialized and the digest returns 404. A consumer
should wait/back off on delayed or missing digests, surface freshness, and never
interpret missing evidence as "nothing happened." Partial candidates never replace
the root. A complete digest may contain fewer than three concepts or even zero
when collection completed but qualified technical evidence was insufficient;
`quality.coverage_limitations` explains this explicitly. Empty code patterns mean
none were evidence-supported, not an instruction to invent code.

## Publication boundary

Only approved radar branches accept data publication. Existing `intel`, funding,
AUX and world archives are independent. Routine collection validates its sealed checkpoint in the same read-only job.
Optional fresh-runner durability validation also has a read-only token. Only reviewed main-branch publishing receives write access;
registry publication/scheduling flags start false. Manual qualification cannot
publish. Model output cannot select branches, paths or executable files.


Fork optimization (2026-11-09): the pilot controller is manual-only until approved
schedule materialization. Ordinary collection is once daily; a configurable second
slot remains available. No-change/not-due snapshots skip artifact/publication;
validated freshness/due-time checkpoint changes may still publish without a new
weekly identity. Friday cutoff/window and immutable history semantics are unchanged.
See FORK_ACTIONS_REACTIVATION.md for safe schedule review and budget estimates.
