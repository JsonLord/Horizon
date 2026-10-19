"""Robots-aware public HTML retrieval using the shared bounded SSRF client."""

import asyncio
from dataclasses import dataclass, field
import hashlib
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ..analyzers import canonical
from ..collector import BoundedClient
from ..profiles import safe_url


@dataclass
class Page:
    requested_url: str
    final_url: str
    observed_at: str
    html: str = ""
    error: str | None = None
    redirects: list[str] = field(default_factory=list)

    @property
    def fingerprint(self):
        return hashlib.sha256(self.html.encode()).hexdigest()


class ProgramFetcher:
    def __init__(self, client=None, max_pages=20):
        self.client = client
        self.max_pages = max_pages
        self.requests = 0
        self.robots = {}

    async def fetch(self, url, observed_at):
        url = canonical(url)
        safe_url(url)
        if self.requests >= self.max_pages:
            return Page(url, url, observed_at, error="page_budget_exhausted")
        self.requests += 1
        own = self.client is None
        client = self.client or BoundedClient(timeout=15, headers={"User-Agent": "HorizonProgramWatch/1.0"})
        current, redirects = url, []
        try:
            # BoundedClient normally handles redirects; an explicit redirect hook
            # checks robots on every destination before its HTML is requested.
            async def allow(target):
                origin = f"https://{urlsplit(target).netloc}"
                if origin not in self.robots:
                    try:
                        response = await client.get(origin + "/robots.txt")
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code != 404:
                            raise
                        response = httpx.Response(200, text="")
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    self.robots[origin] = parser
                if not self.robots[origin].can_fetch("HorizonProgramWatch", target):
                    raise ValueError("robots_disallowed")
                redirects.append(target)
            if isinstance(client, BoundedClient):
                client.before_request = allow
                # robots requests must not recursively invoke their own hook.
                client.robots_in_progress = False
            else:
                await allow(url)
            response = await client.get(url)
            current = canonical(str(response.url))
            if not response.headers.get("content-type", "").lower().startswith(("text/html", "application/xhtml+xml")):
                raise ValueError("unsupported_mime")
            if any(marker in response.text.lower() for marker in ("cf-chl-", "verify you are human", "checking your browser", "enable javascript and cookies")):
                raise ValueError("challenge_page")
            return Page(url, current, observed_at, response.text, redirects=redirects[:4])
        except Exception as exc:
            code = "HTTP_" + str(exc.response.status_code) if isinstance(exc, httpx.HTTPStatusError) else str(exc) if isinstance(exc, ValueError) else "network_unavailable"
            return Page(url, current, observed_at, error=code[:100], redirects=redirects[:4])
        finally:
            if own:
                await client.aclose()
