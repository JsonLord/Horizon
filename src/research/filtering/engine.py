import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import UTC,datetime

from pydantic import Field,model_validator
from ..profiles import ROOT,Strict
from ..reporting import dumps
from .provider import DecisionModelProvider,COMMANDS

class FilterPolicy(Strict):
    version: str
    profile_id: str
    topics: list[str]
    exclusions: list[str]
    weights: dict[str,float]
    concurrency: int=Field(default=1,ge=1,le=4)
    threshold: float=Field(ge=0,le=1)
    max_requests: int=Field(ge=0,le=120)
    max_tokens: int=Field(ge=0,le=100000)
    @model_validator(mode='after')
    def valid_weights(self):
        if set(self.weights)!={'relevance','novelty','importance','actionability','evidence'} or abs(sum(self.weights.values())-1)>1e-8 or any(v<0 for v in self.weights.values()):raise ValueError('Invalid weights')
        return self
    @classmethod
    def load(cls,profile):
        binding=json.loads((ROOT/'config/filtering/bindings.json').read_text())
        name=binding.get(profile,'world-radar' if profile.startswith(('world/','institutions/')) else None)
        if not name:return None
        base=json.loads((ROOT/'config/filtering/defaults.yaml').read_text())
        base.update(json.loads((ROOT/f'config/filtering/policies/{name}.yaml').read_text()))
        return cls.model_validate({**base,'profile_id':profile})

class DurableCheckpointStore:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (kind TEXT, key TEXT, value TEXT, PRIMARY KEY(kind,key))');self.db.commit()
    def get(self,kind,key):
        row=self.db.execute('SELECT value FROM state WHERE kind=? AND key=?',(kind,key)).fetchone()
        return json.loads(row[0]) if row else None
    def put(self,kind,key,value):
        with self.db:self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?,?)',(kind,key,dumps(value)))
    def snapshot(self,target):
        with sqlite3.connect(target) as dest:self.db.backup(dest)
    def close(self):self.db.close()

DecisionCache=DurableCheckpointStore
class FeedbackStore:
    def __init__(self,state):self.state=state
    def add(self,profile,item,command,reason,topics=(),sources=()):
        if command not in ('more_like_this','less_like_this','important_but_not_actionable'):raise ValueError('Invalid feedback')
        key=profile+'|'+item
        events=self.state.get('feedback',key) or []
        events.append({'command':command,'reason':reason[:500],'at':datetime.now(UTC).isoformat()});self.state.put('feedback',key,events[-100:])
        taste=self.state.get('taste',profile) or {'topics':{},'sources':{}}
        delta=.025 if command=='more_like_this' else -.025 if command=='less_like_this' else 0
        for category,names in [('topics',topics),('sources',sources)]:
            for name in list(names)[:20]:
                name=str(name)[:120];taste[category][name]=max(-.1,min(.1,taste[category].get(name,0)+delta))
        self.state.put('taste',profile,taste)
        record=self.state.get('history',profile+'|'+item)
        if record and record.get('public_summary'):
            examples=self.state.get('examples',profile) or []
            examples.append({'summary':record['public_summary'],'feedback':command})
            self.state.put('examples',profile,examples[-5:])
    def adjustment(self,profile,item):
        events=self.state.get('feedback',profile+'|'+item) or []
        return max(-.1,min(.1,sum(.025 if e['command']=='more_like_this' else -.025 if e['command']=='less_like_this' else 0 for e in events)))

class DeterministicGate:
    def run(self,item,policy):
        text=item.get('summary','').lower()
        return bool(item.get('source_ids')) and not any(x.lower() in text for x in policy.exclusions)
class SemanticGate:
    async def run(self,provider,payload):return await provider.decide(self.command,payload)
class SemanticRelevanceGate(SemanticGate):command='relevance'
class ActionabilityGate(SemanticGate):command='worth-attention'
class SameStoryGate(SemanticGate):command='same-story'
class ClaimSupportGate(SemanticGate):command='claim-support'
class ImportanceGate(SemanticGate):command='importance'
class HFSGate(SemanticGate):command='hfs'
class NoveltyGate:
    def run(self,item,previous):
        same=[p for p in previous if p.get('event_id')==item.get('event_id')]
        if not same:return 'new'
        old=same[-1]
        return 'coverage' if old.get('summary')==item.get('summary') else 'development'
class AttentionRanking:
    def score(self,values,policy):return round(sum(policy.weights[k]*values[k] for k in policy.weights),4)

class HorizonFilterPipeline:
    def __init__(self,policy,state,provider=None):self.policy=policy;self.state=state;self.provider=provider or DecisionModelProvider(concurrency=policy.concurrency);self.feedback=FeedbackStore(state)
    async def run(self,findings,sources,previous=None,hard_statuses=None):
        results=[];requests=0;reserved=0
        evidence={s['source_id']:s for s in sources}
        for item in findings:
            public={'summary':item['summary'][:1000],'event_id':item['event_id'],'evidence':[{'id':e['source_id'],'snippet':e['snippet'][:500],'fingerprint':evidence[e['source_id']].get('content_fingerprint')} for e in item.get('evidence',[]) if e['source_id'] in evidence]}
            digest=hashlib.sha256(dumps(public).encode()).hexdigest()
            key=hashlib.sha256(dumps([self.policy.model_dump(),self.provider.identity(),item['finding_id'],digest,previous or [],self.state.get('feedback',self.policy.profile_id+'|'+item['finding_id']),self.state.get('taste',self.policy.profile_id),self.state.get('examples',self.policy.profile_id),hard_statuses]).encode()).hexdigest()
            cached=self.state.get('completed',key)
            if cached:results.append({**cached,'cache_hit':True});continue
            text=item['summary'].lower();novelty=NoveltyGate().run(item,previous or [])
            values={'relevance':min(1,sum(t.lower() in text for t in self.policy.topics)/2),'novelty':0 if novelty=='coverage' else 1,'importance':.5,'actionability':.5,'evidence':1 if public['evidence'] else 0}
            gates={};failures=[]
            for command in COMMANDS:
                cachekey=key+'|'+command
                entry=self.state.get('decision',cachekey)
                if entry is None and self.provider.configured and requests+3<=self.policy.max_requests and reserved+13500<=self.policy.max_tokens:
                    requests+=3;reserved+=13500
                    decision,meta=await {'relevance':SemanticRelevanceGate,'worth-attention':ActionabilityGate,'same-story':SameStoryGate,'importance':ImportanceGate,'claim-support':ClaimSupportGate,'hfs':HFSGate}[command]().run(self.provider,{**public,'topics':self.policy.topics,'curated_examples':self.state.get('examples',self.policy.profile_id) or [],'previous':[{'event_id':p['event_id'],'summary':p['summary'][:500]} for p in (previous or [])[-3:]]})
                    entry={'decision':decision.model_dump() if decision else None,'provider':meta}
                    if decision:self.state.put('decision',cachekey,entry)
                if entry is None:entry={'decision':None,'provider':{'family':'openai_chat','status':'budget_limit' if self.provider.configured else 'unavailable','tokens':None,'cost':None}}
                if entry:
                    gates[command]=entry
                    if not entry['decision']:failures.append(command)
            for cmd,dimension in [('relevance','relevance'),('importance','importance'),('worth-attention','actionability')]:
                if gates.get(cmd,{}).get('decision'):values[dimension]=gates[cmd]['decision']['score']
            story=gates.get('same-story',{}).get('decision')
            if story and story['verdict'] in ('same','development','contradiction'):
                novelty={'same':'coverage','development':'development','contradiction':'review'}[story['verdict']]
            support=gates.get('claim-support',{}).get('decision')
            taste=self.state.get('taste',self.policy.profile_id) or {'topics':{},'sources':{}}
            adjustment=sum(v for t,v in taste['topics'].items() if t.lower() in text)+sum(taste['sources'].get(s,0) for s in item['source_ids'])
            values['relevance']=max(0,min(1,values['relevance']+max(-.1,min(.1,adjustment))))
            if any(e['command']=='important_but_not_actionable' for e in (self.state.get('feedback',self.policy.profile_id+'|'+item['finding_id']) or [])):
                values['importance']=max(.75,values['importance']);values['actionability']=min(.25,values['actionability'])
            hard=DeterministicGate().run(item,self.policy) and bool(public['evidence'])
            if hard_statuses is not None:hard=hard and hard_statuses.get(item['event_id'])=='ELIGIBLE_NOW'
            score=max(0,min(1,AttentionRanking().score(values,self.policy)+self.feedback.adjustment(self.policy.profile_id,item['finding_id'])))
            result={'cache_hit':False,'public_summary':item['summary'][:500],'item_id':item['finding_id'],'event_id':item['event_id'],'profile_id':self.policy.profile_id,'policy_version':self.policy.version,'input_hash':digest,'gates':gates,'dimensions':values,'attention':score,'novelty':novelty,'evidence_ids':item['source_ids'],'accepted':hard and score>=self.policy.threshold and novelty not in ('coverage','review') and not(support and support['verdict']=='no'),'hard_gate':hard,'fallback':not gates or bool(failures),'failures':failures,'provider_family':'openai_chat','heuristic_not_probability':True}
            # Failed inference is retried on a later execution, not cached forever.
            if not result['fallback']:self.state.put('completed',key,result)
            self.state.put('history',self.policy.profile_id+'|'+item['finding_id'],result)
            results.append(result)
        return sorted(results,key=lambda r:r['attention'],reverse=True)
