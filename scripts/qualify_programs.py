"""Read-only hosted qualification; writes only local artifacts and job notices."""

import asyncio
import base64
import zlib
from datetime import UTC, datetime
import json
import os
from pathlib import Path

from src.research.branches import resolve
from src.research.profiles import ROOT
from src.research.programs.fetch import ProgramFetcher
from src.research.programs.model_contract import inspect_contract
from src.research.programs.verify import refresh, seed_record
from src.research.programs.config import load_config
from src.research.programs.discovery import nominate, official_links
from src.research.profiles import load_profiles
from src.research.reporting import atomic, dumps


async def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    selected = await resolve(os.environ["RESEARCH_REF"], repository)
    if selected["sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Select the same approved immutable workflow/research revision")
    now = datetime.now(UTC).isoformat()
    sources, discovery = load_config()
    nominated, metrics = await nominate(load_profiles()["programs/incubators"], discovery, now)
    seeds = [s.model_dump() for s in sources.sources]
    seeds += [{"key": r.program_id, "name": r.name, "url": r.original_url, "official_domains": domains, "related_urls": []} for r, domains in nominated if domains]
    fetcher = ProgramFetcher(max_pages=discovery.max_pages)
    observations = []
    for seed in seeds:
        record = seed_record(seed, now)
        if seed.get("url"):
            page = await fetcher.fetch(seed["url"], now)
            record = refresh(record, page, seed["official_domains"])
            observations.append({"requested_url": page.requested_url, "final_url": page.final_url, "observed_at": page.observed_at, "error": page.error, "redirects": page.redirects})
            for url in official_links(page, seed["official_domains"], discovery.max_links_per_site):
                linked = await fetcher.fetch(url, now)
                record = refresh(record, linked, seed["official_domains"])
                observations.append({"requested_url": url, "final_url": linked.final_url, "observed_at": now, "error": linked.error})
        observations.append({"program": record.model_dump(mode="json")})
        for url in seed.get("related_urls", []):
            page = await fetcher.fetch(url, now)
            observations.append({"requested_url": url, "final_url": page.final_url, "observed_at": now, "error": page.error, "redirects": page.redirects})
    contract = await inspect_contract()
    result = {"read_only": True, "source": selected, "observations": observations, "discovery_metrics": metrics, "model_contract": contract}
    atomic(Path("data/program-qualification/observations.json"), dumps(result))
    # GitHub annotations provide independently retrievable, bounded public proof.
    # Escape workflow-command characters; never echo scraped text as commands.
    public = dict(result)
    public["observations"] = []
    for observation in observations:
        if "program" not in observation:
            public["observations"].append(observation)
            continue
        program = observation["program"]
        public["observations"].append({"program": {k: program[k] for k in ("program_id", "name", "canonical_url", "application_status", "deadline", "extraction_status", "check_error", "facts", "source_evidence")}})
    encoded = base64.b64encode(zlib.compress(json.dumps(public, separators=(",", ":")).encode())).decode()
    # Check annotations truncate individual messages at ~4 KB. Bounded parts
    # retain complete public proof, rather than a silently truncated JSON blob.
    chunks = [encoded[i:i+2800] for i in range(0, len(encoded), 2800)]
    if len(chunks) > 10:
        raise ValueError("Public qualification proof exceeds the ten-notice budget; full artifacts are retained")
    for index, chunk in enumerate(chunks):
        print(f"::notice title=program-evidence-zlib-{index+1}-of-{len(chunks)}::{chunk}")


asyncio.run(main())
