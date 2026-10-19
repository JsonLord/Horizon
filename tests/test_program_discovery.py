import asyncio
from datetime import UTC, datetime

from src.research.profiles import load_profiles
from src.research.programs.config import load_config
from src.research.programs.discovery import nominate, official_links
from src.research.programs.fetch import Page
from tests.test_research import fixture_item


def test_search_nominates_but_cannot_establish_primary_or_open_status():
    _, config = load_config()
    async def collect(profile):
        return [fixture_item("Applications open, free money", "https://aggregator.example/offer")], [{"status": "ok", "source": "google_news"}]
    result, metrics = asyncio.run(nominate(load_profiles()["programs/incubators"], config, datetime.now(UTC).isoformat(), collect))
    assert len(result) <= config.max_candidates
    candidate, domains = result[-1]
    assert domains == [] and not candidate.facts
    assert candidate.application_status == "unknown" and candidate.fit.decision == "review"


def test_discovery_budgets_and_primary_links_are_bounded():
    _, config = load_config()
    config.max_candidates = 1
    async def collect(profile):
        return [], [{"source": "google_news", "status": "failed"}]
    result, metrics = asyncio.run(nominate(load_profiles()["programs/incubators"], config, datetime.now(UTC).isoformat(), collect))
    assert len(result) == 1 and metrics[0]["status"] == "failed"
    html = '<a href="/program">Founder program</a><a href="https://evil.example/">Apply</a><a href="https://127.0.0.1/">Grant</a>'
    page = Page("https://official.example/", "https://official.example/", "2026-10-19T00:00:00Z", html)
    assert official_links(page, ["official.example"], 1) == ["https://official.example/program"]
