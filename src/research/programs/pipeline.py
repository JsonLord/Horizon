"""Program-watch analysis feeding the existing Report/Archive/publisher contract."""

import asyncio
from datetime import UTC, datetime
import hashlib

from ..analyzers import canonical, ident
from ..collector import collect
from ..reporting import dumps, make_report
from .config import load_config
from .discovery import nominate, official_links
from .fetch import ProgramFetcher
from .laya import classify
from .model_contract import inspect_contract
from .models import Dataset, Program
from .relevance import load_policy, score
from .verify import deduplicate, official, refresh, seed_record


MATERIAL = ("canonical_url", "application_url", "program_type", "application_status", "deadline", "deadline_timezone", "deadline_precision", "benefits", "funding_terms", "equity_terms", "cost_terms", "eligibility", "application_steps", "stale_fields", "extraction_status")


def material(record):
    return {k: getattr(record, k) for k in MATERIAL} | {"policy_version": record.fit.policy_version, "fit_score": record.fit.fit_score, "decision": record.fit.decision}


def changes(record, previous, now, soon_days):
    if previous is None:
        kind = "added"
    elif material(record) != material(previous):
        kind = "expired" if record.application_status == "closed" and previous.application_status != "closed" else "changed"
    else:
        kind = "unchanged"
    labels = [kind]
    if record.application_status == "unknown" or record.extraction_status != "verified_page":
        labels.append("unknown")
    if record.deadline and "deadline" not in record.stale_fields:
        days = (datetime.fromisoformat(record.deadline.replace("Z", "+00:00")).date() - now.date()).days
        if 0 <= days <= soon_days:
            labels.append("deadline_soon")
        elif days < 0 and kind != "expired":
            labels.append("expired")
    return [{"type": label, "observed_at": now.isoformat(), "fields": [k for k in MATERIAL if previous is not None and getattr(previous, k) != getattr(record, k)]} for label in labels]


async def build_report(profile, report_id, previous=None, *, collector=collect, fetcher=None, contract=None):
    if profile.profile_id != "programs/incubators" or profile.mode != "program_watch":
        raise ValueError("Only the approved public program profile is supported")
    now = datetime.now(UTC)
    timestamp = now.isoformat()
    sources_config, discovery = load_config()
    policy = load_policy()
    old_data = previous.get("statistics", {}).get("programs") if previous else None
    old = Dataset.model_validate(old_data) if old_data else None
    previous_by_id = {p.program_id: p for p in old.programs} if old else {}
    fetcher = fetcher or ProgramFetcher(max_pages=discovery.max_pages)
    nominations, metrics = await nominate(profile, discovery, timestamp, collector)
    pending = []
    for seed in sources_config.sources:
        record = seed_record(seed.model_dump(), timestamp)
        record = previous_by_id.get(record.program_id, record).model_copy(deep=True)
        pending.append((record, seed.official_domains, seed.related_urls))
    for record, domains in nominations:
        record = previous_by_id.get(record.program_id, record).model_copy(deep=True)
        pending.append((record, domains, []))
    nominated_ids = {p.program_id for p, _, _ in pending}
    reviewed = sources_config.sources + discovery.discovery_sites
    for record in previous_by_id.values():
        if record.program_id not in nominated_ids:
            domains = next((s.official_domains for s in reviewed if record.canonical_url and official(record.canonical_url, s.official_domains)), [])
            pending.append((record.model_copy(deep=True), domains, []))
    pending = pending[: min(profile.max_items, 20)]
    semaphore = asyncio.Semaphore(discovery.concurrency)
    failures = []

    async def update(record, domains, related):
        record.last_checked = timestamp
        if not record.canonical_url or not domains:
            failures.append({"program_id": record.program_id, "error": "primary_source_not_verified"})
            return record
        async with semaphore:
            page = await fetcher.fetch(record.canonical_url, timestamp)
            record = refresh(record, page, domains, now)
            metrics.append({"source": "program_primary", "url": page.final_url, "status": "failed" if page.error else "ok", "error_code": page.error})
            if record.check_error:
                failures.append({"program_id": record.program_id, "url": page.final_url, "error": record.check_error})
            for target in list(dict.fromkeys(related + official_links(page, domains, discovery.max_links_per_site)))[:2]:
                linked = await fetcher.fetch(target, timestamp)
                metrics.append({"source": "program_primary", "url": linked.final_url, "status": "failed" if linked.error else "ok", "error_code": linked.error})
                if linked.error:
                    failures.append({"program_id": record.program_id, "url": target, "error": linked.error})
                    record.check_error = "related_page_unavailable"
                    # The successful primary page is still fresh; inability to
                    # read an application page never establishes open/closed.
                    if target == record.application_url:
                        record.application_status = "unknown"
                        record.facts.pop("application_status", None)
                elif official(linked.final_url, domains):
                    primary = record.model_copy(deep=True)
                    fresh_primary = set(primary.facts) - set(primary.stale_fields)
                    record = refresh(record, linked, domains, now)
                    record.canonical_url, record.name = primary.canonical_url, primary.name
                    record.stale_fields = [k for k in record.stale_fields if k not in fresh_primary]
                    if record.application_status == "unknown" and "application_status" in fresh_primary:
                        record.application_status = primary.application_status
                        record.facts["application_status"] = primary.facts["application_status"]
            return record

    records = deduplicate(await asyncio.gather(*(update(*args) for args in pending)))
    contract = contract if contract is not None else await inspect_contract()
    for record in records:
        semantic, metadata = await classify(record, policy, contract)
        record.fit = score(record, policy, semantic, metadata, now)
        record.material_changes = changes(record, previous_by_id.get(record.program_id), now, discovery.deadline_soon_days)
    coverage = {"known_seed_count": len(sources_config.sources), "nomination_count": len(nominations), "records": len(records), "primary_pages_attempted": fetcher.requests,
                "verified_primary_records": sum(p.extraction_status == "verified_page" for p in records), "public_only": True, "exhaustive": False,
                "freshness_days": discovery.freshness_days, "pruned_prior_records": max(0, len(previous_by_id) + len(nominated_ids) - len(pending))}
    dataset = Dataset(policy_version=policy.policy_version, observed_at=timestamp, programs=records, coverage=coverage, failures=failures[:100],
                      previous_dataset_sha256=hashlib.sha256(dumps(old_data).encode()).hexdigest() if old_data else None,
                      model_contract={k: v for k, v in contract.items() if k not in ("schemas", "documented_interfaces")})
    # Validate complete typed records before they enter the common report.
    dataset = Dataset.model_validate(dataset.model_dump())
    findings, sources = evidence_findings(dataset)
    warnings = ["Program scores are provisional heuristics, not calibrated probabilities.", "Unknown eligibility or inaccessible application pages require human review.", "Legacy dates are historical notes, never verified current deadlines."]
    if any(not p.fit.model.get("inference_succeeded") for p in records):
        warnings.append("model_unavailable: deterministic relevance fallback used; routing is not inference.")
    if failures:
        metrics.append({"source": "program_coverage", "status": "failed", "items": 0})
    report = make_report(profile, report_id, "", findings, sources, metrics, next((p.fit.model.get("model_identity") for p in records if p.fit.model.get("inference_succeeded")), None), "program_watch", warnings)
    report["statistics"]["programs"] = dataset.model_dump(mode="json")
    report["coverage"].update(coverage)
    report["changes"] = [{"finding_id": ident(p.program_id), "program_id": p.program_id, "type": c["type"], "observed_at": c["observed_at"], "fields": c["fields"]} for p in records for c in p.material_changes if c["type"] != "unchanged"]
    return report


def evidence_findings(dataset):
    sources, findings = {}, []
    for program in dataset.programs:
        ids = []
        for evidence in program.source_evidence:
            url = canonical(evidence.url)
            sid = ident(url)
            sources[sid] = {"source_id": sid, "original_url": url, "canonical_url": url, "publisher": url.split('/')[2], "source_kind": "primary", "published_at": evidence.published_at,
                            "fetched_at": evidence.observed_at, "origin_collector": "program_primary", "profile_id": dataset.profile_id, "content_fingerprint": evidence.content_fingerprint}
            if sid not in ids:
                ids.append(sid)
        if not ids or program.extraction_status != "verified_page":
            continue
        kind = next((c["type"] for c in program.material_changes if c["type"] in ("added", "changed", "unchanged", "expired")), "unchanged")
        findings.append({"finding_id": ident(program.program_id), "event_id": program.program_id, "summary": f"{program.name}: application status {program.application_status}; {program.fit.decision}. Missing eligibility or deadlines require review."[:500],
                         "classification": "program_observation", "institutions": [], "regions": [], "topics": program.target_domains, "source_ids": ids,
                         "profile_relevance": program.fit.fit_score, "ranking_explanation": "Provisional weighted public-evidence heuristic; see statistics.programs.",
                         "verification": "single_primary_source" if program.application_status != "unknown" else "unverified", "corroboration": len(ids), "published_at": None,
                         "observed_at": program.last_checked, "evidence": [{"source_id": ident(canonical(e.url)), "location": e.location, "snippet": e.quotation} for e in program.source_evidence],
                         "limitations": ["Primary page observation does not establish eligibility or current availability unless explicitly cited."], "provenance": "deterministic_program_verification",
                         "geography": {"event_region": "unknown", "confidence": None, "evidence": []}, "change_type": "new" if kind == "added" else "unchanged" if kind == "unchanged" else "updated"})
    return findings, list(sources.values())
