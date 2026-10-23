"""Conservative official-page collection; eligibility is never inferred from snippets."""

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from ..analyzers import canonical
from ..profiles import ROOT
from ..programs.fetch import ProgramFetcher
from ..reporting import make_report
from .models import FundingDataset, Opportunity, Resource, merge_refresh


async def collect_opportunities(*, sources=None, fetcher=None, observed_at=None):
    now = observed_at or datetime.now(UTC)
    sources = sources if sources is not None else json.loads((ROOT / "config/funding-sources.json").read_text())["sources"]
    if len(sources) > 40 or len({s["opportunity_id"] for s in sources}) != len(sources):
        raise ValueError("Funding registry requires at most 40 unique stable IDs")
    fetcher = fetcher or ProgramFetcher(max_pages=40)
    records = []
    for source in sources:
        resource = Resource(resource_id="program", url=source["url"], title=source["program"], kind="program")
        record = Opportunity(opportunity_id=source["opportunity_id"], provider=source["provider"], program=source["program"], official_domains=source["official_domains"], checked_at=now, resources=[resource])
        if not any(urlsplit(resource.url).hostname == d or urlsplit(resource.url).hostname.endswith("." + d) for d in record.official_domains):
            raise ValueError("Funding registry URL must belong to a reviewed official domain")
        try:
            page = await fetcher.fetch(resource.url, now.isoformat())
            host = urlsplit(page.final_url).hostname or ""
            if page.error or not any(host == d or host.endswith("." + d) for d in record.official_domains):
                record.collection_error = page.error or "unreviewed_official_redirect"
            else:
                soup = BeautifulSoup(page.html, "html.parser")
                for node in soup(["script", "style", "nav", "footer"]):
                    node.decompose()
                title = soup.find("h1") or soup.find("title")
                snippet = " ".join(title.get_text(" ", strip=True).split())[:500] if title else ""
                if not snippet:
                    record.collection_error = "missing_official_program_heading"
                else:
                    record.resources = [Resource(resource_id="program", url=page.final_url, title=source["program"], kind="program", retrieved_at=now, verified=True, content_sha256=page.fingerprint, quotation=snippet)]
                    # A fetched heading proves only page availability. It proves no
                    # deadline, application availability, amount or eligibility.
            record = Opportunity.model_validate(record.model_dump())
        except (ValueError, KeyError):
            record.collection_error = "invalid_or_unavailable_official_page"
        records.append(record)
    return records


async def build_report(profile, report_id, previous=None, *, fetcher=None):
    if profile.profile_id != "funding/de-eu":
        raise ValueError("Funding requires an operator-reviewed adapter")
    registry = json.loads((ROOT / "config/funding-sources.json").read_text())["sources"]
    records = await collect_opportunities(sources=registry[:profile.max_items], fetcher=fetcher)
    prior = {r.opportunity_id: r for p in (ROOT / "research/funding-de-eu").glob("opportunities/*/opportunity.json") if (r := Opportunity.model_validate_json(p.read_text()))}
    if previous:
        prior.update({r.opportunity_id: r for r in FundingDataset.model_validate(previous["statistics"]["funding"]).opportunities})
    records = [merge_refresh(prior[r.opportunity_id], r) if r.opportunity_id in prior else r for r in records]
    sources, findings, metrics = [], [], []
    for record in records:
        metrics.append({"source": record.opportunity_id, "status": "review_required" if record.collection_error == "official_terms_need_reverification" else "failed" if record.collection_error else "ok"})
        for resource in record.resources:
            if not resource.verified or resource.retrieved_at != record.checked_at:
                continue
            canonical_url = canonical(resource.url)
            sid = hashlib.sha256(canonical_url.encode()).hexdigest()[:24]
            sources.append({"source_id": sid, "original_url": resource.url, "canonical_url": canonical_url, "publisher": record.provider, "source_kind": "primary", "published_at": None, "fetched_at": resource.retrieved_at.isoformat(), "origin_collector": "funding_official", "profile_id": profile.profile_id, "content_fingerprint": resource.content_sha256})
            findings.append({"finding_id": hashlib.sha256(record.opportunity_id.encode()).hexdigest()[:24], "event_id": record.opportunity_id, "summary": resource.quotation[:380] + "; current official page observed; applicant eligibility requires separate review.", "classification": "official_program_page", "institutions": [], "regions": [], "topics": ["funding"], "source_ids": [sid], "profile_relevance": 0, "ranking_explanation": "Official-page verification only; no eligibility inference", "verification": "single_primary_source", "corroboration": 1, "published_at": None, "observed_at": record.checked_at.isoformat(), "evidence": [{"source_id": sid, "location": "official page heading", "snippet": resource.quotation}], "limitations": ["Official terms require structured review"], "provenance": "deterministic", "geography": {}, "change_type": "new"})
    report = make_report(profile, report_id, "", findings, sources, metrics, None, "deterministic", ["Funding-specific claims require reviewed official quotations; candidate URLs are not verified facts. Applicant facts default to unknown."])
    report["statistics"]["funding"] = FundingDataset(opportunities=records).model_dump(mode="json")
    return report
