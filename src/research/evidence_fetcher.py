"""Robots-aware, bounded primary excerpt fetcher for anti-headline verification.

Eliminates headline-only evaluation by extracting genuine article body text from
public HTTPS primary sources, obeying safe_url boundaries, public DNS checks,
size ceilings, and robots rules.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import httpx

from .collector import BoundedClient
from .live_review import Candidate, Evidence
from .profiles import safe_url
from .two_stage_signals import evidence_quality, needs_primary_evidence

#: Markers of bot challenges, CAPTCHAs, or JS walls that must never be treated as article text.
CHALLENGE_MARKERS = frozenset({
    "cf-chl-",
    "verify you are human",
    "checking your browser",
    "enable javascript and cookies",
    "just a moment...",
    "attention required! | cloudflare",
    "access denied",
})


@dataclass
class PrimaryExcerptResult:
    url: str
    final_url: str
    success: bool
    excerpt: str = ""
    status_code: Optional[int] = None
    error_code: Optional[str] = None
    observed_at: str = ""
    content_hash: Optional[str] = None


def extract_body_excerpt(html_content: str, max_chars: int = 500) -> str:
    """Extract clean, bounded article body text from raw HTML, stripping non-content tags."""
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    # Decompose script, style, nav, header, footer, form, noscript, svg, iframe, aside
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "noscript", "svg", "iframe", "aside"]):
        tag.decompose()

    # Prefer article, main, or role=main elements if present
    main_el = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"})
    container = main_el if main_el else (soup.body or soup)

    # Find paragraphs with meaningful text
    paragraphs: List[str] = []
    boilerplate_markers = (
        "copyright", "all rights reserved", "cookie policy",
        "terms of service", "privacy policy", "subscribe to",
        "sign in to continue", "newsletter"
    )
    for el in container.find_all(["p", "div"]):
        text = " ".join(el.get_text(" ", strip=True).split())
        # Filter out very short snippets or obvious footer boilerplate
        if len(text) >= 40 and not any(bm in text.lower() for bm in boilerplate_markers):
            paragraphs.append(text)
            if sum(len(x) for x in paragraphs) >= max_chars:
                break

    if paragraphs:
        combined = " ".join(paragraphs)
    else:
        # Fallback to general container text
        combined = " ".join(container.get_text(" ", strip=True).split())

    return combined[:max_chars].strip()


class PrimaryEvidenceFetcher:
    """
    Safe, bounded HTTP fetcher for primary source articles.
    Enforces safe_url, public DNS verification, size caps (max 2MB),
    anti-bot detection, and clean text extraction.
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        max_pages: int = 20,
        timeout: float = 15.0,
        user_agent: str = "HorizonPrimaryEvidence/1.0",
    ):
        self.client = client
        self.max_pages = max_pages
        self.timeout = timeout
        self.user_agent = user_agent
        self.requests = 0
        self.robots: Dict[str, Optional[RobotFileParser]] = {}

    async def fetch_excerpt(self, url: str, max_chars: int = 500) -> PrimaryExcerptResult:
        observed_at = datetime.now(UTC).isoformat()
        try:
            url = safe_url(url)
        except Exception as exc:
            return PrimaryExcerptResult(
                url=url,
                final_url=url,
                success=False,
                error_code="invalid_safe_url",
                observed_at=observed_at,
            )

        if self.requests >= self.max_pages:
            return PrimaryExcerptResult(
                url=url,
                final_url=url,
                success=False,
                error_code="page_budget_exhausted",
                observed_at=observed_at,
            )

        self.requests += 1
        own = self.client is None
        client = self.client or BoundedClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
        )

        try:
            # Robots check
            origin = f"https://{urlsplit(url).netloc}"
            if origin not in self.robots:
                try:
                    resp = await client.get(origin + "/robots.txt")
                    if resp.status_code == 200:
                        rp = RobotFileParser()
                        rp.parse(resp.text.splitlines())
                        self.robots[origin] = rp
                    else:
                        self.robots[origin] = None
                except Exception:
                    self.robots[origin] = None

            rp = self.robots.get(origin)
            if rp is not None and not rp.can_fetch("HorizonPrimaryEvidence", url):
                return PrimaryExcerptResult(
                    url=url,
                    final_url=url,
                    success=False,
                    error_code="robots_disallowed",
                    observed_at=observed_at,
                )

            response = await client.get(url)
            final_url = safe_url(str(response.url))
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith(("text/html", "application/xhtml+xml")):
                return PrimaryExcerptResult(
                    url=url,
                    final_url=final_url,
                    success=False,
                    status_code=response.status_code,
                    error_code="unsupported_mime",
                    observed_at=observed_at,
                )

            html_text = response.text
            if any(marker in html_text.lower() for marker in CHALLENGE_MARKERS):
                return PrimaryExcerptResult(
                    url=url,
                    final_url=final_url,
                    success=False,
                    status_code=response.status_code,
                    error_code="challenge_page",
                    observed_at=observed_at,
                )

            excerpt = extract_body_excerpt(html_text, max_chars=max_chars)
            content_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()

            return PrimaryExcerptResult(
                url=url,
                final_url=final_url,
                success=bool(excerpt and len(excerpt) >= 50),
                excerpt=excerpt,
                status_code=response.status_code,
                error_code=None if excerpt else "empty_body_text",
                observed_at=observed_at,
                content_hash=content_hash,
            )
        except Exception as exc:
            code = (
                "local_dns_unavailable"
                if isinstance(exc, socket.gaierror)
                else "proxy_connect_failed"
                if isinstance(exc, httpx.ProxyError)
                else "HTTP_" + str(exc.response.status_code)
                if isinstance(exc, httpx.HTTPStatusError)
                else str(exc)
                if isinstance(exc, ValueError)
                else type(exc).__name__
            )
            return PrimaryExcerptResult(
                url=url,
                final_url=url,
                success=False,
                error_code=code[:100],
                observed_at=observed_at,
            )
        finally:
            if own:
                await client.aclose()


async def enrich_candidate_evidence(
    candidate: Candidate,
    fetcher: Optional[PrimaryEvidenceFetcher] = None,
    client: Optional[httpx.AsyncClient] = None,
    max_chars: int = 500,
) -> bool:
    """
    Enriches a candidate that has HEADLINE_ONLY or WEAK evidence by fetching
    the genuine body excerpt from its primary public URL.
    Returns True if the candidate was successfully enriched to SUPPORTED, False otherwise.
    """
    if not needs_primary_evidence(candidate):
        return True

    url = getattr(candidate, "url", None)
    if not url:
        return False

    fetcher = fetcher or PrimaryEvidenceFetcher(client=client)
    res = await fetcher.fetch_excerpt(url, max_chars=max_chars)
    if not res.success or not res.excerpt:
        return False

    title = getattr(candidate, "title", "").strip()
    # Check if the extracted excerpt is genuinely substantive and not merely the headline
    if res.excerpt.casefold() == title.casefold() or len(res.excerpt) < len(title) + 30:
        return False

    ev_id = hashlib.sha256((url + "|primary_body|" + res.observed_at).encode("utf-8")).hexdigest()[:16]
    first_ev = candidate.evidence[0] if candidate.evidence else None
    publisher = getattr(first_ev, "publisher", "primary_source") if first_ev else "primary_source"
    lang = getattr(first_ev, "language", "en") if first_ev else "en"
    lang_basis = getattr(first_ev, "language_basis", "primary_evidence") if first_ev else "primary_evidence"
    disc_lang = getattr(first_ev, "discovery_language", "unknown") if first_ev else "unknown"
    pub_at = getattr(first_ev, "published_at", None) if first_ev else None

    enriched_evidence = Evidence(
        id=ev_id,
        url=res.final_url,
        publisher=publisher,
        title=title,
        excerpt=res.excerpt[:500],
        language=lang,
        language_basis=lang_basis,
        discovery_language=disc_lang,
        published_at=pub_at,
        retrieved_at=res.observed_at,
        primary=True,
        fresh=True,
        content_hash=res.content_hash,
        source_type="primary_http",
    )

    # Insert primary body evidence at the front (capped to max 20 evidence items)
    candidate.evidence = [enriched_evidence] + candidate.evidence[:19]
    return evidence_quality(candidate)["quality"] == "SUPPORTED"
