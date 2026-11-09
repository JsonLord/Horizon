"""Native state/questions integration: choices cannot fabricate generative facts."""
import asyncio,copy,json
import httpx
import pytest
from src.research.filtering.provider import DecisionModelProvider,COMMANDS
from src.research.filtering.engine import HorizonFilterPipeline,FilterPolicy,DurableCheckpointStore


def configure(monkeypatch):
    for key,value in {'BASE_URL':'https://classifier.example.com/v1/operation','MODEL':'requested-alias','RESPONSE_MODEL':'approved-backend','API_MODE':'systemone','API_KEY':'private-test-token'}.items():monkeypatch.setenv('HORIZON_DECISION_'+key,value)
    monkeypatch.delenv('HORIZON_DECISION_CHAT_URL',raising=False)


def response(body,changes=None):
    answers={}
    for key,q in body['questions'].items():
        names=list(q['criteria'])
        choice='e' if key=='citation' else 'old-event' if key=='event' else 'development' if 'development' in names else 'yes' if 'yes' in names else 'high'
        if choice not in names:choice=names[0]
        answers[key]={'type':'choice','choice':choice,'probabilities':{name:1.0 if name==choice else 0.0 for name in names},'confidence':.0244,'action':{'act_probability':1.0}}
    envelope={'model':'approved-backend','answers':answers,'usage':{'input_tokens':82,'output_tokens':0},'routing':{'model':'english','reason':'Ignored service metadata'}}
    if changes:changes(envelope)
    return envelope


@pytest.mark.parametrize('command',COMMANDS)
def test_native_commands_exact_contract_and_normalization(monkeypatch,command):
    configure(monkeypatch);requests=[]
    def handle(request):
        assert request.url.path=='/v1/operation'
        assert request.headers['authorization']=='Bearer private-test-token'
        body=json.loads(request.content);requests.append(body)
        assert set(body)=={'model','state','questions'} and isinstance(body['state'],str)
        assert 'Français' in body['state'] and 'Gedächtnis' in body['state']
        return httpx.Response(200,json=response(body))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider=DecisionModelProvider(client)
            assert provider.family=='systemone'
            return await provider.decide(command,{'summary':'Français et Gedächtnis','topics':['memory'],'evidence':[{'id':'e','snippet':'Original public excerpt'}],'previous':[{'event_id':'old-event','summary':'Prior evidence'}]})
    decision,meta=asyncio.run(run())
    assert decision and meta['status']=='success' and meta['model_identity_verified']
    assert meta['model']=='requested-alias' and meta['response_model']=='approved-backend'
    assert meta['tokens']==82 and meta['output_tokens']==0
    assert decision.evidence_ids==['e'] and meta['ordinal_scores_not_probabilities']
    if command=='same-story':assert decision.related_event_id=='old-event' and decision.verdict=='development'
    assert 'private-test-token' not in json.dumps(meta)


@pytest.mark.parametrize('case',['identity','missing-question','wrong-choice','wrong-probability-keys','probability-sum','bool-probability','nonfinite','negative-usage','extra-answer','wrong-citation'])
def test_native_schema_fails_closed(monkeypatch,case):
    configure(monkeypatch)
    def mutate(value):
        a=value['answers']['decision']
        if case=='identity':value['model']='unapproved'
        if case=='missing-question':value['answers'].pop('citation')
        if case=='wrong-choice':a['choice']='invented'
        if case=='wrong-probability-keys':a['probabilities']['invented']=0
        if case=='probability-sum':a['probabilities']={key:0.0 for key in a['probabilities']}
        if case=='bool-probability':a['confidence']=True
        if case=='nonfinite':a['confidence']=float('nan')
        if case=='negative-usage':value['usage']['input_tokens']=-1
        if case=='extra-answer':value['answers']['invented']=copy.deepcopy(a)
        if case=='wrong-citation':value['answers']['citation']['choice']='invented-evidence'
    def handle(request):return httpx.Response(200,json=response(json.loads(request.content),mutate))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await DecisionModelProvider(client).decide('relevance',{'evidence':[{'id':'e','snippet':'Public evidence'}]})
    decision,meta=asyncio.run(run())
    assert decision is None and meta['status']=='invalid_or_unavailable'


def test_native_abstention_citation_and_event_limits(monkeypatch):
    configure(monkeypatch)
    def handle(request):
        body=json.loads(request.content)
        assert 'event' not in body['questions']
        result=response(body);result['answers']['citation']['action']['act_probability']=0.0
        return httpx.Response(200,json=result)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            provider=DecisionModelProvider(client)
            decision,meta=await provider.decide('same-story',{'evidence':[{'id':'e','snippet':'public'}],'previous':[]})
            assert decision.verdict=='unknown' and decision.related_event_id is None and meta['abstained']
            before=provider.requests
            value,meta=await provider.decide('technical-learning',{'evidence':[{'id':'e','snippet':'public'}]})
            assert value is None and meta['status']=='capability_unavailable' and provider.requests==before
    asyncio.run(run())


def test_native_funding_eligibility_independent(monkeypatch,tmp_path):
    configure(monkeypatch)
    def handle(request):return httpx.Response(200,json=response(json.loads(request.content)))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            store=DurableCheckpointStore(tmp_path/'state.sqlite')
            pipeline=HorizonFilterPipeline(FilterPolicy.load('funding/de-eu'),store,DecisionModelProvider(client))
            finding={'finding_id':'i','event_id':'f','summary':'Public funding fixture','source_ids':['e'],'evidence':[{'source_id':'e','snippet':'public'}]}
            result=await pipeline.run([finding],[{'source_id':'e'}],hard_statuses={'f':'ELIGIBILITY_UNKNOWN'})
            assert result[0]['provider_family']=='systemone' and not result[0]['accepted'] and not result[0]['hard_gate']
            store.close()
    asyncio.run(run())


def test_native_does_not_use_probabilities_as_importance(monkeypatch):
    configure(monkeypatch);scores=[]
    for probability in (.51,.99):
        def handle(request):
            result=response(json.loads(request.content))
            result['answers']['decision']['probabilities']={'high':probability,'medium':1-probability,'low':0.0,'unknown':0.0}
            return httpx.Response(200,json=result)
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
                return await DecisionModelProvider(client).decide('importance',{'evidence':[{'id':'e','snippet':'public'}]})
        decision,_=asyncio.run(run());scores.append(decision.score)
    assert scores==[.9,.9]
