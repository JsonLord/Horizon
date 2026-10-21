"""Deterministic per-entity storage with stable IDs and append-only source history."""

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

from ..reporting import atomic, dumps
from .models import Applicant, Opportunity, assess


def text(value):
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("[", "&#91;").replace("]", "&#93;")


def slug(value):
    value = value.replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-")[:80]
    if not value:
        raise ValueError("Provider/program needs a canonical ASCII folder label")
    return value


def folder_name(record):
    return f"{slug(record.provider)}__{slug(record.program)}__{record.deadline_token}"


def claim(record, key):
    item = record.claims.get(key)
    return text(item.value) + " (" + ", ".join(text(i) for i in item.evidence_ids) + ")" if item else "UNKNOWN — not verified"


def render(record, applicant):
    result = assess(record, applicant)
    verified = [r.retrieved_at.isoformat() for r in record.resources if r.verified]
    overview = f"# {text(record.provider)} — {text(record.program)}\n\n"
    overview += f"Stable ID: `{record.opportunity_id}`\n\nFounder eligibility: **{result['status']}**\n\nApplication status: **{record.application_status}**\n\nDeadline: **{record.deadline_token}**; timezone: {text(record.deadline_timezone or 'UNKNOWN')}\n\nLast official verification: {max(verified) if verified else 'UNKNOWN'}\n\nLast collection attempt: {record.checked_at.isoformat()}\n\n"
    fields = {"Funding amount and type": "funding", "Equity, repayment and co-financing": "obligations", "Berlin / Germany / EU eligibility": "geography", "Unincorporated founder eligibility": "unincorporated", "AI / software suitability": "software_ai", "Research project suitability": "research", "Financing assessment": "financing"}
    overview += "\n".join(f"- {label}: {claim(record, key)}" for label, key in fields.items())
    overview += f"\n- Relevance score: {record.relevance_score if record.relevance_score is not None else 'UNKNOWN'} (heuristic, not a probability)\n- Financing suitability: {record.financing_suitability}\n- Score explanation: {text(record.relevance_explanation or 'Not scored')}\n\n"
    overview += "## Hard conditions\n\n" + ("\n".join("- " + text(c.description) + " (" + ", ".join(c.evidence_ids) + ")" for c in record.conditions) or "UNKNOWN — official conditions not fully verified")
    for title, key in [("Missing prerequisites", "missing_prerequisites"), ("Achievable eligibility milestones", "achievable_milestones"), ("Hard exclusions", "hard_rejections")]:
        overview += f"\n\n## {title}\n\n" + ("\n".join("- " + text(x) for x in result[key]) or "None identified; this does not establish eligibility.")
    overview += "\n\n## Recommended next action\n\n" + result["next_action"] + "\n\n## Official resources\n\n"
    overview += "\n".join(f"- [{text(r.title)}]({quote(r.url, safe=':/%.-_~')}) — {r.kind}; {'verified' if r.verified else 'UNVERIFIED candidate URL'}" for r in record.resources)
    overview += "\n\n[Eligibility](eligibility.md) · [Benefits and costs](benefits-and-costs.md) · [Application guide](application-guide.md) · [Required documents](required-documents.md) · [Evidence](evidence.md) · [Resource register](resources/links.json)\n"
    evidence = "# Official evidence\n\n" + "\n\n".join(f"## {r.resource_id}\n\n[{text(r.title)}]({quote(r.url, safe=':/%.-_~')})\n\nVerified: {r.verified}; retrieved: {r.retrieved_at.isoformat() if r.retrieved_at else 'UNKNOWN'}; SHA-256: {r.content_sha256 or 'UNKNOWN'}\n\n{text(r.quotation or 'No official evidence retrieved.')}" for r in record.resources)
    return {f"00_OVERVIEW__{result['status']}__{record.deadline_token}.md": overview,
            "eligibility.md": "# Eligibility\n\n" + "\n\n".join(claim(record, k) for k in ("geography", "unincorporated", "eligibility_complete")) + "\n\n" + "\n".join(text(c.description) for c in record.conditions),
            "benefits-and-costs.md": "# Benefits and costs\n\n" + "\n\n".join(claim(record, k) for k in ("funding", "obligations", "financing")),
            "application-guide.md": "# Application guide\n\n" + claim(record, "application_steps"),
            "required-documents.md": "# Required documents\n\n" + claim(record, "required_documents"), "evidence.md": evidence,
            "resources/README.md": "# Resource register\n\nSee [links.json](links.json) for official URLs, metadata and verification status. No full pages or documents are copied. Unverified URLs must not be treated as application instructions. Historical resources remain in [sources.json](../sources.json) and [change-history.jsonl](../change-history.jsonl).\n"}


class OpportunityFolderStorage:
    """Upsert records; omitted entities persist. Archiving requires explicit records."""

    def __init__(self, root, applicant):
        self.root = Path(root)
        self.applicant = Applicant.model_validate(applicant)

    def sync(self, records):
        import fcntl
        import shutil
        import tempfile
        self.root.parent.mkdir(parents=True, exist_ok=True)
        # The lock is outside generated contents and is never part of the data archive.
        with (self.root.parent / ("." + self.root.name + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.root.is_symlink() or any(p.is_symlink() for p in self.root.rglob("*")):
                raise ValueError("Symlinks are not permitted in opportunity storage")
            # Render and validate a complete copy before changing the live tree.
            # Failure (including artifact-size limits) leaves old history intact.
            with tempfile.TemporaryDirectory(prefix=".funding-stage-", dir=self.root.parent) as temp:
                staged, backup = Path(temp) / "new", Path(temp) / "old"
                if self.root.exists():
                    shutil.copytree(self.root, staged)
                index = OpportunityFolderStorage(staged, self.applicant)._sync(records)
                if self.root.exists():
                    self.root.rename(backup)
                try:
                    staged.rename(self.root)
                except BaseException:
                    if backup.exists():
                        backup.rename(self.root)
                    raise
                return index

    def _sync(self, records):
        if self.root.is_symlink() or any(p.is_symlink() for p in self.root.rglob("*")):
            raise ValueError("Symlinks are not permitted in opportunity storage")
        current, locations = {}, {}
        for path in self.root.glob("opportunities/*/opportunity.json"):
            record = Opportunity.model_validate_json(path.read_text())
            if record.opportunity_id in current:
                raise ValueError("Duplicate existing opportunity ID")
            current[record.opportunity_id], locations[record.opportunity_id] = record, path.parent
        incoming = [Opportunity.model_validate(r.model_dump() if isinstance(r, Opportunity) else r) for r in records]
        if len({r.opportunity_id for r in incoming}) != len(incoming):
            raise ValueError("Duplicate input opportunity ID")
        current.update({r.opportunity_id: r for r in incoming})
        names = [folder_name(r) for r in current.values()]
        identities = [(slug(r.provider).casefold(), slug(r.program).casefold()) for r in current.values()]
        if len(identities) != len(set(identities)) or len(names) != len(set(n.casefold() for n in names)):
            raise ValueError("Canonical folder collision; use distinct reviewed program names")
        for record in sorted(current.values(), key=lambda r: r.opportunity_id):
            target = self.root / "opportunities" / folder_name(record)
            previous = locations.get(record.opportunity_id)
            if target.exists() and previous != target:
                raise ValueError("Refusing to overwrite another opportunity folder")
            if previous and previous != target:
                previous.rename(target)
            target.mkdir(parents=True, exist_ok=True)
            serialized = record.model_dump(mode="json")
            digest = hashlib.sha256(dumps(serialized).encode()).hexdigest()
            history_path = target / "change-history.jsonl"
            events = [json.loads(line) for line in history_path.read_text().splitlines()] if history_path.exists() else []
            for event in events:
                historical = Opportunity.model_validate(event["record"])
                if event["opportunity_id"] != record.opportunity_id or historical.opportunity_id != record.opportunity_id or hashlib.sha256(dumps(historical.model_dump(mode="json")).encode()).hexdigest() != event["record_sha256"]:
                    raise ValueError("Invalid historical opportunity identity or checksum")
            if not events or events[-1]["record_sha256"] != digest:
                events.append({"opportunity_id": record.opportunity_id, "observed_at": record.checked_at.isoformat(), "record_sha256": digest, "folder": target.name, "record": serialized})
            atomic(history_path, "".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in events))
            atomic(target / "opportunity.json", dumps(serialized))
            resources = {json.dumps(r, sort_keys=True): r for event in events for r in event["record"]["resources"]}
            atomic(target / "sources.json", dumps({"schema_version": "1.0", "resources": list(resources.values())}))
            atomic(target / "resources/links.json", dumps({"schema_version": "1.0", "resources": serialized["resources"]}))
            rendered = render(record, self.applicant)
            current_overview = next(iter(rendered))
            for old in target.glob("00_OVERVIEW__*.md"):
                if old.name != current_overview:
                    old.unlink()
            for path, content in rendered.items():
                atomic(target / path, content.rstrip() + "\n")
        rows = []
        groups = {"ACTIVE_OPPORTUNITIES.md": [], "REVIEW_REQUIRED.md": [], "ARCHIVED_OPPORTUNITIES.md": []}
        for record in sorted(current.values(), key=lambda r: (r.provider.casefold(), r.program.casefold(), r.opportunity_id)):
            result = assess(record, self.applicant)
            archived = record.archived or record.deadline_kind == "discontinued" or result["status"] in ("WATCH_FUTURE_ROUND", "VERIFIED_INELIGIBLE")
            group = "ARCHIVED_OPPORTUNITIES.md" if archived else "ACTIVE_OPPORTUNITIES.md" if result["status"] == "ELIGIBLE_NOW" else "REVIEW_REQUIRED.md"
            path = f"opportunities/{folder_name(record)}/00_OVERVIEW__{result['status']}__{record.deadline_token}.md"
            rows.append({"opportunity_id": record.opportunity_id, "provider": record.provider, "program": record.program, "deadline": record.deadline_token, "application_status": record.application_status, "eligibility_status": result["status"], "archived": archived, "overview": path, "record": f"opportunities/{folder_name(record)}/opportunity.json"})
            groups[group].append(f"- [{text(record.provider)} — {text(record.program)}]({quote(path, safe='/._-')}) — {result['status']}; {record.deadline_token}")
        index = {"schema_version": "1.0", "active_count": len(groups["ACTIVE_OPPORTUNITIES.md"]), "review_count": len(groups["REVIEW_REQUIRED.md"]), "archived_count": len(groups["ARCHIVED_OPPORTUNITIES.md"]), "applicant": self.applicant.model_dump(mode="json"), "opportunities": rows}
        atomic(self.root / "index.json", dumps(index))
        for filename, links in groups.items():
            atomic(self.root / filename, "# " + filename.removesuffix(".md").replace("_", " ").title() + "\n\n" + ("\n".join(links) or "No verified opportunities in this category.") + "\n")
        atomic(self.root / "README.md", "# Germany / EU funding knowledge base\n\nGenerated from each folder's `opportunity.json` and the applicant policy. Unknown facts remain unknown. Application status and founder eligibility are separate. Relevance scores never override hard conditions.\n\n[Active opportunities](ACTIVE_OPPORTUNITIES.md) · [Review required](REVIEW_REQUIRED.md) · [Archived / future rounds](ARCHIVED_OPPORTUNITIES.md) · [Machine index](index.json)\n\nFolders change with verified deadlines; stable IDs and append-only events preserve history. External documents are linked, not copied. See the repository AGENTS.md for updating sources and steering research.\n")
        return index
