#!/usr/bin/env python3
"""Collect candidate pages or sync reviewed records into navigable funding folders."""

import argparse
import asyncio
import json
from pathlib import Path

from src.research.funding.models import Applicant, Opportunity, merge_refresh
from src.research.funding.pipeline import collect_opportunities
from src.research.funding.storage import OpportunityFolderStorage
from src.research.profiles import ROOT
from src.research.reporting import atomic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "sync", "check"])
    parser.add_argument("--root", type=Path, default=ROOT / "research/funding-de-eu")
    parser.add_argument("--records", type=Path, help="Reviewed JSON array; sync otherwise reads existing opportunity.json files")
    parser.add_argument("--applicant", type=Path, default=ROOT / "config/funding-applicant.json")
    args = parser.parse_args()
    applicant = Applicant.model_validate_json(args.applicant.read_text())
    if args.command == "collect":
        records = asyncio.run(collect_opportunities())
        # Preserve reviewed facts on a failed refresh. Their original retrieval
        # timestamps age naturally and collection_error prevents eligibility.
        existing = {r.opportunity_id: r for p in args.root.glob("opportunities/*/opportunity.json") if (r := Opportunity.model_validate_json(p.read_text()))}
        for i, record in enumerate(records):
            if old := existing.get(record.opportunity_id):
                records[i] = merge_refresh(old, record)
    else:
        records = [Opportunity.model_validate(x) for x in json.loads(args.records.read_text())] if args.records else [Opportunity.model_validate_json(p.read_text()) for p in args.root.glob("opportunities/*/opportunity.json")]
    storage = OpportunityFolderStorage(args.root, applicant)
    if args.command == "check":
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            clone = Path(temp) / "funding"
            shutil.copytree(args.root, clone)
            before = {p.relative_to(clone): p.read_bytes() for p in clone.rglob("*") if p.is_file()}
            OpportunityFolderStorage(clone, applicant).sync(records)
            after = {p.relative_to(clone): p.read_bytes() for p in clone.rglob("*") if p.is_file()}
            if before != after:
                raise SystemExit("Generated funding output is stale; run sync")
        print("Funding output is valid and deterministic")
        return
    index = storage.sync(records)
    if args.root.resolve() == (ROOT / "research/funding-de-eu").resolve():
        atomic(ROOT / "Funding DK (DE missing).md", "# Funding — Germany / EU\n\n[Funding knowledge base](research/funding-de-eu/README.md) · [Active](research/funding-de-eu/ACTIVE_OPPORTUNITIES.md) · [Review required](research/funding-de-eu/REVIEW_REQUIRED.md) · [Archived](research/funding-de-eu/ARCHIVED_OPPORTUNITIES.md)\n\n" + f"Verified eligible now: {index['active_count']}; review required: {index['review_count']}; archived / future rounds: {index['archived_count']}.\n")
    print(json.dumps({k: index[k] for k in ("active_count", "review_count", "archived_count")}))


if __name__ == "__main__":
    main()
