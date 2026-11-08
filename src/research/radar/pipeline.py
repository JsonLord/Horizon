"""Conservative multilingual technical evidence, scoring and digest assembly."""
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from bs4 import BeautifulSoup
from pydantic import Field, model_validator
from ..profiles import ROOT, Strict, load_profiles
from ..analyzers import canonical, ident
from ..reporting import atomic, dumps
from ..filtering.engine import FilterPolicy, HorizonFilterPipeline, DurableCheckpointStore
from ..filtering.provider import DecisionModelProvider
from .contracts import Components, Concept, Digest, Pattern, Quality, Reference, RADARS, cutoff, stamp, utc
from .storage import load_manifest, read_json

CATEGORIES=('HIGH_SIGNAL','RESEARCH_REQUIRED','WATCHLIST','REDUNDANT_COVERAGE','LOW_PRIORITY','INSUFFICIENT_EVIDENCE')


class Support(Strict):
    dimension: Literal['mechanism','integration_change','reproducibility','learning','primary_evidence']
    evidence_id: str
    quote: str = Field(min_length=1,max_length=300)


class TechnicalDecision(Strict):
    reason: str = Field(max_length=500)
    evidence_ids: list[str] = Field(max_length=20)
    components: Components
    support: list[Support] = Field(max_length=10)
    explanation: str = Field(min_length=1,max_length=500)
    mechanism: str = Field(max_length=500)
    what_is_new: str = Field(max_length=500)
    learning_objective: str = Field(max_length=500)
    prerequisites: list[str] = Field(max_length=10)
    uncertainties: list[str] = Field(max_length=10)
    deeper_research: bool
    code_patterns: list[Pattern] = Field(default_factory=list,max_length=1)
    def validate_evidence(self,evidence):
        refs={e['id']:e for e in evidence}
        dimensions=set()
        for pattern in self.code_patterns:
            if not set(pattern.evidence_references)<=refs.keys():raise ValueError('Unknown pattern citation')
            if pattern.documentation_url not in {e.get('url') for e in refs.values()}:raise ValueError('Invented pattern URL')
            if pattern.mechanism!=self.mechanism:raise ValueError('Unreviewed pattern mechanism')
            if pattern.example_kind=='attributed_excerpt' and not any(pattern.example in e['snippet'] for e in refs.values()):raise ValueError('Unsupported code excerpt')
        for s in self.support:
            e=refs.get(s.evidence_id)
            if not e or s.quote not in e['snippet']:raise ValueError('Unsupported rubric quote')
            if s.dimension=='primary_evidence' and not e.get('primary'):raise ValueError('Not primary evidence')
            dimensions.add(s.dimension)
        for name,value in self.components.model_dump().items():
            if value and name not in dimensions:raise ValueError('Uncited rubric dimension')
        if not self.evidence_ids or not set(self.evidence_ids)<=refs.keys():raise ValueError('Unknown technical citation')
        # A benchmark score requires measured context, not a promise of speed.
        if self.components.reproducibility and not any(re.search(r'\d',s.quote) for s in self.support if s.dimension=='reproducibility'):
            raise ValueError('Missing measured result')


class TechnicalFinding(Strict):
    id: str = Field(pattern=r'^[a-f0-9]{24}$')
    radar_id: Literal['agent-control-planes','distributed-training','rag-memory']
    event_id: str = Field(pattern=r'^[a-f0-9]{24}$')
    references: list[Reference] = Field(min_length=1,max_length=20)
    classification: Literal['HIGH_SIGNAL','RESEARCH_REQUIRED','WATCHLIST','REDUNDANT_COVERAGE','LOW_PRIORITY','INSUFFICIENT_EVIDENCE']
    reason_codes: list[str] = Field(max_length=20)
    technical: TechnicalDecision | None = None
    significance: int = Field(ge=1,le=10)
    model: str | None = None
    policy_version: str
    shared_decision: dict
    provider: dict
    observed_at_utc: str
    @model_validator(mode='after')
    def supported(self):
        if self.technical:
            self.technical.validate_evidence([{'id':r.id,'snippet':r.excerpt,'primary':r.primary,'url':r.url} for r in self.references])
        if self.significance!=(self.technical.components.score if self.technical else 1):raise ValueError('Significance mismatch')
        if self.classification=='HIGH_SIGNAL':
            support=self.shared_decision.get('gates',{}).get('claim-support',{}).get('decision')
            if not self.technical or not any(r.primary and r.language!='unknown' for r in self.references) or not support or support['verdict']!='yes':raise ValueError('Unverified technical concept')
        return self


class State(Strict):
    schema_version: Literal['1.0']='1.0'
    radar_id: Literal['agent-control-planes','distributed-training','rag-memory']
    policy_version: str
    source_revision: str | None = None
    decision_identity: str | None = None
    coverage_start_utc: str | None = None
    last_attempted_collection_utc: str | None = None
    last_successful_collection_utc: str | None = None
    next_eligible_collection_utc: str | None = None
    source_freshness: dict[str,str] = Field(default_factory=dict)
    failed_sources: dict[str,dict] = Field(default_factory=dict)
    collection_backlog: int = Field(default=0,ge=0)
    processed: dict[str,str] = Field(default_factory=dict)
    findings: list[TechnicalFinding] = Field(default_factory=list,max_length=500)
    checkpoint: list[dict] = Field(default_factory=list,max_length=2000)


def registry():
    data=json.loads((ROOT/'config/radar/registry.json').read_text())
    entries=data['radars']
    if {e['radar_id'] for e in entries}!=set(RADARS) or len(entries)!=3:raise ValueError('Invalid radar registry')
    for e in entries:
        if e['branch']!='radar/'+e['radar_id'] or e['source_registry']!='config/radar/sources/'+e['radar_id']+'.json':raise ValueError('Unsafe registry')
        if not 1<=e['max_candidates']<=30 or not 0<=e['max_model_requests']<=120 or not 0<=e['max_model_tokens']<=200000:raise ValueError('Unbounded radar')
    return data


def language(text, declared=None):
    if declared in ('en','de','fr'):return declared,'source_metadata'
    # Query language is deliberately excluded. Low confidence remains unknown.
    tokens=set(re.findall(r'\w+',text.lower()))
    markers={'en':{'the','with','and','for','from','this','training'},'de':{'die','der','das','und','für','mit','eine'},'fr':{'les','une','des','pour','avec','dans','sur'}}
    scores=sorted(((len(tokens & words),lang) for lang,words in markers.items()),reverse=True)
    if scores[0][0]>=3 and scores[0][0]>scores[1][0]:return scores[0][1],'lexical_heuristic_requires_review'
    return 'unknown','insufficient_language_evidence'


def event_identity(url):
    # Versions/tags remain part of the identity. Same repository is not same event.
    match=re.search(r'arxiv\.org/(?:abs|pdf)/([\d.]+(?:v\d+)?)',url)
    return ident('arxiv:'+match[1]) if match else ident(canonical(url))


def reference(item):
    title=BeautifulSoup(item.title,'html.parser').get_text(' ',strip=True)[:500]
    text=BeautifulSoup(item.content or item.title,'html.parser').get_text(' ',strip=True)
    # Short attributed quotation only; never store full release/page bodies.
    excerpt=' '.join(text.split()[:55])[:500]
    lang,basis=language(title+' '+excerpt,item.metadata.get('source_language'))
    url=canonical(str(item.url))
    return Reference(id=ident(url+'|'+title),title=title,language=lang,discovery_language=item.metadata.get('query_language','unknown') if item.metadata.get('query_language') in ('en','de','fr') else 'unknown',language_basis=basis,author=item.author,publisher=str(item.metadata.get('source_name') or item.metadata.get('repository') or 'unknown')[:200],published_at_utc=stamp(item.published_at),fetched_at_utc=stamp(item.fetched_at),url=url,excerpt=excerpt or title,content_hash=hashlib.sha256((title+'|'+text).encode()).hexdigest(),primary=bool(item.metadata.get('registered_primary')))


def prefilter(ref):
    if len(ref.excerpt)<35:return 'insufficient_content'
    # Only explicitly maintenance-only titles are excluded; uncertain patch bumps
    # are reviewed rather than rejected based on a version number alone.
    if re.search(r'^(chore|dependencies only|bump dependencies)[: ]',ref.title,re.I):return 'maintenance_only'
    return None


async def collect_items(entry, profile, client=None):
    from ..collector import collect,BoundedClient
    from src.models import ContentItem,SourceType
    items,metrics=await collect(profile,client=client)
    seeds=json.loads((ROOT/entry['source_registry']).read_text())
    own=client is None
    client=client or BoundedClient(timeout=20,headers={'User-Agent':'Horizon technical radar'})
    # Registered fixed GitHub API source only; no token needed, no arbitrary targets.
    client.trusted_hosts=getattr(client,'trusted_hosts',frozenset()) | {'api.github.com'}
    try:
        for repo in seeds['primary_repositories']:
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('Invalid repository seed')
            try:
                response=await client.get('https://api.github.com/repos/'+repo+'/releases',params={'per_page':10})
                releases=response.json()
                if not isinstance(releases,list):raise ValueError('Invalid release payload')
                for release in releases[:10]:
                    if release.get('draft') or not release.get('published_at'):continue
                    published=utc(release['published_at'])
                    if not datetime.now(UTC)-timedelta(hours=profile.lookback_hours)<=published<=datetime.now(UTC):continue
                    items.append(ContentItem(id='github:release:'+str(release['id']),source_type=SourceType.GITHUB,title=release.get('name') or release['tag_name'],url=release['html_url'],content=release.get('body') or release['tag_name'],author=(release.get('author') or {}).get('login'),published_at=published,metadata={'registered_primary':True,'repository':repo}))
                metrics.append({'source':'github:'+repo,'status':'ok','items':len(releases)})
            except Exception:
                metrics.append({'source':'github:'+repo,'status':'failed','items':0})
    finally:
        if own:await client.aclose()
    return items,metrics


async def run_collection(radar, root, now=None, items=None, metrics=None, provider=None, source_revision=None):
    now=utc(now or datetime.now(UTC));root=Path(root)
    entry=next(e for e in registry()['radars'] if e['radar_id']==radar)
    state=State.model_validate(read_json(root/'radar-state.json')) if (root/'radar-state.json').exists() else State(radar_id=radar,policy_version=entry['policy_version'])
    if state.radar_id!=radar:raise ValueError('Cross-radar checkpoint')
    profile=load_profiles()[entry['profile_id']]
    if items is None:
        if state.next_eligible_collection_utc and now<utc(state.next_eligible_collection_utc):return state,[{'source':'scheduler','status':'not_due'}]
        items,metrics=await collect_items(entry,profile)
    metrics=metrics or []
    refs={}
    for item in items:
        try:
            ref=reference(item)
            if utc(ref.published_at_utc)>now or utc(ref.published_at_utc)<now-timedelta(days=7):continue
            refs[ref.id]=ref
        except (ValueError,TypeError):continue
    # Fair language round-robin under a single bounded candidate budget.
    buckets={l:[r for r in refs.values() if r.discovery_language==l or (r.discovery_language=='unknown' and r.language==l)] for l in ('en','de','fr')}
    ordered=[]
    for i in range(max((len(v) for v in buckets.values()),default=0)):
        for values in buckets.values():
            if i<len(values):ordered.append(values[i])
    ordered += [r for r in refs.values() if r not in ordered]
    provider=provider or DecisionModelProvider()
    if state.decision_identity!=provider.identity() or state.policy_version!=entry['policy_version'] or state.source_revision!=source_revision:
        state.processed={};state.checkpoint=[]
    pending=[r for r in ordered if state.processed.get(r.id)!=r.content_hash]
    selected=pending[:entry['max_candidates']];state.collection_backlog=max(0,len(pending)-len(selected))
    store=DurableCheckpointStore(root/'.working-filter.sqlite')
    # Portable JSON checkpoint only. Never load or execute branch-supplied Python,
    # pickle or SQLite. Cache rows are bounded and policy/model-keyed by shared engine.
    if state.source_revision==source_revision and state.policy_version==entry['policy_version']:
        for row in state.checkpoint:
            if set(row)=={'kind','key','value'} and row['kind'] in ('decision','completed','history'):
                store.put(row['kind'],row['key'],row['value'])
    policy=FilterPolicy.load(entry['profile_id'])
    # Reserve distillation + independent claim-support capacity before the shared
    # gates spend the entire per-radar budget. Overflow candidates stay in review.
    policy=policy.model_copy(update={'max_requests':max(0,entry['max_model_requests']-6),'max_tokens':max(0,entry['max_model_tokens']-66000)})
    eligible=[r for r in selected if not prefilter(r) and not any(f.id!=r.id and any(pr.content_hash==r.content_hash for pr in f.references) for f in state.findings)]
    shared_items=[{'finding_id':r.id,'event_id':event_identity(r.url),'summary':r.title,'source_ids':[r.id],'evidence':[{'source_id':r.id,'snippet':r.excerpt}]} for r in eligible]
    previous=[{'event_id':f.event_id,'summary':f.references[0].title} for f in state.findings[-30:] if f.technical]
    decisions=await HorizonFilterPipeline(policy,store,provider).run(shared_items,[{'source_id':r.id,'content_fingerprint':r.content_hash} for r in selected],previous=previous)
    byid={d['item_id']:d for d in decisions}
    # Shared filtering reserves conservatively. Remaining technical budget assumes
    # all six decisions made three attempts, not just actual successful requests.
    reserved_calls=sum(3 for d in decisions for g in d['gates'].values() if g['provider'].get('attempts',0)>0 and not d.get('cache_hit'))
    reserved_tokens=reserved_calls*6500
    existing={f.id:f for f in state.findings}
    for ref in selected:
        d=byid.get(ref.id,{'event_id':event_identity(ref.url),'gates':{},'novelty':'new','accepted':False});reason=prefilter(ref);technical=None;meta={'status':'deterministic_fallback','tokens':None,'cost':None}
        duplicate=next((f for f in existing.values() if f.id!=ref.id and any(r.content_hash==ref.content_hash for r in f.references)),None)
        category='INSUFFICIENT_EVIDENCE' if reason=='insufficient_content' else 'LOW_PRIORITY' if reason else 'RESEARCH_REQUIRED'
        codes=[reason] if reason else ['technical_evidence_requires_review']
        event=d['event_id']
        if duplicate or d['novelty']=='coverage':
            category='REDUNDANT_COVERAGE';codes=['duplicate_coverage'];event=duplicate.event_id if duplicate else event
        elif not reason and provider.configured and reserved_calls+6<=entry['max_model_requests'] and reserved_tokens+66000<=entry['max_model_tokens']:
            reserved_calls+=6;reserved_tokens+=66000
            technical,meta=await provider.decide('technical-learning',{'summary':ref.title,'source_language':ref.language,'topics':profile.topics,'rubric':{'baseline':1,'mechanism':'0-3','integration_change':'0-2','reproducibility':'0-2','learning':'0-1','primary_evidence':'0-1'},'evidence':[{'id':ref.id,'snippet':ref.excerpt,'primary':ref.primary,'url':ref.url}]})
            support=d['gates']['claim-support']['decision']
            technical_support=None
            if technical:
                technical_support,support_meta=await provider.decide('claim-support',{'summary':(' '.join([technical.explanation,technical.mechanism,technical.what_is_new,technical.learning_objective]))[:2000],'evidence':[{'id':ref.id,'snippet':ref.excerpt}]})
                meta['distillation_support']=support_meta
            if technical and technical.components.score>=6 and ref.primary and ref.language in ('en','de','fr') and ref.language_basis=='source_metadata' and technical_support and technical_support.verdict=='yes' and support and support['verdict']=='yes' and d['accepted'] and not technical.uncertainties:
                category='HIGH_SIGNAL';codes=['primary_supported_technical_learning']
            elif technical and technical.deeper_research:category='RESEARCH_REQUIRED'
            elif technical:category='WATCHLIST'
        if ref.language=='unknown':codes.append('language_requires_review')
        finding=TechnicalFinding(id=ref.id,radar_id=radar,event_id=event,references=[ref],classification=category,reason_codes=codes,technical=technical,significance=technical.components.score if technical else 1,model=meta.get('model') if technical else None,policy_version=entry['policy_version'],shared_decision=d,provider=meta,observed_at_utc=stamp(now))
        existing[ref.id]=finding
        # Failed/uncertain inference remains retryable; deterministic exact duplicate
        # screening retains unchanged successful decisions without new model calls.
        if technical or category in ('REDUNDANT_COVERAGE','LOW_PRIORITY'):state.processed[ref.id]=ref.content_hash
    state.findings=sorted(existing.values(),key=lambda f:f.observed_at_utc)[-80:]
    state.processed={k:v for k,v in state.processed.items() if k in {f.id for f in state.findings}}
    rows=store.db.execute('SELECT kind,key,value FROM state ORDER BY rowid DESC LIMIT 2000').fetchall()
    state.checkpoint=[];checkpoint_bytes=0
    for k,key,v in rows:
        checkpoint_bytes+=len(v.encode())
        if checkpoint_bytes>150000:break
        state.checkpoint.append({'kind':k,'key':key,'value':json.loads(v)})
    store.close();(root/'.working-filter.sqlite').unlink(missing_ok=True)
    state.last_attempted_collection_utc=stamp(now);state.next_eligible_collection_utc=stamp(now+timedelta(hours=12))
    complete=bool(metrics) and all(m['status']=='ok' for m in metrics)
    for m in metrics:
        key=m.get('query') or m['source']
        if m['status']=='ok':state.source_freshness[key]=stamp(now);state.failed_sources.pop(key,None)
        else:state.failed_sources[key]={'attempts':min(10,state.failed_sources.get(key,{}).get('attempts',0)+1),'last_attempt_utc':stamp(now),'next_retry_utc':stamp(now+timedelta(hours=12))}
    if complete:
        since=now-timedelta(days=7)
        if not state.coverage_start_utc or not state.last_successful_collection_utc or utc(state.last_successful_collection_utc)<since:state.coverage_start_utc=stamp(since)
        state.last_successful_collection_utc=stamp(now)
    state.policy_version=entry['policy_version'];state.source_revision=source_revision;state.decision_identity=provider.identity()
    atomic(root/'radar-state.json',dumps(state.model_dump(mode='json')))
    manifest=load_manifest(root,radar);manifest.last_successful_collection_utc=state.last_successful_collection_utc
    atomic(root/'radar-manifest.json',dumps(manifest.model_dump(mode='json')))
    for f in state.findings:
        report_id=ident(dumps(f.model_dump(mode='json')))
        atomic(root/'reports'/f'{report_id}.json',dumps(f.model_dump(mode='json')))
        atomic(root/'reports'/f'{report_id}.md',render_finding(f))
    return state,metrics


def render_finding(f):
    r=f.references[0];t=f.technical
    body=f'# {r.title}\n\nLanguage: {r.language} ({r.language_basis})\nPublication: {r.published_at_utc}\nRadar: {f.radar_id}\nArchitectural significance: {f.significance}/10 (heuristic)\nStatus: {f.classification}\n\n'
    for label,value in [('What changed?',t.what_is_new if t else r.excerpt),('Why does it matter?',t.reason if t else 'Requires technical review.'),('Underlying mechanism',t.mechanism if t else 'Not verified.'),('Evidence and benchmarks','Only quoted source claims; no independent reproduction.'),('Relevant implementation pattern','No verified code pattern extracted.'),('Limitations and open questions','; '.join(t.uncertainties) if t else '; '.join(f.reason_codes)),('Prerequisites to understand it','; '.join(t.prerequisites) if t else 'Not established.'),('Related previous findings',f.event_id)]:
        body+=f'## {label}\n\n{value}\n\n'
    body+='## Original sources and references\n\n'
    for r in f.references:body+=f'- [{r.title}]({r.url}) — {r.publisher}, author {r.author or "unknown"}, {r.language}; `{r.id}`\n\n> {r.excerpt}\n\n'
    return body


def make_digest(state,end,now=None,root=None):
    end=utc(end);now=utc(now or datetime.now(UTC));start=end-timedelta(days=7)
    history={f.id:f for f in state.findings}
    if root:
        for p in (Path(root)/'reports').glob('*.json'):
            f=TechnicalFinding.model_validate(read_json(p))
            if f.id not in history or f.observed_at_utc>history[f.id].observed_at_utc:history[f.id]=f
    candidates=[f for f in history.values() if start<=utc(f.references[0].published_at_utc)<end]
    confirmed=sorted((f for f in candidates if f.classification=='HIGH_SIGNAL' and f.policy_version==state.policy_version),key=lambda f:(-f.significance,f.id))
    selected=[];seen=set()
    for f in confirmed:
        if f.event_id not in seen:selected.append(f);seen.add(f.event_id)
        if len(selected)==5:break
    concepts=[];references={};prerequisites=[];patterns=[]
    for f in selected:
        r=f.references[0];t=f.technical
        related_refs={ref.id:ref for related in candidates if related.event_id==f.event_id for ref in related.references if start<=utc(ref.published_at_utc)<end}
        concepts.append(Concept(event_id=f.event_id,title=r.title,original_source_language=r.language,technical_explanation=t.explanation,architectural_significance=f.significance,score_components=t.components,what_is_new=t.what_is_new,evidence_references=list(related_refs),learning_objective=t.learning_objective,uncertainties=t.uncertainties,model=f.model,policy_version=f.policy_version))
        references.update(related_refs)
        patterns.extend(t.code_patterns)
        for p in t.prerequisites:
            if p not in prerequisites:prerequisites.append(p)
    limitations=[]
    if len(selected)<3:limitations.append('Insufficient verified evidence for 3–5 strong concepts; no entries invented.')
    if not candidates:limitations.append('No collected candidates within the intended weekly window.')
    languages={r.language for r in references.values()}
    for lang in ('en','de','fr'):
        if lang not in languages:limitations.append('No confirmed '+lang+' concept in this window.')
    # Successful source requests alone do not prove full historical coverage.
    success=state.last_successful_collection_utc
    complete=bool(state.coverage_start_utc and utc(state.coverage_start_utc)<=start and success and utc(success)>=end and utc(success)<=end+timedelta(days=7) and not state.failed_sources and not state.collection_backlog)
    if not complete:limitations.append('Collection coverage incomplete or weekly recovery evidence unavailable; retain previous latest digest.')
    if not patterns:limitations.append('No evidence-supported code pattern available; none invented.')
    return Digest(radar_id=state.radar_id,week_start_utc=stamp(start),week_end_utc=stamp(end),generated_at_utc=stamp(now),policy_version=state.policy_version,source_languages=sorted(languages),source_references=list(references.values()),top_concepts=concepts,code_patterns=patterns,suggested_prerequisites=prerequisites[:30],quality=Quality(collection_complete=complete,evidence_validated=True,coverage_limitations=limitations,candidate_count=len(candidates),confirmed_count=len(concepts),review_count=sum(f.classification in ('RESEARCH_REQUIRED','INSUFFICIENT_EVIDENCE') for f in candidates),metrics={name:None for name in ('precision_at_10','high_significance_recall','duplicate_suppression','new_development_recall','cross_language_accuracy','evidence_support_rate','model_cost_per_accepted')}),status='complete' if complete else 'partial')
