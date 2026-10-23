"""Explicit operator-authorized data-only PR qualification against an isolated base.

Never targets main/intel. Uses the existing GitHub identity, not a fabricated job token.
"""
import argparse
import asyncio
import json
import os
import re
from pathlib import Path
import tempfile
from urllib.parse import quote

from src.research.funding.research import ROOT, Queue, render_queue, policy
from src.research.funding.review import publish_review
from src.research.programs.review import ReviewAPI
from src.research.reporting import atomic, dumps

REPO='JsonLord/Horizon'
IMPLEMENTATION='feature/program-intelligence-implementation'


class QualificationAPI(ReviewAPI):
    last_operation = None

    async def call(self, method, path, payload=None, **kwargs):
        type(self).last_operation = {'method':method, 'path':path.split('?')[0]}
        return await super().call(method, path, payload, **kwargs)


def generated(queue):
    Queue.model_validate(queue)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);render_queue(queue,root)
        return {'research/funding-de-eu/'+name:(root/name).read_text() for name in ('RESEARCH_QUEUE.json','RESEARCH_UPDATES.md')}


async def qualify():
    hosted=os.getenv('GITHUB_ACTIONS')=='true'
    if hosted and (os.getenv('GITHUB_REF')!='refs/heads/'+IMPLEMENTATION or os.getenv('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.getenv('GITHUB_WORKFLOW_REF')!=REPO+'/.github/workflows/horizon-intel.yml@refs/heads/'+IMPLEMENTATION):
        raise PermissionError('Job-token qualification is restricted to explicit implementation-branch dispatch')
    api=QualificationAPI(REPO)
    source=await api.call('GET','commits/'+quote(IMPLEMENTATION,safe=''))
    if hosted and source['sha']!=os.getenv('GITHUB_SHA'):raise ValueError('Selected qualification source advanced')
    sha=source['sha'];base='automation/funding-acceptance-base-'+sha[:12];branch='automation/funding-acceptance-review-'+sha[:12]
    existing=await api.call('GET','git/ref/heads/'+base,missing=True)
    if existing and existing['object']['sha']!=sha:raise ValueError('Sandbox base advanced; do not overwrite')
    if not existing:await api.call('POST','git/refs',{'ref':'refs/heads/'+base,'sha':sha})
    original=json.loads((ROOT/'research/funding-de-eu/RESEARCH_QUEUE.json').read_text())
    async def publish(queue):
        return await publish_review(api,files=generated(queue),base_ref=base,base_sha=sha,branch=branch,
                                    title='Funding acceptance qualification — DO NOT MERGE',
                                    body='Isolated acceptance fixture. Intentionally reduced nomination queue, using existing public references only. No verified facts or eligibility changes. Do not merge this PR or its sandbox base.',qualification=True)
    public=[c for c in original['candidates'] if c['origin']=='public_search']
    if len(public)<2:raise ValueError('Need two existing public nominations for isolated fixture')
    first=dict(original,candidates=[c for c in original['candidates'] if c['candidate_id']!=public[0]['candidate_id']])
    second=dict(original,candidates=[c for c in first['candidates'] if c['candidate_id']!=public[1]['candidate_id']])
    opened=await api.call('GET','pulls?state=open&base='+quote(base,safe='')+'&per_page=100')
    reused_fixture=any(p.get('head',{}).get('ref')==branch for p in opened)
    baseline=await publish(second if reused_fixture else original)
    if baseline.get('writes')!=0:raise ValueError('Initial/no-change fixture unexpectedly wrote data')
    created=await publish(first);updated=await publish(second);repeated=await publish(second)
    if created['url']!=updated['url'] or updated['url']!=repeated['url'] or not updated['reused'] or repeated['writes']!=0:raise ValueError('Review PR was not reused idempotently')
    result={'source_sha':sha,'sandbox_base':base,'sandbox_head':branch,'qualification_only':True,
            'identity':'automatic Actions GITHUB_TOKEN' if hosted else 'existing operator GitHub identity; not automatic Actions GITHUB_TOKEN',
            'baseline_no_change':baseline,'created':created,'updated':updated,'repeated':repeated,
            'production_review_enabled':policy().review_pr_enabled,'merged':False}
    prior=ROOT/'docs/funding-review-qualification.json'
    if prior.exists():
        old=json.loads(prior.read_text())
        if old['source_sha']==sha:result['initial_execution']=old.get('initial_execution',old)
    atomic(ROOT/'docs/funding-review-qualification.json',dumps(result));print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true',required=True);p.parse_args()
    if os.getenv('GITHUB_ACTIONS')!='true':
        asyncio.run(qualify())
    else:
        from scripts.qualify_funding_acceptance import notice
        try:
            result=asyncio.run(qualify())
        except RuntimeError as exc:
            # ReviewAPI deliberately emits only safe HTTP status text.
            match=re.search(r'HTTP (403|422)',str(exc))
            if not match:raise
            result={'status':'blocked','http_status':int(match[1]),'identity':'automatic Actions GITHUB_TOKEN',
                    'source_sha':os.environ['GITHUB_SHA'],'workflow_run_id':os.environ['GITHUB_RUN_ID'],
                    'qualification_only':True,'production_review_enabled':policy().review_pr_enabled,
                    'failed_operation':QualificationAPI.last_operation,
                    'reason_code':'actions_pr_creation_disabled' if 'actions_pr_creation_disabled' in str(exc) else 'integration_permission_denied' if 'integration_permission_denied' in str(exc) else 'github_api_rejected',
                    'reason':'GitHub refused a sandbox API operation; no policy or permission settings changed.'}
            print('::warning title=Sandbox publication blocked::Automatic job-token API write refused; inspect the funding-review-token-proof notice. This is not successful PR publication.')
        result['workflow_run_id']=os.environ['GITHUB_RUN_ID']
        atomic(ROOT/'data/funding-review-qualification/proof.json',dumps(result))
        notice('funding-review-token-proof',result)
