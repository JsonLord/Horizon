"""Review safety, honest unknowns, real cache identity and publication isolation."""
import json
from pathlib import Path
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.research.live_review import (Candidate, Evidence, ReviewPack, classify, decide_cached,
    evaluate, export_notices, from_items, labels, policy_for, DOMAINS)
from src.research.profiles import load_profiles
from src.research.filtering.engine import DurableCheckpointStore
from src.research.filtering.provider import Decision, COMMANDS
from src.models import ContentItem, SourceType


@pytest.fixture
def anyio_backend(): return "asyncio"

def candidate(**kw):
    e = Evidence(id='source-1', url='https://example.org/release', title='Accessible tool release',
        publisher='Example', excerpt='The tool supports accessible navigation and testing.', language='en',
        language_basis='source_metadata', published_at='2026-11-08T12:00:00Z', retrieved_at='2026-11-09T00:00:00Z')
    return Candidate(id='one', event_id='event-1', title=e.title, url=e.url, evidence=[e], **kw)


class Provider:
    requests = 0
    model = 'test-backend'
    def identity(self): return 'public-test-provider'
    async def decide(self, command, payload):
        self.requests += 1
        verdict = 'unknown' if command == 'same-story' else 'yes'
        value = Decision(score=.9, verdict=verdict, reason='Public excerpt classification',
            evidence_ids=[payload['evidence'][0]['id']], related_event_id=None, hype=.5, facts=.5, signal=.5)
        return value, {'model': self.model, 'status': 'success', 'tokens': 10, 'latency_ms': 1, 'attempts': 1}


def policy(): return policy_for(load_profiles()['examples/ai-usability'])


@pytest.mark.anyio
async def test_actual_decisions_cache_replay_and_unlabelled_feedback(tmp_path):
    async def acquisition(domain, profile):
        assert profile.lookback_hours == 168
        return [candidate()], [{'source': 'approved', 'status': 'ok', 'items': 1}], {'retrieved_items': 1}
    p = Provider()
    result = await evaluate('aux', tmp_path, provider=p, acquisition=acquisition)
    assert result.statistics['model_requests'] == 6
    assert result.cache_replay['cache_hits'] == 6
    assert result.cache_replay['provider_requests'] == 0
    assert result.cache_replay['unchanged_content_avoids_calls']
    assert p.requests == 6
    assert result.candidates[0].classification == 'REVIEW'
    assert result.candidates[0].technical_significance is None
    assert result.statistics['confirmed_findings'] == 0
    assert result.precision_at_10 is None and result.recall is None
    assert labels(result)['labels'][0]['relevant'] is None
    assert (tmp_path / 'aux/REVIEW.md').exists()
    ReviewPack.model_validate_json((tmp_path / 'aux/findings.json').read_text())


@pytest.mark.parametrize('hard', ['ELIGIBILITY_UNKNOWN', 'review_required', 'ineligible', 'FUTURE_OPPORTUNITY'])
def test_semantics_never_promote_unknown_founder_or_funding_eligibility(hard):
    row = candidate(eligibility=hard)
    for command in COMMANDS:
        row.decisions[command] = {'decision': {'score': .9, 'verdict': 'yes', 'reason': '', 'evidence_ids': ['source-1'], 'related_event_id': None, 'hype': .5, 'facts': .5, 'signal': .5}, 'provider': {'status': 'success'}}
    assert classify(row, policy()).classification == 'VERIFICATION_REQUIRED'


def test_unknown_citation_and_fake_confirmation_fail_validation():
    row = candidate()
    with pytest.raises(ValidationError): Candidate.model_validate({**row.model_dump(), 'confirmed': True})
    with pytest.raises(ValidationError): Candidate.model_validate({**row.model_dump(), 'technical_significance': 9})
    bad = {'decision': {'score': .9, 'verdict': 'yes', 'reason': '', 'evidence_ids': ['fabricated'], 'related_event_id': None, 'hype': .5, 'facts': .5, 'signal': .5}}
    with pytest.raises(ValidationError): Candidate.model_validate({**row.model_dump(), 'decisions': {c: bad for c in COMMANDS}})


@pytest.mark.anyio
async def test_budget_does_not_make_additional_calls_or_cache_failures(tmp_path):
    state = DurableCheckpointStore(tmp_path / 'cache.sqlite')
    p = Provider(); pol = policy(); pol.max_requests = 2
    budget = {'requests': 0, 'tokens': 0, 'known_tokens': 0, 'unknown_usage_calls': 0}
    payload = {'summary': 'test', 'evidence': [{'id': 'source-1', 'snippet': 'test'}]}
    entry = await decide_cached(p, state, 'relevance', payload, pol, budget)
    assert entry['provider']['status'] == 'budget_limit' and p.requests == 0
    state.close()


def test_duplicate_and_language_provenance_not_query_locale():
    now = datetime.now(UTC)
    item = ContentItem(id='one', title='FSDP update', content='FSDP update', url='https://example.org/release',
        source_type=SourceType.RSS, published_at=now, metadata={'query_language': 'de'})
    rows, invalid = from_items([item, item], [])
    assert invalid == 0 and rows[1].duplicate_of == rows[0].id
    assert rows[0].evidence[0].language == 'unknown'
    assert rows[0].evidence[0].discovery_language == 'de'


@pytest.mark.anyio
async def test_empty_collection_is_reported_no_fabricated_findings(tmp_path):
    async def unavailable(*args): raise TimeoutError()
    pack = await evaluate('distributed-training', tmp_path, provider=Provider(), acquisition=unavailable)
    assert pack.acceptance == 'EMPTY' and not pack.candidates
    assert pack.statistics['model_requests'] == 0
    assert any('No verified fr' in x for x in pack.limitations)
    assert not pack.cache_replay['performed']


def test_public_handoff_rejects_provider_secret(tmp_path, monkeypatch):
    (tmp_path / 'INDEX.md').write_text('accidentally included private-test-key')
    monkeypatch.setenv('HORIZON_DECISION_API_KEY', 'private-test-key')
    with pytest.raises(ValueError, match='Sensitive'): export_notices(tmp_path)


def test_only_three_domains_are_git_data_branches():
    assert len(DOMAINS) == 7
    for profile in load_profiles().values():
        if profile.profile_id in DOMAINS.values(): assert profile.lookback_hours <= 168

@pytest.mark.anyio
async def test_real_funding_adapter_keeps_unknown_eligibility(monkeypatch):
    from src.research.live_review import acquire
    from src.research.programs.fetch import ProgramFetcher, Page
    async def fetch(self, url, observed_at):
        return Page(url, url, observed_at, '<html><h1>Official funding program</h1></html>')
    monkeypatch.setattr(ProgramFetcher, 'fetch', fetch)
    rows, metrics, extra = await acquire('funding-de-eu', load_profiles()['funding/de-eu'])
    assert len(rows) == 3 and len(metrics) == 3
    assert all(row.eligibility in ('ELIGIBILITY_UNKNOWN', 'WATCH_FUTURE_ROUND') for row in rows)
    assert all(row.application_status != 'OPEN' for row in rows)


@pytest.mark.anyio
async def test_real_program_adapter_no_native_legacy_calls(monkeypatch):
    from src.research.live_review import acquire
    from src.research.programs.fetch import ProgramFetcher, Page
    import src.research.programs.pipeline as pipeline
    async def fetch(self, url, observed_at):
        return Page(url, url, observed_at, '<html><h1>Official founder program</h1></html>')
    async def nominate(*args): return [], [{'source': 'public_discovery', 'status': 'ok', 'items': 0}]
    async def forbidden(*args): raise AssertionError('Legacy endpoint must not be contacted')
    monkeypatch.setattr(ProgramFetcher, 'fetch', fetch)
    monkeypatch.setattr(pipeline, 'nominate', nominate)
    monkeypatch.setattr(pipeline, 'inspect_contract', forbidden)
    rows, metrics, extra = await acquire('incubators', load_profiles()['programs/incubators'])
    assert rows and metrics
    assert all(row.eligibility == 'review_required' for row in rows)

@pytest.mark.anyio
async def test_public_handoff_roundtrip_validates_all_seven_domains(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    from scripts.review_bundle import validate
    from src.research.live_review import portfolio
    from src.research.reporting import atomic, dumps
    async def acquisition(*args):
        return [candidate()], [{'source': 'approved', 'status': 'ok'}], {'retrieved_items': 1}
    packs = [await evaluate(d, tmp_path, provider=Provider(), acquisition=acquisition) for d in DOMAINS]
    atomic(tmp_path / 'INDEX.md', portfolio(packs))
    atomic(tmp_path / 'review.schema.json', dumps(ReviewPack.model_json_schema()))
    export_notices(tmp_path)
    output = capsys.readouterr().out.splitlines()
    assert len(output) == 7 and all(len(line.encode()) < 4000 for line in output)
    files = validate(tmp_path, packs[0].source_revision, packs[0].workflow_run_id)
    assert len(files) == 23
    assert files['aux/findings.json'] == (tmp_path / 'aux/findings.json').read_bytes()
    (tmp_path / 'aux/review-labels.json').write_text('{}')
    with pytest.raises((ValueError, KeyError)): validate(tmp_path, 'local-development', None)


@pytest.mark.anyio
async def test_cache_changes_when_evidence_or_context_changes(tmp_path):
    p = Provider(); state = DurableCheckpointStore(tmp_path / 'cache.sqlite')
    budget = {'requests': 0, 'tokens': 0, 'known_tokens': 0, 'unknown_usage_calls': 0}
    payload = {'summary': 'old', 'evidence': [{'id': 'source-1', 'snippet': 'old'}]}
    first = await decide_cached(p, state, 'relevance', payload, policy(), budget)
    same = await decide_cached(p, state, 'relevance', payload, policy(), budget)
    assert not first['cache_hit'] and same['cache_hit'] and p.requests == 1
    changed = await decide_cached(p, state, 'relevance', {**payload, 'previous': [{'event_id': 'other', 'summary': 'different event'}]}, policy(), budget)
    assert not changed['cache_hit'] and p.requests == 2
    state.close()


def test_review_publisher_refuses_nonqualification_context(tmp_path, monkeypatch):
    from scripts.review_bundle import publish
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_dispatch')
    for ref in ('refs/heads/main', 'refs/heads/radar/rag-memory', 'refs/heads/intel'):
        monkeypatch.setenv('GITHUB_REF', ref)
        with pytest.raises(ValueError, match='qualification'): publish(tmp_path, None)


@pytest.mark.anyio
async def test_review_publisher_changes_only_approved_pr_report_paths(tmp_path, monkeypatch):
    from scripts.review_bundle import publish, seal, TARGET
    from src.research.live_review import portfolio
    from src.research.reporting import atomic, dumps
    async def acquisition(*args): return [candidate()], [{'source': 'approved', 'status': 'ok'}], {'retrieved_items': 1}
    monkeypatch.setenv('GITHUB_SHA', 'source-sha')
    monkeypatch.setenv('GITHUB_RUN_ID', '42')
    packs = [await evaluate(d, tmp_path, provider=Provider(), acquisition=acquisition) for d in DOMAINS]
    atomic(tmp_path / 'INDEX.md', portfolio(packs))
    atomic(tmp_path / 'review.schema.json', dumps(ReviewPack.model_json_schema()))
    class API:
        calls = []
        def api(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            if path == 'actions/runs/42': return {'head_sha': 'source-sha', 'head_branch': 'qualification/live-review-test', 'conclusion': 'success', 'html_url': 'https://github.com/JsonLord/Horizon/actions/runs/42'}
            if method == 'GET' and path.startswith('git/ref/'): return {'object': {'sha': 'old'}}
            if method == 'GET' and path.startswith('git/commits/'): return {'tree': {'sha': 'old-tree'}}
            return {'sha': 'new'}
    api = API()
    seal(tmp_path, 'source-sha', '42', api)
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_dispatch')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/qualification/live-review-test')
    publish(tmp_path, api)
    tree = next(kwargs['json'] for method, path, kwargs in api.calls if method == 'POST' and path == 'git/trees')
    assert len(tree['tree']) == 24
    assert all(entry['path'].startswith('data/live-review/') and entry['mode'] == '100644' for entry in tree['tree'])
    patch = [(path, kwargs['json']) for method, path, kwargs in api.calls if method == 'PATCH']
    assert patch == [('git/refs/heads/' + TARGET, {'sha': 'new', 'force': False})]


def test_generic_release_titles_do_not_collapse_different_repositories():
    now = datetime.now(UTC)
    items = [ContentItem(id=str(i), title='v1.0.0', url='https://github.com/org/' + repo + '/releases/tag/v1.0.0',
        source_type=SourceType.GITHUB, published_at=now, content='A new public release.') for i, repo in enumerate(('first', 'second'))]
    rows, _ = from_items(items, [])
    assert all(row.duplicate_of is None for row in rows)


def test_budget_selection_prefers_primary_evidence_within_each_language():
    from src.research.live_review import fair_order
    secondary = candidate(); secondary.evidence[0].language = 'unknown'
    primary = candidate(); primary.id = 'primary'; primary.evidence[0].language = 'unknown'; primary.evidence[0].primary = True
    assert fair_order([secondary, primary])[0].id == 'primary'


def test_sampling_does_not_starve_discovery_when_many_releases_exist():
    from src.research.live_review import fair_order
    rows = []
    for cid, primary in [('p1', True), ('p2', True), ('p3', True), ('s1', False), ('s2', False)]:
        row = candidate(); row.id = cid; row.evidence[0].language = 'unknown'; row.evidence[0].primary = primary; rows.append(row)
    assert [row.id for row in fair_order(rows)] == ['p1', 's1', 'p2', 's2', 'p3']
