"""Unit tests for robots-aware, bounded primary excerpt fetcher (anti-headline gate)."""
from datetime import UTC, datetime
import pytest
import httpx

from src.research.evidence_fetcher import (
    CHALLENGE_MARKERS,
    PrimaryEvidenceFetcher,
    PrimaryExcerptResult,
    enrich_candidate_evidence,
    extract_body_excerpt,
)
from src.research.live_review import Candidate, Evidence
from src.research.two_stage_signals import evidence_quality, needs_primary_evidence


def make_candidate(cid: str, title: str, excerpt: str, url: str = "https://example.org/article") -> Candidate:
    ev = Evidence(
        id=f"ev-{cid}",
        url=url,
        publisher="TestPub",
        title=title,
        excerpt=excerpt,
        language="en",
        language_basis="source_metadata",
        published_at="2026-11-20T10:00:00Z",
        retrieved_at="2026-11-20T11:00:00Z",
        primary=False,
        fresh=True,
        source_type="news",
    )
    return Candidate(
        id=f"cand-{cid}",
        event_id=f"event-{cid}",
        title=title,
        url=url,
        evidence=[ev],
    )


# --------------------------------------------------------------------------- #
# 1. HTML Body Extraction & Anti-Boilerplate
# --------------------------------------------------------------------------- #

def test_extract_body_excerpt_cleans_non_content_tags():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <nav><a href="/">Home</a><a href="/news">News</a></nav>
        <header><h1>Site Header Banner</h1></header>
        <article>
            <p>Delegations from Germany and France reached an accord on strategic industrial investment in clean technologies.</p>
            <p>The bilateral agreement specifies capital mobilization and priority allocation for domestic supply-chain resilience.</p>
        </article>
        <script>console.log("analytics tracking code");</script>
        <style>.ads { display: none; }</style>
        <footer><p>Copyright 2026 All Rights Reserved. Privacy Policy.</p></footer>
    </body>
    </html>
    """
    excerpt = extract_body_excerpt(html, max_chars=300)
    assert "accord on strategic industrial investment" in excerpt
    assert "bilateral agreement specifies capital" in excerpt
    assert "Site Header Banner" not in excerpt
    assert "analytics tracking code" not in excerpt
    assert "Privacy Policy" not in excerpt
    assert len(excerpt) <= 300


def test_extract_body_excerpt_handles_empty_or_broken_html():
    assert extract_body_excerpt("") == ""
    assert extract_body_excerpt("   ") == ""
    assert extract_body_excerpt("<p>Only short</p>") == "Only short"


# --------------------------------------------------------------------------- #
# 2. needs_primary_evidence and challenge detection
# --------------------------------------------------------------------------- #

def test_needs_primary_evidence_classifies_correctly():
    title = "Significant European trade policy announcement in Brussels"
    # Headline-only excerpt
    cand_hl = make_candidate("1", title, title)
    assert needs_primary_evidence(cand_hl) is True
    assert evidence_quality(cand_hl)["quality"] == "HEADLINE_ONLY"

    # Weak excerpt (< 100 chars)
    cand_weak = make_candidate("2", title, "Short summary statement.")
    assert needs_primary_evidence(cand_weak) is True
    assert evidence_quality(cand_weak)["quality"] == "WEAK"

    # Supported excerpt
    substantive = (
        "European trade officials announced a comprehensive policy framework addressing bilateral tariffs and "
        "establishing verifiable production standards for key industrial components produced across partner states."
    )
    cand_sup = make_candidate("3", title, substantive)
    assert needs_primary_evidence(cand_sup) is False
    assert evidence_quality(cand_sup)["quality"] == "SUPPORTED"


def test_challenge_markers_downgrade_evidence_quality():
    title = "Cloud infrastructure platform updates global services"
    challenge_text = "Checking your browser before accessing the site. Just a moment... cf-chl-bypass"
    cand = make_candidate("chl", title, challenge_text)
    assert needs_primary_evidence(cand) is True
    assert evidence_quality(cand)["quality"] != "SUPPORTED"


# --------------------------------------------------------------------------- #
# 3. PrimaryEvidenceFetcher URL and MIME Validation
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_fetcher_rejects_unsafe_urls():
    fetcher = PrimaryEvidenceFetcher()
    # Non-https
    res1 = await fetcher.fetch_excerpt("http://example.org/plain-http")
    assert res1.success is False
    assert res1.error_code == "invalid_safe_url"

    # Localhost
    res2 = await fetcher.fetch_excerpt("https://localhost/admin")
    assert res2.success is False
    assert res2.error_code == "invalid_safe_url"

    # Credentials
    res3 = await fetcher.fetch_excerpt("https://user:pass@example.org/secret")
    assert res3.success is False
    assert res3.error_code == "invalid_safe_url"


@pytest.mark.anyio
async def test_fetcher_rejects_non_html_mime():
    def handler(request):
        return httpx.Response(200, headers={"Content-Type": "application/json"}, text='{"data": "json"}')

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = PrimaryEvidenceFetcher(client=client)

    res = await fetcher.fetch_excerpt("https://example.org/api/data")
    assert res.success is False
    assert res.error_code == "unsupported_mime"


@pytest.mark.anyio
async def test_fetcher_detects_challenge_page():
    def handler(request):
        html = "<html><body><p>Please enable JavaScript and cookies to continue. Checking your browser...</p></body></html>"
        return httpx.Response(200, headers={"Content-Type": "text/html; charset=utf-8"}, text=html)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = PrimaryEvidenceFetcher(client=client)

    res = await fetcher.fetch_excerpt("https://example.org/protected-article")
    assert res.success is False
    assert res.error_code == "challenge_page"


@pytest.mark.anyio
async def test_fetcher_enforces_max_pages_budget():
    def handler(request):
        return httpx.Response(200, headers={"Content-Type": "text/html"}, text="<article><p>Valid content text here.</p></article>")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = PrimaryEvidenceFetcher(client=client, max_pages=1)

    res1 = await fetcher.fetch_excerpt("https://example.org/page-1")
    assert res1.error_code != "page_budget_exhausted"

    res2 = await fetcher.fetch_excerpt("https://example.org/page-2")
    assert res2.success is False
    assert res2.error_code == "page_budget_exhausted"


# --------------------------------------------------------------------------- #
# 4. enrich_candidate_evidence Flow
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_enrich_candidate_evidence_upgrades_headline_only():
    article_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <article>
            <p>Berlin and Paris have finalized an accord on joint raw material procurement and critical supply-chain resilience.</p>
            <p>The joint strategic facility will support manufacturing resilience and safeguard essential European production lines.</p>
        </article>
    </body>
    </html>
    """

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, headers={"Content-Type": "text/html; charset=utf-8"}, text=article_html)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = PrimaryEvidenceFetcher(client=client)

    title = "Berlin and Paris finalize strategic raw material procurement pact"
    candidate = make_candidate("hl-1", title, excerpt=title, url="https://example.org/article-1")

    # Before enrichment: candidate is HEADLINE_ONLY
    assert evidence_quality(candidate)["quality"] == "HEADLINE_ONLY"
    assert needs_primary_evidence(candidate) is True

    # Run enrichment
    enriched = await enrich_candidate_evidence(candidate, fetcher=fetcher)
    assert enriched is True

    # After enrichment: candidate has primary article excerpt and is SUPPORTED
    eq = evidence_quality(candidate)
    assert eq["quality"] == "SUPPORTED"
    assert eq["has_article_excerpt"] is True
    assert candidate.evidence[0].primary is True
    assert "Berlin and Paris have finalized an accord" in candidate.evidence[0].excerpt


@pytest.mark.anyio
async def test_enrich_candidate_evidence_fails_safely_on_error():
    def handler(request):
        return httpx.Response(404, text="Not Found")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = PrimaryEvidenceFetcher(client=client)

    title = "Major trade announcement delayed pending bilateral negotiations"
    candidate = make_candidate("hl-fail", title, excerpt=title, url="https://example.org/article-404")

    enriched = await enrich_candidate_evidence(candidate, fetcher=fetcher)
    assert enriched is False
    # Remains HEADLINE_ONLY, never silently promoted
    assert evidence_quality(candidate)["quality"] == "HEADLINE_ONLY"
