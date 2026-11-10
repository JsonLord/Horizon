"""Held-out, bounded comparison of full and two-stage semantic review."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

from .filtering.engine import DurableCheckpointStore
from .filtering.provider import COMMANDS, DecisionModelProvider
from .live_review import DOMAINS, acquire, payload_for, policy_for
from .profiles import ROOT, load_profiles
from .reporting import atomic, dumps

EXPERIMENT_DOMAINS = (
    'agent-control-planes', 'distributed-training', 'rag-memory', 'aux', 'world-intelligence'
)
VERSION = 'two-stage-heldout-1.0'
ARM_REQUEST_CAP = 27
EXPECTED_CANDIDATES = 8

# Matched phrases are intentionally multilingual and domain-specific. These are
# prioritization cues only; they never establish factual truth or eligibility.
DOMAIN_TERMS = {
    'agent-control-planes': {
        'en': ('agent', 'orchestration', 'control plane', 'mcp', 'workflow', 'durable execution', 'evaluation'),
        'de': ('agent', 'orchestrierung', 'steuerung', 'ablauf', 'auswertung'),
        'fr': ('agent', 'orchestration', 'contrôle', 'flux', 'évaluation'),
    },
    'distributed-training': {
        'en': ('distributed', 'training', 'gpu', 'cuda', 'parallel', 'throughput', 'memory'),
        'de': ('verteilt', 'training', 'gpu', 'parallel', 'durchsatz', 'speicher'),
        'fr': ('distribué', 'entraînement', 'gpu', 'parallèle', 'débit', 'mémoire'),
    },
    'rag-memory': {
        'en': ('retrieval', 'rag', 'memory', 'vector', 'citation', 'grounding', 'search'),
        'de': ('suche', 'retrieval', 'speicher', 'vektor', 'zitat', 'beleg'),
        'fr': ('recherche', 'mémoire', 'vecteur', 'citation', 'preuve', 'récupération'),
    },
    'aux': {
        'en': ('accessibility', 'accessible', 'inclusive ux', 'inclusive design', 'usability', 'assistive'),
        'de': ('barrierefreiheit', 'zugänglich', 'inklusive ux', 'inklusiv', 'usability', 'assistiv'),
        'fr': ('accessibilité', 'accessible', 'ux inclusive', 'conception inclusive', 'utilisabilité', 'assistive'),
    },
    'world-intelligence': {
        'en': ('iran', 'united states', 'us', 'peace talks', 'ceasefire', 'cop31', 'climate summit', 'election', 'sanction'),
        'de': ('iran', 'vereinigte staaten', 'usa', 'friedensgespräche', 'waffenstillstand', 'cop31', 'klimagipfel', 'wahl', 'sanktion'),
        'fr': ('iran', 'états-unis', 'usa', 'pourparlers de paix', 'cessez-le-feu', 'cop31', 'sommet climatique', 'élection', 'sanction'),
    },
}
LONG_TAIL = {
    'world-intelligence': (
        'iran-us peace talks', 'iran–us peace talks', 'iran us peace talks',
        'iran-usa friedensgespräche', 'pourparlers de paix iran', 'cop31', 'cop 31', 'cop-31',
    ),
}
AUX_TERMS = ('accessibility', 'accessible', 'inclusive ux', 'inclusive design', 'barrierefreiheit', 'zugänglich', 'accessibilité', 'ux inclusive')


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def load_nov9_event_ids(root: Path = ROOT) -> set[str]:
    """Read event IDs from committed live-review runs generated on Nov 9."""
    excluded: set[str] = set()
    for path in sorted((root / 'data/live-review').glob('*/findings.json')):
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        generated = report.get('generated_at_utc', '')
        if not generated.startswith('2026-11-09'):
            continue
        for candidate in report.get('candidates', []):
            # Keep both stable event identity and report-local candidate ID. The
            # latter closes any same-run reordering gap in held-out comparisons.
            excluded.update(candidate.get(field) for field in ('event_id', 'id') if candidate.get(field))
    triage_path = root / 'data/quality-calibration/2026-11-09/triage-labels.json'
    try:
        triage = json.loads(triage_path.read_text(encoding='utf-8'))
        excluded.update(row['id'] for row in triage.get('rows', []) if row.get('id'))
    except (OSError, json.JSONDecodeError):
        pass
    return excluded


def _text(row) -> str:
    return ' '.join([row.title, *(e.title + ' ' + e.excerpt for e in row.evidence)]).casefold()


def source_type(row) -> str:
    return row.evidence[0].source_type if row.evidence and row.evidence[0].source_type else 'unknown'


def source_language(row) -> str:
    return row.evidence[0].language if row.evidence else 'unknown'


def protected(row, domain: str) -> bool:
    text = _text(row)
    if domain == 'world-intelligence':
        return any(term in text for term in LONG_TAIL[domain]) or ('iran' in text and any(t in text for t in ('peace', 'talk', 'ceasefire', 'friedens', 'pourparlers')))
    return domain == 'aux' and any(term in text for term in AUX_TERMS)


def priority_score(row, domain: str) -> int:
    """Stable lexical priority; no model call or fabricated evidence."""
    text = _text(row)
    terms = DOMAIN_TERMS[domain]
    # The candidate's established source language is respected; other language
    # cues are also checked so mixed-language titles retain priority.
    matches = sum(2 for words in terms.values() for term in words if term in text)
    score = min(40, matches)
    if any(e.primary and e.fresh for e in row.evidence):
        score += 4
    if source_language(row) in ('en', 'de', 'fr'):
        score += 2
    if any(e.excerpt and len(e.excerpt) >= 100 for e in row.evidence):
        score += 1
    if protected(row, domain):
        score += 100
    return score


def _balance_cost(rows, left, right):
    # L1 distance across both language and source type distributions.
    cost = 0
    for getter in (source_language, source_type):
        a, b = Counter(getter(rows[i]) for i in left), Counter(getter(rows[i]) for i in right)
        cost += sum(abs(a[k] - b[k]) for k in set(a) | set(b))
    return cost


def deterministic_split(rows, domain: str, seed: str) -> tuple[list, list]:
    """Exhaustively choose a balanced 4/4 split, with stable hash tie breaks."""
    if len(rows) != EXPECTED_CANDIDATES:
        raise ValueError('Exactly eight fresh candidates are required for a 4/4 split')
    import itertools
    indices = range(len(rows))
    candidates = []
    for control_indices in itertools.combinations(indices, 4):
        treatment_indices = tuple(i for i in indices if i not in control_indices)
        protected_count = sum(protected(rows[i], domain) for i in treatment_indices)
        # At most two protected treatment candidates can both be routed; keep
        # additional protected long-tail cases in the fully-reviewed control.
        penalty = max(0, protected_count - 2) * 100
        tie = stable_hash(seed + '|' + domain + '|' + '|'.join(sorted(rows[i].event_id for i in control_indices)))
        candidates.append((_balance_cost(rows, control_indices, treatment_indices) + penalty, tie, control_indices, treatment_indices))
    _, _, control_indices, treatment_indices = min(candidates)
    return [rows[i] for i in control_indices], [rows[i] for i in treatment_indices]


def select_eight(rows, domain: str, seed: str) -> list:
    """Select an eight-item sample with language/source balance and topic coverage."""
    unique = {}
    for row in rows:
        unique.setdefault(row.event_id, row)
    pool = list(unique.values())
    if len(pool) <= EXPECTED_CANDIDATES:
        return sorted(pool, key=lambda r: stable_hash(seed + '|' + domain + '|' + r.event_id))
    chosen = []
    # Preserve relevant long-tail cases in the sample when collectors found them.
    required = [r for r in pool if protected(r, domain)]
    if domain == 'aux':
        required = [r for r in pool if any(t in _text(r) for t in AUX_TERMS)]
    required.sort(key=lambda r: stable_hash(seed + '|coverage|' + r.event_id))
    chosen.extend(required[:EXPECTED_CANDIDATES])
    remaining = [r for r in pool if r not in chosen]
    while len(chosen) < EXPECTED_CANDIDATES:
        def cost(row):
            trial = chosen + [row]
            # Penalize overrepresented language/source families while the sample fills.
            lang = Counter(source_language(x) for x in trial)
            src = Counter(source_type(x) for x in trial)
            return (max(lang.values()) - min(lang.values()), max(src.values()) - min(src.values()),
                    lang[source_language(row)] + src[source_type(row)],
                    stable_hash(seed + '|sample|' + domain + '|' + row.event_id))
        picked = min(remaining, key=cost)
        chosen.append(picked)
        remaining.remove(picked)
    return chosen


def treatment_route(rows, domain: str, seed: str) -> tuple[list, list]:
    if len(rows) != 4:
        raise ValueError('Treatment requires four candidates')
    ordered = sorted(rows, key=lambda r: (-priority_score(r, domain), stable_hash(seed + '|priority|' + domain + '|' + r.event_id)))
    top = ordered[0]
    exploratory_pool = [r for r in rows if r is not top]
    protected_pool = [r for r in exploratory_pool if protected(r, domain)]
    if protected_pool:
        exploratory_pool = protected_pool
    exploration = min(exploratory_pool, key=lambda r: stable_hash(seed + '|explore|' + domain + '|' + r.event_id))
    routed = [top] if exploration is top else [top, exploration]
    return routed, [r for r in rows if r not in routed]


def _estimate_request_tokens(payload: dict) -> int:
    # Provider requests cap generated output at 500 tokens. UTF-8 bytes/2 is a
    # deliberately conservative prompt estimate for the short evidence payload.
    return math.ceil(len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) / 2) + 500


async def decide_experiment(provider, state, command, payload, policy, budget):
    key = stable_hash(dumps([VERSION, provider.identity(), policy.model_dump(), command, payload]))
    cached = state.get('experiment-decision', key)
    if cached:
        return {**cached, 'cache_hit': True, 'charged_tokens': 0}
    estimate = _estimate_request_tokens(payload)
    request_limit = provider.request_limit if provider.request_limit is not None else ARM_REQUEST_CAP
    if provider.requests >= request_limit or budget['token_budget_reserved'] + estimate > policy.max_tokens:
        return {'decision': None, 'provider': {'status': 'experiment_budget_limit', 'model': provider.model},
                'cache_hit': False, 'charged_tokens': 0, 'estimated_tokens': estimate}
    budget['token_budget_reserved'] += estimate
    before = provider.requests
    decision, metadata = await provider.decide(command, payload)
    used = provider.requests - before
    actual = metadata.get('tokens')
    if actual is None and metadata.get('input_tokens') is not None and metadata.get('output_tokens') is not None:
        actual = metadata['input_tokens'] + metadata['output_tokens']
    if actual is not None:
        charged = actual + (max(0, used - 1) * estimate)
        budget['actual_tokens_known'] += actual
    else:
        charged = estimate * used
    # Reconcile reservations with usage after the response. On unknown usage,
    # retain the conservative reservation for each actual HTTP attempt.
    budget['token_budget_reserved'] += max(0, charged - estimate)
    budget['charged_token_estimate'] += charged
    budget['unknown_usage_calls'] += used if actual is None else max(0, used - 1)
    budget['latencies_ms'].extend([metadata['latency_ms']] if metadata.get('latency_ms') is not None else [])
    result = {'decision': decision.model_dump() if decision else None,
              'provider': {k: metadata[k] for k in ('status', 'model', 'response_model', 'model_identity_verified', 'attempts', 'tokens', 'input_tokens', 'output_tokens', 'latency_ms', 'error_code', 'format', 'abstained') if k in metadata},
              'cache_hit': False, 'charged_tokens': charged, 'estimated_tokens': estimate,
              'actual_requests': used}
    if decision:
        state.put('experiment-decision', key, result)
    return result


def _decision_payload(row, policy):
    return payload_for(row, policy, [])


def _candidate_evidence(row):
    return {'candidate_id': row.id, 'event_id': row.event_id, 'title': row.title, 'url': row.url,
            'evidence': [e.model_dump(mode='json') for e in row.evidence]}


def _review_label(row, domain, arm, status):
    return {'domain': domain, 'candidate_id': row.id, 'event_id': row.event_id, 'arm': arm,
            'route_status': status, 'human_labels': {'relevant': None, 'important': None,
            'evidence_supported': None, 'preferred_over_control': None, 'reviewer_notes': None,
            'reviewed_at_utc': None}}


async def run_experiment(output: Path, *, run_id: str, run_attempt: int = 1, acquisition=acquire, provider_factory=DecisionModelProvider,
                         excluded_event_ids: set[str] | None = None):
    output.mkdir(parents=True, exist_ok=True)
    excluded_event_ids = load_nov9_event_ids() if excluded_event_ids is None else excluded_event_ids
    profiles = load_profiles()
    domain_results = {}
    all_labels, all_evidence = [], []
    for domain in EXPERIMENT_DOMAINS:
        profile_id = DOMAINS[domain]
        profile = profiles[profile_id].model_copy(deep=True)
        profile.lookback_hours = min(profile.lookback_hours, 168)
        policy = policy_for(profile)
        collection_started = time.monotonic()
        try:
            async with asyncio.timeout(300):
                collected, source_metrics, extra = await acquisition(domain, profile)
            collection_error = None
        except Exception as exc:
            collected, source_metrics, extra = [], [], {}
            collection_error = type(exc).__name__
        collected_n = len(collected)
        fresh = [r for r in collected if r.evidence and all(e.fresh for e in r.evidence)]
        unseen = [r for r in fresh if r.event_id not in excluded_event_ids and r.id not in excluded_event_ids]
        sample = select_eight(unseen, domain, run_id)
        selected_ids = {r.event_id for r in sample}
        for row in sample:
            all_evidence.append({'domain': domain, **_candidate_evidence(row)})
        duration = round(time.monotonic() - collection_started, 3)
        domain_out = {'domain': domain, 'profile_id': profile_id,
                      'collection': {'retrieved_candidates': collected_n, 'fresh_candidates': len(fresh),
                          'excluded_nov9_events': len(fresh) - len(unseen), 'unique_unseen_candidates': len(unseen),
                          'selected_candidates': len(sample), 'collection_seconds': duration,
                          'source_metrics': source_metrics, 'additional_metrics': extra, 'error': collection_error},
                      'complete': len(sample) == EXPECTED_CANDIDATES,
                      'excluded_event_ids_sha256': stable_hash('\n'.join(sorted(excluded_event_ids))),
                      'policy_token_budget_per_arm': policy.max_tokens,
                      'request_cap_per_arm': min(ARM_REQUEST_CAP, policy.max_requests)}
        if not domain_out['complete']:
            domain_out['status'] = 'INCOMPLETE_INSUFFICIENT_FRESH_UNSEEN_CANDIDATES'
            domain_out['unassigned_candidates'] = [_candidate_evidence(r) for r in sample]
            for row in sample:
                all_labels.append(_review_label(row, domain, 'unassigned', 'DOMAIN_INCOMPLETE'))
            domain_results[domain] = domain_out
            continue
        rows = sorted(sample, key=lambda r: stable_hash(run_id + '|order|' + domain + '|' + r.event_id))
        control, treatment = deterministic_split(rows, domain, run_id)
        routed, screened = treatment_route(treatment, domain, run_id)
        domain_out['split'] = {'control_event_ids': [r.event_id for r in control],
                               'treatment_event_ids': [r.event_id for r in treatment],
                               'language_balance': {'control': dict(Counter(source_language(r) for r in control)),
                                                    'treatment': dict(Counter(source_language(r) for r in treatment))},
                               'source_type_balance': {'control': dict(Counter(source_type(r) for r in control)),
                                                       'treatment': dict(Counter(source_type(r) for r in treatment))}}
        domain_out['priority_scores'] = {r.event_id: priority_score(r, domain) for r in treatment}
        domain_out['routed_treatment_event_ids'] = [r.event_id for r in routed]
        domain_out['screened_out_event_ids'] = [r.event_id for r in screened]
        domain_out['protected_event_ids'] = [r.event_id for r in sample if protected(r, domain)]
        domain_out['arms'] = {}
        for arm, arm_rows in (('control', control), ('treatment', routed)):
            # Cache and provider identities never cross arm boundaries.
            provider = provider_factory()
            arm_request_cap = min(ARM_REQUEST_CAP, policy.max_requests)
            provider.request_limit = arm_request_cap
            state = DurableCheckpointStore(output / '.private-cache' / f'{domain}-{arm}.sqlite')
            budget = {'token_budget_reserved': 0, 'charged_token_estimate': 0,
                      'actual_tokens_known': 0, 'unknown_usage_calls': 0,
                      'latencies_ms': [], 'requests_before': provider.requests}
            decisions = {}
            try:
                async with asyncio.timeout(900):
                    for row in arm_rows:
                        payload = _decision_payload(row, policy)
                        command_results = {}
                        for command in COMMANDS:
                            command_results[command] = await decide_experiment(provider, state, command, payload, policy, budget)
                        decisions[row.event_id] = command_results
                        row.decisions = command_results
                expected_decisions = len(arm_rows) * len(COMMANDS)
                decisions_with_output = sum(bool(v['decision']) for d in decisions.values() for v in d.values())
                domain_out['arms'][arm] = {
                    'routed_candidates': len(arm_rows), 'expected_decisions': expected_decisions,
                    'decision_coverage_fraction': round(decisions_with_output / expected_decisions, 4) if expected_decisions else 0,
                    'decisions_with_model_output': decisions_with_output,
                    'decision_status_counts': dict(Counter(v.get('provider', {}).get('status', 'unknown')
                        for d in decisions.values() for v in d.values())),
                    'actual_provider_requests': provider.requests,
                    'request_cap': arm_request_cap,
                    'requests_remaining': max(0, arm_request_cap - provider.requests),
                    'actual_tokens_reported': budget['actual_tokens_known'],
                    'charged_token_estimate': budget['charged_token_estimate'],
                    'token_budget_reserved': budget['token_budget_reserved'],
                    'token_budget_limit': policy.max_tokens,
                    'token_budget_used_fraction': round(budget['token_budget_reserved'] / policy.max_tokens, 6) if policy.max_tokens else 0,
                    'token_usage_complete': budget['unknown_usage_calls'] == 0,
                    'latency_ms': {'count': len(budget['latencies_ms']),
                                   'total': sum(budget['latencies_ms']),
                                   'mean': round(sum(budget['latencies_ms']) / len(budget['latencies_ms']), 2) if budget['latencies_ms'] else None,
                                   'max': max(budget['latencies_ms']) if budget['latencies_ms'] else None},
                    'cache_hits': sum(bool(v.get('cache_hit')) for d in decisions.values() for v in d.values()),
                    'cache_identity_sha256': stable_hash(provider.identity()),
                    'decisions': decisions,
                }
            except TimeoutError:
                domain_out['arms'][arm] = {'routed_candidates': len(arm_rows), 'expected_decisions': len(arm_rows) * len(COMMANDS),
                    'actual_provider_requests': provider.requests, 'status': 'ARM_TIMEOUT', 'decisions': decisions}
            finally:
                state.close()
        domain_out['arms']['treatment']['screened_out'] = [
            {'event_id': row.event_id, 'status': 'SCREENED_OUT_FOR_BUDGET',
             'priority_score': priority_score(row, domain), 'provider_calls': 0}
            for row in screened]
        for row in control:
            all_labels.append(_review_label(row, domain, 'control', 'ROUTED_ALL_SIX_COMMANDS'))
        for row in treatment:
            all_labels.append(_review_label(row, domain, 'treatment',
                'ROUTED_ALL_SIX_COMMANDS' if row in routed else 'SCREENED_OUT_FOR_BUDGET'))
        domain_results[domain] = domain_out
    report = {
        'schema_version': '1.0', 'experiment_version': VERSION, 'run_id': run_id,
        'run_attempt': run_attempt,
        'created_at_utc': datetime.now(UTC).isoformat(), 'source_revision': os.getenv('GITHUB_SHA', 'local-development'),
        'workflow_run_id': os.getenv('GITHUB_RUN_ID'), 'domains': domain_results,
        'human_labels_available': False, 'precision': None, 'recall': None,
        'limitations': ['Human review labels are blank; precision and recall are not computed.',
                        'Model decisions are uncalibrated editorial judgments, not verified facts.',
                        'Source language comes from evidence metadata or the existing lexical heuristic; discovery locale is not treated as source language.',
                        'An incomplete domain is reported without reusing prior candidates.'],
    }
    atomic(output / 'experiment.json', dumps(report))
    atomic(output / 'candidate-evidence.json', dumps({'schema_version': '1.0', 'run_id': run_id,
        'run_attempt': run_attempt, 'candidates': all_evidence}))
    atomic(output / 'review-labels.json', dumps({'schema_version': '1.0', 'run_id': run_id,
        'run_attempt': run_attempt,
        'human_labels_available': False, 'precision': None, 'recall': None, 'labels': all_labels}))
    atomic(output / 'REPORT.md', render_report(report))
    # Cache databases are private execution state and never part of uploaded results.
    cache_dir = output / '.private-cache'
    if cache_dir.exists():
        for path in cache_dir.glob('*'):
            path.unlink(missing_ok=True)
        cache_dir.rmdir()
    return report


def render_report(report):
    lines = ['# Two-stage held-out filtering experiment', '',
             f"Run ID: `{report['run_id']}`. Attempt: `{report['run_attempt']}`. Created: `{report['created_at_utc']}`.",
             '', 'All human labels remain blank. Precision and recall are not calculated.', '',
             '| Domain | Status | Fresh unseen candidates | Control requests / decisions | Treatment requests / decisions | Screened out |',
             '|---|---|---:|---:|---:|---:|']
    for domain, result in report['domains'].items():
        collected = result['collection']['selected_candidates']
        if not result['complete']:
            lines.append(f"| {domain} | INCOMPLETE | {collected}/8 | — | — | — |")
            continue
        arms = result['arms']
        control = arms['control']; treatment = arms['treatment']
        lines.append(f"| {domain} | COMPLETE | {collected}/8 | {control.get('actual_provider_requests', 0)} / {control.get('decisions_with_model_output', 0)} | {treatment.get('actual_provider_requests', 0)} / {treatment.get('decisions_with_model_output', 0)} | {len(result['screened_out_event_ids'])} |")
    lines += ['', '## Method and coverage', '',
              'Each complete domain is deterministically divided into four control and four treatment candidates, balancing recorded language and source type. The control requests all six existing decision commands for every candidate. The treatment routes the top priority candidate and one seeded exploration candidate; each remaining candidate is marked `SCREENED_OUT_FOR_BUDGET` and receives zero provider calls.', '',
              'Actual HTTP attempts include retries and are capped at 27 per arm and domain. Token ceilings inherit the existing domain policy. Model request, token, latency and cache observations are recorded in `experiment.json`; no production policy limits were changed.', '',
              '## Human review', '', 'Review all rows in `review-labels.json`, including screen-outs. Until labels are entered, precision and recall remain null.', '', '## Limitations', '']
    lines.extend('- ' + x for x in report['limitations'])
    return '\n'.join(lines) + '\n'
