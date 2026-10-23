"""Bounded public program records; unknown facts remain explicit."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from ..profiles import Strict, safe_url


class Evidence(Strict):
    evidence_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    url: str = Field(max_length=2048)
    observed_at: str
    quotation: str = Field(max_length=500)
    location: str = Field(max_length=120)
    published_at: str | None = None
    content_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    primary: bool = True

    @field_validator("url")
    @classmethod
    def url_valid(cls, value):
        return safe_url(value)


class Fact(Strict):
    value: str | list[str] | float | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    last_verified: str | None = None

    @model_validator(mode="after")
    def backed(self):
        if self.value is not None and (not self.evidence_ids or not self.last_verified):
            raise ValueError("Every material fact requires dated primary evidence")
        return self


class Fit(Strict):
    policy_version: str = "1.0-provisional"
    hard_eligibility: Literal["eligible", "ineligible", "review_required"] = "review_required"
    fit_score: float = Field(default=0, ge=0, le=1)
    dimensions: dict[str, float] = Field(default_factory=dict)
    evidence_confidence: float = Field(default=0, ge=0, le=1)
    model_self_reported_confidence: float | None = Field(default=None, ge=0, le=1)
    probability_relevant: None = None
    calibration_status: Literal["uncalibrated"] = "uncalibrated"
    decision: Literal["prioritize", "review", "not_prioritized"] = "review"
    reason_codes: list[str] = Field(default_factory=list, max_length=30)
    model: dict = Field(default_factory=dict)
    human_override: dict | None = None


class Program(Strict):
    program_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    name: str = Field(max_length=200)
    operator: str | None = Field(default=None, max_length=200)
    original_url: str | None = None
    canonical_url: str | None = None
    application_url: str | None = None
    program_type: Literal["incubator", "accelerator", "grant", "fellowship", "venture_studio", "education", "collaboration", "unknown"] = "unknown"
    target_domains: list[str] = Field(default_factory=list, max_length=20)
    eligible_countries: list[str] | None = None
    location: str | None = None
    remote_policy: str = "unknown"
    stage: str = "unknown"
    application_status: Literal["open", "upcoming", "closed", "unknown"] = "unknown"
    deadline: str | None = None
    deadline_timezone: str | None = None
    deadline_precision: Literal["date", "datetime", "unknown"] = "unknown"
    benefits: str | None = Field(default=None, max_length=500)
    funding_terms: str | None = Field(default=None, max_length=500)
    equity_terms: str | None = Field(default=None, max_length=500)
    cost_terms: str | None = Field(default=None, max_length=500)
    eligibility: str | None = Field(default=None, max_length=500)
    application_steps: str | None = Field(default=None, max_length=500)
    last_checked: str
    extraction_status: Literal["verified_page", "blocked", "failed", "missing_source", "candidate", "stale"] = "candidate"
    source_evidence: list[Evidence] = Field(default_factory=list, max_length=30)
    facts: dict[str, Fact] = Field(default_factory=dict)
    stale_fields: list[str] = Field(default_factory=list, max_length=30)
    check_error: str | None = Field(default=None, max_length=200)
    material_changes: list[dict] = Field(default_factory=list, max_length=30)
    legacy: dict | None = None
    discovery: dict = Field(default_factory=dict)
    fit: Fit = Field(default_factory=Fit)

    @field_validator("original_url", "canonical_url", "application_url")
    @classmethod
    def urls(cls, value):
        return safe_url(value) if value else None

    @model_validator(mode="after")
    def evidence_valid(self):
        evidence = {e.evidence_id: e for e in self.source_evidence}
        if len(evidence) != len(self.source_evidence):
            raise ValueError("Duplicate program evidence")
        for key, fact in self.facts.items():
            if any(eid not in evidence or not evidence[eid].primary for eid in fact.evidence_ids):
                raise ValueError("Fact cites missing or secondary evidence")
            if key in type(self).model_fields and fact.value is not None and getattr(self, key) != fact.value:
                raise ValueError("Fact differs from its structured value")
        for key in ("application_url", "deadline", "benefits", "funding_terms", "equity_terms", "cost_terms", "eligibility", "application_steps", "operator", "location"):
            if getattr(self, key) is not None and key not in self.facts:
                # Legacy labels are explicitly attributed, never treated as verified facts.
                if key != "operator" or not self.legacy:
                    raise ValueError("Structured assertion lacks fact provenance: " + key)
        if self.application_status != "unknown" and "application_status" not in self.facts:
            raise ValueError("Application status needs direct primary evidence")
        for key in ("program_type", "target_domains", "eligible_countries", "remote_policy", "stage"):
            if getattr(self, key) not in (None, "unknown", []) and key not in self.facts:
                raise ValueError("Structured assertion lacks fact provenance: " + key)
        if self.fit.decision == "prioritize" and (self.extraction_status != "verified_page" or self.fit.hard_eligibility != "eligible"):
            raise ValueError("Unverified/uncertain candidates cannot be prioritized")
        return self


class Dataset(Strict):
    schema_version: Literal["1.0"] = "1.0"
    profile_id: Literal["programs/incubators"] = "programs/incubators"
    policy_version: str
    observed_at: str
    programs: list[Program] = Field(max_length=40)
    coverage: dict = Field(default_factory=dict)
    failures: list[dict] = Field(default_factory=list, max_length=100)
    previous_dataset_sha256: str | None = None
    model_contract: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique(self):
        if len({p.program_id for p in self.programs}) != len(self.programs):
            raise ValueError("Duplicate program IDs")
        return self
