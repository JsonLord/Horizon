"""Bounded live-source review packs. No publication or generative inference."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import time
from typing import Literal

from bs4 import BeautifulSoup
from pydantic import Field, model_validator

from .analyzers import canonical, ident
from .collector import collect
from .filtering.engine import DurableCheckpointStore, FilterPolicy, AttentionRanking
from .filtering.provider import COMMANDS, Decision, DecisionModelProvider
from .profiles import ROOT, Strict, load_profiles, safe_url
from .radar.pipeline import collect_items, event_identity, language, reference, registry
from .reporting import atomic, dumps

DOMAINS = {
    'agent-control-planes': 'examples/radar-agent-control-planes',
    'distributed-training': 'examples/radar-distributed-training',
    'rag-memory': 'examples/radar-rag-memory',
    'aux': 'examples/ai-usability',
    'funding-de-eu': 'funding/de-eu',
    'world-intelligence': 'world/global',
    'incubators': 'programs/incubators',
}
QUESTIONS = {
    'agent-control-planes': 'Does the source document a durable-execution, orchestration, MCP or evaluation change? Inspect its API diff and failure-recovery tests before adopting it.',
    'distributed-training': 'Does the source supply hardware, model size, precision, baseline and workload for any measured efficiency claim? Reproduce those conditions before comparing performance.',
    'rag-memory': 'Does this change retrieval or memory behavior, or describe an existing technique? Inspect the implementation and compare retrieval quality on the same evaluation set.',
    'aux': 'Could this affect accessible AI-assisted usability testing or inclusive UX? Test with users and accessibility evidence; product-strategy implications are hypotheses, not market facts.',
    'funding-de-eu': 'Review current official application terms and applicant prerequisites. Semantic relevance cannot establish eligibility or an open application.',
    'world-intelligence': 'What changed in the underlying event? Locate the originating primary statement and compare prior coverage before interpreting consequences.',
    'incubators': 'Check the official current round, founder prerequisites, costs and equity terms. Strategic fit is separate from eligibility and application availability.',
}
VERSION = 'live-review-1.0'


def clean(value, limit=500):
    return ' '.join(BeautifulSoup(str(value or ''), 'html.parser').get_text(' ', strip=True).split())[:limit]


def md(value):
    return re.sub(r'([\\`*_[\]<>|])', r'\\\1', html.escape(str(value), quote=False)).replace('\n', ' ')


class Evidence(Strict):
    id: str
    url: str
    publisher: str
    title: str
    excerpt: str = Field(max_length=500)
    language: Literal['en', 'de', 'fr', 'unknown']
    language_basis: str
    discovery_language: str = 'unknown'
    published_at: str | None
    retrieved_at: str | None
    primary: bool = False
    fresh: bool = True
    content_hash: str | None = None
    source_type: str = 'unknown'
    @model_validator(mode='after')
    def valid(self):
        canonical(self.url)
        if any(c in self.url for c in '\r\n<>`\" '): raise ValueError('Unsafe report URL')
        for value in (self.published_at, self.retrieved_at):
            if value and datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('Evidence requires zoned timestamps')
        return self


class Candidate(Strict):
    id: str
    event_id: str
    title: str
    url: str | None = None
    evidence: list[Evidence] = Field(default_factory=list, max_length=20)
    matched_topics: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None
    eligibility: str | None = None
    application_status: str | None = None
    deadline: str | None = None
    historical_deadline: str | None = None
    historical_application_status: str | None = None
    missing_verification: list[str] = Field(default_factory=list)
    decisions: dict = Field(default_factory=dict)
    attention: float = Field(default=0, ge=0, le=1)
    classification: Literal['REVIEW', 'REJECTED', 'DUPLICATE', 'UNASSESSED', 'VERIFICATION_REQUIRED'] = 'UNASSESSED'
    reasons: list[str] = Field(default_factory=list)
    technical_significance: None = None
    confirmed: Literal[False] = False
    @model_validator(mode='after')
    def valid(self):
        if self.url:
            canonical(self.url)
            if any(c in self.url for c in '\r\n<>`\" '): raise ValueError('Unsafe report URL')
        if self.decisions and set(self.decisions) != set(COMMANDS):
            raise ValueError('All six command states required')
        for entry in self.decisions.values():
            if entry.get('decision'):
                d = Decision.model_validate(entry['decision'])
                if not set(d.evidence_ids) <= {e.id for e in self.evidence if e.fresh}:
                    raise ValueError('Unknown or stale review citation')
        if self.eligibility not in (None, 'ELIGIBLE_NOW', 'eligible') and self.classification == 'REVIEW':
            raise ValueError('Hard restrictions cannot be promoted')
        return self


class ReviewPack(Strict):
    schema_version: Literal['1.0'] = '1.0'
    review_version: Literal['live-review-1.0'] = VERSION
    domain: str
    profile_id: str
    physical_data_branch: str | None
    generated_at_utc: str
    window_hours: int = Field(ge=1, le=168)
    source_revision: str
    workflow_run_id: str | None
    policy: dict
    sources: list[dict]
    candidates: list[Candidate] = Field(max_length=200)
    statistics: dict
    cache_replay: dict
    limitations: list[str]
    acceptance: Literal['REVIEW_READY', 'PARTIAL', 'EMPTY']
    precision_at_10: None = None
    recall: None = None
    @model_validator(mode='after')
    def valid(self):
        if self.domain not in DOMAINS or self.profile_id != DOMAINS[self.domain]:
            raise ValueError('Unknown domain/profile')
        branch = 'radar/' + self.domain if self.domain in tuple(DOMAINS)[:3] else None
        if self.physical_data_branch != branch: raise ValueError('Domain is not a data branch')
        if len({c.id for c in self.candidates}) != len(self.candidates): raise ValueError('Duplicate candidate ID')
        if self.statistics['confirmed_findings'] != 0: raise ValueError('No independent factual verification in this review')
        return self


def policy_for(profile):
    policy = FilterPolicy.load(profile.profile_id)
    if policy: return policy
    # Incubator semantic review inherits the existing shared rubric; the original
    # founder-program policy remains the independent hard eligibility authority.
    from .programs.relevance import load_policy
    base = FilterPolicy.load('funding/de-eu').model_copy(deep=True)
    original = load_policy()
    base.profile_id = profile.profile_id
    base.topics = original.public_interests
    base.public_context = ['Public founder-program research; eligibility is assessed separately.']
    base.version = 'incubator-review-' + original.policy_version
    return base


def from_items(items, topics):
    result = []
    seen = {}
    invalid = 0
    for index, item in enumerate(items[:200]):
        try: ref = reference(item)
        except ValueError:
            invalid += 1
            continue
        key = canonical(ref.url)
        title_key = re.sub(r'\W+', ' ', ref.title.lower()).strip()
        descriptive_title = len(title_key.split()) >= 5
        duplicate = seen.get(key) or (seen.get('title:' + title_key) if descriptive_title else None)
        cid = ident(key + '|' + str(index))
        if not duplicate:
            seen[key] = cid
            seen['title:' + title_key] = cid
        ev = Evidence(id=ref.id, url=ref.url, title=ref.title, publisher=ref.publisher,
                      excerpt=ref.excerpt, language=ref.language, language_basis=ref.language_basis,
                      discovery_language=ref.discovery_language, published_at=None if item.source_type.value == 'gdelt' else ref.published_at_utc,
                      retrieved_at=ref.fetched_at_utc, primary=ref.primary, content_hash=ref.content_hash,
                      source_type=item.source_type.value)
        result.append(Candidate(id=cid, event_id=event_identity(key), title=ref.title, url=key,
                                evidence=[ev], duplicate_of=duplicate,
                                matched_topics=[t for t in topics if t.lower() in (ref.title + ' ' + ref.excerpt).lower()]))
    return result, invalid


async def acquire(domain, profile):
    """Reuse approved source registries and verification; no alternative model."""
    if domain in tuple(DOMAINS)[:3]:
        entry = next(e for e in registry()['radars'] if e['radar_id'] == domain)
        items, metrics = await collect_items(entry, profile)
        rows, invalid = from_items(items, profile.topics)
        return rows, metrics, {'retrieved_items': len(items), 'invalid_public_urls': invalid, 'not_in_review_inventory': max(0, len(items) - 200)}
    if domain not in ('funding-de-eu', 'incubators'):
        items, metrics = await collect(profile)
        rows, invalid = from_items(items, profile.topics)
        return rows, metrics, {'retrieved_items': len(items), 'invalid_public_urls': invalid, 'not_in_review_inventory': max(0, len(items) - 200)}
    if domain == 'funding-de-eu':
        from .funding.pipeline import build_report
        from .funding.models import Applicant, Opportunity, assess
        report = await build_report(profile, ident('live-review-funding') + '00000000')
        applicant = Applicant.model_validate_json((ROOT / 'config/funding-applicant.json').read_text())
        rows = []
        for raw in report['statistics']['funding']['opportunities']:
            r = Opportunity.model_validate(raw)
            evs = []
            for e in r.resources:
                if not e.verified or not e.quotation: continue
                lang, basis = language(e.quotation)
                evs.append(Evidence(id=ident(r.opportunity_id + '|' + e.resource_id), url=e.url,
                    title=e.title, publisher=r.provider, excerpt=e.quotation, language=lang,
                    language_basis=basis, published_at=None,
                    retrieved_at=e.retrieved_at.isoformat(), primary=True,
                    fresh=e.retrieved_at == r.checked_at, content_hash=e.content_sha256))
            assessment = assess(r, applicant)
            rows.append(Candidate(id=ident(r.opportunity_id), event_id=r.opportunity_id,
                title=r.program, url=r.resources[0].url if r.resources else None, evidence=evs,
                eligibility=assessment['status'], application_status='PAST_ROUND_CURRENT_AVAILABILITY_UNKNOWN' if r.deadline and r.deadline < r.checked_at.date() else 'UNKNOWN' if r.collection_error else r.application_status,
                historical_application_status=r.application_status if r.collection_error or r.deadline and r.deadline < r.checked_at.date() else None,
                historical_deadline=r.deadline_token if r.deadline and r.deadline < r.checked_at.date() else None,
                deadline=r.deadline_token, missing_verification=assessment['missing_prerequisites'] + [r.collection_error or 'Full current terms and applicant eligibility need primary review']))
        return rows, report['statistics']['collectors'], {'retrieved_items': len(rows)}
    from .programs.pipeline import build_report
    # Explicitly disable legacy inference/contract discovery. Only the shared
    # DecisionModelProvider below evaluates these public source candidates.
    report = await build_report(profile, ident('live-review-incubators') + '00000000', contract={})
    rows = []
    for r in report['statistics']['programs']['programs']:
        evs = []
        for e in r['source_evidence']:
            lang, basis = language(e['quotation'])
            evs.append(Evidence(id=e['evidence_id'], url=e['url'], title=r['name'], publisher=r['name'],
                excerpt=e['quotation'], language=lang, language_basis=basis,
                published_at=e['published_at'], retrieved_at=e['observed_at'], primary=e['primary'],
                fresh=r['extraction_status'] == 'verified_page' and not r['check_error'], content_hash=e['content_fingerprint']))
        rows.append(Candidate(id=ident(r['program_id']), event_id=r['program_id'], title=r['name'],
            url=r['canonical_url'] or r['original_url'], evidence=evs[:20],
            eligibility=r['fit']['hard_eligibility'], application_status=r['application_status'],
            deadline=r['deadline'], historical_deadline=(r.get('legacy') or {}).get('deadline'),
            missing_verification=list(dict.fromkeys(r['fit']['reason_codes'] + ([r['check_error']] if r['check_error'] else []))) or ['Founder eligibility requires independent review']))
    return rows, report['statistics']['collectors'], {'retrieved_items': len(rows), 'program_coverage': report['coverage']}


def payload_for(row, policy, previous):
    return {'summary': row.title[:500], 'event_id': row.event_id,
            'evidence': [{'id': e.id, 'snippet': e.excerpt[:250]} for e in row.evidence if e.fresh][:2],
            'topics': policy.topics[:15], 'research_assumptions_not_eligibility': policy.public_context,
            'previous': [{'event_id': p.event_id, 'summary': p.title[:250]} for p in previous[-2:]]}


def classify(row, policy):
    gates = row.decisions
    get = lambda cmd: (gates.get(cmd) or {}).get('decision')
    relevance, support, importance, novelty = (get(k) for k in ('relevance', 'claim-support', 'importance', 'same-story'))
    values = {'relevance': relevance['score'] if relevance else min(1, len(row.matched_topics) / 2),
              'importance': importance['score'] if importance else .5,
              'evidence': support['score'] if support else 0,
              'novelty': 0 if novelty and novelty['verdict'] == 'same' else .5 if not novelty or novelty['verdict'] == 'unknown' else 1,
              'actionability': get('worth-attention')['score'] if get('worth-attention') else .5}
    row.attention = AttentionRanking().score(values, policy)
    if row.duplicate_of or novelty and novelty['verdict'] == 'same':
        row.classification = 'DUPLICATE'; row.reasons = ['exact_url_or_title_duplicate' if row.duplicate_of else 'model_same_story_judgement']
    elif any(term.lower() in row.title.lower() for term in policy.exclusions):
        row.classification = 'REJECTED'; row.reasons = ['policy_exclusion']
    elif relevance and relevance['verdict'] == 'no' or support and support['verdict'] == 'no':
        row.classification = 'REJECTED'; row.reasons = ['model_relevance_no' if relevance and relevance['verdict'] == 'no' else 'model_claim_support_no']
    elif not any(e.fresh for e in row.evidence) or row.eligibility not in (None, 'ELIGIBLE_NOW', 'eligible'):
        row.classification = 'VERIFICATION_REQUIRED'; row.reasons = ['missing_fresh_evidence_or_hard_eligibility']
    elif all(get(cmd) for cmd in COMMANDS) and relevance['verdict'] == 'yes' and support['verdict'] == 'yes' and row.attention >= policy.threshold:
        row.classification = 'REVIEW'; row.reasons = ['provisional_domain_rubric_threshold_met_not_verified_truth']
    else:
        row.classification = 'UNASSESSED'; row.reasons = ['incomplete_uncertain_or_below_threshold_model_assessment']
    return Candidate.model_validate(row.model_dump())


async def decide_cached(provider, state, command, payload, policy, budget):
    key = hashlib.sha256(dumps([VERSION, provider.identity(), policy.model_dump(), command, payload]).encode()).hexdigest()
    entry = state.get('live-review-decision', key)
    if entry:
        return {**entry, 'cache_hit': True, 'charged_tokens': 0}
    if not payload['evidence']:
        return {'decision': None, 'provider': {'status': 'no_fresh_evidence', 'model': provider.model}, 'cache_hit': False, 'charged_tokens': 0}
    max_requests = policy.max_requests
    max_tokens = policy.max_tokens
    if budget['requests'] + 3 > max_requests or budget['tokens'] + 19500 > max_tokens:
        return {'decision': None, 'provider': {'status': 'budget_limit', 'model': provider.model}, 'cache_hit': False, 'charged_tokens': 0}
    price = policy.usd_per_million_tokens
    if policy.max_cost_usd is not None and (price is None or (budget['tokens'] + 19500) * price / 1000000 > policy.max_cost_usd):
        return {'decision': None, 'provider': {'status': 'cost_budget_limit', 'model': provider.model}, 'cache_hit': False, 'charged_tokens': 0}
    before = provider.requests
    value, metadata = await provider.decide(command, payload)
    used = provider.requests - before
    budget['requests'] += used
    tokens = metadata.get('tokens')
    budget['tokens'] += tokens + max(0, used - 1) * 19500 if tokens is not None else used * 19500
    budget['known_tokens'] += tokens or 0
    budget['unknown_usage_calls'] += used if tokens is None else max(0, used - 1)
    # No raw response, native routing, endpoint, credential or arbitrary model prose.
    fields = ('status', 'family', 'model', 'response_model', 'model_identity_verified', 'attempts', 'tokens', 'input_tokens', 'output_tokens', 'latency_ms', 'cost', 'error_code', 'format', 'abstained')
    entry = {'decision': value.model_dump() if value else None,
             'provider': {k: metadata[k] for k in fields if k in metadata},
             'cache_hit': False, 'charged_tokens': tokens}
    if value: state.put('live-review-decision', key, entry)
    return entry


def fair_order(rows):
    # Balance evidence families as well as languages. A long release queue must
    # not consume every unknown-language slot ahead of discovered technical news.
    queues = {}
    for row in rows:
        lang = row.evidence[0].language if row.evidence else 'unknown'
        primary = any(e.primary and e.fresh for e in row.evidence)
        queues.setdefault(lang, {True: [], False: []})[primary].append(row)
    for families in queues.values():
        for queue in families.values(): queue.sort(key=lambda r: len(r.matched_topics), reverse=True)
    turns = {lang: True for lang in queues}
    output = []
    while any(queue for families in queues.values() for queue in families.values()):
        for lang in ('en', 'de', 'fr', 'unknown'):
            if lang not in queues: continue
            primary = turns[lang]
            if not queues[lang][primary]: primary = not primary
            if queues[lang][primary]:
                output.append(queues[lang][primary].pop(0))
                turns[lang] = not primary
    return output


async def evaluate(domain, output, *, provider=None, acquisition=acquire):
    started = time.monotonic()
    profile = load_profiles()[DOMAINS[domain]].model_copy(deep=True)
    profile.lookback_hours = 168
    policy = policy_for(profile)
    provider = provider or DecisionModelProvider()
    state = DurableCheckpointStore(output / 'cache' / (domain + '.sqlite'))
    limitations = ['Model choices are uncalibrated editorial judgments, not verified facts.',
        'Short source excerpts may omit context; original publication dates can be unknown.',
        'Novelty compares this run only; no historical corpus was loaded.',
        'Technical significance is unassessed: native choices cannot generate technical-learning explanations or code.',
        'No human ground truth: precision@10 and recall remain null.',
        'The provider reports an alias, not a separately versioned model-weights revision.']
    rows, metrics, extra = [], [], {}
    try:
        async with asyncio.timeout(300):
            rows, metrics, extra = await acquisition(domain, profile)
    except Exception as exc:
        limitations.append('Collection failed or exceeded 300 seconds; no invented replacement findings.')
        metrics.append({'source': 'domain_collection', 'status': 'failed', 'error_code': type(exc).__name__})
    budget = {'requests': 0, 'tokens': 0, 'known_tokens': 0, 'unknown_usage_calls': 0}
    previous, replay_input = [], None
    try:
        async with asyncio.timeout(420):
            for row in fair_order(rows):
                payload = payload_for(row, policy, previous)
                row.decisions = {}
                for command in COMMANDS:
                    if row.duplicate_of:
                        row.decisions[command] = {'decision': None, 'provider': {'status': 'exact_duplicate_no_call', 'model': provider.model}, 'cache_hit': False, 'charged_tokens': 0}
                    else:
                        row.decisions[command] = await decide_cached(provider, state, command, payload, policy, budget)
                classify(row, policy)
                if replay_input is None and all(e['decision'] for e in row.decisions.values()): replay_input = payload
                if not row.duplicate_of: previous.append(row)
    except TimeoutError:
        limitations.append('Model evaluation exceeded 420 seconds; remaining candidates explicitly unassessed.')
    for row in rows:
        for command in COMMANDS:
            row.decisions.setdefault(command, {'decision': None, 'provider': {'status': 'evaluation_timeout', 'model': provider.model}, 'cache_hit': False, 'charged_tokens': 0})
        classify(row, policy)
    replay = {'performed': False, 'cache_hits': 0, 'provider_requests': 0, 'unchanged_content_avoids_calls': None}
    if replay_input:
        before = provider.requests
        entries = [await decide_cached(provider, state, c, replay_input, policy, budget) for c in COMMANDS]
        replay = {'performed': True, 'cache_hits': sum(e['cache_hit'] for e in entries), 'provider_requests': provider.requests - before,
                  'unchanged_content_avoids_calls': provider.requests == before and all(e['cache_hit'] for e in entries)}
    state.close()
    langs = Counter(e.language for r in rows for e in r.evidence if e.fresh)
    if domain in tuple(DOMAINS)[:3]:
        for lang in ('en', 'de', 'fr'):
            if not langs[lang]: limitations.append(f'No verified {lang} language evidence retrieved. Inspect approved native-language discovery query results; query locale is not source language. Primary research/laboratory/conference families remain pending source review in this radar registry.')
    if extra.get('not_in_review_inventory'):
        limitations.append(f"{extra['not_in_review_inventory']} retrieved items exceed the 200-item review inventory bound; no decisions are claimed for them.")
    failures = sum(m.get('status') not in ('ok', 'review_required') and m.get('source') != 'program_coverage' for m in metrics)
    if failures: limitations.append(f'{failures} source checks failed; inspect the per-source table. No restrictions were bypassed.')
    if any(e['provider']['status'] == 'budget_limit' for r in rows for e in r.decisions.values()): limitations.append('Model budget exhausted; remaining command states are explicitly budget_limit, not inferred decisions.')
    stats = {**extra, 'candidates': len(rows), 'duplicates': sum(r.classification == 'DUPLICATE' for r in rows),
        'rejected': sum(r.classification == 'REJECTED' for r in rows), 'review_worthy': sum(r.classification == 'REVIEW' for r in rows),
        'retained_for_review': sum(r.classification not in ('DUPLICATE', 'REJECTED') for r in rows),
        'confirmed_findings': 0, 'source_failures': failures, 'source_languages': dict(langs),
        'fresh_evidence_references': sum(e.fresh for r in rows for e in r.evidence),
        'historical_evidence_references': sum(not e.fresh for r in rows for e in r.evidence),
        'discovery_languages': dict(Counter(e.discovery_language for r in rows for e in r.evidence)),
        'model_requests': budget['requests'], 'known_tokens': budget['known_tokens'],
        'token_usage_complete': budget['unknown_usage_calls'] == 0, 'cost_usd': None,
        'cache_hits': sum(e['cache_hit'] for r in rows for e in r.decisions.values()),
        'runtime_seconds': round(time.monotonic() - started, 3)}
    pack = ReviewPack(domain=domain, profile_id=profile.profile_id,
        physical_data_branch='radar/' + domain if domain in tuple(DOMAINS)[:3] else None,
        generated_at_utc=datetime.now(UTC).isoformat(), window_hours=168,
        source_revision=os.getenv('GITHUB_SHA', 'local-development'), workflow_run_id=os.getenv('GITHUB_RUN_ID'),
        policy=policy.model_dump(), sources=metrics, candidates=rows, statistics=stats, cache_replay=replay,
        limitations=limitations, acceptance='EMPTY' if not rows else 'PARTIAL' if failures or not stats['model_requests'] or not stats['review_worthy'] else 'REVIEW_READY')
    folder = output / domain
    atomic(folder / 'findings.json', dumps(pack.model_dump(mode='json')))
    atomic(folder / 'REVIEW.md', render(pack))
    atomic(folder / 'review-labels.json', dumps(labels(pack)))
    return pack


def ranked(pack):
    return sorted(pack.candidates, key=lambda c: (c.classification == 'REVIEW', c.attention), reverse=True)


def labels(pack):
    rows = ranked(pack)
    # Include top, tail and uncertain/verification cases; no fabricated labels.
    selected = list(dict.fromkeys([r.id for r in rows[:8] + rows[-5:] + [r for r in rows if r.classification in ('UNASSESSED', 'VERIFICATION_REQUIRED')][:7]]))[:20]
    return {'schema_version': '1.0', 'domain': pack.domain, 'findings_sha256': hashlib.sha256(dumps(pack.model_dump(mode='json')).encode()).hexdigest(),
        'precision_at_10': None, 'recall': None, 'labels': [{'candidate_id': cid, 'relevant': None, 'important': None,
        'new_development': None, 'evidence_supported': None, 'correct_duplicate_classification': None,
        'preference': None, 'reviewer_notes': None, 'reviewed_at': None} for cid in selected]}


def render(pack):
    s = pack.statistics
    lines = [f'# Live review: {pack.domain}', '', f'Profile: `{pack.profile_id}`. Data branch: `{pack.physical_data_branch}`.' if pack.physical_data_branch else f'Profile: `{pack.profile_id}`; this is not a separate Git data branch.',
        f'Generated: {pack.generated_at_utc}. Window: previous 7 days for news; current official refresh for opportunities. Status: **{pack.acceptance}**.',
        '', '## A. Collection overview', '', '| Metric | Observed |', '| --- | --- |']
    for key, value in s.items(): lines.append(f'| {key} | {md(json.dumps(value, ensure_ascii=False))} |')
    lines += ['', 'Cache replay: `' + json.dumps(pack.cache_replay) + '`.', '', '| Source / query | Status | Items | Error |', '| --- | --- | --- | --- |']
    for source in pack.sources:
        lines.append(f"| {md(source.get('source', 'unknown'))} / {md(source.get('query', source.get('url', '')))} | {md(source.get('status', 'unknown'))} | {source.get('items', 'unknown')} | {md(source.get('error_code') or '')} |")
    lines += ['', '## B. Top candidates (up to 10)', '', 'Ranked within this domain only. Source statements, model judgments and editorial investigation questions are distinct. No independently confirmed technical facts are claimed.']
    top = [r for r in ranked(pack) if r.classification == 'REVIEW' or pack.domain in ('funding-de-eu', 'incubators') and r.classification == 'VERIFICATION_REQUIRED'][:10]
    if not top: lines += ['', 'No model-qualified review candidates; inspect unassessed candidates and coverage limitations rather than inventing a top ten.']
    for row in top:
        lines += ['', f'### {md(row.title)}', '', f'[Original source](<{row.url}>)' if row.url else 'No verified source URL available.',
            f'Classification: **{row.classification}**. Provisional domain attention: {row.attention}. Technical significance: **unassessed**.',
            f'Matched topics: {md(", ".join(row.matched_topics) or "none matched lexically; inspect semantic judgments")}.']
        for e in row.evidence[:2]:
            lines += [f'Language: {e.language} ({e.language_basis}); discovery locale: {e.discovery_language}. Publication: {e.published_at or "unknown"}; retrieved: {e.retrieved_at or "unknown"}; fresh: {e.fresh}.',
                f'Source-attributed statement from {md(e.publisher)}: “{md(e.excerpt)}”. This excerpt records what the source says; it does not independently establish the claim or its implications.']
        lines += [f'**Editorial investigation / potential implications:** {QUESTIONS[pack.domain]}',
            '**Model judgments:** ' + '; '.join(f"{cmd}: {(entry.get('decision') or {}).get('verdict', 'unassessed')} / score {(entry.get('decision') or {}).get('score', 'null')} ({entry['provider']['status']}; {'cache' if entry['cache_hit'] else 'live' if entry['provider'].get('attempts') else 'no call'})" for cmd, entry in row.decisions.items()),
            'Reason: ' + md('; '.join(row.reasons) or 'not evaluated'),
            'Unresolved: ' + md('; '.join(row.missing_verification) or 'Full original context and independent corroboration have not been verified.'),
            'Next investigation: open the cited original, compare primary evidence and label this candidate in review-labels.json.']
        if row.eligibility is not None:
            lines += [f'Hard eligibility: **{md(row.eligibility)}**; application: {md(row.application_status)}; deadline: {md(row.deadline or "unknown")}; historical deadline: {md(row.historical_deadline or "none recorded")}. Historical dates never establish a currently open round.']
    lines += ['', '## C. Rejected, duplicate or deprioritized examples (up to 5)', '']
    suppressed = [r for r in ranked(pack) if r.classification in ('REJECTED', 'DUPLICATE')][:5]
    suppressed += [r for r in reversed(ranked(pack)) if r.classification == 'UNASSESSED'][:5-len(suppressed)]
    if not suppressed: lines.append('No observed rejected/duplicate examples; do not invent five examples. See low-ranked unassessed candidates in findings.json.')
    for row in suppressed: lines += [f'- [{md(row.title)}](<{row.url}>) — {row.classification}: {md("; ".join(row.reasons))}; duplicate target: {row.duplicate_of or "none established; inspect command states"}. Unassessed means deprioritized/uncertain, not a model rejection.']
    lines += ['', '## D. Missing discoveries and coverage limitations', ''] + ['- ' + md(x) for x in pack.limitations]
    lines += ['', '**Source improvements:** Inspect failed approved sources first. Review primary papers, release-note feeds and benchmark/laboratory sources before adding their verified URLs to the source registry. German/French query hits alone do not establish language coverage.',
        '**Policy improvements:** Label low-ranked and ambiguous cases before changing thresholds. Compare the approved topic list against actual false positives; no precision/recall claim is available without reviewed labels.',
        '', 'Detailed per-command identity, policy, usage, cache and citation records: [findings.json](findings.json). Feedback template: [review-labels.json](review-labels.json). Feedback is separate from source evidence and cannot change hard eligibility.', '']
    return '\n'.join(lines)


def portfolio(packs):
    lines = ['# Horizon live research portfolio', '', 'Real public-source collection; read-only review, not production publication.', '',
        '| Domain | Candidates | Review worthy | Confirmed | Duplicates | Source failures | Languages | Model requests | Runtime s | Main limitation | Status |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for p in packs:
        s = p.statistics
        limitation = 'Eligibility/current round unverified' if p.domain in ('funding-de-eu', 'incubators') else 'Short evidence; ' + str(sum(r.classification == 'UNASSESSED' for r in p.candidates)) + ' unassessed candidates'
        lines.append(f"| [{p.domain}]({p.domain}/REVIEW.md) | {s['candidates']} | {s['review_worthy']} | 0 | {s['duplicates']} | {s['source_failures']} | {md(json.dumps(s['source_languages']))} | {s['model_requests']} | {s['runtime_seconds']} | {limitation} | {p.acceptance} |")
    lines += ['', '## Five discoveries to inspect', '', 'A diverse editorial selection, not a universal ranking: each domain uses its own rubric. Technical significance is unassessed.']
    queues = [(p, [r for r in ranked(p) if r.classification == 'REVIEW']) for p in packs]
    chosen = []
    while len(chosen) < 5 and any(rows for _, rows in queues):
        for p, rows in queues:
            if rows and len(chosen) < 5: chosen.append((p, rows.pop(0)))
    for p, r in chosen: lines += [f'- [{md(r.title)}](<{r.url}>) — {p.domain}; inspect [domain review]({p.domain}/REVIEW.md). Source-attributed candidate, not independently confirmed.']
    lines += ['', '## Five likely false positives / uncertain selections', '']
    uncertain = [(p, r) for p in packs for r in ranked(p) if r.classification == 'REJECTED']
    uncertain += [(p, r) for p in packs for r in ranked(p) if r.classification == 'UNASSESSED' and re.search(r'\b(form 4|idex|fiscal|holyrood)\b', r.title, re.I)]
    for p, r in uncertain[:5]: lines += [f'- [{md(r.title)}](<{r.url}>) — {p.domain}: {md("; ".join(r.reasons))}. This is an inspection hypothesis, not a fabricated reviewer label.']
    lines += ['', '## Five important research gaps', '', '- Primary papers, laboratories, conferences and benchmark registries remain incomplete.',
        '- Actual German/French evidence is sparse or language-uncertain; inspect each radar language table.',
        '- Short discovery excerpts do not establish mechanisms or measured benchmark context.',
        '- Unknown founder eligibility and current round terms require official evidence and reviewed applicant facts.',
        '- Bounded inference leaves some candidates unassessed; no historical corpus or reviewed ground truth was loaded.',
        '', '## Recommendations and acceptance', '', 'Repair evidenced failed sources, review native-language primary registries, and obtain full evidence before adopting technical claims. Use the separate review-labels.json files to assess over-aggressive filtering before adjusting thresholds. Precision@10 and recall remain null.',
        '', 'Acceptance is domain-specific: REVIEW_READY means candidates are available for human review, not confirmed factual correctness. PARTIAL/EMPTY preserves observed limitations. No weekly digest or research data branch was published.', '']
    return '\n'.join(lines)


def export_notices(output):
    """Seven bounded summaries; full reports stay in the uploaded artifact."""
    allowed = ['INDEX.md', 'review.schema.json'] + [f'{d}/{name}' for d in DOMAINS for name in ('findings.json', 'REVIEW.md', 'review-labels.json')]
    for relative in allowed:
        path = output / relative
        if not path.is_file(): continue
        raw = path.read_bytes()
        for name in ('HORIZON_DECISION_API_KEY', 'HORIZON_DECISION_BASE_URL', 'HORIZON_DECISION_CHAT_URL'):
            value = os.getenv(name, '')
            if value and value.encode() in raw: raise ValueError('Sensitive configured value in review output')
        if len(raw) > 1_000_000: raise ValueError('Review output size ceiling')
        if os.getenv('GITHUB_STEP_SUMMARY') and path.name in ('INDEX.md', 'REVIEW.md'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f: f.write(raw.decode()[:60000] + '\n')
    for domain in DOMAINS:
        path = output / domain / 'findings.json'
        if not path.is_file(): continue
        pack = ReviewPack.model_validate_json(path.read_text())
        proof = {'domain': domain, 'statistics': pack.statistics, 'cache_replay': pack.cache_replay,
                 'acceptance': pack.acceptance, 'source_revision': pack.source_revision, 'run_id': pack.workflow_run_id}
        raw = json.dumps(proof)
        if len(raw.encode()) > 3800: raise ValueError('Summary size ceiling')
        print('::notice title=live-review-summary::' + raw.replace('%', '%25'))
