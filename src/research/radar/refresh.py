"""Bounded source checkpoints and inference telemetry; never cache raw pages."""
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pydantic import Field,model_validator
from ..profiles import Strict
from ..reporting import dumps
from .contracts import Reference, stamp


class SourceSnapshot(Strict):
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    etag: str | None = Field(default=None,max_length=256,pattern=r'^[^\r\n]*$')
    last_checked_utc: str
    references: list[Reference] = Field(max_length=30)
    @model_validator(mode='after')
    def valid(self):
        stamp(self.last_checked_utc)
        if self.content_hash!=fingerprint(self.references):raise ValueError('Source checkpoint hash mismatch')
        return self


def fingerprint(refs):
    # Retrieval time is not article content. Original-language text is preserved.
    return hashlib.sha256(dumps([{k:v for k,v in r.model_dump(mode='json').items() if k!='fetched_at_utc'} for r in sorted(refs,key=lambda r:r.id)]).encode()).hexdigest()


def cached_items(refs):
    from src.models import ContentItem,SourceType
    return [ContentItem(id=r.id,source_type=SourceType.RSS,title=r.title,url=r.url,content=r.excerpt,author=r.author,published_at=r.published_at_utc,fetched_at=r.fetched_at_utc,metadata={'radar_cached_reference':r.model_dump(mode='json')}) for r in refs]


class MeteredProvider:
    """A global per-radar reservation boundary around all shared/technical calls."""
    def __init__(self,provider,entry):
        self.provider=provider;self.entry=entry;self.records=[]
        self.reserved_requests=0;self.reserved_tokens=0
    @property
    def configured(self):return self.provider.configured
    @property
    def model(self):return getattr(self.provider,'model',None)
    def identity(self):return self.provider.identity()
    async def decide(self,command,payload):
        reserve=46500 if command=='technical-learning' else 19500
        price=self.entry.get('usd_per_million_tokens');cap=self.entry.get('max_cost_usd')
        used=max(self.reserved_tokens,sum(m['tokens'] for m in self.records if type(m.get('tokens')) is int))
        cost_ok=cap is None or price is not None and (used+reserve)*price/1_000_000<=cap
        if not cost_ok or self.reserved_requests+3>self.entry['max_model_requests'] or used+reserve>self.entry['max_model_tokens']:
            return None,{'status':'budget_limit','attempts':0,'tokens':None,'model':self.model,'family':'openai_chat'}
        self.reserved_requests+=3;self.reserved_tokens+=reserve
        decision,meta=await self.provider.decide(command,payload)
        self.records.append(meta)
        actual=sum(m['tokens'] for m in self.records if type(m.get('tokens')) is int)
        if actual>self.entry['max_model_tokens'] or cap is not None and price is not None and actual*price/1_000_000>cap:
            meta={**meta,'status':'usage_budget_exceeded'};decision=None
        return decision,meta
    def telemetry(self):
        attempts=sum(m.get('attempts',0) for m in self.records)
        known=sum(m['tokens'] for m in self.records if type(m.get('tokens')) is int)
        complete=all(type(m.get('tokens')) is int and m.get('attempts',0)==1 for m in self.records)
        price=self.entry.get('usd_per_million_tokens')
        return {'model_requests':attempts,'successful_decisions':sum(m.get('status')=='success' for m in self.records),'known_total_tokens':known,'token_usage_complete':complete,'reported_usage_exceeds_token_budget':known>self.entry['max_model_tokens'],'cost_usd':(known*price/1_000_000 if complete and price is not None else 0 if not attempts else None),'cost_basis':'no_requests' if not attempts else 'configured_token_rate_estimate' if complete and price is not None else 'unknown','reserved_requests':self.reserved_requests,'reserved_tokens':self.reserved_tokens}


def next_collection_due(now,interval):
    # Align normal pilot slots to the intended UTC cadence. A delayed daily run
    # must not move tomorrow's due time past tomorrow's scheduled event.
    if interval not in (12,24):return stamp(now+timedelta(hours=interval))
    hours=(2,14) if interval==12 else (2,)
    slots=[(now+timedelta(days=day)).replace(hour=hour,minute=13,second=0,microsecond=0) for day in (0,1) for hour in hours]
    return stamp(min(slot for slot in slots if slot>now))
