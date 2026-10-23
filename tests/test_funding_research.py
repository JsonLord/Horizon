import asyncio
import copy
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.research.funding.research import ROOT, SEED, Queue, clean_url, discover, policy, seed_queue
from scripts.funding_research import allowed_path, apply, propose, verify_bundle


def test_seed_preserves_provenance_without_copying_notes_dates_or_credentials():
    content = '| VC | Deadline | Notes |\n| --- | --- | --- |\n| Test grant | 2024-01-01 | PRIVATE PLAN https://example.org/grant?utm_source=x |\n| Named fund | January 15 | secret narrative |\n'
    rows = seed_queue(content)
    assert len(rows) == 2
    assert rows[0]['url'] == 'https://example.org/grant'
    assert rows[1]['url'] is None
    serialized = json.dumps(rows)
    assert all(word not in serialized for word in ('PRIVATE', '2024', 'January', 'secret narrative'))
    assert rows[0]['seed_line'] == 3
    assert rows[1]['status'] == 'source_discovery_required'
    assert seed_queue('[https://example.org/](https://example.org/)')[0]['url'] == 'https://example.org/'
    assert len(seed_queue('[https://example.org/](https://example.org/)')) == 1


@pytest.mark.parametrize('url', ['http://example.org/', 'https://example.org/?token=private', 'https://example.org/?token=', 'https://example.org/#api_key=private', 'https://user:pass@example.org/', 'https://127.0.0.1/'])
def test_seed_urls_do_not_weaken_existing_url_rules(url):
    with pytest.raises(ValueError):
        clean_url(url)


def test_existing_collector_pydantic_urls_are_supported():
    from pydantic import HttpUrl
    assert clean_url(HttpUrl('https://example.org/grant'))=='https://example.org/grant'


def test_google_news_public_reference_parameter_is_normalized_without_dropping_auth():
    assert clean_url('https://news.google.com/rss/articles/ABC?oc=5')=='https://news.google.com/rss/articles/ABC'
    for url in ['https://news.google.com/rss/articles/ABC?oc=5&token=private','https://example.org/grant?oc=5']:
        with pytest.raises(ValueError):clean_url(url)


def test_search_uses_reviewed_queries_and_never_promotes_nominations():
    seen = []
    async def search(profile):
        seen.extend(q.text for q in profile.queries)
        return [SimpleNamespace(url='https://example.org/new-grant')], [{'source':'google_news','status':'ok','private_detail':'SECRET'}]
    queue = asyncio.run(discover('PRIVATE STARTUP PLAN', collector=search))
    assert seen and not any('PRIVATE' in q for q in seen)
    assert queue['candidates'][0]['status'] == 'official_source_review_required'
    assert 'SECRET' not in json.dumps(queue)


def test_search_does_not_replace_the_authored_seed_provenance():
    async def search(profile):return [SimpleNamespace(url='https://example.org/grant')], []
    queue=asyncio.run(discover('| Grant | https://example.org/grant |',collector=search))
    assert len(queue['candidates'])==1
    assert queue['candidates'][0]['origin']=='authored_seed'


def test_empty_search_retains_previous_candidates():
    async def search(profile):
        return [SimpleNamespace(url='https://example.org/new-grant')], []
    first = asyncio.run(discover('', collector=search))
    async def failed(profile):
        raise RuntimeError('private transport payload')
    second = asyncio.run(discover('', previous=first, collector=failed))
    assert second['candidates'] == first['candidates']
    assert 'private transport' not in json.dumps(second)


def payload():
    records = [json.loads(p.read_text()) for p in (ROOT/'research/funding-de-eu').glob('opportunities/*/opportunity.json')]
    content = (ROOT/SEED).read_text()
    async def search(profile):return [], []
    return {'schema_version':'1.0','report_status':'complete','source_sha':'a'*40, 'seed_sha256':hashlib.sha256(content.encode()).hexdigest(), 'funding':{'schema_version':'1.0','opportunities':records},'queue':asyncio.run(discover(content,collector=search))}


def test_proposal_rerenders_only_data_and_preserves_authored_seed(tmp_path):
    data = payload()
    shutil.copytree(ROOT/'research/funding-de-eu',tmp_path/'research/funding-de-eu')
    original = (tmp_path/SEED).read_bytes()
    data['untrusted_files'] = {'.github/workflows/pwn.yml':'untrusted code'}
    changed = apply(data, source_sha='a'*40, destination=tmp_path)
    assert all(allowed_path(p) for p in changed)
    assert (tmp_path/SEED).read_bytes() == original
    assert not (tmp_path/'.github').exists()
    assert not allowed_path(SEED)
    assert not allowed_path('.github/workflows/test.yml')
    assert not allowed_path('research/funding-de-eu/opportunities/X/agent.py')
    assert not allowed_path('research/funding-de-eu/opportunities/X/../../AGENTS.md')


def test_provenance_and_source_approval_are_required():
    data=payload()
    with pytest.raises(ValueError,match='revision'):
        verify_bundle(data,'b'*40)
    data['funding']['opportunities'][0]['official_domains'].append('other.example')
    with pytest.raises(ValueError,match='Unreviewed'):
        verify_bundle(data,'a'*40)


def test_disabled_or_branch_proposals_make_no_api_writes(monkeypatch):
    class API:
        async def call(self,*args,**kwargs):raise AssertionError('no GitHub calls allowed')
    result=asyncio.run(propose({},'a'*40,api=API()))
    assert result['writes']==0
    config=policy().model_copy(update={'review_pr_enabled':True})
    monkeypatch.setattr('scripts.funding_research.policy',lambda:config)
    monkeypatch.setenv('GITHUB_REF','refs/heads/feature/test')
    with pytest.raises(PermissionError):
        asyncio.run(propose({},'a'*40,api=API()))


def test_workflow_and_real_starting_point_contract():
    config=policy()
    assert not config.schedule_enabled and not config.review_pr_enabled
    queue=Queue.model_validate_json((ROOT/'research/funding-de-eu/RESEARCH_QUEUE.json').read_text())
    assert seed_queue((ROOT/SEED).read_text())
    assert 0 < len(queue.candidates) <= config.max_candidates
    assert all('](' not in (r.url or '') for r in queue.candidates)
    workflow=(ROOT/'.github/workflows/funding-research.yml').read_text()
    assert 'pull_request_target' not in workflow and 'pull-requests: write' in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert 'branches: [feature/program-intelligence-implementation]' in workflow


def test_queue_markdown_encodes_untrusted_url_markup(tmp_path):
    from src.research.funding.research import render_queue
    async def search(profile):return [SimpleNamespace(url='https://example.org/<script>alert(1)</script>',title='Funding grant')], []
    queue=asyncio.run(discover('',collector=search))
    render_queue(queue,tmp_path)
    rendered=(tmp_path/'RESEARCH_UPDATES.md').read_text()
    assert '<script>' not in rendered and '%3Cscript%3E' in rendered


def test_general_innovation_news_is_not_a_funding_nomination():
    async def search(profile):return [SimpleNamespace(url='https://example.org/news',title='New international technology partnership')], []
    assert not asyncio.run(discover('',collector=search))['candidates']


def test_proposal_creates_only_new_data_ref_and_draft_pr(tmp_path, monkeypatch):
    data=payload()
    url='https://example.org/new-grant'
    data['queue']['candidates'].append({'candidate_id':hashlib.sha256(('url:'+url).encode()).hexdigest()[:24], 'origin':'public_search','url':url,'label':'example.org','status':'official_source_review_required','approved_opportunity_id':None})
    shutil.copytree(ROOT/'research/funding-de-eu',tmp_path/'research/funding-de-eu')
    config=policy().model_copy(update={'review_pr_enabled':True})
    monkeypatch.setattr('scripts.funding_research.policy',lambda:config)
    monkeypatch.setenv('GITHUB_REF','refs/heads/main')
    monkeypatch.setenv('GITHUB_WORKFLOW_REF','JsonLord/Horizon/.github/workflows/funding-research.yml@refs/heads/main')
    monkeypatch.setenv('GITHUB_SHA','a'*40)
    class API:
        repository="JsonLord/Horizon"
        calls=[]
        async def call(self,method,path,payload=None,**kwargs):
            self.calls.append((method,path,payload))
            if path.startswith('pulls?'):return []
            if path=='commits/main':return {'sha':'a'*40,'commit':{'tree':{'sha':'base-tree'}}}
            if path.startswith('git/ref/heads/'):return None
            if method=='GET' and path.startswith('git/trees/'):
                return {'tree':[], 'truncated':False}
            if path=='git/trees':
                assert all(allowed_path(e['path']) and e['path']!=SEED for e in payload['tree'])
            if path=='pulls':
                assert payload['draft'] is True
                return {'html_url':'https://github.com/JsonLord/Horizon/pull/99'}
            return {'sha':'object'}
    api=API()
    result=asyncio.run(propose(data,'a'*40,api=api,destination=tmp_path))
    assert result['status']=='pending_review'
    assert all(c[0] in {'GET','POST'} for c in api.calls)
    assert any(c[1]=='git/refs' for c in api.calls)


def test_pipeline_collects_and_discovers_without_exporting_source_prose(tmp_path,monkeypatch):
    from scripts.funding_research import run
    from src.research.funding import pipeline
    original=pipeline.collect_opportunities
    from src.research.programs.fetch import Page
    class Fetcher:
        async def fetch(self,url,at):return Page(url,url,at,error='HTTP_503')
    async def collect(**kwargs):
        kwargs['fetcher']=Fetcher()
        return await original(**kwargs)
    async def discovery(content,**kwargs):
        async def search(profile):return [], []
        return await discover(content,collector=search,**kwargs)
    monkeypatch.setattr(pipeline,'collect_opportunities',collect)
    result=asyncio.run(run(tmp_path/'proposal',discovery=discovery))
    assert result['report_status']=='failed'
    assert len(result['funding']['opportunities'])==3
    assert verify_bundle(result,result['source_sha'])
    public=json.dumps(result)
    assert 'during our internship' not in public
    assert 'Market validation data' not in public
    assert (tmp_path/'proposal/proposal.json').is_file()


def test_public_run_proof_exports_only_bounded_review_metadata():
    from scripts.funding_research import public_proof
    data = payload()
    data['workflow_run_id'] = '123'
    data['funding']['opportunities'][0]['collection_error'] = 'PRIVATE TRANSPORT DETAILS'
    proof = public_proof(data)
    assert proof['read_only'] is True
    assert proof['opportunities'][0]['refresh_ok'] is False
    assert proof['nomination_counts']['authored_seed'] == len(data['queue']['candidates'])
    assert 'PRIVATE' not in json.dumps(proof)
    assert len(json.dumps(proof).encode()) < 3900
    data['funding']['opportunities'] = [dict(data['funding']['opportunities'][0], opportunity_id='x'*96) for _ in range(40)]
    data['queue']['search_metrics'] = [{'source':'google_news','status':'ok','error':'PRIVATE'} for _ in range(50)]
    expanded = public_proof(data)
    assert expanded['opportunity_count'] == 40
    assert expanded['opportunity_details_truncated'] is True
    assert len(expanded['opportunities']) == 8
    assert 'PRIVATE' not in json.dumps(expanded)
    assert len(json.dumps(expanded).encode()) < 3900
