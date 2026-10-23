"""Funding maintenance driven by the authored DK/DE/EU starting document.

run: collect/discover into a local proposal artifact; never publish.
apply: validate provenance and re-render that proposal with trusted checkout code.
index: create the initial research queue offline, without source collection.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from src.research.funding.models import Applicant, FundingDataset, Opportunity
from src.research.funding.research import ROOT, SEED, Queue, discover, policy, render_queue, safe_metrics, seed_queue
from src.research.funding.storage import OpportunityFolderStorage, funding_dashboard
from src.research.reporting import Archive, atomic, dumps
from src.research.publisher import validate
from src.research.service import ResearchService


def seed():
    path = ROOT / SEED
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("The authored funding starting document is missing or unsafe")
    return path.read_text()


def verify_bundle(payload, source_sha):
    if payload.get("schema_version") != "1.0" or payload.get("report_status") not in {"complete", "partial", "failed", "no_new_items"}:
        raise ValueError("Invalid funding proposal contract")
    if payload.get("source_sha") != source_sha or payload.get("seed_sha256") != hashlib.sha256(seed().encode()).hexdigest():
        raise ValueError("Proposal source revision or authored document changed")
    dataset = FundingDataset.model_validate(payload["funding"])
    approved = {s["opportunity_id"]: s for s in json.loads((ROOT / "config/funding-sources.json").read_text())["sources"]}
    for record in dataset.opportunities:
        entry = approved.get(record.opportunity_id)
        if not entry or record.official_domains != entry["official_domains"] or (record.provider, record.program) != (entry["provider"], entry["program"]):
            raise ValueError("Unreviewed source or entity cannot enter the opportunity store")
    queue = Queue.model_validate(payload["queue"])
    if queue.seed_sha256 != payload["seed_sha256"]:
        raise ValueError("Queue cites another source document")
    if any(c.approved_opportunity_id and c.approved_opportunity_id not in approved for c in queue.candidates):
        raise ValueError("Nomination claims an unapproved tracked identity")
    authored = {c["candidate_id"]: c for c in seed_queue(seed())}
    for candidate in queue.candidates:
        if candidate.origin == "authored_seed" and (candidate.candidate_id not in authored or any(getattr(candidate, k) != authored[candidate.candidate_id].get(k) for k in ("seed_line", "url", "approved_opportunity_id"))):
            raise ValueError("Nomination does not match the authored starting point")
    return dataset, queue


async def run(output, *, discovery=discover):
    content = seed()
    if output.exists():
        raise ValueError("Use a fresh proposal output directory")
    # Restore committed records and histories, including the authored seed file.
    shutil.copytree(ROOT / "research/funding-de-eu", output / "research/funding-de-eu")
    service = ResearchService(output)
    job = await service.submit({"profile_id": "funding/de-eu", "depth": 40}, requested_by="github_actions" if os.getenv("GITHUB_ACTIONS") == "true" else "local_cli")
    done = await service.wait(job["job_id"])
    if not done.get("report_id"):
        raise ValueError("Research did not produce a structured report")
    report = Archive(output).get(done["report_id"])
    validate(output)
    previous_path = ROOT / "research/funding-de-eu/RESEARCH_QUEUE.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else None
    queue = await discovery(content, previous=previous)
    payload = {"schema_version": "1.0", "source_sha": os.getenv("GITHUB_SHA") or "local", "seed_sha256": hashlib.sha256(content.encode()).hexdigest(),
               "workflow_run_id": os.getenv("GITHUB_RUN_ID"), "report_status": report["status"], "funding": report["statistics"]["funding"], "queue": queue}
    verify_bundle(payload, payload["source_sha"])
    atomic(output / "proposal.json", dumps(payload))
    render_queue(queue, output / "research/funding-de-eu")
    atomic(output / "SUMMARY.md", f"# Funding maintenance proposal\n\nSource: `{payload['source_sha']}`\n\nExisting-source refresh: {report['status']}. Research nominations: {len(queue['candidates'])}. Nominations do not establish eligibility or current deadlines. Review failures and evidence before accepting changes.\n")
    return payload


def allowed_path(path):
    import re
    return path in {"Funding DK (DE missing).md", "research/funding-de-eu/index.json", "research/funding-de-eu/README.md", "research/funding-de-eu/ACTIVE_OPPORTUNITIES.md", "research/funding-de-eu/REVIEW_REQUIRED.md", "research/funding-de-eu/ARCHIVED_OPPORTUNITIES.md", "research/funding-de-eu/RESEARCH_QUEUE.json", "research/funding-de-eu/RESEARCH_UPDATES.md"} or bool(re.fullmatch(r"research/funding-de-eu/opportunities/[A-Za-z0-9_-]+/(opportunity\.json|sources\.json|change-history\.jsonl|eligibility\.md|benefits-and-costs\.md|application-guide\.md|required-documents\.md|evidence\.md|00_OVERVIEW__[A-Z_]+__[A-Z0-9-]+\.md)", path)) or bool(re.fullmatch(r"research/funding-de-eu/opportunities/[A-Za-z0-9_-]+/resources/(README\.md|links\.json)", path))


async def propose(payload, source_sha, *, api, destination=None):
    if not policy().review_pr_enabled:
        return {"status": "disabled_pending_review", "writes": 0}
    if os.getenv("GITHUB_REF") != "refs/heads/main" or not os.getenv("GITHUB_WORKFLOW_REF", "").endswith("/.github/workflows/funding-research.yml@refs/heads/main") or source_sha != os.getenv("GITHUB_SHA"):
        raise PermissionError("Only reviewed default-branch workflow code can create a review PR")
    changed = apply(payload, source_sha=source_sha, destination=destination)
    if not changed:
        return {"status": "no_change", "writes": 0}
    destination = Path(destination or ROOT)
    values = {str(p.relative_to(destination)):p.read_text() for p in (destination/'research/funding-de-eu').rglob('*') if p.is_file() and allowed_path(str(p.relative_to(destination)))}
    values['Funding DK (DE missing).md']=(destination/'Funding DK (DE missing).md').read_text()
    values.update({p:None for p in changed if not (destination/p).exists()})
    from src.research.funding.review import publish_review
    return await publish_review(api, files=values, base_ref='main', base_sha=source_sha,
                                branch=policy().generated_branch, complete_data_tree=True,
                                title='Review funding research updates and new nominations',
                                body='Official-source refresh status: '+payload['report_status']+'. Review incomplete evidence and nominations; no eligibility promotion or automatic merge.\n\nSource revision: '+source_sha)


def apply(payload, *, source_sha, destination=None):
    dataset, queue = verify_bundle(payload, source_sha)
    destination = Path(destination or ROOT)
    base = destination / "research/funding-de-eu"
    before = {str(p.relative_to(destination)): p.read_bytes() for p in base.rglob("*") if p.is_file()}
    dashboard = destination / "Funding DK (DE missing).md"
    if dashboard.exists():
        before[dashboard.name] = dashboard.read_bytes()
    original = (base / "Funding DK (DE missing).md").read_bytes()
    applicant = Applicant.model_validate_json((ROOT / "config/funding-applicant.json").read_text())
    index = OpportunityFolderStorage(base, applicant).sync(dataset.opportunities)
    render_queue(queue.model_dump(mode="json"), base)
    atomic(dashboard, funding_dashboard(index))
    if (base / "Funding DK (DE missing).md").read_bytes() != original:
        raise ValueError("Authored source must never be rewritten")
    after = {str(p.relative_to(destination)): p.read_bytes() for p in base.rglob("*") if p.is_file()}
    after[dashboard.name] = dashboard.read_bytes()
    changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
    if any(not allowed_path(p) for p in changed):
        raise ValueError("Generated change escaped the data-only allowlist")
    return changed


def public_proof(payload):
    """Bounded public run evidence; never export seed prose or transport errors."""
    records = payload["funding"]["opportunities"]
    return {"workflow_run_id": payload["workflow_run_id"], "source_sha": payload["source_sha"],
            "seed_sha256": payload["seed_sha256"], "read_only": True,
            "report_status": payload["report_status"],
            "nomination_counts": dict(Counter(c["origin"] for c in payload["queue"]["candidates"])),
            "search_metrics": safe_metrics(payload["queue"]["search_metrics"])[:8],
            "opportunity_count": len(records),
            "successful_refresh_count": sum(not bool(r.get("collection_error")) for r in records),
            "opportunity_details_truncated": len(records) > 8,
            "opportunities": [{"opportunity_id": r["opportunity_id"],
                               "refresh_ok": not bool(r.get("collection_error")),
                               "eligibility_complete": r["eligibility_complete"],
                               "deadline": r["deadline"]} for r in records[:8]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "apply", "propose", "index"])
    parser.add_argument("--output", type=Path, default=ROOT / "data/funding-update")
    parser.add_argument("--check", action="store_true", help="Validate authored input and stored queue without rewriting either")
    args = parser.parse_args()
    if args.command == "run":
        result = asyncio.run(run(args.output))
        if result["report_status"] == "failed":
            print("::warning title=Funding refresh incomplete::Official-source refresh failed; retained evidence and discovery nominations need review. This is not a verified-current funding report.")
        print(json.dumps({"report_status": result["report_status"], "candidates": len(result["queue"]["candidates"])}))
        if os.getenv("GITHUB_ACTIONS") == "true":
            proof = json.dumps(public_proof(result), separators=(",", ":"))
            if len(proof.encode()) > 3900:
                raise ValueError("Public funding proof exceeds annotation ceiling")
            print("::notice title=funding-maintenance-proof::" + proof.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D"))
    elif args.command in ("apply", "propose"):
        if not policy().review_pr_enabled or os.getenv("GITHUB_REF") != "refs/heads/main" or not os.getenv("GITHUB_WORKFLOW_REF", "").endswith("/.github/workflows/funding-research.yml@refs/heads/main"):
            raise PermissionError("Review proposals require enabled, reviewed default-branch workflow code")
        payload_path = args.output / "proposal.json"
        if payload_path.is_symlink() or payload_path.stat().st_size > 1_000_000:
            raise ValueError("Unsafe proposal artifact")
        payload = json.loads(payload_path.read_text())
        if args.command == "propose":
            from src.research.programs.review import ReviewAPI
            print(json.dumps(asyncio.run(propose(payload, os.environ["GITHUB_SHA"], api=ReviewAPI(os.environ["GITHUB_REPOSITORY"])))))
        else:
            print(json.dumps({"changed_paths": apply(payload, source_sha=os.environ["GITHUB_SHA"])}))
    else:
        if args.check:
            content = seed()
            candidates = seed_queue(content)
            stored = ROOT / "research/funding-de-eu/RESEARCH_QUEUE.json"
            previous = Queue.model_validate_json(stored.read_text()) if stored.exists() else None
            print(json.dumps({"valid": True, "seed_candidates": len(candidates), "queue_needs_refresh": previous is None or previous.seed_sha256 != hashlib.sha256(content.encode()).hexdigest()}))
            return
        async def offline(profile):
            return [], []
        content = seed()
        previous = ROOT / "research/funding-de-eu/RESEARCH_QUEUE.json"
        queue = asyncio.run(discover(content, collector=offline, previous=json.loads(previous.read_text()) if previous.exists() else None))
        render_queue(queue, ROOT / "research/funding-de-eu")
        print(json.dumps({"seed_candidates": len(queue["candidates"]), "seed_sha256": queue["seed_sha256"]}))


if __name__ == "__main__":
    main()
