"""Validated, credential-free research profiles."""

import ipaddress
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Short = Annotated[str, Field(min_length=1, max_length=120)]

ROOT = Path(__file__).resolve().parents[2]


def safe_url(value: str) -> str:
    u = urlsplit(value)
    if (
        u.scheme != "https"
        or not u.hostname
        or u.username
        or u.password
        or u.port not in (None, 443)
    ):
        raise ValueError("Public HTTPS URL required")
    host = u.hostname.lower()
    if (
        host == "localhost"
        or host.endswith((".local", ".internal", ".ts.net"))
        or "." not in host
    ):
        raise ValueError("Public hostname required")
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError("Private address")
    except ValueError as e:
        if str(e) == "Private address":
            raise
    if u.query or u.fragment:
        raise ValueError("Query credentials and fragments are not allowed")
    return value


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Query(Strict):
    source: Literal["gdelt", "google_news"]
    text: str = Field(min_length=3, max_length=240, pattern=r"^[^\r\n{}$`]+$")
    language: str = Field(default="en", pattern=r"^[a-zA-Z-]{2,24}$")
    country: str = Field(default="US", pattern=r"^[A-Z]{2}$")
    topic: Short = "general"
    region: Short = "unknown"


class Institution(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    names: list[Short] = Field(min_length=1, max_length=10)
    aliases: list[Short] = Field(default_factory=list, max_length=20)
    official_domains: list[str] = Field(default_factory=list, max_length=10)
    official_feeds: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("official_feeds")
    @classmethod
    def feeds(cls, v):
        return [safe_url(x) for x in v]

    @field_validator("official_domains")
    @classmethod
    def domains(cls, v):
        for d in v:
            safe_url("https://" + d)
        return v


class Ranking(Strict):
    mode: Literal["keyword", "institution_relevance"] = "keyword"
    minimum_score: float = Field(default=0, ge=0, le=20)


class Output(Strict):
    languages: list[Short] = ["en"]
    markdown: bool = True
    json_output: bool = Field(default=True, alias="json")
    changes: bool = True


class Feed(Strict):
    name: Short
    url: str = Field(max_length=2048)
    topic: Short = "general"
    region: Short = "unknown"

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        return safe_url(value)


class Profile(Strict):
    schema_version: Literal["1.0"]
    profile_id: str = Field(pattern=r"^(world|institutions|examples)/[a-z0-9-]{1,64}$")
    mode: Literal["world_radar", "institution_watch", "research_job"]
    name: str = Field(min_length=1, max_length=120)
    enabled: bool
    topics: list[Short] = Field(max_length=20)
    regions: list[Short] = Field(max_length=20)
    languages: list[Short] = Field(max_length=10)
    queries: list[Query] = Field(min_length=1, max_length=16)
    sources: list[Literal["gdelt", "google_news", "rss"]]
    schedule_hint: Literal["daily", "weekly", "manual"]
    lookback_hours: int = Field(ge=1, le=168)
    max_items: int = Field(ge=1, le=200)
    max_queries: int = Field(ge=1, le=16)
    ranking: Ranking
    output: Output
    institution: Institution | None = None
    feeds: list[Feed] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def bounds(self):
        if len(self.queries) > self.max_queries:
            raise ValueError("Too many queries")
        if any(q.source not in self.sources for q in self.queries):
            raise ValueError("Query source disabled")
        if self.mode == "institution_watch" and not self.institution:
            raise ValueError("Institution required")
        return self

    def canonical(self):
        import json

        return json.dumps(
            self.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            separators=(",", ":"),
        )


def load_profiles(directory=None, registry_path=None, include_registry=True):
    profiles = {
        p.profile_id: p
        for f in sorted(Path(directory or ROOT / "profiles").rglob("*.json"))
        if (p := Profile.model_validate_json(f.read_text())).enabled
    }
    if include_registry and (directory is None or registry_path is not None):
        from .registry import REGISTRY, apply_registry, load_registry

        apply_registry(profiles, load_registry(registry_path or REGISTRY))
    return profiles
