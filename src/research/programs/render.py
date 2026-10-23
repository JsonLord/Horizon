"""Deterministic Markdown, with escaped untrusted text and explicit unknowns."""

import html
from urllib.parse import quote

from .models import Dataset


def cell(value):
    return html.escape(str(value) if value is not None else "unknown").replace("|", "&#124;").replace("\n", " ").replace("`", "&#96;")


def link(url, label="primary source"):
    return f"[{cell(label)}]({quote(url, safe=':/?=&%#-_.~')})"


def render_dataset(dataset):
    dataset = Dataset.model_validate(dataset) if isinstance(dataset, dict) else dataset
    lines = ["# Incubator and Programs", "", f"Policy: {cell(dataset.policy_version)} (provisional). Observed: {cell(dataset.observed_at)}.", "", "Scores are heuristics, not probabilities. Unknown eligibility and availability require review; coverage is not exhaustive.", "", "| Program | Current status / deadline | Eligibility | Benefit / terms | Fit / decision | Evidence |", "| --- | --- | --- | --- | --- | --- |"]
    for p in sorted(dataset.programs, key=lambda p: (p.legacy is None, -p.fit.fit_score, p.program_id)):
        deadline = cell(p.deadline)
        if p.deadline and "deadline" in p.stale_fields:
            deadline += " (stale; review)"
        if p.legacy and p.legacy.get("deadline"):
            deadline += "; historical note " + cell(p.legacy["deadline"]) + " (unverified current deadline)"
        urls = list(dict.fromkeys(e.url for e in p.source_evidence))
        evidence = "; ".join(link(u) for u in urls) or (link(p.original_url, "unverified legacy/nomination URL") if p.original_url else "no authoritative source supplied")
        lines.append(f"| {cell(p.name)} | {p.application_status}; {deadline} | {cell(p.eligibility)}; {p.fit.hard_eligibility} | {cell(p.benefits)}; equity: {cell(p.equity_terms)}; cost: {cell(p.cost_terms)} | {p.fit.fit_score:.4f}; {p.fit.decision} | {evidence} |")
    lines += ["", "## Changes and limitations", ""]
    for p in dataset.programs:
        labels = ", ".join(c["type"] for c in p.material_changes) or "seed import / not verified"
        lines.append(f"- {cell(p.name)}: {cell(labels)}; extraction={p.extraction_status}; last checked {cell(p.last_checked)}; model={cell(p.fit.model.get('status', 'model_unavailable'))}.")
        if p.check_error:
            lines.append(f"  - Check gap: {cell(p.check_error)}. Prior facts may be stale; no inferred opening or closure.")
    lines += ["", f"Coverage: {cell(dataset.coverage)}", "", "Machine-readable records preserve exact evidence IDs, bounded quotations, timestamps, content fingerprints and per-fact last verification. No private founder profile is included."]
    return "\n".join(lines) + "\n"


def render_report(report):
    dataset = Dataset.model_validate(report["statistics"]["programs"])
    return render_dataset(dataset) + "\n## Snapshot provenance\n\n" + f"Report: {cell(report['report_id'])}; research status: {report['status']}.\n\n" + f"History: {cell(report.get('history', {}))}\n"
