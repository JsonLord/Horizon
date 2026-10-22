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
