import asyncio
from datetime import UTC, datetime

import httpx

from src.research.analyzers import analyze
from src.research.collector import BoundedClient, collect
from src.research.profiles import load_profiles


def test_multi_query_and_malformed():
    calls = []

    def response(request):
        calls.append(str(request.url))
        if "gdelt" in request.url.host:
            return httpx.Response(
                200,
                json={
                    "articles": [
                        {
                            "url": "https://example.org/science",
                            "title": "Science technology discovery",
                            "seendate": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                            "domain": "example.org",
                            "sourcecountry": "France",
                            "language": "English",
                        }
                    ]
                },
            )
        from email.utils import format_datetime

        return httpx.Response(
            200,
            text=f'<rss version="2.0"><channel><title>Fixture news</title><item><title>Science technology discovery</title><link>https://second.example.org/science</link><pubDate>{format_datetime(datetime.now(UTC))}</pubDate></item></channel></rss>',
        )

    async def run():
        p = load_profiles()["world/global"]
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as c:
            items, metrics = await collect(p, client=c)
        assert len(calls) == 7 and len(items) == 7
        assert all(m["status"] == "ok" for m in metrics)
        findings, sources = analyze(p, items)
        assert len(findings) == 1 and len(findings[0]["source_ids"]) == 2
        assert findings[0]["geography"]["event_region"] == "unknown"
        assert (
            next(s for s in sources if s["origin_collector"] == "gdelt")["published_at"]
            is None
        )
        assert (
            next(s for s in sources if s["origin_collector"] == "gdelt")[
                "source_country"
            ]
            == "France"
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, text="broken XML")
            )
        ) as c:
            items, metrics = await collect(p, client=c)
        assert not items and all(m["status"] == "failed" for m in metrics)

    asyncio.run(run())


def test_empty_valid_sources():
    async def run():
        p = load_profiles()["institutions/ecb"]

        def empty(req):
            return (
                httpx.Response(200, json={"articles": []})
                if "gdelt" in req.url.host
                else httpx.Response(
                    200,
                    text='<rss version="2.0"><channel><title>Empty fixture</title></channel></rss>',
                )
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(empty)) as c:
            items, metrics = await collect(p, client=c)
        assert items == [] and all(m["status"] == "ok" for m in metrics)

    asyncio.run(run())


def test_private_dns_and_redirect(monkeypatch):
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ],
    )

    async def run():
        async with BoundedClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200))
        ) as c:
            import pytest

            with pytest.raises(ValueError):
                await c.get("https://example.org")

    asyncio.run(run())


def test_compressed_response_is_not_decoded_twice():
    import gzip

    async def run():
        def response(req):
            return httpx.Response(
                200,
                content=gzip.compress(b'{"articles": []}'),
                headers={"Content-Encoding": "gzip"},
            )

        async with BoundedClient(transport=httpx.MockTransport(response)) as c:
            result = await c.get("https://api.gdeltproject.org/api/v2/doc/doc")
            assert result.json() == {"articles": []}

    asyncio.run(run())


def test_url_canonicalization_preserves_public_identifiers():
    from src.research.analyzers import canonical
    import pytest

    assert (
        canonical("https://example.org/article?id=123&utm_campaign=test")
        == "https://example.org/article?id=123"
    )
    with pytest.raises(ValueError):
        canonical("https://example.org/article?token=private")
