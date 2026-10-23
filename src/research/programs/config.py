"""Validated, versioned public configuration with hard implementation ceilings."""

import json
from pathlib import Path

from pydantic import Field, field_validator

from ..profiles import ROOT, Strict, safe_url


class Seed(Strict):
    key: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    name: str = Field(min_length=1, max_length=200)
    url: str | None
    official_domains: list[str] = Field(max_length=10)
    related_urls: list[str] = Field(default_factory=list, max_length=4)
    legacy: dict | None = None

    @field_validator("url")
    @classmethod
    def url_valid(cls, value):
        return safe_url(value) if value else None

    @field_validator("official_domains")
    @classmethod
    def domain_valid(cls, value):
        for domain in value:
            safe_url("https://" + domain)
        return value

    @field_validator("related_urls")
    @classmethod
    def related_valid(cls, value):
        return [safe_url(u) for u in value]


class Sources(Strict):
    schema_version: str
    attribution: str
    sources: list[Seed] = Field(max_length=20)


class Discovery(Strict):
    schema_version: str
    max_candidates: int = Field(ge=0, le=20)
    max_pages: int = Field(ge=1, le=20)
    max_links_per_site: int = Field(ge=0, le=2)
    concurrency: int = Field(ge=1, le=3)
    freshness_days: int = Field(ge=1, le=90)
    deadline_soon_days: int = Field(ge=1, le=60)
    discovery_sites: list[Seed] = Field(max_length=8)


def load_config():
    sources = Sources.model_validate_json((ROOT / "config/program-sources.json").read_text())
    discovery = Discovery.model_validate_json((ROOT / "config/program-discovery.json").read_text())
    keys = [s.key for s in sources.sources + discovery.discovery_sites]
    if len(keys) != len(set(keys)):
        raise ValueError("Program source keys must be unique")
    return sources, discovery
