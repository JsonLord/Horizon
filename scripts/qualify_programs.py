"""Read-only hosted qualification; writes only local artifacts and job notices."""

import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path

from src.research.branches import resolve
from src.research.profiles import ROOT
from src.research.programs.fetch import ProgramFetcher
from src.research.programs.model_contract import inspect_contract
from src.research.programs.verify import refresh, seed_record
from src.research.reporting import atomic, dumps


async def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    selected = await resolve(os.environ["RESEARCH_REF"], repository)
    if selected["sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Select the same approved immutable workflow/research revision")
    now = datetime.now(UTC).isoformat()
    sources = json.loads((ROOT / "config/program-sources.json").read_text())["sources"]
    fetcher = ProgramFetcher(max_pages=6)
    observations = []
    for seed in sources:
        record = seed_record(seed, now)
        if seed.get("url"):
            page = await fetcher.fetch(seed["url"], now)
            record = refresh(record, page, seed["official_domains"])
            observations.append({"requested_url": page.requested_url, "final_url": page.final_url, "observed_at": page.observed_at, "error": page.error, "redirects": page.redirects})
        observations.append({"program": record.model_dump(mode="json")})
        for url in seed.get("related_urls", []):
            page = await fetcher.fetch(url, now)
            observations.append({"requested_url": url, "final_url": page.final_url, "observed_at": now, "error": page.error, "redirects": page.redirects})
    contract = await inspect_contract()
    result = {"read_only": True, "source": selected, "observations": observations, "model_contract": contract}
    atomic(Path("data/program-qualification/observations.json"), dumps(result))
    # GitHub annotations provide independently retrievable, bounded public proof.
    # Escape workflow-command characters; never echo scraped text as commands.
    notice = json.dumps(result, separators=(",", ":"))
    if len(notice) > 50000:
        notice = json.dumps({"source": selected, "read_only": True, "details": "see artifact", "model_status": contract["status"]})
    print("::notice title=program-qualification::" + notice.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"))


asyncio.run(main())
