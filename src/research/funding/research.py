"""User-authored seed -> research nominations -> reviewed official-source refresh.

Seed prose is untrusted historical context, never verified evidence, applicant
facts, executable instructions, or outbound model/search prompts.
"""

import hashlib
import html
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import markdown
from bs4 import BeautifulSoup
from typing import Literal
from pydantic import Field, field_validator, model_validator

from ..collector import collect
from ..profiles import ROOT, Strict, Query, load_profiles, safe_url
from ..reporting import atomic, dumps

SEED = "research/funding-de-eu/Funding DK (DE missing).md"
LIMITATIONS = ["Seed notes and search results are nominations, not verified opportunities, deadlines or eligibility.", "Only config/funding-sources.json authorizes official source collection."]


def safe_metrics(metrics):
    return [{"source": m.get("source") if m.get("source") in {"google_news", "gdelt", "rss", "discovery"} else "discovery", "status": "ok" if m.get("status") == "ok" else "failed"} for m in metrics[:50]]


class ResearchPolicy(Strict):
    schema_version: str = Field(pattern=r"^1\.0$")
    seed_document: str = Field(pattern=r"^research/funding-de-eu/Funding DK \(DE missing\)\.md$")
    schedule_enabled: bool = False
    review_pr_enabled: bool = False
    max_candidates: int = Field(ge=1, le=200)
    max_search_results: int = Field(ge=1, le=40)
    regions: list[str] = Field(max_length=10)
    queries: list[Query] = Field(min_length=1, max_length=8)
    generated_branch: str = Field(pattern=r"^automation/funding-research$")
    seed_aliases: dict[str, str] = Field(max_length=30)


def policy():
    return ResearchPolicy.model_validate_json((ROOT / "config/funding-research.json").read_text())


class Nomination(Strict):
    candidate_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    origin: Literal["authored_seed", "public_search"]
    label: str = Field(max_length=240)
    headline: str | None = Field(default=None, max_length=300)
    url: str | None
    status: Literal["tracked", "official_source_review_required", "source_discovery_required"]
    approved_opportunity_id: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,96}$")
    seed_line: int | None = Field(default=None, ge=1, le=10000)
    seed_document: Literal["research/funding-de-eu/Funding DK (DE missing).md"] | None = None

    @field_validator("url")
    @classmethod
    def public(cls, value):
        return safe_url(value) if value else None

    @model_validator(mode="after")
    def reference_only(self):
        if self.origin == "authored_seed" and self.headline:
            raise ValueError("Authored prose is not an exported search headline")
        if (self.status == "tracked") != (self.approved_opportunity_id is not None):
            raise ValueError("Tracked references require an approved identity")
        if self.origin == "public_search" and self.approved_opportunity_id:
            raise ValueError("Search cannot authorize an official source")
        if self.url:
            if self.label != urlsplit(self.url).hostname:
                raise ValueError("Nominations retain host labels, not source prose")
        elif self.origin != "authored_seed" or self.seed_line is None or self.label != f"Seed program at line {self.seed_line}":
            raise ValueError("Unlinked nominations require an opaque authored-source reference")
        if self.origin == "public_search" and not self.url:
            raise ValueError("Search nomination needs a public URL")
        return self


class Queue(Strict):
    schema_version: Literal["1.0"] = "1.0"
    seed_document: Literal["research/funding-de-eu/Funding DK (DE missing).md"]
    seed_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidates: list[Nomination] = Field(max_length=200)
    search_metrics: list[dict] = Field(max_length=50)
    coverage: list[str] = Field(max_length=10)
    limitations: list[str] = Field(max_length=10)


def clean_url(url):
    # Remove known tracking and fragment presentation only. Never remove auth
    # parameters to make a secret-bearing URL look public or upgrade HTTP.
    url = re.sub(r"\\([.:/_-])", r"\1", str(url)).rstrip(".,;")
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    parsed = urlsplit(url)
    if re.search(r"token|secret|password|credential|session|api.?key", parsed.fragment, re.I):
        raise ValueError("Credential-bearing URL fragment")
    params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid"} and not (parsed.hostname == "news.google.com" and k == "oc" and re.fullmatch(r"[0-9]{1,3}", v))]
    return safe_url(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), "")))


def key(value):
    value = value.lower().replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def seed_queue(content, config=None):
    config = config or policy()
    if len(content.encode()) > 250_000:
        raise ValueError("Seed document exceeds 250 KB")
    rows, seen = [], set()
    for number, line in enumerate(content.splitlines(), 1):
        # Read only headings in the first table cell and URLs. Other cells may
        # contain personal plans, stale dates and unsupported financial claims.
        cells = re.split(r"(?<!\\)\|", line.strip())
        label = ""
        if line.strip().startswith("|") and len(cells) >= 3:
            label = BeautifulSoup(markdown.markdown(cells[1]), "html.parser").get_text(" ", strip=True)
            if key(label) in {"vc", "name"} or re.fullmatch(r"[:\s-]*", label):
                continue
        normalized = re.sub(r"\\([.:/_-])", r"\1", line)
        soup = BeautifulSoup(markdown.markdown(line), "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True)]
        links += re.findall(r"https?://[^\s<>|\[\]\"]+", normalized)
        urls = []
        for raw in links:
            try:
                url = clean_url(raw)
                if url not in urls:
                    urls.append(url)
            except ValueError:
                continue
        if not label and not urls:
            continue
        approved = next((pid for alias, pid in config.seed_aliases.items() if key(alias) in key(label)), None) if label else None
        for url in urls or [None]:
            identity = "url:" + url if url else "label:" + key(label)
            cid = hashlib.sha256(identity.encode()).hexdigest()[:24]
            if cid in seen:
                continue
            seen.add(cid)
            rows.append({"candidate_id": cid, "origin": "authored_seed", "seed_line": number, "seed_document": SEED,
                         # Avoid copying personal first-cell annotations into the
                         # generated queue. The original document remains readable.
                         "label": urlsplit(url).hostname if url else f"Seed program at line {number}", "url": url,
                         "approved_opportunity_id": approved, "status": "tracked" if approved else "official_source_review_required" if url else "source_discovery_required"})
            if len(rows) >= config.max_candidates:
                return rows
    return rows


async def discover(content, *, previous=None, collector=collect, config=None):
    config = config or policy()
    nominees = seed_queue(content, config)
    p = load_profiles()["funding/de-eu"].model_copy(deep=True)
    p.queries = config.queries
    p.max_queries = len(config.queries)
    p.max_items = config.max_search_results
    p.regions = config.regions
    try:
        items, metrics = await collector(p)
    except Exception:
        items, metrics = [], [{"source": "discovery", "status": "failed", "error_code": "SEARCH_UNAVAILABLE"}]
    for item in items[:config.max_search_results]:
        try:
            url = clean_url(item.url)
        except ValueError:
            continue
        headline = BeautifulSoup(str(getattr(item, "title", "")), "html.parser").get_text(" ", strip=True)[:300] or None
        if not re.search(r"grant|fund|scholarship|fellowship|accelerat|incubat|loan|financ|stipend|foerder|förder|zuschuss|legat|tilskud", (headline or "") + " " + urlsplit(url).path, re.I):
            continue
        nominees.append({"candidate_id": hashlib.sha256(("url:" + url).encode()).hexdigest()[:24], "origin": "public_search", "label": urlsplit(url).hostname,
                         "headline": headline,
                         "url": url, "status": "official_source_review_required", "approved_opportunity_id": None})
    # Retain previous nominations when a search is temporarily empty or fails.
    merged = {}
    for r in nominees:
        merged.setdefault(r["candidate_id"], r)
    for r in (previous or {}).get("candidates", []):
        if r.get("origin") == "authored_seed" and r["candidate_id"] not in merged:
            continue
        merged.setdefault(r["candidate_id"], r)
    candidates = list(merged.values())[:config.max_candidates]
    return {"schema_version": "1.0", "seed_document": SEED, "seed_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "candidates": candidates, "search_metrics": safe_metrics(metrics), "coverage": config.regions, "limitations": LIMITATIONS}


def render_queue(queue, root):
    queue = Queue.model_validate(queue).model_dump(mode="json")
    queue.update(search_metrics=safe_metrics(queue["search_metrics"]), coverage=policy().regions, limitations=LIMITATIONS)
    root = Path(root)
    atomic(root / "RESEARCH_QUEUE.json", dumps(queue))
    lines = ["# Funding research queue", "", "Starting point: [the authored funding document](Funding%20DK%20%28DE%20missing%29.md). Historical dates and notes are not verified facts.", "", "[Verified evidence and current opportunities](README.md) · [Review required](REVIEW_REQUIRED.md)", "", "New sites require official-source review before config/funding-sources.json is extended. Unknown eligibility cannot be promoted by discovery.", ""]
    for origin, title in [("public_search", "New public-search nominations — unverified"), ("authored_seed", "Authored starting-point research references")]:
        selected = [r for r in queue["candidates"] if r["origin"] == origin]
        lines.extend(["## " + title, "", f"Entries: {len(selected)}. These are research tasks, not verified available funding offers.", ""])
        for r in selected:
            # Values are validated public URLs or opaque references; no seed prose.
            target = r.get("url")
            lines.append(f"- `{r['candidate_id']}` — {r['status']} — " + ("<" + quote(safe_url(target), safe="/:%._-~") + ">" if target else f"authored source line {int(r.get('seed_line', 0))}"))
            if r.get("headline"):
                lines[-1] += " — " + html.escape(" ".join(r["headline"].split())).replace("[", "&#91;").replace("]", "&#93;")
        lines.append("")
    atomic(root / "RESEARCH_UPDATES.md", "\n".join(lines).rstrip() + "\n")
