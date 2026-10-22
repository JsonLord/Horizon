"""Read-only hosted funding qualification using two consecutive fresh services.

No publisher or write token. The second execution restores the first execution's
folder and intel trees, rather than starting again from repository seed records.
"""

import asyncio
import hashlib
import json
import os
import shutil
from pathlib import Path

from src.research.branches import resolve
from src.research.funding.models import Applicant, Opportunity
from src.research.funding.storage import OpportunityFolderStorage
from src.research.profiles import ROOT
from src.research.publisher import validate
from src.research.reporting import Archive, atomic, dumps
from src.research.service import ResearchService


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def verify_folders(root):
    folder = root / "research/funding-de-eu"
    index = json.loads((folder / "index.json").read_text())
    records = [Opportunity.model_validate_json((folder / row["record"]).read_text()) for row in index["opportunities"]]
    before = snapshot(folder)
    applicant = Applicant.model_validate_json((ROOT / "config/funding-applicant.json").read_text())
    OpportunityFolderStorage(folder, applicant).sync(records)
    if snapshot(folder) != before:
        raise ValueError("Funding projection is not deterministic")
    rows = []
    for row in index["opportunities"]:
        entity = (folder / row["record"]).parent
        events = [json.loads(line) for line in (entity / "change-history.jsonl").read_text().splitlines()]
        if not (folder / row["overview"]).is_file() or len(list(entity.glob("00_OVERVIEW__*.md"))) != 1:
            raise ValueError("Missing or duplicate overview")
        rows.append({"opportunity_id": row["opportunity_id"], "folder": entity.name, "deadline": row["deadline"], "eligibility_status": row["eligibility_status"], "history_events": len(events)})
    return {"active_count": index["active_count"], "review_count": index["review_count"], "rows": rows, "tree_sha256": hashlib.sha256(dumps(before).encode()).hexdigest()}


async def qualify(output):
    if output.exists():
        raise ValueError("Qualification output must be fresh")
    proofs = []
    for number in (1, 2):
        root = output / f"execution-{number}"
        seed = ROOT if number == 1 else output / "execution-1"
        shutil.copytree(seed / "research/funding-de-eu", root / "research/funding-de-eu")
        if number == 2:
            shutil.copytree(seed / "intel", root / "intel")
        service = ResearchService(root)
        job = await service.submit({"profile_id": "funding/de-eu", "depth": 3}, requested_by="github_actions")
        done = await service.wait(job["job_id"])
        if done["status"] not in ("completed", "partial"):
            raise ValueError("Funding research failed: " + str(done.get("error")))
        report = Archive(root).get(done["report_id"])
        records = report["statistics"]["funding"]["opportunities"]
        fresh = sum(any(r["verified"] and r["retrieved_at"] == item["checked_at"] for r in item["resources"]) for item in records)
        if fresh != 3:
            raise ValueError("Not all three official pages were collected under existing guards")
        validate(root)
        state = verify_folders(root)
        if state["active_count"] != 0 or state["review_count"] != 3:
            raise ValueError("Qualification must not promote unreviewed applicant eligibility")
        proofs.append({"execution": number, "report_id": done["report_id"], "report_status": report["status"], "fresh_official_pages": fresh, "comparison_report_id": report["history"].get("previous_report_id"), "collection_errors": {r["opportunity_id"]: r["collection_error"] for r in records}, **state})
    first, second = proofs
    if second["comparison_report_id"] != first["report_id"]:
        raise ValueError("Second service did not restore the first report")
    for a, b in zip(first["rows"], second["rows"], strict=True):
        if any(a[k] != b[k] for k in ("opportunity_id", "folder", "deadline", "eligibility_status")) or b["history_events"] <= a["history_events"]:
            raise ValueError("Consecutive funding state lost identity, path or history")
    return proofs


async def main():
    selected = await resolve(os.getenv("RESEARCH_REF", ""), os.environ["GITHUB_REPOSITORY"])
    if selected["sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Qualification must execute the same approved source revision")
    root = ROOT / "data/funding-qualification"
    proof = {"workflow_run_id": os.environ["GITHUB_RUN_ID"], "source_sha": selected["sha"], "read_only": True, "execution_environment": "one GitHub-hosted job, two fresh service instances with explicit state restoration", "executions": await qualify(root)}
    atomic(root / "proof.json", dumps(proof))
    compact = json.dumps(proof, separators=(",", ":"))
    if len(compact.encode()) > 3900:
        raise ValueError("Public proof exceeds annotation ceiling")
    print("::notice title=funding-qualification-json::" + compact.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D"))


if __name__ == "__main__":
    asyncio.run(main())
