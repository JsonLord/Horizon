"""Versioned public contracts and deterministic UTC windowing."""
from datetime import UTC, datetime, timedelta
from typing import Literal
from pydantic import Field, field_validator, model_validator
from ..profiles import Strict, safe_url

RADARS = ('agent-control-planes', 'distributed-training', 'rag-memory')
LANGUAGES = ('en', 'de', 'fr')


def utc(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError('Explicit UTC timestamp required')
    return dt.astimezone(UTC)


def stamp(value):
    return utc(value).isoformat().replace('+00:00', 'Z')


def cutoff(now):
    now = utc(now)
    end = (now - timedelta(days=(now.weekday()-4) % 7)).replace(hour=18, minute=0, second=0, microsecond=0)
    return end if end <= now else end-timedelta(days=7)


def week_key(end):
    end = utc(end)
    if cutoff(end) != end:
        raise ValueError('Expected Friday 18:00 UTC cutoff')
    return end.strftime('%G-W%V')


class Reference(Strict):
    id: str = Field(pattern=r'^[a-f0-9]{24}$')
    title: str = Field(min_length=1, max_length=500)
    language: Literal['en', 'de', 'fr', 'unknown']
    discovery_language: Literal['en', 'de', 'fr', 'unknown'] = 'unknown'
    language_basis: str = Field(max_length=120)
    author: str | None = Field(default=None, max_length=200)
    publisher: str = Field(max_length=200)
    published_at_utc: str
    fetched_at_utc: str
    url: str = Field(max_length=2048)
    excerpt: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    primary: bool
    @field_validator('url')
    @classmethod
    def public(cls, value):
        from ..analyzers import public_original
        return public_original(value)
    @field_validator('published_at_utc', 'fetched_at_utc')
    @classmethod
    def times(cls, value): return stamp(value)


class Components(Strict):
    mechanism: int = Field(ge=0, le=3, strict=True)
    integration_change: int = Field(ge=0, le=2, strict=True)
    reproducibility: int = Field(ge=0, le=2, strict=True)
    learning: int = Field(ge=0, le=1, strict=True)
    primary_evidence: int = Field(ge=0, le=1, strict=True)
    @property
    def score(self): return 1 + sum(self.model_dump().values())


class Concept(Strict):
    event_id: str = Field(pattern=r'^[a-f0-9]{24}$')
    title: str = Field(min_length=1, max_length=500)
    original_source_language: Literal['en', 'de', 'fr']
    technical_explanation: str = Field(min_length=1, max_length=500)
    architectural_significance: int = Field(ge=1, le=10)
    score_components: Components
    what_is_new: str = Field(max_length=500)
    evidence_references: list[str] = Field(min_length=1, max_length=20)
    related_concepts: list[str] = Field(default_factory=list, max_length=20)
    learning_objective: str = Field(min_length=1, max_length=500)
    uncertainties: list[str] = Field(max_length=20)
    model: str | None = None
    policy_version: str
    @model_validator(mode='after')
    def score_matches(self):
        if self.architectural_significance != self.score_components.score:
            raise ValueError('Rubric sum mismatch')
        return self


class Pattern(Strict):
    title: str = Field(max_length=200)
    problem: str = Field(max_length=500)
    mechanism: str = Field(max_length=500)
    example: str = Field(max_length=1000)
    example_kind: Literal['original_pseudocode', 'attributed_excerpt']
    evidence_references: list[str] = Field(min_length=1, max_length=20)
    documentation_url: str
    prerequisites: list[str] = Field(max_length=10)
    limitations: list[str] = Field(min_length=1, max_length=10)
    @field_validator('documentation_url')
    @classmethod
    def url(cls, value): return safe_url(value)


class Quality(Strict):
    collection_complete: bool
    evidence_validated: bool
    coverage_limitations: list[str] = Field(max_length=30)
    candidate_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    review_count: int = Field(ge=0)
    metrics: dict[str, float | None] = Field(default_factory=dict)


class Digest(Strict):
    schema_version: Literal['1.0'] = '1.0'
    radar_id: Literal['agent-control-planes', 'distributed-training', 'rag-memory']
    week_start_utc: str
    week_end_utc: str
    generated_at_utc: str
    policy_version: str
    source_languages: list[Literal['en', 'de', 'fr', 'unknown']]
    source_references: list[Reference] = Field(max_length=600)
    top_concepts: list[Concept] = Field(max_length=5)
    code_patterns: list[Pattern] = Field(max_length=10)
    suggested_prerequisites: list[str] = Field(max_length=30)
    quality: Quality
    status: Literal['complete', 'partial']
    @model_validator(mode='after')
    def consistent(self):
        end, start, generated = map(utc, (self.week_end_utc,self.week_start_utc,self.generated_at_utc))
        week_key(end)
        if end-start != timedelta(days=7) or generated < end: raise ValueError('Invalid weekly interval')
        refs = {r.id:r for r in self.source_references}
        if len(refs) != len(self.source_references): raise ValueError('Duplicate source identity')
        if set(self.source_languages) != {r.language for r in refs.values()}: raise ValueError('Invented language coverage')
        if len({c.event_id for c in self.top_concepts}) != len(self.top_concepts): raise ValueError('Duplicate concept')
        for c in self.top_concepts:
            if not set(c.evidence_references) <= refs.keys(): raise ValueError('Unknown concept citation')
            cited = [refs[i] for i in c.evidence_references]
            if not any(r.primary for r in cited): raise ValueError('Primary evidence required')
            if c.original_source_language not in {r.language for r in cited}: raise ValueError('Unsupported language')
            if not all(start <= utc(r.published_at_utc) < end for r in cited): raise ValueError('Evidence outside window')
            if c.policy_version != self.policy_version: raise ValueError('Policy mismatch')
        for p in self.code_patterns:
            if not set(p.evidence_references) <= refs.keys(): raise ValueError('Unknown pattern citation')
        if self.quality.confirmed_count != len(self.top_concepts): raise ValueError('Count mismatch')
        if len(self.top_concepts)<3 and not self.quality.coverage_limitations: raise ValueError('Missing coverage limitation')
        if self.status=='complete' and not (self.quality.collection_complete and self.quality.evidence_validated): raise ValueError('Partial validation cannot be complete')
        return self


class RadarManifest(Strict):
    schema_version: Literal['1.0'] = '1.0'
    radar_id: Literal['agent-control-planes', 'distributed-training', 'rag-memory']
    latest_digest_path: Literal['weekly-digest.json'] | None = None
    latest_week: str | None = Field(default=None, pattern=r'^\d{4}-W\d{2}$')
    digest_status: Literal['uninitialized', 'complete'] = 'uninitialized'
    last_successful_collection_utc: str | None = None
    last_successful_digest_utc: str | None = None
    @model_validator(mode='after')
    def consistent(self):
        for v in (self.last_successful_collection_utc,self.last_successful_digest_utc):
            if v is not None: utc(v)
        initialized = self.digest_status=='complete'
        if initialized != bool(self.latest_digest_path and self.latest_week and self.last_successful_digest_utc):
            raise ValueError('Manifest pointer/status mismatch')
        return self
