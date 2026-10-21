"""Conservative primary-page extraction; search snippets never establish facts."""

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from dateutil.parser import parse

from ..analyzers import canonical, ident
from .fetch import Page
from .models import Evidence, Fact, Program


def seed_record(seed, observed_at):
    return Program(program_id=ident(seed["key"]), name=seed["name"], original_url=seed.get("url"), canonical_url=canonical(seed["url"]) if seed.get("url") else None,
                   legacy=seed.get("legacy"), last_checked=observed_at,
                   extraction_status="candidate" if seed.get("url") else "missing_source")


def official(url, domains):
    host = urlsplit(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in domains)


def refresh(record, page: Page, domains, now=None):
    now = now or datetime.now(UTC)
    result = record.model_copy(deep=True)
    result.last_checked = page.observed_at
    result.fit.decision = "review"
    result.fit.hard_eligibility = "review_required"
    if page.error or not official(page.final_url, domains):
        result.extraction_status = "blocked" if page.error and ("403" in page.error or "robots" in page.error or "challenge" in page.error) else "failed"
        result.check_error = page.error or "redirect_outside_verified_primary_domain"
        result.stale_fields = list(result.facts)
        # Retain prior verified facts, but never claim currently open after failure.
        result.application_status = "unknown"
        if "application_status" in result.facts:
            result.facts["last_known_application_status"] = result.facts["application_status"]
            result.stale_fields.append("last_known_application_status")
            del result.facts["application_status"]
        result.fit.hard_eligibility = "review_required"
        result.fit.decision = "review"
        return result
    soup = BeautifulSoup(page.html, "html.parser")
    for element in soup(["script", "style", "noscript", "nav", "footer"]):
        element.decompose()
    blocks = []
    for element in soup.find_all(["h1", "h2", "h3", "p", "li", "dt", "dd"]):
        text = " ".join(element.get_text(" ", strip=True).split())
        if text and text not in blocks:
            blocks.append(text[:1000])
    text = "\n".join(blocks)[:60000]
    if len(text.strip()) < 30:
        return refresh(record, Page(page.requested_url, page.final_url, page.observed_at, error="empty_or_script_only_page"), domains, now)
    result.canonical_url = canonical(page.final_url)
    result.extraction_status, result.check_error, result.stale_fields = "verified_page", None, []
    # Each successful refresh rebuilds current facts; previous facts without
    # fresh support survive with explicit staleness, never as new assertions.
    previous = dict(result.facts)
    result.application_status = "unknown"
    result.facts.pop("application_status", None)
    fresh = set()

    def fact(key, value, quotation, location="visible primary page text"):
        quote = quotation[:500]
        eid = ident(page.final_url + "|" + key + "|" + quote)
        evidence = Evidence(evidence_id=eid, url=page.final_url, observed_at=page.observed_at, quotation=quote, location=location,
                            content_fingerprint=page.fingerprint)
        existing = {e.evidence_id: e for e in result.source_evidence}
        existing[eid] = evidence
        result.source_evidence = list(existing.values())[-30:]
        result.facts[key] = Fact(value=value, evidence_ids=[eid], last_verified=page.observed_at)
        if key in type(result).model_fields:
            setattr(result, key, value)
        fresh.add(key)

    heading = soup.find("h1") or soup.find("title")
    if heading:
        name = " ".join(heading.get_text(" ", strip=True).split())[:200]
        # Preserve legacy names; the current page title is its own verified fact.
        fact("page_title", name, name, "h1/title")
    for anchor in soup.find_all("a", href=True):
        if re.search(r"\b(apply|application form|applications)\b", anchor.get_text(" ", strip=True), re.I):
            try:
                target = canonical(urljoin(page.final_url, anchor["href"]))
                if official(target, domains):
                    fact("application_url", target, anchor.get_text(" ", strip=True) or "application link", "a[href]=" + target[:100])
                    break
            except ValueError:
                pass
    deadline_found = None
    for block in blocks:
        match = re.search(r"(?:application\s+deadline|apply\s+by|applications?\s+close[sd]?|deadline)\s*[:\-]?\s*(.{4,100})", block, re.I)
        if not match:
            continue
        date = re.search(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}", match[1])
        if not date:
            continue
        try:
            parsed = parse(date[0])
        except (ValueError, OverflowError):
            continue
        # Old round dates are historical observations, not current deadlines.
        if parsed.year < now.year:
            fact("historical_deadline", date[0], block)
            continue
        deadline_found = parsed
        value = parsed.isoformat() if parsed.tzinfo else parsed.date().isoformat()
        fact("deadline", value, block)
        result.deadline_precision = "datetime" if parsed.tzinfo else "date"
        result.deadline_timezone = str(parsed.tzinfo) if parsed.tzinfo else None
        break
    for block in blocks:
        lower = block.lower()
        if re.search(r"\bapplications? (?:are |is |now )?closed\b|\bnot accepting applications\b", lower):
            fact("application_status", "closed", block)
            break
        if re.search(r"\bapplications? (?:are |is |now )?open\b|\baccepting applications\b", lower) and not re.search(r"\b(not|no longer|will be|soon)\b", lower):
            # An undated landing-page slogan alone is not a current open offer.
            rolling = bool(re.search(r"rolling|year[- ]round|continuously", text, re.I))
            future = deadline_found and deadline_found.date() >= now.date()
            if result.application_url and (future or rolling):
                fact("application_status", "open", block)
        if re.search(r"\bapplications? (?:will |are scheduled to )open\b", lower):
            fact("application_status", "upcoming", block)
    for key, pattern in {
        "benefits": r"\b(mentoring|mentorship|networking|workspace|coaching)\b",
        "funding_terms": r"\b(grant|funding|investment|stipend)\b",
        "equity_terms": r"\b(equity|equity[- ]free)\b",
        "cost_terms": r"\b(tuition|fee|costs?)\b",
        "eligibility": r"\b(eligible|eligibility|applicants must|who can apply)\b",
        "application_steps": r"\b(application process|submit your application|selection process)\b",
    }.items():
        block = next((b for b in blocks if re.search(pattern, b, re.I)), None)
        if block:
            fact(key, block[:500], block)
    for kind, pattern in (("education", r"\b(degree|curriculum|tuition|school)\b"), ("fellowship", r"\bfellowship\b"), ("grant", r"\bgrant program\b"), ("accelerator", r"\baccelerator\b"), ("incubator", r"\bincubator\b"), ("venture_studio", r"\bventure studio\b"), ("collaboration", r"\bproject collaboration\b")):
        block = next((b for b in blocks if re.search(pattern, b, re.I)), None)
        if block:
            fact("program_type", kind, block)
            break
    result.stale_fields = sorted(set(previous) - fresh - {"application_status"})
    if result.deadline and "deadline" in result.stale_fields:
        # Preserve the last known value but flag it; scoring ignores stale facts.
        result.fit.decision = "review"
    if not result.legacy:
        title = result.facts.get("page_title")
        if title and title.value:
            result.name = str(title.value)[:200]
    # Keep only evidence needed by retained facts, maintaining a bounded snapshot.
    retained = {eid for f in result.facts.values() for eid in f.evidence_ids}
    result.source_evidence = [e for e in result.source_evidence if e.evidence_id in retained]
    return Program.model_validate(result.model_dump())


def deduplicate(records):
    """Reviewed program identity first, canonical program page second."""
    merged = {}
    aliases = {}
    semantic = {}
    for record in records:
        key = record.program_id
        canonical_url = record.canonical_url
        title = record.facts.get("page_title")
        semantic_key = None
        if title and isinstance(title.value, str) and len(title.value) > 8 and canonical_url:
            semantic_key = (".".join(urlsplit(canonical_url).hostname.split(".")[-2:]), re.sub(r"\W+", " ", title.value.lower()).strip())
            if semantic_key in semantic:
                key = semantic[semantic_key]
        if canonical_url and canonical_url in aliases:
            key = aliases[canonical_url]
        if key in merged:
            prior = merged[key]
            # A failed alias must not replace a successfully observed program.
            if prior.extraction_status == "verified_page" and record.extraction_status != "verified_page":
                continue
            record = record.model_copy(update={"program_id": prior.program_id, "legacy": prior.legacy or record.legacy})
        merged[key] = record
        if canonical_url:
            aliases[canonical_url] = key
        if semantic_key:
            semantic[semantic_key] = key
    return list(merged.values())
