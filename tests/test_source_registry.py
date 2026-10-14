import asyncio

import httpx
import pytest

from src.research.profiles import load_profiles
from src.research.registry import apply_registry, discover, load_registry, register

FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Test official news</title><link>https://example.org</link><description>Test</description><item><title>Test publication</title><link>https://example.org/news/one</link><pubDate>Fri, 09 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>"""


def run(coro):
    return asyncio.run(coro)


def test_discovery_registration_and_effective_profiles(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/":
            return httpx.Response(
                200,
                text='<link rel="alternate" type="application/rss+xml" href="/news.rss">',
            )
        return httpx.Response(200, content=FEED)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            path = tmp_path / "registry.json"
            source = await register(
                "https://example.org/",
                "Test source",
                ["world/global"],
                registry_path=path,
                client=client,
            )
            assert source["feed_url"] == "https://example.org/news.rss"
            assert source["verification"]["entries"] == 1
            effective = load_profiles(registry_path=path)
            assert any(
                f.url == source["feed_url"] for f in effective["world/global"].feeds
            )
            await register(
                "https://example.org/news.rss",
                "Test source",
                ["world/science-technology"],
                registry_path=path,
                client=client,
            )
            registry = load_registry(path)
            assert len(registry.sources) == 1
            assert registry.sources[0].profile_ids == [
                "world/global",
                "world/science-technology",
            ]

    run(check())
    assert seen[0:2] == ["https://example.org/", "https://example.org/news.rss"]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "https://localhost",
        "https://127.0.0.1",
        "https://example.org/?token=secret",
        "https://user:pass@example.org",
    ],
)
def test_unsafe_urls_never_requested(url):
    def handler(request):
        pytest.fail("Unsafe target must not be fetched")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            with pytest.raises(ValueError):
                await discover(url, client=c)

    run(check())


def test_cross_site_and_private_discovery_not_followed():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(
            200,
            text='<link type="application/rss+xml" href="https://127.0.0.1/private.rss"><link type="application/rss+xml" href="https://other.example/feed">',
        )

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            with pytest.raises(ValueError, match="No valid"):
                await discover("https://example.org/", client=c)

    run(check())
    assert seen == ["https://example.org/"]


def test_no_feed_and_invalid_profile_do_not_write(tmp_path):
    path = tmp_path / "registry.json"

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, text="<html>No RSS</html>")
            )
        ) as c:
            with pytest.raises(ValueError, match="No valid"):
                await register(
                    "https://example.org/",
                    "Example",
                    ["world/global"],
                    registry_path=path,
                    client=c,
                )
            with pytest.raises(ValueError, match="reviewed"):
                await register(
                    "https://example.org/",
                    "Example",
                    ["world/not-reviewed"],
                    registry_path=path,
                    client=c,
                )

    run(check())
    assert not path.exists()


def test_combined_feed_limit_is_atomic(tmp_path):
    profiles = load_profiles(include_registry=False)
    p = profiles["world/global"]
    from src.research.profiles import Feed

    p.feeds = [
        Feed(name="Fixture", url=f"https://example.org/{i}.rss") for i in range(10)
    ]
    path = tmp_path / "registry.json"

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=FEED))
        ) as c:
            with pytest.raises(ValueError):
                await register(
                    "https://example.org/feed",
                    "Example",
                    ["world/global"],
                    registry_path=path,
                    client=c,
                    profiles=profiles,
                )

    run(check())
    assert not path.exists()


def test_unknown_assignment_fails_validation(tmp_path):
    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=FEED))
        ) as c:
            await register(
                "https://example.org/feed",
                "Example",
                ["world/global"],
                registry_path=tmp_path / "registry.json",
                client=c,
            )

    run(check())
    registry = load_registry(tmp_path / "registry.json")
    registry.sources[0].profile_ids = ["world/unknown"]
    with pytest.raises(ValueError, match="unknown/disabled"):
        apply_registry(load_profiles(include_registry=False), registry)


def test_registry_feed_is_collected_and_attributed(tmp_path):
    from src.research.collector import collect
    from src.research.analyzers import analyze
    from datetime import UTC, datetime

    current = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
    content = FEED.replace(b"Fri, 09 Oct 2026 00:00:00 GMT", current)

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=content)
            )
        ) as c:
            await register(
                "https://example.org/feed",
                "Example",
                ["world/global"],
                registry_path=tmp_path / "registry.json",
                client=c,
            )
            p = load_profiles(registry_path=tmp_path / "registry.json")["world/global"]
            p.queries = []
            p.feeds = [f for f in p.feeds if "example.org" in f.url]
            items, metrics = await collect(p, client=c)
            assert metrics[0]["feed_url"] == "https://example.org/feed"
            assert metrics[0]["status"] == "ok"
            findings, sources = analyze(p, items, None)
            assert len(findings) == 1
            assert sources[0]["canonical_url"] == "https://example.org/news/one"

    run(check())


def test_feed_is_retained_when_search_fills_budget(tmp_path):
    from src.research.collector import collect
    from src.models import SourceType
    from datetime import UTC, datetime

    current = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
    content = FEED.replace(b"Fri, 09 Oct 2026 00:00:00 GMT", current)

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=content)
            )
        ) as c:
            await register(
                "https://example.org/feed",
                "Example",
                ["world/global"],
                registry_path=tmp_path / "registry.json",
                client=c,
            )
            p = load_profiles(registry_path=tmp_path / "registry.json")["world/global"]
            p.queries = [p.queries[0]]
            p.max_items = 1
            p.max_queries = 1
            p.feeds = [f for f in p.feeds if "example.org" in f.url]
            items, metrics = await collect(p, client=c)
            assert len(items) == 1
            assert items[0].source_type == SourceType.RSS
            assert len(metrics) == 2

    run(check())


def test_merged_assignment_limit_preserves_existing_file(tmp_path):
    base = load_profiles(include_registry=False)["world/global"]
    profiles = {
        f"world/test{i}": base.model_copy(
            update={"profile_id": f"world/test{i}", "feeds": []}
        )
        for i in range(21)
    }
    path = tmp_path / "registry.json"

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=FEED))
        ) as c:
            await register(
                "https://example.org/feed",
                "Example",
                list(profiles)[:20],
                registry_path=path,
                client=c,
                profiles=dict(profiles),
            )
            original = path.read_bytes()
            with pytest.raises(ValueError):
                await register(
                    "https://example.org/feed",
                    "Example",
                    [list(profiles)[20]],
                    registry_path=path,
                    client=c,
                    profiles=dict(profiles),
                )
            assert path.read_bytes() == original

    run(check())


def test_scheduled_cli_honors_profile_item_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    from argparse import Namespace
    from src.research import cli, history, profiles as profile_module

    p = load_profiles(include_registry=False)["world/global"].model_copy(
        update={"max_items": 150}
    )
    submitted = []

    class Service:
        def __init__(self, root):
            pass

        async def submit(self, payload, requested_by):
            submitted.append(payload)
            return {"job_id": "fixture"}

        async def wait(self, jid):
            return {"status": "completed", "report_id": "fixture"}

    monkeypatch.setattr(cli, "ResearchService", Service)
    monkeypatch.setattr(cli, "validate", lambda root: True)
    monkeypatch.setattr(history, "restore", lambda root, remote: {"state": "bootstrap"})
    monkeypatch.setattr(profile_module, "load_profiles", lambda: {"world/global": p})
    assert (
        run(
            cli.run(
                Namespace(
                    profile_id="world/global",
                    lookback_hours=48,
                    output=str(tmp_path),
                    publish=False,
                )
            )
        )
        == 0
    )
    assert submitted[0]["depth"] == 150
