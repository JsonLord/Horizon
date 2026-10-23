"""Auditable heuristic fit, distinct from eligibility and calibrated probability."""

from datetime import UTC, datetime
import json
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ..profiles import ROOT, Strict
from .models import Fit


DIMENSIONS = {"strategic_fit", "software_ai", "inclusive_innovation", "mentoring_network", "benefits", "terms_effort"}


class LayaConfig(Strict):
    enabled: bool = True
    inference_endpoint: str | None = None
    model: str | None = Field(default=None, max_length=120)
    timeout_seconds: int = Field(ge=1, le=30)


class Policy(Strict):
    schema_version: Literal["1.0"]
    policy_version: str = Field(max_length=80)
    provisional: Literal[True]
    public_interests: list[str] = Field(max_length=20)
    weights: dict[str, float]
    prioritize_threshold: float = Field(ge=0, le=1)
    review_threshold: float = Field(ge=0, le=1)
    semantic_weight: float = Field(ge=0, le=0.5)
    calibration: dict
    laya: LayaConfig
    human_overrides: list[dict] = Field(max_length=40)

    @model_validator(mode="after")
    def bounds(self):
        if set(self.weights) != DIMENSIONS or any(not 0 <= w <= 1 for w in self.weights.values()) or abs(sum(self.weights.values()) - 1) > 1e-8:
            raise ValueError("All known dimension weights must sum to one")
        if self.review_threshold >= self.prioritize_threshold:
            raise ValueError("Review threshold must be below prioritize threshold")
        if self.calibration != {"status": "uncalibrated", "method": None, "holdout_sample_size": 0, "metrics": None}:
            raise ValueError("No measured calibration is available; probabilities must remain null")
        for override in self.human_overrides:
            if set(override) != {"program_id", "decision", "reason", "reviewed_at"} or override["decision"] not in {"review", "not_prioritized"}:
                raise ValueError("Overrides require explicit review provenance and cannot bypass primary verification")
        return self


def load_policy():
    # JSON is a YAML 1.2 subset; this avoids another runtime parser dependency.
    return Policy.model_validate_json((ROOT / "config/program-relevance.yaml").read_text())


def score(record, policy, semantic=None, model_metadata=None, now=None):
    now = now or datetime.now(UTC)
    fresh = [e.quotation.lower() for e in record.source_evidence if any(e.evidence_id in f.evidence_ids and k not in record.stale_fields for k, f in record.facts.items())]
    text = " ".join(fresh)
    def hits(patterns):
        return min(1.0, sum(bool(re.search(p, text, re.I)) for p in patterns) / max(1, len(patterns)))
    dimensions = {
        "strategic_fit": hits([r"founder|startup|venture", r"accelerator|incubator|fellowship|grant", r"entrepreneur"]),
        "software_ai": hits([r"\bsoftware\b|digital", r"\bAI\b|artificial intelligence", r"technology|innovation"]),
        "inclusive_innovation": hits([r"inclusive|accessibility|accessible", r"design|user experience|\bUX\b"]),
        "mentoring_network": hits([r"mentor|coaching", r"network|community", r"founder|entrepreneur"]),
        "benefits": hits([r"grant|funding|investment", r"workspace|support|mentoring", r"equity.free|stipend"]),
        "terms_effort": hits([r"equity.free|no equity", r"no fee|free to apply|no cost"]),
    }
    if semantic:
        dimensions = {key: (1 - policy.semantic_weight) * value + policy.semantic_weight * semantic.dimensions[key] for key, value in dimensions.items()}
    weighted = round(sum(policy.weights[key] * value for key, value in dimensions.items()), 4)
    reasons = []
    eligibility = "eligible"
    if record.application_status == "closed" and "application_status" not in record.stale_fields:
        eligibility = "ineligible"
        reasons.append("verified_round_closed")
    if record.deadline and "deadline" not in record.stale_fields:
        deadline = datetime.fromisoformat(record.deadline.replace("Z", "+00:00"))
        if deadline.date() < now.date():
            eligibility = "ineligible"
            reasons.append("verified_deadline_expired")
    if eligibility != "ineligible" and (record.application_status != "open" or not record.eligibility or "eligibility" in record.stale_fields or record.extraction_status != "verified_page"):
        eligibility = "review_required"
        reasons.append("critical_eligibility_or_primary_evidence_unknown")
    if record.program_type == "education":
        eligibility = "review_required" if eligibility != "ineligible" else eligibility
        reasons.append("education_is_not_an_open_founder_offer")
    evidence_confidence = round(min(1, sum(k not in record.stale_fields for k in record.facts) / 8), 3)
    decision = "prioritize" if weighted >= policy.prioritize_threshold else "review" if weighted >= policy.review_threshold else "not_prioritized"
    if eligibility == "ineligible":
        decision = "not_prioritized"
    elif eligibility == "review_required":
        decision = "review"
    override = next((o for o in policy.human_overrides if o["program_id"] == record.program_id), None)
    if override:
        decision = override["decision"]
        reasons.append("reviewed_human_override")
    return Fit(policy_version=policy.policy_version, hard_eligibility=eligibility, fit_score=weighted, dimensions={k: round(v, 4) for k, v in dimensions.items()},
               evidence_confidence=evidence_confidence, model_self_reported_confidence=semantic.self_reported_confidence if semantic else None,
               decision=decision, reason_codes=reasons + (semantic.reason_codes if semantic else []), model=model_metadata or {"status": "model_unavailable", "fallback": "deterministic"}, human_override=override)
