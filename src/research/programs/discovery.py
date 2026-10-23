"""Bounded nominations reuse Horizon collectors; primary verification is separate."""

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..analyzers import canonical, ident
from ..collector import collect
from .models import Program
from .verify import official, seed_record


async def nominate(profile, configuration, observed_at, collector=collect):
    metrics = []
    records = []
    for seed in configuration.discovery_sites[: configuration.max_candidates]:
        record = seed_record(seed.model_dump(), observed_at)
        record.discovery = {"nominated_by": "reviewed_primary_site_seed", "source_url": seed.url, "primary_status": "not_yet_checked"}
        records.append((record, seed.official_domains))
    try:
        items, metrics = await collector(profile)
    except Exception:
        items = []
        metrics = [{"source": "discovery", "status": "failed", "error_code": "search_unavailable"}]
    known = {r.canonical_url for r, _ in records}
    for item in items[: profile.max_items]:
        if len(records) >= configuration.max_candidates:
            break
        try:
            url = canonical(item.url)
            # A search/aggregator mention alone never establishes primary status.
            matching = next((s for s in configuration.discovery_sites if official(url, s.official_domains)), None)
            if url in known:
                continue
            record = Program(program_id=ident(url), name=item.title[:200], original_url=url, canonical_url=url, last_checked=observed_at,
                             discovery={"nominated_by": "existing_horizon_search", "query": item.metadata.get("search_query"), "primary_status": "unverified"})
            records.append((record, matching.official_domains if matching else []))
            known.add(url)
        except ValueError:
            continue
    return records, metrics


def official_links(page, domains, limit):
    """Nominate at most a few same-operator program links, never execute them."""
    if page.error or not official(page.final_url, domains):
        return []
    import re
    output = []
    soup = BeautifulSoup(page.html, "html.parser")
    for a in soup.find_all("a", href=True):
        if len(output) >= limit:
            break
        if not re.search(r"program|accelerat|incubat|fellowship|grant|apply|funding", a.get_text(" ", strip=True), re.I):
            continue
        try:
            url = canonical(urljoin(page.final_url, a["href"]))
            if url != canonical(page.final_url) and url not in output and official(url, domains):
                output.append(url)
        except ValueError:
            continue
    return output
