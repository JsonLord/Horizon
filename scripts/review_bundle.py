"""Validate/recover public review artifacts; narrowly publish to the draft PR only."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from src.research.live_review import DOMAINS, ReviewPack
from src.research.radar.publisher import GitHubData
from src.research.reporting import atomic, dumps

TARGET = 'feature/technical-radar-fleet'
FILES = ['INDEX.md', 'review.schema.json'] + [f'{d}/{n}' for d in DOMAINS for n in ('findings.json', 'REVIEW.md', 'review-labels.json')]


def validate(root, source, run_id):
    files = {}
    for name in FILES:
        p = root / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 1_000_000: raise ValueError('Missing/unsafe review file')
        raw = p.read_bytes()
        for key in ('HORIZON_DECISION_API_KEY', 'HORIZON_DECISION_BASE_URL', 'HORIZON_DECISION_CHAT_URL'):
            value = os.getenv(key, '')
            if value and value.encode() in raw: raise ValueError('Configured secret/endpoint in public report')
        if b'Authorization: Bearer ' in raw: raise ValueError('Credential-like public output')
        files[name] = raw
    if sum(map(len, files.values())) > 10_000_000: raise ValueError('Review bundle size ceiling')
    if json.loads(files['review.schema.json']) != ReviewPack.model_json_schema(): raise ValueError('Review schema mismatch')
    for domain in DOMAINS:
        pack = ReviewPack.model_validate_json(files[domain + '/findings.json'])
        if pack.domain != domain or pack.source_revision != source or pack.workflow_run_id != str(run_id): raise ValueError('Review source/run mismatch')
        label = json.loads(files[domain + '/review-labels.json'])
        if label['findings_sha256'] != hashlib.sha256(files[domain + '/findings.json']).hexdigest(): raise ValueError('Feedback/report mismatch')
        if len(label['labels']) > 20 or not {r['candidate_id'] for r in label['labels']} <= {c.id for c in pack.candidates}: raise ValueError('Invalid feedback selection')
        for row in label['labels']:
            if any(row.get(k) is not None for k in ('relevant', 'important', 'new_development', 'evidence_supported', 'correct_duplicate_classification', 'preference', 'reviewer_notes', 'reviewed_at')): raise ValueError('Labels must be genuinely unreviewed')
    return files


def seal(root, source, run_id, api):
    run = api.api('GET', 'actions/runs/' + str(run_id))
    if run['head_sha'] != source or not run['head_branch'].startswith('qualification/live-review-') or run['conclusion'] != 'success': raise ValueError('Unapproved collection run')
    files = validate(root, source, run_id)
    proof = {'schema_version': '1.0', 'source_revision': source, 'collection_run_id': str(run_id),
        'collection_run_url': run['html_url'], 'validation_run_id': os.getenv('GITHUB_RUN_ID'),
        'files': {p: hashlib.sha256(raw).hexdigest() for p, raw in files.items()}}
    atomic(root / 'review-handoff.json', dumps(proof))
    atomic(root / 'hosted-proof.json', dumps(proof))
    return proof


def verified(root):
    proof = json.loads((root / 'review-handoff.json').read_text())
    files = validate(root, proof['source_revision'], proof['collection_run_id'])
    if proof['files'] != {p: hashlib.sha256(raw).hexdigest() for p, raw in files.items()}: raise ValueError('Review handoff hash mismatch')
    return files, proof


def summary(root, domain):
    pack = ReviewPack.model_validate_json((root / domain / 'findings.json').read_text())
    rows = sorted(pack.candidates, key=lambda c: c.attention, reverse=True)
    proof = {'domain': domain, 'statistics': pack.statistics, 'cache_replay': pack.cache_replay,
        'top': [{'title': r.title[:120], 'url': r.url, 'classification': r.classification, 'attention': r.attention} for r in rows[:2]],
        'source_errors': [s for s in pack.sources if s.get('status') != 'ok'][:3], 'acceptance': pack.acceptance}
    # Runner notice messages are capped at4096bytes; one per domain step.
    raw = json.dumps(proof, ensure_ascii=True)
    if len(raw.encode()) > 3500:
        proof['top'] = [{k:v for k,v in r.items() if k != 'url'} for r in proof['top']]
        proof['source_errors'] = proof['source_errors'][:1]
        raw = json.dumps(proof, ensure_ascii=True)
    if len(raw.encode()) > 3800: raise ValueError('Summary bound')
    print('::notice title=live-review-summary::' + raw.replace('%', '%25'))


def publish(root, api):
    if os.getenv('GITHUB_EVENT_NAME') != 'workflow_dispatch' or not os.getenv('GITHUB_REF', '').startswith('refs/heads/qualification/live-review-'):
        raise ValueError('Review publication requires the explicit isolated qualification dispatch')
    files, proof = verified(root)
    if proof['validation_run_id'] != os.getenv('GITHUB_RUN_ID'): raise ValueError('Cross-run handoff prohibited')
    files['hosted-proof.json'] = dumps(proof).encode()
    # No code/config, cache, production archive, data branch, deletion or force push.
    head = api.api('GET', 'git/ref/heads/' + TARGET)['object']['sha']
    tree_sha = api.api('GET', 'git/commits/' + head)['tree']['sha']
    entries = []
    for name, raw in files.items():
        blob = api.api('POST', 'git/blobs', json={'encoding': 'base64', 'content': base64.b64encode(raw).decode()})
        entries.append({'path': 'data/live-review/' + name, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    tree = api.api('POST', 'git/trees', json={'base_tree': tree_sha, 'tree': entries})
    if tree['sha'] == tree_sha:
        print('::notice title=live-review-publication::' + json.dumps({'branch': TARGET, 'commit': head, 'files': 0, 'status': 'unchanged'}))
        return
    commit = api.api('POST', 'git/commits', json={'message': 'Add validated public seven-domain live research review packs', 'tree': tree['sha'], 'parents': [head]})
    api.api('PATCH', 'git/refs/heads/' + TARGET, json={'sha': commit['sha'], 'force': False})
    print('::notice title=live-review-publication::' + json.dumps({'branch': TARGET, 'commit': commit['sha'], 'files': len(files)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['seal', 'verify', 'summary', 'publish'])
    p.add_argument('--root', type=Path, default=Path('data/live-review'))
    p.add_argument('--source-sha')
    p.add_argument('--run-id')
    p.add_argument('--domain', choices=DOMAINS)
    args = p.parse_args()
    if args.command == 'seal': seal(args.root, args.source_sha, args.run_id, GitHubData())
    elif args.command == 'verify': verified(args.root)
    elif args.command == 'summary': summary(args.root, args.domain)
    else: publish(args.root, GitHubData())
