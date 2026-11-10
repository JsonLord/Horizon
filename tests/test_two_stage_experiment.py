"""Deterministic routing and safety checks for the held-out experiment."""
from datetime import UTC, datetime
import json

import pytest

from src.models import ContentItem, SourceType
from src.research.filtering.provider import COMMANDS, Decision
from src.research.live_review import Candidate, Evidence
from src.research.profiles import load_profiles
from src.research.two_stage_experiment import (
    ARM_REQUEST_CAP, deterministic_split, priority_score, protected,
    run_experiment, select_eight, treatment_route,
)


def row(i, *, domain='agent-control-planes', language='en', source='rss', title=None):
    title = title or f'Agent orchestration release {i} improves durable execution workflow'
    ev = Evidence(id=f'src-{i}', url=f'https://example.org/{i}', publisher=f'P{i}',
        title=title, excerpt=(title + ' describes a concrete implementation and public release details. ')*2,
        language=language, language_basis='source_metadata', discovery_language=language,
        published_at='2026-11-10T10:00:00Z', retrieved_at='2026-11-10T11:00:00Z',
        primary=source == 'github', fresh=True, source_type=source)
    return Candidate(id=f'candidate-{i}', event_id=f'event-{i}', title=title,
        url=ev.url, evidence=[ev])


class RecordingProvider:
    def __init__(self):
        self.requests = 0
        self.model = 'test-model'
        self.request_limit = None
        self.calls = []

    def identity(self):
        return 'same-test-identity'

    async def decide(self, command, payload):
        assert command in COMMANDS
        self.calls.append((payload['event_id'], command))
        self.requests += 1
        decision = Decision(score=.7, verdict='unknown' if command == 'same-story' else 'yes',
            reason='Test-only deterministic response.', evidence_ids=['src-' + payload['event_id'].split('-')[-1]],
            related_event_id=None, hype=.2, facts=.5, signal=.7)
        return decision, {'status': 'success', 'model': self.model, 'tokens': 40,
                          'input_tokens': 30, 'output_tokens': 10, 'latency_ms': 2}


def test_deterministic_split_balances_languages_and_source_types():
    rows = [row(i, language=('en', 'de', 'fr', 'unknown')[i % 4], source=('rss', 'github')[i % 2]) for i in range(8)]
    control, treatment = deterministic_split(rows, 'agent-control-planes', 'seed')
    control2, treatment2 = deterministic_split(rows, 'agent-control-planes', 'seed')
    assert [r.event_id for r in control] == [r.event_id for r in control2]
    assert [r.event_id for r in treatment] == [r.event_id for r in treatment2]
    assert len(control) == len(treatment) == 4
    for getter in (lambda r: r.evidence[0].language, lambda r: r.evidence[0].source_type):
        from collections import Counter
        a, b = Counter(map(getter, control)), Counter(map(getter, treatment))
        assert sum(abs(a[k] - b[k]) for k in set(a) | set(b)) <= 2


def test_two_stage_routes_priority_plus_seeded_exploration_without_overlap():
    rows = [row(i) for i in range(4)]
    routed, screened = treatment_route(rows, 'agent-control-planes', 'seed')
    assert len(routed) == 2 and len(screened) == 2
    assert {r.event_id for r in routed}.isdisjoint(r.event_id for r in screened)
    assert routed[0] == max(rows, key=lambda r: (priority_score(r, 'agent-control-planes'), r.event_id)) or priority_score(routed[0], 'agent-control-planes') == max(priority_score(r, 'agent-control-planes') for r in rows)
    routed_again, screened_again = treatment_route(rows, 'agent-control-planes', 'seed')
    assert [r.event_id for r in routed] == [r.event_id for r in routed_again]
    assert [r.event_id for r in screened] == [r.event_id for r in screened_again]


def test_world_long_tail_and_accessibility_are_protected():
    iran = row(1, domain='world-intelligence', title='Iran and US resume peace talks after regional ceasefire')
    cop = row(2, domain='world-intelligence', title='COP31 climate summit agenda and negotiations')
    other = [row(i, domain='world-intelligence', title=f'Other diplomatic development number {i}') for i in range(3, 5)]
    assert protected(iran, 'world-intelligence') and protected(cop, 'world-intelligence')
    routed, screened = treatment_route([iran, cop, *other], 'world-intelligence', 'seed')
    assert iran in routed and cop in routed
    assert iran not in screened and cop not in screened
    accessible = row(8, domain='aux', title='Barrierefreiheit and inclusive UX testing for AI-assisted usability')
    assert protected(accessible, 'aux')
    routed, screened = treatment_route([accessible, *[row(i, domain='aux', title=f'Generic AI launch update {i}') for i in range(3)]], 'aux', 'seed')
    assert accessible in routed and accessible not in screened


def test_selection_is_stable_and_balances_source_language():
    rows = [row(i, language=('en', 'de', 'fr', 'unknown')[i % 4], source=('rss', 'github')[i % 2]) for i in range(20)]
    selected = select_eight(rows, 'agent-control-planes', 'stable')
    again = select_eight(rows, 'agent-control-planes', 'stable')
    assert [r.event_id for r in selected] == [r.event_id for r in again]
    assert len({r.event_id for r in selected}) == 8
    assert len({r.evidence[0].language for r in selected}) == 4
    assert len({r.evidence[0].source_type for r in selected}) == 2


@pytest.mark.anyio
async def test_experiment_isolates_arms_and_never_calls_for_screenouts(tmp_path):
    instances = []
    def factory():
        instance = RecordingProvider()
        instances.append(instance)
        return instance
    async def acquisition(domain, profile):
        titles = [f'Agent orchestration workflow update {i} with concrete release details' for i in range(8)]
        return [row(i, title=titles[i]) for i in range(8)], [{'source': 'approved', 'status': 'ok'}], {}
    profiles = load_profiles()
    from src.research import two_stage_experiment as experiment
    original = experiment.policy_for
    def low_policy(profile):
        result = original(profile)
        assert result.max_tokens >= 120000
        return result
    experiment.policy_for = low_policy
    try:
        report = await run_experiment(tmp_path / '42', run_id='42', acquisition=acquisition,
            provider_factory=factory, excluded_event_ids=set())
    finally:
        experiment.policy_for = original
    assert len(instances) == 10
    assert len({id(provider) for provider in instances}) == 10
    assert report['domains']['agent-control-planes']['complete']
    result = report['domains']['agent-control-planes']
    control = result['arms']['control']
    treatment = result['arms']['treatment']
    assert control['expected_decisions'] == 24
    assert treatment['expected_decisions'] == 12
    assert control['actual_provider_requests'] == 24
    assert treatment['actual_provider_requests'] == 12
    assert control['cache_hits'] == treatment['cache_hits'] == 0
    assert len(result['screened_out_event_ids']) == 2
    calls = [event for provider in instances[:2] for event, _ in provider.calls]
    assert not (set(result['screened_out_event_ids']) & set(calls))
    assert all(len([c for c in provider.calls]) <= ARM_REQUEST_CAP for provider in instances)
    labels = json.loads((tmp_path / '42/review-labels.json').read_text())['labels']
    assert len(labels) == 40
    assert all(label['human_labels']['relevant'] is None for label in labels)
    assert (tmp_path / '42/REPORT.md').exists()
    assert (tmp_path / '42/experiment.json').exists()
    assert (tmp_path / '42/candidate-evidence.json').exists()
    assert json.loads((tmp_path / '42/experiment.json').read_text())['run_attempt'] == 1


@pytest.mark.anyio
async def test_incomplete_domain_excludes_prior_events_and_does_not_reuse(tmp_path):
    providers = []
    def factory():
        p = RecordingProvider(); providers.append(p); return p
    async def acquisition(domain, profile):
        return [row(i) for i in range(7)], [], {}
    report = await run_experiment(tmp_path / 'incomplete', run_id='incomplete', acquisition=acquisition,
        provider_factory=factory, excluded_event_ids={'event-0'})
    domain = report['domains']['agent-control-planes']
    assert not domain['complete']
    assert domain['collection']['selected_candidates'] == 6
    assert domain['status'] == 'INCOMPLETE_INSUFFICIENT_FRESH_UNSEEN_CANDIDATES'
    assert providers == []
    labels = json.loads((tmp_path / 'incomplete/review-labels.json').read_text())['labels']
    first_domain_labels = [x for x in labels if x['domain'] == 'agent-control-planes']
    assert len(first_domain_labels) == 6 and all(x['route_status'] == 'DOMAIN_INCOMPLETE' for x in first_domain_labels)


def test_existing_collector_source_type_is_preserved():
    now = datetime.now(UTC)
    item = ContentItem(id='x', title='A release title', content='A release contains sufficient descriptive content for review.',
        url='https://example.org/x', source_type=SourceType.RSS, published_at=now, metadata={'source_language': 'de'})
    from src.research.live_review import from_items
    candidates, invalid = from_items([item], [])
    assert invalid == 0
    assert candidates[0].evidence[0].source_type == 'rss'
    assert candidates[0].evidence[0].language == 'de'
