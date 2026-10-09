import json
import asyncio
from datetime import UTC, datetime

import pytest

from src.models import ContentItem, SourceType
from src.research.profiles import Profile, load_profiles, safe_url
from src.research.reporting import Archive
from src.research.service import ResearchService


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://localhost",
        "https://x.internal",
        "https://example.com?token=a",
        "https://user:pass@example.com",
    ],
)
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        safe_url(url)


def test_profiles():
    profiles = load_profiles()
    assert len(profiles) == 9
    for p in profiles.values():
        assert Profile.model_validate_json(p.canonical()).canonical() == p.canonical()
    d = profiles["world/global"].model_dump()
    d["profile_id"] = "../../bad"
    with pytest.raises(ValueError):
        Profile.model_validate(d)


def fixture_item(
    title="European Central Bank announces decision",
    url="https://ecb.europa.eu/press/test",
):
    return ContentItem(
        id="fixture",
        source_type=SourceType.GDELT,
        title=title,
        url=url,
        published_at=datetime.now(UTC),
        metadata={"query_region": "Europe", "domain": "ecb.europa.eu"},
    )


def test_e2e_archive_and_changes(tmp_path):
    async def fixture(profile, question):
        return [fixture_item()], [{"source": "gdelt", "status": "ok", "items": 1}]

    async def run():
        s = ResearchService(tmp_path, collector=fixture)
        job = await s.submit(
            {"profile_id": "institutions/ecb", "idempotency_key": "one"}
        )
        assert (
            await s.submit({"profile_id": "institutions/ecb", "idempotency_key": "one"})
        )["job_id"] == job["job_id"]
        done = await s.wait(job["job_id"])
        assert done["status"] == "completed"
        consumer = Archive(tmp_path)
        report = consumer.get(done["report_id"])
        assert report["model_used"] is None
        assert report["findings"][0]["verification"] == "single_primary_source"
        assert report["findings"][0]["change_type"] == "new"
        job2 = await s.submit({"profile_id": "institutions/ecb"})
        await s.wait(job2["job_id"])
        assert consumer.get(job2["job_id"])["findings"][0]["change_type"] == "unchanged"
        assert (tmp_path / "intel/latest/institutions/ecb.md").exists()
        for a in done["artifact_manifest"]["artifacts"]:
            import hashlib

            assert (
                hashlib.sha256((tmp_path / a["path"]).read_bytes()).hexdigest()
                == a["sha256"]
            )

    asyncio.run(run())


def test_empty_partial_and_restart(tmp_path):
    async def fixture(p, q):
        return [], [{"source": "gdelt", "status": "failed", "items": 0}]

    async def run():
        s = ResearchService(tmp_path, collector=fixture)
        j = await s.submit({"profile_id": "world/global"})
        await s.wait(j["job_id"])
        assert s.archive.get(j["job_id"])["status"] == "failed"
        assert not (tmp_path / "intel/latest/world.json").exists()
        j["status"] = "running"
        s.persist(j)
        assert ResearchService(tmp_path).get_job(j["job_id"])["stage"] == "interrupted"

    asyncio.run(run())


def test_safe_registration_persists(tmp_path):
    from src.research.profiles import load_profiles

    s = ResearchService(tmp_path)
    profile = load_profiles()["institutions/ecb"].model_dump(by_alias=True)
    s.register(profile)
    assert (
        ResearchService(tmp_path).profile("institutions/ecb").canonical()
        == s.profile("institutions/ecb").canonical()
    )
    profile["institution"]["official_feeds"] = ["https://ecb.europa.eu/fictional-feed"]
    with pytest.raises(ValueError):
        s.register(profile)


def test_secondary_mention_and_title_update():
    from src.research.analyzers import analyze

    p = load_profiles()["institutions/ecb"]
    first = fixture_item(url="https://example.org/fixture-article")
    findings, sources = analyze(p, [first])
    assert sources[0]["source_kind"] == "secondary"
    assert findings[0]["verification"] == "single_secondary_source"
    previous = {"findings": findings}
    updated = fixture_item(
        title="European Central Bank correction to decision",
        url="https://example.org/fixture-article",
    )
    changed, _ = analyze(p, [updated], previous)
    assert changed[0]["finding_id"] == findings[0]["finding_id"]
    assert changed[0]["change_type"] == "contradicted"
    assert any("review" in x for x in changed[0]["limitations"])


def test_cancel_and_queue_bounds(tmp_path):
    async def slow(p, q):
        await asyncio.Event().wait()

    async def run():
        s = ResearchService(tmp_path, collector=slow)
        jobs = [await s.submit({"profile_id": "world/global"}) for _ in range(6)]
        with pytest.raises(OverflowError):
            await s.submit({"profile_id": "world/global"})
        for j in jobs:
            assert s.cancel(j["job_id"])["status"] == "cancelled"
        await asyncio.gather(*s.tasks.values(), return_exceptions=True)

    asyncio.run(run())


def test_json_schema_fixtures():
    from pathlib import Path
    from jsonschema import validate

    for filename, schema in [
        ("report.json", "research-report"),
        ("manifest.json", "manifest"),
    ]:
        validate(
            json.loads(Path("tests/fixtures/research/" + filename).read_text()),
            json.loads(Path("schemas/" + schema + ".schema.json").read_text()),
        )


def test_empty_run_then_findings_same_day(tmp_path):
    count = 0

    async def fixture(p, q):
        nonlocal count
        count += 1
        return ([] if count == 1 else [fixture_item()]), [
            {"source": "gdelt", "status": "ok", "items": count - 1}
        ]

    async def run():
        s = ResearchService(tmp_path, collector=fixture)
        for _ in range(2):
            j = await s.submit({"profile_id": "institutions/ecb"})
            assert (await s.wait(j["job_id"]))["status"] == "completed"
        assert len(s.archive.latest("institutions/ecb")["findings"]) == 1

    asyncio.run(run())


def test_acronym_mentions_are_not_substrings():
    from src.research.analyzers import mentions

    profiles = load_profiles()
    assert not mentions(
        profiles["institutions/cern"].institution, "Growing concern over policy"
    )
    assert not mentions(
        profiles["institutions/who"].institution, "Who makes science policy?"
    )
    assert mentions(profiles["institutions/who"].institution, "WHO announces report")


def test_agent_question_sources_and_institutions(tmp_path):
    async def fixture(p, q):
        assert all(query.source == "google_news" for query in p.queries)
        assert "European Central Bank" in p.queries[0].text
        return [fixture_item(url="https://example.org/fixture")], [
            {"source": "google_news", "status": "ok", "items": 1}
        ]

    async def run():
        s = ResearchService(tmp_path, collector=fixture)
        j = await s.submit(
            {
                "profile_id": "examples/custom-research",
                "question": "Recent decisions",
                "sources": ["google_news"],
                "institution_ids": ["ecb"],
            }
        )
        done = await s.wait(j["job_id"])
        assert done["status"] == "completed"
        assert s.archive.get(done["report_id"])["findings"][0]["institutions"] == [
            "ecb"
        ]

    asyncio.run(run())


def test_cross_language_same_url_retains_query_provenance():
    from src.research.analyzers import analyze

    profile = load_profiles()["world/global"]
    first = fixture_item(
        title="FICTIONAL multilingual test announcement",
        url="https://example.org/fixture",
    )
    first.metadata.update(
        search_query="fixture english", language="English", query_region="Europe"
    )
    second = fixture_item(
        title="FIKTIVE mehrsprachige Testankündigung", url="https://example.org/fixture"
    )
    second.metadata.update(
        search_query="fixture german", language="German", query_region="Europe"
    )
    findings, sources = analyze(profile, [first, second])
    assert len(findings) == 1 and len(sources) == 1
    assert {o["language"] for o in sources[0]["observations"]} == {"English", "German"}
    assert len(findings[0]["source_ids"]) == 1
