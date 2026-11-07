import asyncio,json
import httpx
import pytest
from src.research.filtering import FilterPolicy,HorizonFilterPipeline
from src.research.filtering.provider import DecisionModelProvider
from src.research.filtering.engine import DurableCheckpointStore,FeedbackStore

@pytest.mark.parametrize('kind',['strict','plain','bad-citation','bad-model'])
def test_openai_contract_validation_and_format_fallback(monkeypatch,kind):
    for key,value in {'BASE_URL':'https://example.org/v1','MODEL':'exact-model','API_MODE':'openai_chat','API_KEY':'test-key'}.items():monkeypatch.setenv('HORIZON_DECISION_'+key,value)
    calls=[]
    def respond(r):
        calls.append(json.loads(r.content));assert r.url.path=='/v1/chat/completions'
        if kind=='plain' and len(calls)==1:return httpx.Response(400,json={'error':'format unsupported'})
        d={'score':.8,'verdict':'yes','reason':'Supported','evidence_ids':['bad' if kind=='bad-citation' else 'e'],'hype':.1,'facts':.8,'signal':.8}
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
