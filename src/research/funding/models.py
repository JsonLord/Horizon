"""Public funding data contract. Unknown eligibility never becomes approval."""

from datetime import datetime, date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from ..profiles import Strict, safe_url


class Resource(Strict):
    resource_id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    url: str
    title: str = Field(min_length=1, max_length=300)
    kind: Literal["program", "application", "eligibility", "form", "template", "checklist", "guideline", "faq", "contact", "other"] = "other"
    retrieved_at: datetime | None = None
    verified: bool = False
    content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    quotation: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def public(cls, value):
        return safe_url(value)

    @model_validator(mode="after")
    def provenance(self):
        if self.verified and (not self.retrieved_at or not self.content_sha256 or not self.quotation):
            raise ValueError("Verified resources require retrieval date, hash and a short quotation")
        if self.retrieved_at and self.retrieved_at.tzinfo is None:
            raise ValueError("Retrieval date requires timezone")
        return self


class Claim(Strict):
    value: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class Condition(Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    description: str = Field(min_length=1, max_length=1000)
    # Operator-published restriction, compared with the versioned applicant profile.
    accepted_values: list[str] = Field(min_length=1, max_length=30)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    milestone: str | None = Field(default=None, max_length=1000)


class AccessCheck(Strict):
    observed_at: datetime
    method: Literal["HEAD", "GET"]
    url: str
    http_status: int | None = Field(default=None, ge=100, le=599)
    proxy_connect_status: int | None = Field(default=None, ge=100, le=599)
    proxy_configured: bool
    local_dns_resolves: bool
    redirect_chain: list[str] = Field(default_factory=list, max_length=4)
    redirect_chain_complete: bool = True
    response_headers: dict[str, str] = Field(default_factory=dict, max_length=12)
    failure_origin: Literal["proxy_path", "unknown", "none"] = "none"
    collector_limitation: Literal["local_dns_unavailable"] | None = None

    @model_validator(mode="after")
    def safe(self):
        safe_url(self.url)
        for url in self.redirect_chain:
            safe_url(url)
        allowed = {"content-type", "date", "server", "via", "location", "retry-after", "x-cache", "x-envoy-upstream-service-time"}
        if not set(self.response_headers) <= allowed or any(len(v) > 500 or "\n" in v or "\r" in v for v in self.response_headers.values()):
            raise ValueError("Only bounded non-sensitive diagnostic headers are allowed")
        if "location" in self.response_headers:
            safe_url(self.response_headers["location"])
        if self.observed_at.tzinfo is None:
            raise ValueError("Access observation requires timezone")
        return self


class Opportunity(Strict):
    schema_version: Literal["1.0"] = "1.0"
    opportunity_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,95}$")
    provider: str = Field(min_length=1, max_length=160)
    program: str = Field(min_length=1, max_length=200)
    official_domains: list[str] = Field(min_length=1, max_length=10)
    application_status: Literal["OPEN", "UPCOMING", "CLOSED", "UNKNOWN"] = "UNKNOWN"
    deadline_kind: Literal["date", "rolling", "unknown", "discontinued", "next_round_unknown"] = "unknown"
    deadline: date | None = None
    deadline_timezone: str | None = None
    deadline_scope: str | None = Field(default=None, max_length=500)
    access_checks: list[AccessCheck] = Field(default_factory=list, max_length=20)
    claims: dict[str, Claim] = Field(default_factory=dict, max_length=60)
    conditions: list[Condition] = Field(default_factory=list, max_length=40)
    eligibility_complete: bool = False
    resources: list[Resource] = Field(default_factory=list, max_length=100)
    checked_at: datetime
    collection_error: str | None = Field(default=None, max_length=200)
    relevance_score: float | None = Field(default=None, ge=0, le=1)
    relevance_explanation: str | None = Field(default=None, max_length=1000)
    financing_suitability: Literal["suitable", "unsuitable", "unknown"] = "unknown"
    archived: bool = False

    @model_validator(mode="after")
    def evidence(self):
        if self.checked_at.tzinfo is None:
            raise ValueError("Check date requires timezone")
        for host in self.official_domains:
            safe_url("https://" + host)
            if urlsplit("https://" + host).netloc != host or "/" in host:
                raise ValueError("Official domains must be hostnames")
        ids = {r.resource_id: r for r in self.resources}
        if len(ids) != len(self.resources):
            raise ValueError("Duplicate resource IDs")
        for resource in self.resources:
            host = urlsplit(resource.url).hostname
            if resource.verified and not any(host == d or host.endswith("." + d) for d in self.official_domains):
                raise ValueError("Evidence must be on a reviewed official domain")
        for assertion in [*self.claims.values(), *self.conditions]:
            if any(i not in ids or not ids[i].verified for i in assertion.evidence_ids):
                raise ValueError("Assertion lacks verified official evidence")
        required = []
        if self.application_status != "UNKNOWN":
            required.append("application_status")
        if self.deadline_kind != "unknown":
            required.append("deadline")
        if self.deadline_kind == "date":
            if not self.deadline:
                raise ValueError("Verified date required")
        elif self.deadline is not None:
            raise ValueError("Only date deadlines may contain dates")
        if self.deadline_timezone:
            from zoneinfo import ZoneInfo
            ZoneInfo(self.deadline_timezone)
            required.append("deadline_timezone")
        if self.deadline_scope:
            required.append("deadline_scope")
        if self.eligibility_complete:
            required.append("eligibility_complete")
        if any(k not in self.claims for k in required):
            raise ValueError("Status, deadline and complete eligibility require evidence")
        if "application_status" in self.claims and self.claims["application_status"].value != self.application_status:
            raise ValueError("Status differs from supporting claim")
        if "deadline" in self.claims and self.claims["deadline"].value != self.deadline_token:
            raise ValueError("Deadline differs from supporting claim")
        if self.deadline_timezone and self.claims["deadline_timezone"].value != self.deadline_timezone:
            raise ValueError("Timezone differs from supporting claim")
        if self.financing_suitability != "unknown" and "financing" not in self.claims:
            raise ValueError("Financing suitability requires official terms evidence")
        if self.relevance_score is not None and not self.relevance_explanation:
            raise ValueError("Heuristic relevance requires an explanation")
        if any(r.retrieved_at and r.retrieved_at > self.checked_at for r in self.resources):
            raise ValueError("Evidence retrieval cannot be later than the check date")
        return self

    @property
    def deadline_token(self):
        return {"date": self.deadline.isoformat() if self.deadline else "UNKNOWN", "rolling": "ROLLING", "unknown": "UNKNOWN", "discontinued": "CLOSED", "next_round_unknown": "NEXT-ROUND-UNKNOWN"}[self.deadline_kind]


class Applicant(Strict):
    schema_version: Literal["1.0"] = "1.0"
    facts: dict[str, str] = Field(default_factory=dict, max_length=40)
    # Unknown applicant facts are intentionally omitted, never inferred from a search.
    interests: list[str] = Field(default_factory=list, max_length=30)
    evidence_max_age_days: int = Field(default=30, ge=1, le=365)


class FundingDataset(Strict):
    schema_version: Literal["1.0"] = "1.0"
    opportunities: list[Opportunity] = Field(max_length=40)

    @model_validator(mode="after")
    def unique(self):
        if len({r.opportunity_id for r in self.opportunities}) != len(self.opportunities):
            raise ValueError("Duplicate funding opportunity IDs")
        return self


def assess(record: Opportunity, applicant: Applicant):
    missing, milestones, rejected = [], [], []
    verified = [r.retrieved_at for r in record.resources if r.verified]
    stale = not verified or (record.checked_at - min(verified)).days > applicant.evidence_max_age_days
    if stale or record.collection_error:
        missing.append("Official evidence is missing, stale or could not be refreshed")
    for condition in record.conditions:
        actual = applicant.facts.get(condition.key)
        if actual is None or actual == "unknown":
            missing.append(condition.description)
        elif actual not in condition.accepted_values:
            (milestones if condition.milestone else rejected).append(condition.milestone or condition.description)
    expired = record.deadline is not None and record.deadline < record.checked_at.date()
    if rejected and not stale and not record.collection_error:
        status = "VERIFIED_INELIGIBLE"
    elif record.deadline_kind in ("discontinued", "next_round_unknown") or record.application_status == "CLOSED" or expired:
        status = "WATCH_FUTURE_ROUND"
    elif missing or not record.eligibility_complete:
        status = "ELIGIBILITY_UNKNOWN"
    elif milestones:
        status = "ELIGIBLE_AFTER_MILESTONE"
    elif record.application_status == "OPEN":
        status = "ELIGIBLE_NOW"
    else:
        status = "ELIGIBILITY_UNKNOWN"
    return {"status": status, "missing_prerequisites": missing, "achievable_milestones": milestones, "hard_rejections": rejected,
            "next_action": "Review official eligibility and resolve missing facts" if status == "ELIGIBILITY_UNKNOWN" else "Complete eligibility milestones" if status == "ELIGIBLE_AFTER_MILESTONE" else "Prepare application using official instructions" if status == "ELIGIBLE_NOW" else "Monitor the next official round" if status == "WATCH_FUTURE_ROUND" else "Do not apply under current conditions"}


def merge_refresh(old: Opportunity, fresh: Opportunity):
    """Keep reviewed terms; changed content requires a new explicit terms review."""
    payload = old.model_dump(mode="json")
    payload["checked_at"] = fresh.checked_at.isoformat()
    payload["collection_error"] = fresh.collection_error
    resources = {r.resource_id: r.model_dump(mode="json") for r in old.resources}
    for resource in fresh.resources:
        if not resource.verified:
            continue
        prior = resources.get(resource.resource_id)
        if old.claims and prior and prior["content_sha256"] != resource.content_sha256:
            payload["collection_error"] = "official_terms_need_reverification"
            # Old quotations still back historical claims; new availability
            # evidence gets a separate ID until those claims are re-reviewed.
            item = resource.model_dump(mode="json")
            item["resource_id"] = "observed-" + resource.content_sha256[:24]
            resources[item["resource_id"]] = item
        else:
            resources[resource.resource_id] = resource.model_dump(mode="json")
    payload["resources"] = list(resources.values())
    return Opportunity.model_validate(payload)
