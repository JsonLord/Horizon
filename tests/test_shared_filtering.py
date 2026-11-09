import asyncio,json
import httpx
import pytest
from src.research.filtering import FilterPolicy,HorizonFilterPipeline
from src.research.filtering.provider import DecisionModelProvider
from src.research.filtering.engine import DurableCheckpointStore,FeedbackStore

@pytest.mark.parametrize('kind',['strict','plain','bad-citation','bad-model','bad-type','bad-verdict'])
def test_openai_contract_validation_and_format_fallback(monkeypatch,kind):
    for key,value in {'BASE_URL':'https://example.org/v1','MODEL':'exact-model','API_MODE':'openai_chat','API_KEY':'test-key'}.items():monkeypatch.setenv('HORIZON_DECISION_'+key,value)
    calls=[]
    def respond(r):
        calls.append(json.loads(r.content));assert r.url.path=='/v1/chat/completions'
        if kind=='plain' and len(calls)==1:return httpx.Response(400,json={'error':'format unsupported'})
        d={'related_event_id':None,'score':True if kind=='bad-type' else .8,'verdict':'different' if kind=='bad-verdict' else 'yes','reason':'Supported','evidence_ids':['bad' if kind=='bad-citation' else 'e'],'hype':.1,'facts':.8,'signal':.8}
        return httpx.Response(200,json={'model':'wrong' if kind=='bad-model' else 'exact-model','choices':[{'message':{'content':json.dumps(d)}}],'usage':{'total_tokens':100}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:return await DecisionModelProvider(client).decide('relevance',{'evidence':[{'id':'e','snippet':'public'}]})
    d,m=asyncio.run(run());assert bool(d)==(kind in ('strict','plain'))
    if kind=='plain':assert len(calls)==2 and 'response_format' not in calls[-1]
    assert 'test-key' not in json.dumps(m)


def item():return {'finding_id':'i','event_id':'event','summary':'Accessibility testing policy','source_ids':['e'],'evidence':[{'source_id':'e','snippet':'Accessibility testing policy'}]}


def test_policy_hard_rules_feedback_and_snapshot_restore(tmp_path):
    state=DurableCheckpointStore(tmp_path/'state.sqlite')
    feedback=FeedbackStore(state);feedback.add('world/global','i','more_like_this','reviewed')
    assert feedback.adjustment('funding/de-eu','i')==0
    for profile in ('examples/ai-usability','funding/de-eu','world/global'):
        p=FilterPolicy.load(profile)
        r=asyncio.run(HorizonFilterPipeline(p,state).run([item()],[{'source_id':'e'}],hard_statuses={'event':'ELIGIBILITY_UNKNOWN'}))
        assert not r[0]['accepted'] and r[0]['provider_family']=='openai_chat'
    state.snapshot(str(tmp_path/'backup.sqlite'));state.close()
    other=DurableCheckpointStore(tmp_path/'backup.sqlite')
    assert other.get('history','world/global|i')['item_id']=='i';other.close()


def test_new_event_not_entity_duplicate_and_coverage(tmp_path):
    state=DurableCheckpointStore(tmp_path/'state.sqlite');pipeline=HorizonFilterPipeline(FilterPolicy.load('world/global'),state)
    a=item();r=asyncio.run(pipeline.run([a],[{'source_id':'e'}],[a]));assert r[0]['novelty']=='coverage' and not r[0]['accepted']
    b={**a,'event_id':'different'};r=asyncio.run(pipeline.run([b],[{'source_id':'e'}],[a]));assert r[0]['novelty']=='new'
    state.close()


def test_cache_does_not_override_changed_funding_eligibility(tmp_path):
    from src.research.filtering.provider import Decision
    class Provider:
        configured=True
        calls=0
        def identity(self):return 'fixture'
        async def decide(self,command,payload):
            self.calls+=1
            return Decision(score=.9,verdict='different' if command=='same-story' else 'yes',reason='Public fixture',evidence_ids=['e'],hype=.1,facts=.9,signal=.9),{'status':'success','model':'fixture'}
    state=DurableCheckpointStore(tmp_path/'state.sqlite');provider=Provider();p=HorizonFilterPipeline(FilterPolicy.load('funding/de-eu'),state,provider)
    first=asyncio.run(p.run([item()],[{'source_id':'e'}],hard_statuses={'event':'ELIGIBLE_NOW'}))
    assert first[0]['accepted']
    same=asyncio.run(p.run([item()],[{'source_id':'e'}],hard_statuses={'event':'ELIGIBLE_NOW'}))
    assert same[0]['cache_hit'] and provider.calls==6
    changed=asyncio.run(p.run([item()],[{'source_id':'e'}],hard_statuses={'event':'ELIGIBILITY_UNKNOWN'}))
    assert not changed[0]['accepted'] and not changed[0]['cache_hit']
    state.close()


def test_deduplication_within_a_single_batch(tmp_path):
    state=DurableCheckpointStore(tmp_path/'state.sqlite')
    a=item();b={**a,'finding_id':'second-coverage'}
    result=asyncio.run(HorizonFilterPipeline(FilterPolicy.load('world/global'),state).run([a,b],[{'source_id':'e'}]))
    second=next(r for r in result if r['item_id']=='second-coverage')
    assert second['novelty']=='coverage' and not second['accepted']
    state.close()


def test_unreviewed_benchmark_labels_never_become_ground_truth():
    from scripts.benchmark_shared_filtering import metrics
    assert metrics([{'item_id':'missing','accepted':True}],{'other':{'reviewed':True}})['precision_at_10'] is None


def test_spend_cap_without_pricing_fails_closed(tmp_path):
    class Provider:
        configured=True
        def identity(self):return 'fixture'
        async def decide(self,*args):raise AssertionError('Unknown pricing must not bypass USD cap')
    policy=FilterPolicy.load('world/global').model_copy(update={'max_cost_usd':.01,'usd_per_million_tokens':None})
    state=DurableCheckpointStore(tmp_path/'state.sqlite')
    result=asyncio.run(HorizonFilterPipeline(policy,state,Provider()).run([item()],[{'source_id':'e'}]))
    assert result[0]['fallback']
    state.close()


def test_empty_feed_does_not_claim_good_precision_or_recall():
    from scripts.benchmark_shared_filtering import metrics
    result=metrics([{'item_id':'i','accepted':False}],{'i':{'reviewed':True,'relevant':True,'important':True,'new_development':True,'supported':True}})
    assert result['precision_at_10'] is None
    assert result['important_item_recall']==0 and result['new_development_recall']==0


def test_feedback_is_bounded_and_free_text_not_sent_as_examples(tmp_path):
    state=DurableCheckpointStore(tmp_path/'state.sqlite')
    state.put('history','world/global|i',{'public_summary':'Public collected title'})
    feedback=FeedbackStore(state)
    for _ in range(10):feedback.add('world/global','i','more_like_this','PRIVATE REVIEW NOTES',topics=['policy'],sources=['e'])
    assert state.get('taste','world/global')['topics']['policy']==.1
    assert 'PRIVATE' not in json.dumps(state.get('examples','world/global'))
    assert state.get('taste','funding/de-eu') is None
    state.close()


def test_corrupted_snapshot_is_rejected_before_recovery(tmp_path,monkeypatch):
    from scripts.shared_filtering import qualify
    monkeypatch.setenv('HORIZON_DECISION_API_MODE','off')
    asyncio.run(qualify(tmp_path))
    (tmp_path/'checkpoint.sqlite').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):asyncio.run(qualify(tmp_path,True))


def test_normal_actions_cache_binding_and_atomic_install(tmp_path,monkeypatch):
    import io,zipfile
    from scripts.filter_state import seal,install
    monkeypatch.setenv('GITHUB_SHA','a'*40);monkeypatch.setenv('GITHUB_RUN_ID','123')
    root=tmp_path/'source';state=DurableCheckpointStore(root/'state.sqlite');state.put('history','public',{'ok':True});state.close();seal(root)
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        for name in ('checkpoint.sqlite','manifest.json'):z.write(root/name,name)
    target=tmp_path/'fresh-runner'
    assert install(target,data.getvalue(),'a'*40)['status']=='restored'
    state=DurableCheckpointStore(target/'state.sqlite');assert state.get('history','public')=={'ok':True};state.close()
    with pytest.raises(ValueError,match='binding'):install(target,data.getvalue(),'b'*40)


def test_long_retry_after_falls_back_without_premature_retry(monkeypatch):
    monkeypatch.setenv('HORIZON_DECISION_BASE_URL','https://example.org')
    monkeypatch.setenv('HORIZON_DECISION_MODEL','test')
    monkeypatch.setenv('HORIZON_DECISION_API_MODE','openai_chat')
    calls=[]
    def respond(r):calls.append(r);return httpx.Response(429,headers={'Retry-After':'3600'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:return await DecisionModelProvider(client).decide('relevance',{'evidence':[]})
    decision,meta=asyncio.run(run())
    assert decision is None and len(calls)==1 and meta['error_code']=='HTTP_429'


def test_direct_funding_pipeline_defaults_to_unknown_eligibility(tmp_path):
    state=DurableCheckpointStore(tmp_path/'state.sqlite')
    finding={**item(),'summary':'Berlin research software founder grant'}
    result=asyncio.run(HorizonFilterPipeline(FilterPolicy.load('funding/de-eu'),state).run([finding],[{'source_id':'e'}]))
    assert not result[0]['hard_gate'] and not result[0]['accepted']
    state.close()


def test_string_review_flags_are_not_valid_ground_truth():
    from scripts.benchmark_shared_filtering import metrics
    labels={'i':{'reviewed':'false','relevant':True,'important':True,'new_development':True,'supported':True}}
    assert metrics([{'item_id':'i','accepted':True}],labels)['precision_at_10'] is None


def test_exact_chat_operation_url_is_not_rewritten(monkeypatch):
    from src.research.filtering.provider import DecisionModelProvider
    import asyncio,httpx,json
    monkeypatch.setenv('HORIZON_DECISION_CHAT_URL','https://gateway.example.com/v1/custom')
    monkeypatch.setenv('HORIZON_DECISION_BASE_URL','https://ignored.example.com/v1')
    monkeypatch.setenv('HORIZON_DECISION_MODEL','test-model')
    monkeypatch.setenv('HORIZON_DECISION_API_MODE','openai_chat')
    seen=[]
    def handle(request):
        seen.append(str(request.url))
        assert json.loads(request.content)['model']=='test-model'
        return httpx.Response(404)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider=DecisionModelProvider(client)
            assert provider.configured
            await provider.decide('relevance',{'evidence':[]})
            old=provider.identity();provider.base='https://another-unused.example.com'
            assert provider.identity()==old
            provider.chat_url='https://gateway.example.com/v1/changed'
            assert provider.identity()!=old
    asyncio.run(run())
    assert seen==['https://gateway.example.com/v1/custom']


def test_exact_chat_url_can_replace_base_and_fails_closed(monkeypatch):
    from src.research.filtering.provider import DecisionModelProvider
    import asyncio
    monkeypatch.delenv('HORIZON_DECISION_BASE_URL',raising=False)
    monkeypatch.setenv('HORIZON_DECISION_MODEL','test-model')
    monkeypatch.setenv('HORIZON_DECISION_API_MODE','openai_chat')
    monkeypatch.setenv('HORIZON_DECISION_CHAT_URL','http://localhost/internal')
    provider=DecisionModelProvider()
    assert provider.configured
    value,meta=asyncio.run(provider.decide('relevance',{}))
    assert value is None and meta['status']=='invalid_configuration' and provider.requests==0


def test_qualification_url_cannot_redirect_model_secret_to_another_origin():
    from scripts.shared_filtering import qualification_endpoint
    assert qualification_endpoint('https://gateway.example.com/v1','https://gateway.example.com/operation')=='https://gateway.example.com/operation'
    for bad in ('https://attacker.example.com/operation','http://gateway.example.com/operation','https://gateway.example.com/operation?token=secret'):
        with pytest.raises(ValueError):qualification_endpoint('https://gateway.example.com/v1',bad)


def test_qualification_model_override_does_not_change_repository_environment(tmp_path,monkeypatch):
    from scripts.shared_filtering import qualify
    monkeypatch.setenv('HORIZON_DECISION_MODEL','repository-model')
    monkeypatch.delenv('HORIZON_DECISION_BASE_URL',raising=False)
    monkeypatch.delenv('HORIZON_DECISION_CHAT_URL',raising=False)
    proof=asyncio.run(qualify(tmp_path,model='approved-model'))
    assert proof['provider']['model']=='approved-model'
    import os
    assert os.environ['HORIZON_DECISION_MODEL']=='repository-model'
    with pytest.raises(ValueError,match='Invalid qualification model'):
        asyncio.run(qualify(tmp_path/'bad',model='model\nnot-an-id'))
