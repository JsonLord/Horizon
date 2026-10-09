import asyncio
from datetime import datetime, timezone
from src.models import Config, ContentItem, SourceType
from src.orchestrator import HorizonOrchestrator
from src.storage.manager import StorageManager


def test_native_no_key_pipeline_stages(tmp_path, monkeypatch):
    monkeypatch.delenv("HORIZON_AI_MODE", raising=False)
    monkeypatch.delenv("MISSING_FIXTURE_KEY", raising=False)
    config = Config.model_validate(
        {
            "ai": {
                "provider": "openai",
                "model": "fixture",
                "api_key_env": "MISSING_FIXTURE_KEY",
                "mode": "off",
            },
            "sources": {},
            "filtering": {},
        }
    )
    o = HorizonOrchestrator(config, StorageManager(str(tmp_path)))
    items = [
        ContentItem(
            id="fixture",
            title="Fixture grounded title",
            source_type=SourceType.RSS,
            url="https://example.org/fixture",
            published_at=datetime.now(timezone.utc),
        )
    ]

    async def run():
        result = await o._analyze_content(items)
        assert result[0].ai_summary == items[0].title
        assert result[0].metadata["model_used"] is None
        await o._enrich_important_items(result)
        summary = await o._generate_summary(result, "2026-01-01", 1)
        assert (
            "Fixture grounded title" in summary
            and "https://example.org/fixture" in summary
        )

    asyncio.run(run())


def test_mcp_native_scoring_and_enrichment_without_key(tmp_path, monkeypatch):
    import json
    from src.mcp.service import HorizonPipelineService

    monkeypatch.setenv("HORIZON_AI_MODE", "off")
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "ai": {
                    "provider": "openai",
                    "model": "fixture",
                    "api_key_env": "FIXTURE_MISSING_KEY",
                },
                "sources": {},
                "filtering": {},
            }
        )
    )
    service = HorizonPipelineService(runs_root=tmp_path / "runs")
    # Use the actual stage store and actual native models, with only collection provided by fixtures.

    store = service.run_store
    run_id = store.create_run()
    if isinstance(run_id, dict):
        run_id = run_id["run_id"]
    item = ContentItem(
        id="fixture",
        title="Fixture grounded title",
        source_type=SourceType.RSS,
        url="https://example.org/fixture",
        published_at=datetime.now(timezone.utc),
    )
    store.save_items(run_id, "raw", [item.model_dump(mode="json")])

    async def run():
        scored = await service.score_items(run_id, config_path=str(config))
        assert scored["scored"] == 1
        await service.filter_items(run_id, config_path=str(config), topic_dedup=False)
        result = await service.enrich_items(run_id, config_path=str(config))
        assert result["enriched"] == 1

    asyncio.run(run())
