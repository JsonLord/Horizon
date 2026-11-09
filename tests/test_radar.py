"""Radar contract, safety, recovery and original-language regression checks."""
import asyncio
import copy
import hashlib
import json
from datetime import UTC,datetime,timedelta
from pathlib import Path
import httpx
import jsonschema
import pytest
from src.models import ContentItem,SourceType
from src.research.reporting import dumps,atomic
from src.research.filtering.provider import DecisionModelProvider
from src.research.radar.contracts import *
from src.research.radar.pipeline import *
from src.research.radar.storage import *
from src.research.radar.publisher import GitHubData
from scripts.radar_fleet import seal,verify

END=datetime(2026,11,6,18,tzinfo=UTC)


def ref(lang='en',tag='v1'):
    title={'en':'The new mechanism improves training with reproducible results','de':'Die neue Methode für das Training und die Auswertung','fr':'Une méthode pour les agents avec des résultats'}[lang]
    return Reference(id=ident(lang+tag),title=title,language=lang,language_basis='source_metadata',author='Fixture author',publisher='Fixture project',published_at_utc=stamp(END-timedelta(hours=1)),fetched_at_utc=stamp(END),url='https://github.com/example/project/releases/tag/'+tag,excerpt=title+' baseline 10 GPU seconds, new result 8 GPU seconds',content_hash=hashlib.sha256((lang+tag).encode()).hexdigest(),primary=True)


def technical(r):
    return TechnicalDecision(reason='Source-attributed fixture',evidence_ids=[r.id],components=Components(mechanism=2,integration_change=1,reproducibility=1,learning=1,primary_evidence=1),support=[Support(dimension=d,evidence_id=r.id,quote=r.excerpt) for d in ('mechanism','integration_change','reproducibility','learning','primary_evidence')],explanation=r.excerpt,mechanism=r.excerpt,what_is_new=r.excerpt,learning_objective=r.title,prerequisites=['Read the baseline implementation'],uncertainties=[],deeper_research=True)


def finding(r,radar='rag-memory'):
    return TechnicalFinding(id=r.id,radar_id=radar,event_id=event_identity(r.url),references=[r],classification='HIGH_SIGNAL',reason_codes=['fixture_only'],technical=technical(r),significance=7,model='mock-test-only',policy_version='radar-1.0-provisional',shared_decision={'gates':{'claim-support':{'decision':{'verdict':'yes'}}}},provider={'status':'test_fixture'},observed_at_utc=stamp(END))


def state(radar='rag-memory'):
    return State(radar_id=radar,policy_version='radar-1.0-provisional',coverage_start_utc=stamp(END-timedelta(days=7)),last_successful_collection_utc=stamp(END),findings=[finding(ref(lang,'v'+str(i)),radar) for i,lang in enumerate(('en','de','fr'))])


def test_registry_and_profiles():
    entries=registry()['radars']
    assert not registry()['schedule_enabled'] and not registry()['publication_enabled']
    for entry in entries:
        p=load_profiles()[entry['profile_id']]
        assert {q.language for q in p.queries}=={'en','de','fr'}
        assert FilterPolicy.load(p.profile_id).version==entry['policy_version']
        assert set(p.languages)=={'en','de','fr'}
        seeds=json.loads((ROOT/entry['source_registry']).read_text())
        assert seeds['discovery_queries']==[q.model_dump() for q in p.queries]
        assert all(re.fullmatch(r'[\w.-]+/[\w.-]+',r) for r in seeds['primary_repositories'])
        assert not any(k in p.canonical() for k in ('api_key','base_url','model_id'))


@pytest.mark.parametrize('delta,expected',[(timedelta(0),END),(timedelta(seconds=-1),END-timedelta(days=7)),(timedelta(days=2),END),(timedelta(days=7),END+timedelta(days=7))])
def test_friday_window(delta,expected):assert cutoff(END+delta)==expected


def test_utc_and_year_boundary():
    with pytest.raises(ValueError):cutoff(datetime(2026,11,6,18))
    assert week_key(datetime(2027,1,1,18,tzinfo=UTC))=='2026-W53'
    with pytest.raises(ValueError):week_key(END+timedelta(seconds=1))


@pytest.mark.parametrize('radar',RADARS)
def test_three_branch_contracts_schema_and_provenance(tmp_path,radar):
    d=make_digest(state(radar),END,END)
    assert d.status=='complete' and set(d.source_languages)=={'en','de','fr'}
    assert len(d.top_concepts)==3
    assert stage_digest(tmp_path,d)['status']=='published'
    assert validate_tree(tmp_path,radar)
    for name,file in [('radar-digest','weekly-digest.json'),('radar-manifest','radar-manifest.json')]:
        jsonschema.validate(read_json(tmp_path/file),json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text()))
    assert all(r.title in dumps(d.model_dump(mode='json')) for r in d.source_references)
    assert 'own_commit_sha' not in (tmp_path/'radar-manifest.json').read_text()


def test_boundary_exclusive_and_partial_last_good(tmp_path):
    s=state();d=make_digest(s,END,END);stage_digest(tmp_path,d)
    original=(tmp_path/'weekly-digest.json').read_bytes()
    s.findings[0].references[0].published_at_utc=stamp(END)
    s.failed_sources={'unavailable':{'attempts':1}}
    newer=make_digest(s,END+timedelta(days=7),END+timedelta(days=7))
    assert newer.status=='partial' and stage_digest(tmp_path,newer)['writes']==0
    assert (tmp_path/'weekly-digest.json').read_bytes()==original
    assert len(make_digest(s,END,END).top_concepts)==2


def test_idempotency_and_corrections(tmp_path):
    d=make_digest(state(),END,END);stage_digest(tmp_path,d)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    again=d.model_copy(update={'generated_at_utc':stamp(END+timedelta(hours=1))})
    assert stage_digest(tmp_path,again)['writes']==0
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert stage_digest(tmp_path,again,correction='review-001')['status']=='published'
    assert read_json(tmp_path/'weekly'/'2026-W45'/'weekly-digest.json')['generated_at_utc']==stamp(END)
    assert (tmp_path/'weekly/2026-W45/corrections/review-001/correction.json').exists()
    assert validate_tree(tmp_path,'rag-memory')
    conflict=again.model_copy(update={'generated_at_utc':stamp(END+timedelta(hours=2))})
    with pytest.raises(ValueError,match='Immutable correction'):stage_digest(tmp_path,conflict,correction='review-001')


def test_catchup_and_no_older_pointer(tmp_path):
    d=make_digest(state(),END,END);stage_digest(tmp_path,d)
    assert missing_weeks(tmp_path,'rag-memory',END+timedelta(days=22))==[END+timedelta(days=i) for i in (7,14,21)]
    old=d.model_copy(update={'week_start_utc':stamp(END-timedelta(days=14)),'week_end_utc':stamp(END-timedelta(days=7)),'top_concepts':[],'source_references':[],'source_languages':[],'quality':Quality(collection_complete=True,evidence_validated=True,coverage_limitations=['No evidence for this earlier week'],candidate_count=0,confirmed_count=0,review_count=0)})
    assert stage_digest(tmp_path,old)['status']=='historical_only'
    assert read_json(tmp_path/'weekly-digest.json')['week_end_utc']==stamp(END)


def test_rubric_and_citations_fail_closed():
    r=ref();t=technical(r);t.validate_evidence([{'id':r.id,'snippet':r.excerpt,'primary':True}])
    assert t.components.score==7
    with pytest.raises(ValueError):t.validate_evidence([{'id':r.id,'snippet':'unrelated marketing','primary':True}])
    with pytest.raises(ValueError):t.validate_evidence([{'id':r.id,'snippet':r.excerpt,'primary':False}])
    with pytest.raises(ValueError):Components(mechanism=True,integration_change=0,reproducibility=0,learning=0,primary_evidence=0)
    d=make_digest(state(),END,END).model_dump(mode='json');d['top_concepts'][0]['evidence_references']=['invented']
    with pytest.raises(ValueError):Digest.model_validate(d)
    d=make_digest(state(),END,END).model_dump(mode='json');d['quality']['evidence_validated']=False
    with pytest.raises(ValueError):Digest.model_validate(d)


@pytest.mark.parametrize('lang,title', [('de','Die Methode für das Training und die Auswertung'),('fr','Une méthode pour les agents avec des résultats'),('en','The new approach for training with the benchmark')])
def test_original_language_extraction(lang,title):
    item=ContentItem(id='test',source_type=SourceType.RSS,title=title,url='https://example.com/'+lang,content=title,author='Author',published_at=END,metadata={'source_language':lang,'query_language':'en'})
    r=reference(item)
    assert r.language==lang and r.title==title and r.excerpt==title and r.author=='Author'
    assert r.discovery_language=='en' # discovery does not overwrite actual language


def test_unknown_language_not_inferred_from_query():
    item=ContentItem(id='test',source_type=SourceType.GOOGLE_NEWS,title='FSDP v3',url='https://example.com/article',published_at=END,metadata={'query_language':'fr'})
    r=reference(item);assert r.language=='unknown' and r.discovery_language=='fr'


def test_release_event_identity_and_language_duplicates():
    assert event_identity('https://github.com/example/project/releases/tag/v1')!=event_identity('https://github.com/example/project/releases/tag/v2')
    assert event_identity('https://arxiv.org/abs/2611.12345')==event_identity('https://arxiv.org/pdf/2611.12345')
    s=state();s.findings[1].event_id=s.findings[0].event_id
    d=make_digest(s,END,END);assert len(d.top_concepts)==2
    # Separate language evidence remains in original reports; duplicate concept not repeated.
    assert s.findings[1].references[0].language=='de'


def test_checkpoint_integrity_and_narrow_paths(tmp_path):
    stage_digest(tmp_path,make_digest(state(),END,END))
    proof=seal(tmp_path,'rag-memory','source-123')
    assert verify(tmp_path,proof,'rag-memory','source-123')
    with pytest.raises(ValueError):verify(tmp_path,proof,'rag-memory','wrong-source')
    (tmp_path/'.github/workflows').mkdir(parents=True)
    (tmp_path/'.github/workflows/evil.yml').write_text('run: evil')
    with pytest.raises(ValueError):validate_tree(tmp_path,'rag-memory')
    for name in ('../evil','intel/manifest.json','src/main.py','weekly/../../evil','reports/link.py'):assert not allowed_path(name)


def test_model_technical_schema_fallback(monkeypatch):
    for k,v in {'BASE_URL':'https://inference.example.com','MODEL':'fixture-model','API_MODE':'openai_chat','API_KEY':'fixture-private-token'}.items():monkeypatch.setenv('HORIZON_DECISION_'+k,v)
    r=ref();response=technical(r).model_dump(mode='json');calls=[]
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        if 'response_format' in body:return httpx.Response(422)
        return httpx.Response(200,json={'model':'fixture-model','choices':[{'message':{'content':json.dumps(response)}}],'usage':{'total_tokens':123}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await DecisionModelProvider(client).decide('technical-learning',{'evidence':[{'id':r.id,'snippet':r.excerpt,'primary':True}]})
    result,meta=asyncio.run(run())
    assert result and meta['format']=='validated_json' and meta['tokens']==123 and len(calls)==2
    nested=calls[0]['response_format']['json_schema']['schema']['$defs']['Components']
    assert set(nested['required'])==set(nested['properties'])


def test_collection_failure_isolation_and_retry(tmp_path):
    item=ContentItem(id='test',source_type=SourceType.RSS,title='Die Methode für das Training und die Auswertung',url='https://example.com/post',content='Die Methode für das Training und die Auswertung ist ein neuer Ansatz.',published_at=END-timedelta(hours=1),metadata={'source_language':'de'})
    s,metrics=asyncio.run(run_collection('rag-memory',tmp_path,END,items=[item],metrics=[{'source':'failed-feed','status':'failed'},{'source':'google_news','query':'de','status':'ok'}],source_revision='fixture'))
    assert s.failed_sources['failed-feed']['attempts']==1
    assert s.last_successful_collection_utc is None
    assert s.findings[0].classification=='RESEARCH_REQUIRED'
    assert s.findings[0].significance==1 and s.findings[0].references[0].language=='de'
    assert validate_tree(tmp_path,'rag-memory')
    prior=seal(tmp_path,'rag-memory','fixture')
    s2,_=asyncio.run(run_collection('rag-memory',tmp_path,END+timedelta(hours=12),items=[],metrics=[{'source':'failed-feed','status':'ok'}],source_revision='fixture'))
    assert not s2.failed_sources and len(s2.findings)==1 and s2.last_successful_collection_utc
    assert verify(tmp_path,seal(tmp_path,'rag-memory','fixture'),'rag-memory','fixture')
    with pytest.raises(ValueError):verify(tmp_path,prior,'rag-memory','fixture')


def test_read_only_consumer_pins_all_reads(tmp_path):
    stage_digest(tmp_path,make_digest(state(),END,END))
    files={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    import base64
    requests=[]
    def handle(request):
        requests.append(request)
        assert request.method=='GET'
        if '/git/ref/' in request.url.path:return httpx.Response(200,json={'object':{'sha':'pinned-commit'}})
        if '/git/trees/' in request.url.path:
            assert request.url.path.endswith('pinned-commit')
            return httpx.Response(200,json={'tree':[{'path':name,'mode':'100644','type':'blob','sha':str(i),'size':len(data)} for i,(name,data) in enumerate(files.items())]})
        data=list(files.values())[int(request.url.path.rsplit('/',1)[1])]
        return httpx.Response(200,json={'content':base64.b64encode(data).decode()})
    client=httpx.Client(base_url='https://api.github.com',transport=httpx.MockTransport(handle))
    dest=tmp_path/'consumer'
    assert GitHubData(token='read-only-test',client=client).read('rag-memory',dest)=='pinned-commit'
    assert read_json(dest/'weekly-digest.json')==read_json(dest/'weekly/2026-W45/weekly-digest.json')
    with pytest.raises(ValueError):GitHubData(client=client).publish('rag-memory',dest)
    with pytest.raises(ValueError):GitHubData(client=client).read('intel',dest)


def test_publisher_data_only_idempotency_history_conflicts(tmp_path):
    import shutil
    root=tmp_path/'incoming';remote=tmp_path/'remote'
    stage_digest(root,make_digest(state(),END,END));shutil.copytree(root,remote)
    class FakeGitHub(GitHubData):
        def __init__(self):self.calls=[];self.blobs={};self.tree=[];self.head='commit-one'
        def read(self,radar,dest):
            for p in remote.rglob('*'):
                if p.is_file():
                    target=Path(dest)/p.relative_to(remote);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
            return self.head
        def api(self,method,path,**kw):
            self.calls.append((method,path,kw))
            if method=='GET' and path.startswith('git/commits/'):return {'tree':{'sha':'actual-base-tree'}}
            if path=='git/blobs':
                import base64
                sha=str(len(self.blobs));self.blobs[sha]=base64.b64decode(kw['json']['content']);return {'sha':sha}
            if path=='git/trees':self.tree=kw['json']['tree'];return {'sha':'new-tree'}
            if path=='git/commits':return {'sha':'commit-two'}
            assert method=='PATCH' and path=='git/refs/heads/radar/rag-memory' and kw['json']['force'] is False
            for entry in self.tree:
                dest=remote/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(self.blobs[entry['sha']])
            self.head='commit-two';return {'object':{'sha':self.head}}
    api=FakeGitHub()
    assert api._publish_validated('rag-memory',root)['writes']==0 and not api.calls
    atomic(root/'README.md','# New public data description\n')
    assert api._publish_validated('rag-memory',root)['commit']=='commit-two'
    count=len(api.calls)
    assert api._publish_validated('rag-memory',root)['writes']==0 and len(api.calls)==count
    assert all('intel' not in path for _,path,_ in api.calls)
    corrupted=read_json(root/'weekly/2026-W45/weekly-digest.json');corrupted['quality']['coverage_limitations'].append('unauthorized mutation')
    atomic(root/'weekly/2026-W45/weekly-digest.json',dumps(corrupted))
    atomic(root/'weekly-digest.json',dumps(corrupted))
    with pytest.raises(ValueError,match='Immutable history|traceable correction'):api._publish_validated('rag-memory',root)


def test_technical_budget_reserved_and_public_model_distillation(tmp_path):
    from src.research.filtering.provider import Decision
    class FixtureProvider:
        configured=True;model='fixture-not-live';family='openai_chat'
        def __init__(self):self.commands=[]
        def identity(self):return 'fixture'
        async def decide(self,command,payload):
            self.commands.append(command)
            if command=='technical-learning':
                e=payload['evidence'][0]
                r=ref().model_copy(update={'id':e['id'],'excerpt':e['snippet']})
                d=technical(r)
            else:d=Decision(score=.9,verdict='different' if command=='same-story' else 'yes',reason='Fixture only',evidence_ids=[e['id'] for e in payload['evidence']],hype=.1,facts=.9,signal=.9)
            return d,{'family':'openai_chat','model':self.model,'status':'success','attempts':1,'tokens':100}
    provider=FixtureProvider()
    items=[ContentItem(id='fixture'+str(i),source_type=SourceType.GITHUB,title=ref().title+str(i),url='https://github.com/example/project/releases/tag/v'+str(i),content=ref().excerpt,author='Fixture',published_at=END-timedelta(hours=1),metadata={'source_language':'en','registered_primary':True}) for i in range(3)]
    s,_=asyncio.run(run_collection('rag-memory',tmp_path,END,items=items,metrics=[{'source':'fixture','status':'ok'}],provider=provider,source_revision='test'))
    assert 'technical-learning' in provider.commands and len(provider.commands)<=36
    assert sum(f.classification=='HIGH_SIGNAL' for f in s.findings)==1
    assert validate_tree(tmp_path,'rag-memory')
    # An unchanged, successfully classified source is not sent back to inference.
    before=len(provider.commands)
    asyncio.run(run_collection('rag-memory',tmp_path,END+timedelta(hours=1),items=items[:1],metrics=[{'source':'fixture','status':'ok'}],provider=provider,source_revision='test'))
    assert len(provider.commands)==before
    asyncio.run(run_collection('rag-memory',tmp_path,END+timedelta(hours=2),items=items[:1],metrics=[{'source':'fixture','status':'ok'}],provider=provider,source_revision='docs-only-new-commit'))
    assert len(provider.commands)==before


def test_code_pattern_is_original_attributed_and_citation_validated():
    s=state();f=s.findings[0];r=f.references[0]
    pattern=Pattern(title='Fixture pattern',problem='Inspect the baseline',mechanism=f.technical.mechanism,example='for shard in shards: aggregate(shard)',example_kind='original_pseudocode',evidence_references=[r.id],documentation_url=r.url,prerequisites=['Baseline implementation'],limitations=['Original explanatory pseudocode; not benchmarked or copied source code.'])
    f.technical.code_patterns=[pattern]
    f.technical.validate_evidence([{'id':r.id,'snippet':r.excerpt,'primary':True,'url':r.url}])
    digest=make_digest(s,END,END)
    assert len(digest.code_patterns)==1
    pattern.documentation_url='https://example.com/invented'
    with pytest.raises(ValueError,match='Invented pattern URL'):f.technical.validate_evidence([{'id':r.id,'snippet':r.excerpt,'primary':True,'url':r.url}])


def test_unreviewed_benchmark_has_no_fabricated_quality(tmp_path):
    from scripts.benchmark_radar import benchmark
    result=benchmark(tmp_path)
    assert not result['reviewed_ground_truth']
    assert all(v is None for group in result['groups'] for v in group['metrics'].values())
    with pytest.raises(ValueError):benchmark(tmp_path,{'reviewer':'reviewer','reviewed_at_utc':stamp(END),'cases':{'invented':{}}})


def test_shared_qualification_checks_revision_policy_and_both_caches(tmp_path,monkeypatch):
    from scripts.shared_filtering import qualify
    monkeypatch.delenv('HORIZON_DECISION_BASE_URL',raising=False)
    monkeypatch.delenv('HORIZON_DECISION_MODEL',raising=False)
    asyncio.run(qualify(tmp_path))
    proof=read_json(tmp_path/'proof.json')
    assert len(proof['command_qualification'])==18 and not proof['all_commands_live_validated']
    asyncio.run(qualify(tmp_path,restore=True))
    manifest=read_json(tmp_path/'manifest.json');manifest['source_revision']='unreviewed-source'
    atomic(tmp_path/'manifest.json',dumps(manifest))
    with pytest.raises(ValueError,match='Source revision'):asyncio.run(qualify(tmp_path,restore=True))


def test_public_reader_does_not_send_blank_bearer_header(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN',raising=False)
    api=GitHubData()
    assert 'Authorization' not in api.client.headers
    api.client.close()


def test_canonical_doi_and_arxiv_pdf_versions():
    assert event_identity('https://doi.org/10.12345/ABC')==event_identity('https://example.org/doi/full/10.12345/abc')
    assert event_identity('https://arxiv.org/abs/2611.12345')==event_identity('https://arxiv.org/pdf/2611.12345.pdf')
    assert event_identity('https://arxiv.org/abs/2611.12345v1')!=event_identity('https://arxiv.org/abs/2611.12345v2')
