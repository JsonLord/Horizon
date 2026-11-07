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
from src.research.profiles import ROOT


def corpus(revision):
    files=subprocess.check_output(['git','ls-tree','-r',revision,'--name-only'],text=True).splitlines()
    rows=[];seen=set();seen_ids=set()
    for name in reversed(sorted(f for f in files if f.endswith('/report.json'))):
        report=json.loads(subprocess.check_output(['git','show',revision+':'+name],text=True))
        sources={s['source_id']:s for s in report['sources']}
        for f in report['findings']:
            if not f['evidence']:continue
            e=f['evidence'][0];source=sources.get(e['source_id'])
            if not source or source['canonical_url'] in seen or f['finding_id'] in seen_ids:continue
            seen_ids.add(f['finding_id'])
            seen.add(source['canonical_url'])
            # Short attributed excerpts, one row per source URL; no full bodies.
            item={**f,'summary':' '.join(f['summary'].split()[:25]),'source_ids':[source['source_id']],'evidence':[{**e,'snippet':' '.join(e['snippet'].split()[:25])}]}
            rows.append({'finding':item,'source':{k:source.get(k) for k in ('source_id','canonical_url','publisher','fetched_at','content_fingerprint')},'archive_profile':report['profile_id'],'archive_report':name,'archive_revision':revision,'label':None,'label_status':'unreviewed_not_ground_truth'})
            if len(rows)==200:return rows
    return rows


def supplements(extra_reports):
    rows=[]
    for path in extra_reports:
        report=json.loads(path.read_text());sources={s['source_id']:s for s in report['sources']}
        for finding in report['findings'][:10]:
            if not finding['evidence']:continue
            e=finding['evidence'][0];source=sources[e['source_id']]
            item={**finding,'summary':' '.join(finding['summary'].split()[:25]),'source_ids':[e['source_id']],'evidence':[{**e,'snippet':' '.join(e['snippet'].split()[:25])}]}
            rows.append({'finding':item,'source':{k:source.get(k) for k in ('source_id','canonical_url','publisher','fetched_at','content_fingerprint')},'archive_profile':report['profile_id'],'source_kind':'actual_local_collection','source_report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_report_id':report['report_id'],'label':None,'label_status':'unreviewed_not_ground_truth'})
    for path in sorted((ROOT/'research/funding-de-eu').glob('opportunities/*/opportunity.json')):
        record=json.loads(path.read_text());claim=record['claims'].get('funding')
        if not claim:continue
        resource=next(r for r in record['resources'] if r['resource_id']==claim['evidence_ids'][0])
        if not resource['verified']:continue
        sid=hashlib.sha256(resource['url'].encode()).hexdigest()[:24]
        item={'finding_id':hashlib.sha256(('benchmark-view|'+record['opportunity_id']).encode()).hexdigest()[:24],'event_id':record['opportunity_id'],'summary':' '.join((record['provider']+' '+record['program']+': '+claim['value']).split()[:25]),'source_ids':[sid],'evidence':[{'source_id':sid,'snippet':' '.join(resource['quotation'].split()[:25])}],'profile_relevance':0,'baseline_score_unavailable':True}
        rows.append({'finding':item,'source':{'source_id':sid,'canonical_url':resource['url'],'publisher':record['provider'],'fetched_at':resource['retrieved_at'],'content_fingerprint':resource['content_sha256']},'archive_profile':'funding/de-eu','source_kind':'historical_opportunity_projection_not_archived_news','source_record':str(path.relative_to(ROOT)),'source_record_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'label':None,'label_status':'unreviewed_not_ground_truth'})
    return rows


def metrics(ranked,labels):
    if not labels or {r['item_id'] for r in ranked}!=set(labels) or any(not isinstance(x,dict) or x.get('reviewed') is not True or any(type(x.get(k)) is not bool for k in ('relevant','important','new_development','supported')) for x in labels.values()):
        return {k:None for k in ('precision_at_10','important_item_recall','new_development_recall','unsupported_finding_rate')}
    known=[r for r in ranked if r['item_id'] in labels]
    accepted=[r for r in known if r['accepted']]
    top=accepted[:10]
    recall=lambda field: sum(labels[r['item_id']].get(field,False) and r['accepted'] for r in known)/sum(v.get(field,False) for v in labels.values()) if any(v.get(field,False) for v in labels.values()) else None
    return {'precision_at_10':sum(labels[r['item_id']].get('relevant',False) for r in top)/len(top) if top else None, 'important_item_recall':recall('important'),'new_development_recall':recall('new_development'),'unsupported_finding_rate':sum(r['accepted'] and not labels[r['item_id']].get('supported',False) for r in known)/len(accepted) if accepted else None}


async def run(revision,output,labels=None,live=False,extra_reports=()):
    extra=supplements(extra_reports);rows=[];seen=set()
    for row in extra+corpus(revision):
        identity=row['finding']['finding_id']
        if identity in seen:continue
        seen.add(identity);rows.append(row)
        if len(rows)==200:break
    proof={'source_revision':revision,'items':len(rows),'source_profile_counts':dict(Counter(r['archive_profile'] for r in rows)),'labels':'unreviewed; no ground truth claimed','policies':[]}
    output.mkdir(parents=True,exist_ok=True);atomic(output/'corpus.json',dumps(rows))
    provider=DecisionModelProvider()
    if not live:provider.mode='off' # Live spend requires an explicit CLI flag.
    with tempfile.TemporaryDirectory() as temp:
        state=DurableCheckpointStore(Path(temp)/'benchmark.sqlite')
        for profile in ('examples/ai-usability','funding/de-eu','world/global'):
            started=time.monotonic();policy=FilterPolicy.load(profile)
            findings=[r['finding'] for r in rows];sources=[r['source'] for r in rows]
            requests_before=provider.requests
            decisions=await HorizonFilterPipeline(policy,state,provider).run(findings,sources,hard_statuses={} if profile=='funding/de-eu' else None)
            latencies=[g['provider']['latency_ms'] for r in decisions for g in r['gates'].values() if g['provider'].get('attempts',0)>0 and 'latency_ms' in g['provider']]
            baseline=sorted([f for f in findings if not f.get('baseline_score_unavailable')],key=lambda f:f['profile_relevance'],reverse=True)
            proof['policies'].append({'profile':profile,'baseline_top10':[f['finding_id'] for f in baseline[:10]],'shared_top10':[r['item_id'] for r in decisions[:10]],'metrics':metrics(decisions,(labels or {}).get(profile)), 'latency_ms':round((time.monotonic()-started)*1000),'fallback_frequency':sum(r['fallback'] for r in decisions)/len(decisions) if decisions else None,'model_latency_ms':sum(latencies)/len(latencies) if latencies else None,'model_requests':provider.requests-requests_before,'model_cost':0 if provider.requests==requests_before else None,'model_cost_per_accepted':0 if provider.requests==requests_before and any(r['accepted'] for r in decisions) else None,'duplicate_publication_rate':None,'publication':'disabled','coverage_limit':'Corpus reflects existing archive coverage; AUX/funding positives require curation and reviewed labels.'})
        state.close()
    atomic(output/'benchmark.json',dumps(proof));print(json.dumps(proof,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',required=True);p.add_argument('--output',type=Path,default=Path('data/shared-benchmark'));p.add_argument('--extra-report',type=Path,action='append',default=[]);p.add_argument('--labels',type=Path);p.add_argument('--live-model',action='store_true');a=p.parse_args()
    # Resolve the revision once, then bind every provenance reference to its SHA.
    sha=subprocess.check_output(['git','rev-parse',a.revision],text=True).strip()
    asyncio.run(run(sha,a.output,json.loads(a.labels.read_text()) if a.labels else None,a.live_model,a.extra_report))
