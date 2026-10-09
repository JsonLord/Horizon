"""Reviewed source registry and bounded public RSS/Atom discovery for local agents."""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urljoin, urlsplit

import feedparser
from bs4 import BeautifulSoup
from pydantic import Field, field_validator

from .collector import BoundedClient
from .profiles import ROOT, Feed, Short, Strict, safe_url
from .reporting import atomic, dumps

REGISTRY = ROOT / "sources/registry.json"


class RegisteredSource(Strict):
    source_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    name: Short
    site_url: str = Field(max_length=2048)
    feed_url: str = Field(max_length=2048)
    profile_ids: list[
        Annotated[
            str, Field(pattern=r"^(world|institutions|examples)/[a-z0-9-]{1,64}$")
        ]
    ] = Field(min_length=1, max_length=20)
    topic: Short = "general"
    region: Short = "unknown"
    enabled: bool = True
    verified_at: datetime
    verification: dict

    @field_validator("site_url", "feed_url")
    @classmethod
    def public_url(cls, value):
        return safe_url(value)


class Registry(Strict):
    schema_version: Literal["1.0"] = "1.0"
    sources: list[RegisteredSource] = Field(default_factory=list, max_length=64)


def load_registry(path=REGISTRY):
    path = Path(path)
    if not path.exists():
        return Registry()
    if path.stat().st_size > 1_000_000:
        raise ValueError("Registry exceeds size ceiling")
    registry = Registry.model_validate_json(path.read_text())
    if len({s.source_id for s in registry.sources}) != len(registry.sources):
        raise ValueError("Duplicate registered source ID")
    if any(
        s.source_id != hashlib.sha256(s.feed_url.encode()).hexdigest()[:24]
        for s in registry.sources
    ):
        raise ValueError("Registered source ID does not match its feed URL")
    return registry


def apply_registry(profiles, registry):
    for source in registry.sources:
        if not source.enabled:
            continue
        for pid in source.profile_ids:
            if pid not in profiles:
                raise ValueError(
                    "Registry targets an unknown/disabled profile; remove its assignment first"
                )
            profile = profiles[pid]
            feed = Feed(
                name=source.name,
                url=source.feed_url,
                topic=source.topic,
                region=source.region,
            )
            existing = {f.url for f in profile.feeds} | set(
                profile.institution.official_feeds if profile.institution else []
            )
            if feed.url not in existing:
                data = profile.model_dump(by_alias=True)
                data["feeds"].append(feed.model_dump())
                profiles[pid] = type(profile).model_validate(data)
    return profiles


def parsed_feed(response):
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if not feed.version or feed.bozo:
        return None
    dates = [e.get("published_parsed") or e.get("updated_parsed") for e in feed.entries]
    latest = max((datetime(*d[:6], tzinfo=UTC) for d in dates if d), default=None)
    return {
        "feed_title": str(feed.feed.get("title", ""))[:300],
        "entries": len(feed.entries),
        "latest_published_at": latest.isoformat() if latest else None,
    }


async def discover(url, feed_url=None, client=None):
    safe_url(url)
    if feed_url:
        safe_url(feed_url)
    own = client is None
    if own:
        # Only already-reviewed hosts may use proxy DNS. New hosts fail closed
        # when public DNS cannot be verified; registration never trusts user input.
        from .profiles import load_profiles

        profiles = load_profiles()
        client = BoundedClient(timeout=20)
        reviewed = [f.url for p in profiles.values() for f in p.feeds]
        reviewed += [
            u
            for p in profiles.values()
            if p.institution
            for u in p.institution.official_feeds
        ]
        client.trusted_hosts = client.trusted_hosts | frozenset(
            urlsplit(u).hostname for u in reviewed
        )
    try:
        response = await client.get(feed_url or url)
        info = parsed_feed(response)
        if info:
            return safe_url(str(response.url)), info
        if feed_url:
            raise ValueError("Explicit feed URL is not valid RSS/Atom")
        page_url = str(response.url)
        soup = BeautifulSoup(response.content, "html.parser")
        candidates = []
        for link in soup.find_all(["link", "a"]):
            href = link.get("href")
            if not href:
                continue
            if link.get("type") not in (
                "application/rss+xml",
                "application/atom+xml",
            ) and not any(
                x in str(href).lower() for x in ("rss", "atom", "/feed", ".xml")
            ):
                continue
            candidate = urljoin(page_url, href)
            try:
                safe_url(candidate)
            except ValueError:
                continue
            if (
                urlsplit(candidate).hostname == urlsplit(page_url).hostname
                and candidate not in candidates
            ):
                candidates.append(candidate)
        for candidate in candidates[:8]:
            try:
                response = await client.get(candidate)
                info = parsed_feed(response)
                if info:
                    return safe_url(str(response.url)), info
            except (ValueError, OSError, TimeoutError):
                continue
            except Exception as exc:
                import httpx

                if not isinstance(exc, httpx.HTTPError):
                    raise
        raise ValueError(
            "No valid same-site RSS/Atom feed discovered; supply a verified --feed-url or use a site: search query"
        )
    finally:
        if own:
            await client.aclose()


async def register(
    url,
    name,
    profile_ids,
    topic="general",
    region="unknown",
    feed_url=None,
    registry_path=REGISTRY,
    client=None,
    profiles=None,
):
    from .profiles import load_profiles

    profiles = (
        profiles if profiles is not None else load_profiles(include_registry=False)
    )
    if not set(profile_ids) <= set(profiles) or not profile_ids:
        raise ValueError("Select enabled repository-reviewed profile IDs")
    if any("rss" not in profiles[pid].sources for pid in profile_ids):
        raise ValueError("Enable rss in each target profile before registering a feed")
    # Bound the complete discovery operation, including candidate feeds/retries.
    resolved, info = await asyncio.wait_for(discover(url, feed_url, client), 60)
    source = RegisteredSource(
        source_id=hashlib.sha256(resolved.encode()).hexdigest()[:24],
        name=name,
        site_url=url,
        feed_url=resolved,
        profile_ids=sorted(set(profile_ids)),
        topic=topic,
        region=region,
        verified_at=datetime.now(UTC),
        verification=info,
    )
    registry = load_registry(registry_path)
    prior = next((s for s in registry.sources if s.source_id == source.source_id), None)
    if prior:
        source.profile_ids = sorted(set(source.profile_ids + prior.profile_ids))
        source = RegisteredSource.model_validate(source.model_dump())
    updated = Registry(
        sources=[s for s in registry.sources if s.source_id != source.source_id]
        + [source]
    )
    # Validate combined per-profile bounds before writing any file.
    apply_registry(profiles, updated)
    atomic(registry_path, dumps(updated.model_dump(mode="json")))
    return source.model_dump(mode="json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser(
        "add", help="Discover/validate and register a feed for review"
    )
    add.add_argument("--url", required=True)
    add.add_argument("--feed-url")
    add.add_argument("--name", required=True)
    add.add_argument("--profile-id", action="append", required=True)
    add.add_argument("--topic", default="general")
    add.add_argument("--region", default="unknown")
    commands.add_parser("list", help="List registered URLs and profile assignments")
    remove = commands.add_parser("remove", help="Remove a source by its stable ID")
    remove.add_argument("source_id")
    commands.add_parser(
        "validate", help="Validate registry and effective profile bounds offline"
    )
    args = parser.parse_args()
    if args.command == "add":
        result = asyncio.run(
            register(
                args.url,
                args.name,
                args.profile_id,
                args.topic,
                args.region,
                args.feed_url,
                args.registry,
            )
        )
    elif args.command == "remove":
        registry = load_registry(args.registry)
        if args.source_id not in {s.source_id for s in registry.sources}:
            parser.error("Source ID not found")
        registry.sources = [
            s for s in registry.sources if s.source_id != args.source_id
        ]
        atomic(args.registry, dumps(registry.model_dump(mode="json")))
        result = {"removed": args.source_id}
    elif args.command == "validate":
        from .profiles import load_profiles

        profiles = load_profiles(registry_path=args.registry)
        result = {"valid": True, "profiles": sorted(profiles)}
    else:
        result = load_registry(args.registry).model_dump(mode="json")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
