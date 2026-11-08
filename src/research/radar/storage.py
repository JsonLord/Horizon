"""Validated immutable data snapshots, last-good pointers and catch-up planning."""
import hashlib
import json
import re
from datetime import timedelta
from pathlib import Path
from ..reporting import atomic, dumps
from .contracts import Digest, RadarManifest, RADARS, cutoff, utc, stamp, week_key


def read_json(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>1_000_000: raise ValueError('Unsafe artifact')
    return json.loads(path.read_text())


def load_manifest(root, radar):
    if radar not in RADARS: raise ValueError('Unknown radar')
    path=Path(root)/'radar-manifest.json'
    result=RadarManifest.model_validate(read_json(path)) if path.exists() else RadarManifest(radar_id=radar)
    if result.radar_id!=radar: raise ValueError('Cross-radar manifest')
    return result


def missing_weeks(root, radar, now, limit=8):
    if not 1<=limit<=52: raise ValueError('Invalid recovery bound')
    end=cutoff(now)
    manifest=load_manifest(root,radar)
    if not manifest.latest_week: return [end]
    latest=Digest.model_validate(read_json(Path(root)/'weekly-digest.json'))
    first=utc(latest.week_end_utc)+timedelta(days=7)
    # Bounded oldest-first catch-up. Never erase older history.
    return [first+timedelta(days=7*i) for i in range(limit) if first+timedelta(days=7*i)<=end]


def stage_digest(root, digest, correction=None):
    digest=Digest.model_validate(digest)
    root=Path(root)
    manifest=load_manifest(root,digest.radar_id)
    # Partial output is retained in run artifacts only, never last-good publication.
    if digest.status!='complete': return {'status':'partial','writes':0}
    week=week_key(digest.week_end_utc)
    path=root/'weekly'/week/'weekly-digest.json'
    value=digest.model_dump(mode='json')
    if path.exists():
        previous=Digest.model_validate(read_json(path))
        # A repeated run retains its first validated immutable identity, even if
        # generated_at or newly discovered inputs differ. Corrections are explicit.
        if correction is None: return {'status':'already_published','writes':0}
        if not re.fullmatch(r'[a-z0-9-]{3,64}',correction): raise ValueError('Invalid correction ID')
        path=root/'weekly'/week/'corrections'/correction/'weekly-digest.json'
        if path.exists():
            if read_json(path)!=value: raise ValueError('Immutable correction conflict')
            return {'status':'already_published','writes':0}
        # Correction metadata identifies previous digest bytes, never own commit SHA.
        metadata={'correction_id':correction,'supersedes_sha256':hashlib.sha256(dumps(previous.model_dump(mode='json')).encode()).hexdigest(),'reason':'Explicit reviewed correction; see corresponding Git commit review.'}
        atomic(path.with_name('correction.json'),dumps(metadata))
    atomic(path,dumps(value))
    latest=root/'weekly-digest.json'
    old=Digest.model_validate(read_json(latest)) if latest.exists() else None
    if old and old.radar_id!=digest.radar_id:raise ValueError('Cross-radar latest digest')
    if old and utc(old.week_end_utc)>utc(digest.week_end_utc):
        return {'status':'historical_only','writes':1}
    atomic(latest,dumps(value))
    manifest.latest_digest_path='weekly-digest.json';manifest.latest_week=week;manifest.digest_status='complete'
    manifest.last_successful_digest_utc=digest.generated_at_utc
    atomic(root/'radar-manifest.json',dumps(manifest.model_dump(mode='json')))
    return {'status':'published','writes':3}


def allowed_path(value):
    return value in ('radar-manifest.json','radar-state.json','weekly-digest.json','README.md') or bool(re.fullmatch(r'(weekly/\d{4}-W\d{2}(/corrections/[a-z0-9-]{3,64})?/(weekly-digest|correction)\.json|reports/[a-f0-9]{24}\.(json|md))',value))


def validate_tree(root, radar):
    root=Path(root)
    if not root.is_dir(): raise ValueError('Missing snapshot')
    files=[p for p in root.rglob('*') if p.is_file() or p.is_symlink()]
    if len(files)>5000: raise ValueError('Snapshot file limit')
    total=0
    for p in files:
        name=p.relative_to(root).as_posix()
        if not allowed_path(name) or p.is_symlink() or p.stat().st_size>1_000_000: raise ValueError('Unapproved data path')
        total+=p.stat().st_size
        if total>20_000_000: raise ValueError('Snapshot size limit')
        if p.name=='weekly-digest.json':
            d=Digest.model_validate(read_json(p))
            if d.radar_id!=radar or d.status!='complete': raise ValueError('Invalid public digest')
            if name!='weekly-digest.json' and name.split('/')[1]!=week_key(d.week_end_utc): raise ValueError('Wrong historical week')
    manifest=load_manifest(root,radar)
    if manifest.latest_digest_path:
        d=Digest.model_validate(read_json(root/manifest.latest_digest_path))
        if week_key(d.week_end_utc)!=manifest.latest_week or d.generated_at_utc!=manifest.last_successful_digest_utc: raise ValueError('Manifest mismatch')
        original=root/'weekly'/manifest.latest_week/'weekly-digest.json'
        candidates=[original]+list((original.parent/'corrections').glob('*/weekly-digest.json'))
        if not any(p.exists() and read_json(p)==d.model_dump(mode='json') for p in candidates): raise ValueError('Missing immutable snapshot')
    elif (root/'weekly-digest.json').exists(): raise ValueError('Unindexed digest')
    state=root/'radar-state.json'
    if state.exists():
        from .pipeline import State
        s=State.model_validate(read_json(state))
        if s.radar_id!=radar: raise ValueError('Cross-radar state')
    for p in (root/'reports').glob('*.json'):
        from .pipeline import TechnicalFinding
        finding=TechnicalFinding.model_validate(read_json(p))
        if finding.radar_id!=radar or p.stem!=hashlib.sha256(dumps(finding.model_dump(mode='json')).encode()).hexdigest()[:24]: raise ValueError('Report identity mismatch')
    return True
