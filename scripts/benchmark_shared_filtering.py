"""Build a bounded public-archive benchmark; never invent reviewed labels."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from collections import Counter

from src.research.filtering import FilterPolicy,HorizonFilterPipeline
from src.research.filtering.engine import DurableCheckpointStore
from src.research.filtering.provider import DecisionModelProvider
from src.research.reporting import atomic,dumps


def corpus(revision):
    files=subprocess.check_output(['git','ls-tree','-r',revision,'--name-only'],text=True).splitlines()
    rows=[];seen=set()
    for name in reversed(sorted(f for f in files if f.endswith('/report.json'))):
        report=json.loads(subprocess.check_output(['git','show',revision+':'+name],text=True))
        sources={s['source_id']:s for s in report['sources']}
        for f in report['findings']:
            if not f['evidence']:continue
            e=f['evidence'][0];source=sources.get(e['source_id'])
            if not source or source['canonical_url'] in seen:continue
            seen.add(source['canonical_url'])
            # Short attributed excerpts, one row per source URL; no full bodies.
            item={**f,'summary':' '.join(f['summary'].split()[:25]),'source_ids':[source['source_id']],'evidence':[{**e,'snippet':' '.join(e['snippet'].split()[:25])}]}
            rows.append({'finding':item,'source':source,'archive_profile':report['profile_id'],'archive_report':name,'archive_revision':revision,'label':None,'label_status':'unreviewed_not_ground_truth'})
            if len(rows)==200:return rows
    return rows


def metrics(ranked,labels):
    if not labels or any(not x.get('reviewed') for x in labels.values()):
        return {k:None for k in ('precision_at_10','important_item_recall','new_development_recall','unsupported_finding_rate')}
    known=[r for r in ranked if r['item_id'] in labels]
    top=known[:10]
    recall=lambda field: sum(labels[r['item_id']].get(field,False) and r['accepted'] for r in known)/max(1,sum(v.get(field,False) for v in labels.values()))
    return {'precision_at_10':sum(labels[r['item_id']].get('relevant',False) for r in top)/max(1,len(top)), 'important_item_recall':recall('important'),'new_development_recall':recall('new_development'),'unsupported_finding_rate':sum(r['accepted'] and not labels[r['item_id']].get('supported',False) for r in known)/max(1,sum(r['accepted'] for r in known))}


async def run(revision,output,labels=None):
    rows=corpus(revision);proof={'source_revision':revision,'items':len(rows),'source_profile_counts':dict(Counter(r['archive_profile'] for r in rows)),'labels':'unreviewed; no ground truth claimed','policies':[]}
    output.mkdir(parents=True,exist_ok=True);atomic(output/'corpus.json',dumps(rows))
    provider=DecisionModelProvider();provider.mode='off' # Explicit baseline, never silent live benchmark spend.
    with tempfile.TemporaryDirectory() as temp:
        state=DurableCheckpointStore(Path(temp)/'benchmark.sqlite')
        for profile in ('examples/ai-usability','funding/de-eu','world/global'):
            started=time.monotonic();policy=FilterPolicy.load(profile)
            findings=[r['finding'] for r in rows];sources=[r['source'] for r in rows]
            decisions=await HorizonFilterPipeline(policy,state,provider).run(findings,sources,hard_statuses={} if profile=='funding/de-eu' else None)
            baseline=sorted(findings,key=lambda f:f['profile_relevance'],reverse=True)
            proof['policies'].append({'profile':profile,'baseline_top10':[f['finding_id'] for f in baseline[:10]],'shared_top10':[r['item_id'] for r in decisions[:10]],'metrics':metrics(decisions,(labels or {}).get(profile)), 'latency_ms':round((time.monotonic()-started)*1000),'fallback_frequency':1 if decisions else None,'model_requests':0,'model_cost':0,'model_cost_per_accepted':0 if any(r['accepted'] for r in decisions) else None,'duplicate_publication_rate':None,'publication':'disabled','coverage_limit':'Corpus reflects existing archive coverage; AUX/funding positives require curation and reviewed labels.'})
        state.close()
    atomic(output/'benchmark.json',dumps(proof));print(json.dumps(proof,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',required=True);p.add_argument('--output',type=Path,default=Path('data/shared-benchmark'));p.add_argument('--labels',type=Path);a=p.parse_args()
    # Resolve the revision once, then bind every provenance reference to its SHA.
    sha=subprocess.check_output(['git','rev-parse',a.revision],text=True).strip()
    asyncio.run(run(sha,a.output,json.loads(a.labels.read_text()) if a.labels else None))
