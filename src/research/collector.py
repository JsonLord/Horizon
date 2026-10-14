"""Bounded multi-query adapter for Horizon's existing scrapers."""

import asyncio
import ipaddress
import socket
from datetime import UTC, datetime, timedelta

import httpx

from src.models import GDELTConfig, GoogleNewsConfig, RSSSourceConfig
from src.scrapers.gdelt import GDELTScraper
from src.scrapers.google_news import GoogleNewsScraper
from src.scrapers.rss import RSSScraper

from .profiles import safe_url


class BoundedClient(httpx.AsyncClient):
    # Fixed reviewed collectors can use proxy-side DNS in proxy-only environments.
    # Arbitrary URLs/redirect targets still require public local DNS or fail closed.
    trusted_hosts = frozenset({"api.gdeltproject.org", "news.google.com"})

    async def get(self, url, **kwargs):
        # Validate every redirect, including DNS answers, before connecting.
        from urllib.parse import urljoin, urlsplit

        kwargs.pop("follow_redirects", None)
        for attempt in range(4):
            safe_url(str(url).split("?")[0])
            host = urlsplit(str(url)).hostname
            if host not in self.trusted_hosts:
                addresses = await asyncio.to_thread(
                    socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM
                )
                if not addresses or any(
                    not ipaddress.ip_address(a[4][0]).is_global for a in addresses
                ):
                    raise ValueError("Non-public DNS target")
            async with self.stream(
                "GET", url, follow_redirects=False, **kwargs
            ) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(str(response.url), response.headers["location"])
                    kwargs.pop("params", None)
                    continue
                if response.status_code in (429, 502, 503) and attempt < 2:
                    await asyncio.sleep(0.5 * 2**attempt)
                    continue
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 2_000_000:
                        raise ValueError("Response exceeds size ceiling")
                    chunks.append(chunk)
                response.raise_for_status()
                return httpx.Response(
                    response.status_code,
                    headers={
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ("content-encoding", "content-length")
                    },
                    content=b"".join(chunks),
                    request=response.request,
                )
        raise ValueError("Redirect/retry limit")


class RecordingClient:
    def __init__(self, client):
        self.client = client
        self.response = None
        self.failed = False
        self.error_code = None

    async def get(self, *args, **kwargs):
        try:
            self.response = await self.client.get(*args, **kwargs)
            self.response.raise_for_status()
            return self.response
        except Exception as exc:
            self.error_code = (
                "HTTP_" + str(exc.response.status_code)
                if isinstance(exc, httpx.HTTPStatusError)
                else "NETWORK_ERROR"
            )
            self.failed = True
            raise

    def valid(self, source):
        if self.failed or self.response is None:
            return False
        try:
            if source == "gdelt":
                payload = self.response.json()
                return isinstance(payload, dict) and isinstance(
                    payload.get("articles"), list
                )
            import feedparser

            feed = feedparser.parse(self.response.content)
            return bool(feed.version) and not feed.bozo
        except Exception:
            return False


async def collect(profile, question="", client=None):
    since = datetime.now(UTC) - timedelta(hours=profile.lookback_hours)
    semaphore = asyncio.Semaphore(2)
    metrics = []
    own = client is None
    client = client or BoundedClient(
        timeout=20,
        limits=httpx.Limits(max_connections=4),
        headers={"User-Agent": "Horizon/0.1 research"},
    )

    if own:
        from urllib.parse import urlsplit

        reviewed = [f.url for f in profile.feeds] + (
            profile.institution.official_feeds if profile.institution else []
        )
        client.trusted_hosts = client.trusted_hosts | frozenset(
            urlsplit(u).hostname for u in reviewed
        )

    async def fetch(q):
        async with semaphore:
            try:
                recorder = RecordingClient(client)
                if q.source == "gdelt":
                    scraper = GDELTScraper(
                        GDELTConfig(
                            enabled=True,
                            query=q.text,
                            language=q.language,
                            max_records=min(100, profile.max_items),
                        ),
                        recorder,
                    )
                else:
                    scraper = GoogleNewsScraper(
                        GoogleNewsConfig(
                            enabled=True,
                            query=q.text,
                            language=q.language,
                            country=q.country,
                            max_results=profile.max_items,
                        ),
                        recorder,
                    )
                items = await asyncio.wait_for(scraper.fetch(since), 45)
                items = [
                    i
                    for i in items
                    if since
                    <= i.published_at
                    <= datetime.now(UTC) + timedelta(minutes=5)
                ]
                for item in items:
                    item.metadata.update(
                        search_query=q.text,
                        profile_id=profile.profile_id,
                        query_region=q.region,
                        query_topic=q.topic,
                        query_language=q.language,
                    )
                metrics.append(
                    {
                        "source": q.source,
                        "query": q.text,
                        "items": len(items),
                        "status": "ok" if recorder.valid(q.source) else "failed",
                        "error_code": recorder.error_code if recorder.failed else None,
                    }
                )
                return items
            except Exception:
                metrics.append(
                    {
                        "source": q.source,
                        "query": q.text,
                        "items": 0,
                        "status": "failed",
                    }
                )
                return []

    try:
        batches = await asyncio.gather(
            *(fetch(q) for q in profile.queries[: profile.max_queries])
        )
        if "rss" in profile.sources:
            feed_specs = [(f.name, f.url, f.topic, f.region) for f in profile.feeds]
            if profile.institution:
                feed_specs += [
                    (profile.name, u, "institution", "unknown")
                    for u in profile.institution.official_feeds
                ]
            for name, url, topic, region in feed_specs:
                try:
                    recorder = RecordingClient(client)
                    scraper = RSSScraper(
                        [RSSSourceConfig(name=name, url=url)], recorder
                    )
                    batch = await asyncio.wait_for(scraper.fetch(since), 45)
                    batch = [
                        i
                        for i in batch
                        if since
                        <= i.published_at
                        <= datetime.now(UTC) + timedelta(minutes=5)
                    ][: profile.max_items]
                    for item in batch:
                        item.metadata.update(
                            profile_id=profile.profile_id,
                            query_region=region,
                            query_topic=topic,
                            search_query=None,
                        )
                    batches.insert(0, batch)
                    metrics.append(
                        {
                            "source": "rss",
                            "feed_url": url,
                            "name": name,
                            "status": "ok" if recorder.valid("rss") else "failed",
                            "items": len(batch),
                            "error_code": recorder.error_code,
                        }
                    )
                except Exception:
                    metrics.append(
                        {
                            "source": "rss",
                            "feed_url": url,
                            "name": name,
                            "status": "failed",
                            "items": 0,
                        }
                    )
        # Share the item ceiling across queries and registered feeds rather than
        # dropping every appended RSS batch when search queries fill the budget.
        items = []
        for row in range(max((len(batch) for batch in batches), default=0)):
            for batch in batches:
                if row < len(batch):
                    items.append(batch[row])
                    if len(items) == profile.max_items * profile.max_queries:
                        return items, metrics
        return items, metrics
    finally:
        if own:
            await client.aclose()
