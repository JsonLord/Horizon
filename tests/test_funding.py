"""Gate 1 acceptance tests; synthetic evidence is confined to temporary folders."""

import asyncio
import json
import re
from pathlib import Path
from datetime import UTC, datetime
from urllib.parse import unquote

import pytest
from pydantic import ValidationError

from src.research.funding.models import Applicant, Opportunity, assess
from src.research.funding.storage import OpportunityFolderStorage, folder_name
from src.research.funding.pipeline import collect_opportunities
from src.research.profiles import load_profiles


def record(**updates):
    payload = {"opportunity_id": "test-grant", "provider": "Test Provider", "program": "AI Grant", "official_domains": ["example.org"], "checked_at": "2026-10-21T12:00:00Z", "resources": [{"resource_id": "rules", "url": "https://example.org/grant", "title": "Synthetic rules", "kind": "guideline", "verified": True, "retrieved_at": "2026-10-21T12:00:00Z", "content_sha256": "a" * 64, "quotation": "Test-only fixture: applications open until 2027-03-15; founders may apply."}]}
    payload.update(updates)
    return Opportunity.model_validate(payload)


def verified(**updates):
    claims = {key: {"value": value, "evidence_ids": ["rules"]} for key, value in {"application_status": "OPEN", "deadline": "2027-03-15", "eligibility_complete": "true"}.items()}
    payload = dict(application_status="OPEN", deadline_kind="date", deadline="2027-03-15", eligibility_complete=True, claims=claims, conditions=[{"key": "entity", "description": "Founder legal form", "accepted_values": ["unincorporated"], "evidence_ids": ["rules"]}])
    payload.update(updates)
    return record(**payload)


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_unique_folder_canonical_names_and_explicit_unknown(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant())
    item = record()
    index = store.sync([item])
    folder = store.root / "opportunities/Test-Provider__AI-Grant__UNKNOWN"
    assert folder.is_dir()
    assert (folder / "00_OVERVIEW__ELIGIBILITY_UNKNOWN__UNKNOWN.md").exists()
    assert index["active_count"] == 0 and index["review_count"] == 1
    assert len(list(store.root.glob("opportunities/*/opportunity.json"))) == 1
    assert "UNKNOWN" in (folder / "required-documents.md").read_text()


def test_deadline_rename_preserves_stable_id_sources_history_and_resources(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant(facts={"entity": "unincorporated"}))
    old = verified()
    store.sync([old])
    old_path = store.root / "opportunities" / folder_name(old)
    (old_path / "resources/operator-note.txt").write_text("preserve permitted local resource")
    payload = old.model_dump(mode="json")
    payload["deadline"] = "2027-04-30"
    payload["claims"]["deadline"]["value"] = "2027-04-30"
    payload["resources"][0]["url"] = "https://example.org/new-round"
    updated = Opportunity.model_validate(payload)
    store.sync([updated])
    target = store.root / "opportunities" / folder_name(updated)
    assert not old_path.exists()
    assert (target / "resources/operator-note.txt").exists()
    assert len(list(store.root.glob("opportunities/*"))) == 1
    assert len(list(target.glob("00_OVERVIEW__*.md"))) == 1
    assert (target / "00_OVERVIEW__ELIGIBLE_NOW__2027-04-30.md").exists()
    events = [json.loads(x) for x in (target / "change-history.jsonl").read_text().splitlines()]
    assert len(events) == 2 and {e["opportunity_id"] for e in events} == {old.opportunity_id}
    sources = json.loads((target / "sources.json").read_text())["resources"]
    assert {r["url"] for r in sources} == {"https://example.org/grant", "https://example.org/new-round"}
    before = files(store.root)
    store.sync([updated])
    assert files(store.root) == before


def test_duplicate_id_and_slug_collision_rejected_before_writes(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant())
    with pytest.raises(ValueError, match="Duplicate"):
        store.sync([record(), record()])
    with pytest.raises(ValueError, match="collision"):
        store.sync([record(), record(opportunity_id="other")])
    assert not store.root.exists()


def test_new_id_cannot_duplicate_same_program_after_deadline_change(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant())
    store.sync([record()])
    before = files(store.root)
    with pytest.raises(ValueError, match="collision"):
        store.sync([verified(opportunity_id="different-id")])
    assert files(store.root) == before


def test_generated_links_exist_and_archived_not_counted_as_active(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant(facts={"entity": "unincorporated"}))
    index = store.sync([verified(), record(opportunity_id="archived", program="Old Program", archived=True)])
    assert index["active_count"] == 1 and index["archived_count"] == 1
    for row in index["opportunities"]:
        assert (store.root / row["overview"]).is_file()
        assert (store.root / row["record"]).is_file()
    for page in store.root.rglob("*.md"):
        for link in re.findall(r"\]\(([^)]+)\)", page.read_text()):
            if not link.startswith("https:"):
                assert (page.parent / unquote(link)).is_file(), (page, link)
    store.sync([])  # Omitted opportunities persist, including archived history.
    assert len(list(store.root.glob("opportunities/*/opportunity.json"))) == 2


@pytest.mark.parametrize("change", [
    {"application_status": "OPEN"}, {"deadline_kind": "rolling"},
    {"deadline": "2027-03-15"}, {"eligibility_complete": True},
    {"claims": {"funding": {"value": "EUR 1 million", "evidence_ids": ["missing"]}}},
    {"official_domains": ["evil.example"]},
])
def test_material_assertions_require_official_evidence(change):
    with pytest.raises((ValueError, ValidationError)):
        record(**change)


def test_hard_filters_unknown_milestone_ineligible_and_stale():
    r = verified()
    assert assess(r, Applicant())["status"] == "ELIGIBILITY_UNKNOWN"
    assert assess(r, Applicant(facts={"entity": "unincorporated"}))["status"] == "ELIGIBLE_NOW"
    assert assess(r, Applicant(facts={"entity": "company"}))["status"] == "VERIFIED_INELIGIBLE"
    payload = r.model_dump(mode="json")
    payload["conditions"][0]["milestone"] = "Complete incorporation review"
    r = Opportunity.model_validate(payload)
    assert assess(r, Applicant(facts={"entity": "company"}))["status"] == "ELIGIBLE_AFTER_MILESTONE"
    r.checked_at = datetime(2027, 1, 1, tzinfo=UTC)
    assert assess(r, Applicant(facts={"entity": "unincorporated"}))["status"] == "ELIGIBILITY_UNKNOWN"
    r = verified(collection_error="HTTP_503")
    assert assess(r, Applicant(facts={"entity": "unincorporated"}))["status"] == "ELIGIBILITY_UNKNOWN"


@pytest.mark.parametrize("kind,token", [("rolling", "ROLLING"), ("discontinued", "CLOSED"), ("next_round_unknown", "NEXT-ROUND-UNKNOWN")])
def test_non_date_tokens_require_evidence(kind, token):
    r = record(deadline_kind=kind, claims={"deadline": {"value": token, "evidence_ids": ["rules"]}})
    assert folder_name(r).endswith("__" + token)


def test_blocked_collection_never_invents_status_or_funding():
    from src.research.programs.fetch import Page
    class Fetcher:
        async def fetch(self, url, at):
            return Page(url, url, at, error="HTTP_403")
    records = asyncio.run(collect_opportunities(sources=[{"opportunity_id": "test", "provider": "Test", "program": "Test", "official_domains": ["example.org"], "url": "https://example.org/"}], fetcher=Fetcher()))
    assert records[0].deadline_token == "UNKNOWN"
    assert records[0].application_status == "UNKNOWN"
    assert records[0].claims == {} and not records[0].resources[0].verified


def test_common_output_default_preserves_existing_archive(tmp_path):
    from src.research.output_storage import store_output
    class Archive:
        def write(self, report):
            return {"unchanged": report}
    assert store_output({"report": "existing"}, Archive()) == {"unchanged": {"report": "existing"}}
    with pytest.raises(ValueError):
        store_output({}, Archive(), mode="opportunity_folders")
    profiles = load_profiles()
    assert profiles["funding/de-eu"].output.storage == "opportunity_folders"
    assert profiles["world/global"].output.storage == "report"


def test_symlinks_cannot_escape_storage(tmp_path):
    root = tmp_path / "funding"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="Symlinks"):
        OpportunityFolderStorage(root, Applicant()).sync([record()])


def test_failed_transaction_leaves_old_tree_and_history_intact(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant())
    store.sync([record()])
    before = files(store.root)
    # Two input records with colliding canonical folder names cannot partially
    # rewrite a previously persisted entity.
    with pytest.raises(ValueError, match="collision"):
        store.sync([record(opportunity_id="other")])
    assert files(store.root) == before


def test_tampered_history_rejected_without_losing_files(tmp_path):
    store = OpportunityFolderStorage(tmp_path / "funding", Applicant())
    store.sync([record()])
    history = next(store.root.glob("opportunities/*/change-history.jsonl"))
    history.write_text(history.read_text().replace('"record_sha256": "', '"record_sha256": "tampered'))
    before = files(store.root)
    with pytest.raises(ValueError, match="checksum"):
        store.sync([record()])
    assert files(store.root) == before


def test_funding_agent_job_produces_existing_archive_and_folder_projection(tmp_path, monkeypatch):
    from src.research.service import ResearchService
    from src.research.funding import pipeline
    from src.research.reporting import Archive
    from src.research.publisher import validate
    async def collect(**kwargs):
        return [record()]
    monkeypatch.setattr(pipeline, "collect_opportunities", collect)
    async def run():
        service = ResearchService(tmp_path)
        request = {"profile_id": "funding/de-eu", "depth": 3, "idempotency_key": "funding-test"}
        job = await service.submit(request)
        await service.tasks[job["job_id"]]
        finished = service.get_job(job["job_id"])
        assert finished["status"] == "completed", finished
        assert (await service.submit(request))["job_id"] == job["job_id"]
        report = Archive(tmp_path).get(finished["report_id"])
        assert report["profile_id"] == "funding/de-eu"
        assert report["statistics"]["funding"]["opportunities"][0]["application_status"] == "UNKNOWN"
        assert (tmp_path / "research/funding-de-eu/index.json").exists()
        validate(tmp_path)
        with pytest.raises(ValueError, match="private questions"):
            await service.submit({"profile_id": "funding/de-eu", "question": "private founder details"})
    asyncio.run(run())


def test_available_official_page_does_not_infer_application_terms():
    from src.research.programs.fetch import Page
    class Fetcher:
        async def fetch(self, url, at):
            return Page(url, url, at, html="<h1>Official test grant</h1><p>Historical deadline 2025-01-01</p>")
    source = {"opportunity_id": "test", "provider": "Test", "program": "Test", "official_domains": ["example.org"], "url": "https://example.org/"}
    result = asyncio.run(collect_opportunities(sources=[source], fetcher=Fetcher()))[0]
    assert result.resources[0].verified
    assert result.claims == {} and result.application_status == "UNKNOWN"
    assert result.deadline_token == "UNKNOWN"


def test_unreviewed_redirect_does_not_supply_official_evidence():
    from src.research.programs.fetch import Page
    class Fetcher:
        async def fetch(self, url, at):
            return Page(url, "https://other.example/", at, html="<h1>Open grant</h1>")
    source = {"opportunity_id": "test", "provider": "Test", "program": "Test", "official_domains": ["example.org"], "url": "https://example.org/"}
    result = asyncio.run(collect_opportunities(sources=[source], fetcher=Fetcher()))[0]
    assert not result.resources[0].verified
    assert result.collection_error == "unreviewed_official_redirect"


def test_refresh_preserves_reviewed_terms_and_requires_review_after_page_change():
    from src.research.funding.models import merge_refresh
    old = verified()
    data = record().model_dump(mode="json")
    data["resources"][0]["content_sha256"] = "b" * 64
    changed = merge_refresh(old, Opportunity.model_validate(data))
    assert changed.deadline_token == "2027-03-15"
    assert changed.collection_error == "official_terms_need_reverification"
    assert len(changed.resources) == 2
    assert assess(changed, Applicant(facts={"entity": "unincorporated"}))["status"] == "ELIGIBILITY_UNKNOWN"
    assert merge_refresh(old, record()).collection_error is None


def test_funding_report_uses_existing_publisher_and_separate_git_consumer(tmp_path):
    from src.research.funding.pipeline import build_report
    from src.research.reporting import Archive
    from src.research.publisher import publish, validate
    from src.research.programs.fetch import Page
    import subprocess
    class Fetcher:
        async def fetch(self, url, at):
            return Page(url, url, at, html="<h1>Test-only funding page</h1>")
    report = asyncio.run(build_report(load_profiles()["funding/de-eu"], "a" * 32, fetcher=Fetcher()))
    archive = tmp_path / "archive"
    Archive(archive).write(report)
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    result = publish(archive, str(remote))  # Local test remote only; no external publication.
    assert result["publication_status"] == "published"
    consumer = tmp_path / "consumer"
    subprocess.run(["git", "clone", "--branch", "intel", str(remote), str(consumer)], check=True, capture_output=True)
    validate(consumer)
    assert Archive(consumer).get("a" * 32)["profile_id"] == "funding/de-eu"
    assert (consumer / "intel/latest/funding/de-eu.json").is_file()
