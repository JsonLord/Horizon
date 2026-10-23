import asyncio
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scripts import qualify_funding_acceptance as qa
from src.research.funding import pipeline
from src.research.programs.fetch import Page


def prepare(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_REF','refs/heads/'+qa.BRANCH)
    monkeypatch.setenv('GITHUB_EVENT_NAME','workflow_dispatch')
    monkeypatch.setenv('GITHUB_SHA','a'*40)
    monkeypatch.setenv('GITHUB_RUN_ID','123')
    monkeypatch.delenv('PREVIOUS_RUN_ID',raising=False)
    monkeypatch.setattr(qa,'ROOT',tmp_path)
    from src.research.profiles import ROOT
    shutil.copytree(ROOT/'research',tmp_path/'research')
    shutil.copytree(ROOT/'config',tmp_path/'config')
    original=pipeline.collect_opportunities
    class Fetcher:
        async def fetch(self,url,at):return Page(url,url,at,error='HTTP_503')
    async def collect(**kwargs):
        kwargs["fetcher"]=Fetcher()
        return await original(**kwargs)
    async def observation():return []
    async def model():return {'fallback':'deterministic'}
    monkeypatch.setattr(pipeline,'collect_opportunities',collect)
    monkeypatch.setattr(qa,'observations',observation)
    monkeypatch.setattr(qa,'nomination_checks',observation)
    monkeypatch.setattr(qa,'model_check',model)
    return tmp_path/'data/funding-acceptance'


def test_acceptance_snapshot_interruption_recovery_and_tamper_rejection(tmp_path,monkeypatch):
    output=prepare(tmp_path,monkeypatch)
    asyncio.run(qa.main())
    state=output/'snapshot'
    manifest=qa.verify_snapshot(state,'a'*40,'123')
    proof=json.loads((output/'proof.json').read_text())
    assert proof['recovery']['exact_tree_restored']
    assert len(proof['records'])==3 and all(r['claims_preserved'] for r in proof['records'].values())
    assert not any('Funding DK' in p or p.startswith('jobs/') or p.endswith('.lock') for p in manifest['files'])
    (state/'intel/manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):qa.verify_snapshot(state,'a'*40,'123')


@pytest.mark.parametrize('path',['../secret','/tmp/secret','intel/../evil.json','intel/code.py','research/funding-de-eu/Funding DK (DE missing).md','.github/workflows/x.yml'])
def test_snapshot_paths_reject_code_private_seed_and_traversal(path):
    assert not qa.snapshot_path(path)


def test_model_check_uses_real_public_contract_dto_and_fallback(monkeypatch):
    async def contract():return {'status':'model_unavailable'}
    monkeypatch.setattr(qa,'inspect_contract',contract)
    result=asyncio.run(qa.model_check())
    assert result['inference']['fallback']=='deterministic'
    assert not result['inference']['inference_succeeded']
    assert result['fallback_score']['hard_eligibility']=='review_required'


def test_committed_funding_folder_navigation_and_nomination_contract():
    from scripts.check_funding_acceptance import audit
    result=audit()
    assert result['opportunities']>=1
    assert sum(result['eligibility_counts'].values())==result['opportunities']
    assert result['nomination_counts']['pending']>=0
    assert result['local_links_checked']>30


def test_navigation_audit_rejects_missing_local_targets(tmp_path):
    from scripts.check_funding_acceptance import audit
    from src.research.profiles import ROOT
    shutil.copytree(ROOT/'research',tmp_path/'research')
    shutil.copytree(ROOT/'config',tmp_path/'config')
    (tmp_path/'Funding DK (DE missing).md').write_text('[Broken](does-not-exist.md)')
    with pytest.raises(ValueError,match='Broken'):audit(tmp_path)


def test_snapshot_download_errors_never_expose_signed_urls(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY','JsonLord/Horizon')
    def respond(request):
        if request.url.path.endswith('/zip'):raise httpx.ReadTimeout('SIGNED URL SECRET')
        if request.url.path.endswith('/artifacts'):
            return httpx.Response(200,json={'artifacts':[{'id':7,'name':qa.NAME,'expired':False}]})
        return httpx.Response(200,json={'head_sha':'a'*40,'head_branch':qa.BRANCH,'event':'workflow_dispatch','path':'.github/workflows/horizon-intel.yml','status':'completed','conclusion':'success'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await qa.restore_previous(tmp_path,'1','a'*40,client)
    with pytest.raises(RuntimeError,match='artifact transport') as exc:asyncio.run(run())
    assert 'SECRET' not in str(exc.value) and exc.value.__suppress_context__
