import asyncio
import json

import httpx
import pytest

from src.research.funding.review import MARKER, blob_sha, publish_review
from src.research.programs.review import ReviewAPI

BASE='automation/funding-acceptance-base-'+ 'a'*12
BRANCH='automation/funding-acceptance-review-'+ 'a'*12
PATH='research/funding-de-eu/RESEARCH_UPDATES.md'

class Git:
    repository='JsonLord/Horizon'
    def __init__(self):
        self.calls=[];self.files={PATH:'old'};self.head=None;self.pr=None;self.version=0;self.pending={};self.blobs={}
    async def call(self,method,path,payload=None,**kwargs):
        self.calls.append((method,path,payload))
        if path.startswith('commits/'):
            return {'sha':self.head if path.endswith(self.head or 'NOHEAD') else 'a'*40,'commit':{'tree':{'sha':'tree'}}}
        if path.startswith('pulls?'):return [self.pr] if self.pr else []
        if path.startswith('compare/'):return {'files':[{'filename':PATH}]}
        if path.startswith('git/ref/heads/'):return {'object':{'sha':self.head}} if self.head else None
        if path.startswith('git/trees/'):
            return {'tree':[{'path':p,'sha':blob_sha(v),'mode':'100644','type':'blob'} for p,v in self.files.items()],'truncated':False}
        if path=='git/blobs':
            sha=blob_sha(payload['content']);self.blobs[sha]=payload['content'];return {'sha':sha}
        if path=='git/trees':self.pending=payload;return {'sha':'new-tree'}
        if path=='git/commits':self.version+=1;return {'sha':str(self.version)*40}
        if path=='git/refs' or path.startswith('git/refs/heads/'):
            if method=='PATCH':assert payload['force'] is False
            self.head=payload['sha']
            for e in self.pending['tree']:
                if e['sha'] is None:self.files.pop(e['path'],None)
                else:self.files[e['path']]=self.blobs[e['sha']]
            return {}
        if path=='pulls':
            assert payload['draft'] and payload['base']==BASE
            self.pr={'number':9,'html_url':'https://github.com/JsonLord/Horizon/pull/9','body':payload['body'],'head':{'ref':BRANCH,'repo':{'full_name':self.repository}}};return self.pr
        if path=='pulls/9':self.pr['body']=payload['body'];return self.pr
        raise AssertionError((method,path))

def publish(api,content,**kwargs):
    return asyncio.run(publish_review(api,files={PATH:content},base_ref=BASE,base_sha='a'*40,branch=BRANCH,title='Qualification only',body='Do not merge.',qualification=True,**kwargs))


def test_owned_review_branch_updates_idempotently_without_duplicate_or_force():
    api=Git()
    first=publish(api,'first');second=publish(api,'second')
    assert first['url']==second['url'] and not first['reused'] and second['reused']
    writes=len([c for c in api.calls if c[0]!='GET'])
    third=publish(api,'second')
    assert third['writes']==0 and third['reused']
    assert len([c for c in api.calls if c[0]!='GET'])==writes
    assert sum(m=='POST' and p=='pulls' for m,p,_ in api.calls)==1
    assert all(v.get('force') is False for m,p,v in api.calls if p.startswith('git/refs/heads/'))


def test_no_change_creates_no_empty_pr():
    api=Git();result=publish(api,'old')
    assert result['status']=='no_change' and not any(c[0]!='GET' for c in api.calls)


@pytest.mark.parametrize('path',['.github/workflows/evil.yml','config/funding-research.json','AGENTS.md','research/funding-de-eu/Funding DK (DE missing).md'])
def test_generated_code_config_policy_and_seed_paths_rejected(path):
    with pytest.raises(ValueError):asyncio.run(publish_review(Git(),files={path:'bad'},base_ref=BASE,base_sha='a'*40,branch=BRANCH,title='x',body='x',qualification=True))


def test_unowned_branch_and_main_cannot_be_adopted():
    api=Git();publish(api,'first');api.pr['body']='unowned'
    with pytest.raises(PermissionError):publish(api,'second')
    with pytest.raises(PermissionError):asyncio.run(publish_review(api,files={},base_ref='main',base_sha='a'*40,branch='automation/funding-research',title='x',body='x',qualification=True))


@pytest.mark.parametrize('status',[403,422])
def test_permission_and_branch_protection_failures_are_transparent_and_sanitized(status,monkeypatch):
    monkeypatch.setenv('GH_TOKEN','test-placeholder')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(status,text='PRIVATE TOKEN BODY'))) as client:
            return await ReviewAPI('JsonLord/Horizon',client).call('POST','git/refs',{})
    with pytest.raises(RuntimeError,match='HTTP '+str(status)) as exc:asyncio.run(run())
    assert 'PRIVATE' not in str(exc.value)


def test_concurrent_review_ref_advance_prevents_overwrite():
    api=Git();publish(api,'first')
    original=api.call
    reads=0
    async def race(method,path,payload=None,**kwargs):
        nonlocal reads
        if method=='GET' and path.startswith('git/ref/heads/'):
            reads+=1
            if reads==2:return {'object':{'sha':'f'*40}}
        return await original(method,path,payload,**kwargs)
    api.call=race;before=len(api.calls)
    with pytest.raises(ValueError,match='advanced'):publish(api,'second')
    assert not any(m=='PATCH' for m,p,v in api.calls[before:])


def test_complete_generated_tree_removes_obsolete_deadline_folder():
    api=Git();publish(api,'first')
    old='research/funding-de-eu/opportunities/X__OLD/opportunity.json'
    api.files[old]='{}'
    publish(api,'second',complete_data_tree=True)
    assert old not in api.files
    assert any(e['path']==old and e['sha'] is None for e in api.pending['tree'])


def test_automatic_token_qualification_rejects_main_before_network(monkeypatch):
    from scripts.qualify_funding_review import qualify
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    monkeypatch.setenv('GITHUB_REF','refs/heads/main')
    with pytest.raises(PermissionError,match='restricted'):asyncio.run(qualify())


def test_job_token_pr_policy_error_is_reported_without_raw_body(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN','test-placeholder')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(403,json={'message':'GitHub Actions is not permitted to create or approve pull requests.','extra':'PRIVATE'}))) as client:
            return await ReviewAPI('JsonLord/Horizon',client).call('POST','pulls',{})
    with pytest.raises(RuntimeError,match='actions_pr_creation_disabled') as exc:asyncio.run(run())
    assert 'PRIVATE' not in str(exc.value)
