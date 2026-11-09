"""Fork schedule, conditional refresh, no-change and inference budget acceptance."""
import asyncio
import copy
import json
import shutil
from datetime import UTC,datetime,timedelta
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from src.research.profiles import ROOT,load_profiles
from src.research.reporting import atomic,dumps
from src.research.radar.contracts import stamp
from src.research.radar.pipeline import State,registry,collect_items,run_collection,reference
from src.research.radar.refresh import MeteredProvider,fingerprint
from scripts.actions_schedule import apply,plan

NOW=datetime(2026,11,9,12,tzinfo=UTC)


def temp_policy(tmp_path):
    for file in ('config/actions-schedules.json','config/radar/registry.json','config/funding-research.json','.github/workflows/horizon-intel.yml','.github/workflows/radar-fleet.yml','.github/workflows/funding-research.yml'):
        dest=tmp_path/file;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/file,dest)
    return tmp_path


def write_json(path,value):path.write_text(json.dumps(value))


def test_disabled_subsystems_have_no_scheduled_gate_runs(tmp_path):
    root=temp_policy(tmp_path);apply(root,check=True)
    for name in ('radar-fleet.yml','funding-research.yml','daily-summary.yml','shared-filtering.yml'):
        text=(ROOT/'.github/workflows'/name).read_text()
        assert '\n  schedule:' not in text and '\n  push:' not in text
    assert "cron: '23 6 * * *'" in (root/'.github/workflows/horizon-intel.yml').read_text()
    assert '\n  push:' not in (ROOT/'.github/workflows/research-validation.yml').read_text()


def test_schedule_render_pilot_optional_second_and_friday(tmp_path):
    root=temp_policy(tmp_path)
    config=json.loads((root/'config/actions-schedules.json').read_text());radar=json.loads((root/'config/radar/registry.json').read_text())
    config['radar']['enabled']=True
    write_json(root/'config/actions-schedules.json',config)
    with pytest.raises(ValueError,match='mismatch'):plan(root)
    radar['schedule_enabled']=True;write_json(root/'config/radar/registry.json',radar)
    result=plan(root)['radar-fleet.yml']
    assert "'13 2 * * *'" in result and "'0 18 * * 5'" in result and "'13 14 * * *'" not in result
    config['radar']['second_daily_run_enabled']=True;radar['second_daily_run_enabled']=True
    write_json(root/'config/actions-schedules.json',config);write_json(root/'config/radar/registry.json',radar)
    apply(root,check=False);apply(root,check=True)
    assert "'13 14 * * *'" in (root/'.github/workflows/radar-fleet.yml').read_text()
    config['radar']['enabled']=False;radar['schedule_enabled']=False
    write_json(root/'config/actions-schedules.json',config);write_json(root/'config/radar/registry.json',radar)
    apply(root,check=False)
    assert '\n  schedule:' not in (root/'.github/workflows/radar-fleet.yml').read_text()


def test_routine_worker_validates_locally_and_publisher_revalidates():
    text=(ROOT/'.github/workflows/radar-worker.yml').read_text()
    assert 'Validate the sealed checkpoint before artifact handoff' in text
    assert "if: inputs.durability == true" in text
    assert "needs.collect.outputs.changed == 'true'" in text
    assert "needs.validate.result == 'skipped'" in text
    assert "contents: read" in text.split('  publish:')[0]
    assert "contents: write" not in text.split('  publish:')[0]
    assert 'enable-cache: true' in text
    shared=(ROOT/'.github/workflows/shared-filtering.yml').read_text()
    assert 'pytest' not in shared and 'push:' not in shared


def test_release_304_retains_original_evidence_and_source_isolation(monkeypatch):
    import src.research.collector as collector
    async def empty(profile,**kwargs):return [],[{'source':'google_news','query':profile.queries[0].text,'status':'ok','items':0}]
    monkeypatch.setattr(collector,'collect',empty)
    entry=registry()['radars'][2];profile=load_profiles()[entry['profile_id']]
    s=State(radar_id=entry['radar_id'],policy_version=entry['policy_version']);rounds={};headers=[]
    def handler(request):
        repo='/'.join(request.url.path.split('/')[2:4]);count=rounds.get(repo,0);rounds[repo]=count+1
        if count:
            headers.append(request.headers.get('If-None-Match'))
            if repo.endswith('faiss'):return httpx.Response(503)
            return httpx.Response(304)
        return httpx.Response(200,headers={'ETag':'"release-v1"'},json=[{'id':1,'name':'The new mechanism for training with evidence','tag_name':'v1','published_at':stamp(NOW-timedelta(hours=1)),'html_url':'https://github.com/'+repo+'/releases/tag/v1','body':'The mechanism for training with evidence improves a measured baseline.','author':{'login':'public-author'}}])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            first,checks=await collect_items(entry,profile,client=client,state=s,now=NOW)
            original={reference(i).id:reference(i) for i in first}
            second,checks2=await collect_items(entry,profile,client=client,state=s,now=NOW+timedelta(days=1))
            assert {reference(i).id:reference(i) for i in second}==original
            assert any(c.get('http_status')==304 and c['content_unchanged'] for c in checks2)
            assert any(c['status']=='failed' for c in checks2)
    asyncio.run(run())
    assert headers==['"release-v1"','"release-v1"']
    assert all(not hasattr(c,'body') for c in s.source_cache.values())


def test_not_due_makes_zero_collection_or_provider_calls(tmp_path,monkeypatch):
    import src.research.radar.pipeline as pipeline
    s=State(radar_id='rag-memory',policy_version='radar-1.0-provisional',next_eligible_collection_utc=stamp(NOW+timedelta(hours=24)))
    atomic(tmp_path/'radar-state.json',dumps(s.model_dump(mode='json')))
    prior=(tmp_path/'radar-state.json').read_bytes()
    async def forbidden(*a,**k):raise AssertionError('Not-due source was fetched')
    monkeypatch.setattr(pipeline,'collect_items',forbidden)
    result,metrics=asyncio.run(run_collection('rag-memory',tmp_path,NOW,source_revision='different-docs-sha'))
    assert metrics[0]['status']=='not_due' and metrics[1]['model_requests']==0
    assert (tmp_path/'radar-state.json').read_bytes()==prior


def test_provider_meter_reserves_calls_tokens_and_unknown_cost():
    class Provider:
        configured=True;model='fixture'
        def identity(self):return 'fixture'
        async def decide(self,*a):return None,{'status':'invalid_or_unavailable','attempts':3,'tokens':None}
    entry={'max_model_requests':3,'max_model_tokens':200000,'max_cost_usd':None,'usd_per_million_tokens':None}
    meter=MeteredProvider(Provider(),entry)
    async def run():
        await meter.decide('relevance',{})
        _,blocked=await meter.decide('relevance',{})
        assert blocked['status']=='budget_limit'
    asyncio.run(run());metrics=meter.telemetry()
    assert metrics['model_requests']==3 and metrics['cost_usd'] is None and not metrics['token_usage_complete']
    meter=MeteredProvider(Provider(),{**entry,'max_cost_usd':1})
    assert asyncio.run(meter.decide('relevance',{}))[1]['status']=='budget_limit'


def test_unchanged_cli_run_suppresses_publisher_handoff(tmp_path,monkeypatch):
    import scripts.radar_fleet as cli
    radar='rag-memory';root=tmp_path/radar
    s=State(radar_id=radar,policy_version='radar-1.0-provisional',next_eligible_collection_utc=stamp(datetime.now(UTC)+timedelta(days=1)))
    atomic(root/'radar-state.json',dumps(s.model_dump(mode='json')))
    atomic(root/'radar-manifest.json',dumps(cli.RadarManifest(radar_id=radar).model_dump(mode='json')))
    output=tmp_path/'job-output';monkeypatch.setenv('GITHUB_OUTPUT',str(output));monkeypatch.delenv('GITHUB_EVENT_NAME',raising=False)
    args=SimpleNamespace(output=tmp_path,radar=radar,command='collect',restore=False)
    asyncio.run(cli.main(args))
    assert output.read_text()=='changed=false\n'
    cli.verify(root,json.loads((tmp_path/(radar+'-checkpoint.json')).read_text()),radar,'local-development')


def test_source_cache_hash_tampering_is_rejected():
    from src.research.radar.refresh import SourceSnapshot
    with pytest.raises(ValueError,match='hash mismatch'):
        SourceSnapshot(content_hash='0'*64,last_checked_utc=stamp(NOW),references=[])


def test_required_live_smoke_cannot_report_fallback_success(tmp_path,monkeypatch):
    from scripts.shared_filtering import qualify
    monkeypatch.delenv('HORIZON_DECISION_BASE_URL',raising=False)
    proof=asyncio.run(qualify(tmp_path))
    assert not proof['all_commands_live_validated'] and proof['provider_requests']==0
    text=(ROOT/'.github/workflows/shared-filtering.yml').read_text()
    assert '--require-live' in text


def test_delayed_daily_cadence_and_friday_refresh(tmp_path,monkeypatch):
    from src.research.radar.refresh import next_collection_due
    from src.research.radar.contracts import utc
    assert next_collection_due(datetime(2026,11,9,2,20,tzinfo=UTC),24)=='2026-11-10T02:13:00Z'
    assert next_collection_due(datetime(2026,11,9,2,20,tzinfo=UTC),12)=='2026-11-09T14:13:00Z'
    import src.research.radar.pipeline as pipeline
    s=State(radar_id='rag-memory',policy_version='radar-1.0-provisional',next_eligible_collection_utc='2026-11-14T02:13:00Z')
    atomic(tmp_path/'radar-state.json',dumps(s.model_dump(mode='json')))
    calls=[]
    async def collect(*a,**k):calls.append(True);return [],[{'source':'fixture','status':'ok'}]
    monkeypatch.setattr(pipeline,'collect_items',collect)
    asyncio.run(run_collection('rag-memory',tmp_path,utc('2026-11-13T18:15:00Z'),force=True))
    assert len(calls)==1


def test_reported_excess_usage_stops_further_inference():
    class Provider:
        configured=True;model='fixture'
        calls=0
        def identity(self):return 'fixture'
        async def decide(self,*args):
            self.calls+=1
            return None,{'status':'success','attempts':1,'tokens':250000}
    p=Provider();meter=MeteredProvider(p,{'max_model_requests':36,'max_model_tokens':200000})
    async def run():
        _,first=await meter.decide('relevance',{})
        _,second=await meter.decide('relevance',{})
        assert first['status']=='usage_budget_exceeded' and second['status']=='budget_limit'
    asyncio.run(run())
    assert p.calls==1 and meter.telemetry()['reported_usage_exceeds_token_budget']


def test_cadence_and_budget_tuning_reuses_semantic_identity():
    from src.research.radar.pipeline import analysis_identity
    entry=registry()['radars'][0];profile=load_profiles()[entry['profile_id']]
    before=analysis_identity(entry,profile)
    assert analysis_identity({**entry,'collection_interval_hours':12,'max_model_requests':12,'max_cost_usd':1},profile)==before
    assert analysis_identity({**entry,'policy_version':'radar-next-reviewed'},profile)!=before
