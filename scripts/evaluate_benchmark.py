"""Deterministic, offline evaluation of the Stage 1 two-stage relevance gate.

This harness replays the permanent benchmark
``data/benchmarks/two_stage_relevance_benchmark.json`` through the *deterministic*
Stage 1 prioritization signals in :mod:`src.research.two_stage_signals` and
reports category-level and aggregate metrics.

Design constraints:

* **Zero network / zero provider calls.** Only pure functions from
  ``two_stage_signals`` are used. No HTTP client, no ``DecisionModelProvider``,
  no model SDK is imported or constructed. The runner is safe to execute in CI
  with no credentials.
* **No invented labels.** The benchmark's own ``expected_label`` values are the
  ground truth; the runner never rewrites them.
* **Honest reporting.** Gates that fail are reported as failures. The runner
  measures the gate, it does not make the gate pass.

Usage::

    python -m scripts.evaluate_benchmark [--format text|json|markdown]
                                        [--benchmark PATH] [--strict]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.research.live_review import Candidate, Evidence
from src.research.two_stage_signals import (
    calculate_priority_score,
    evidence_quality,
    is_protected_candidate,
)

#: A candidate is screened out by Stage 1 when its priority score is below this
#: threshold *and* it is not protected by a long-tail / in-scope rule.
SCREEN_OUT_THRESHOLD = 25

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "data" / "benchmarks" / "two_stage_relevance_benchmark.json"

#: Fixed, zoned timestamps keep the evaluation byte-for-byte reproducible.
FIXED_PUBLISHED_AT = "2026-11-20T10:00:00Z"
FIXED_RETRIEVED_AT = "2026-11-20T11:00:00Z"

#: ``Evidence.excerpt`` is capped at 500 characters by its validator.
MAX_EXCERPT_LEN = 500

#: Source types treated as primary evidence (official / upstream releases).
PRIMARY_SOURCE_TYPES = frozenset({"github", "official", "arxiv", "academic"})

SUPPORTED_LANGUAGES = frozenset({"en", "de", "fr"})

#: Categories whose members must survive Stage 1 (no screen-outs allowed).
RETENTION_CATEGORIES = (
    "relevant_findings",
    "keyword_missed_stories",
    "difficult_multilingual_examples",
)

#: Categories that are reported but carry no retention/rejection gate.
INFORMATIONAL_CATEGORIES = (
    "borderline_findings",
    "duplicate_and_evolving_stories",
)

#: Categories whose members must be screened out by Stage 1.
REJECTION_CATEGORIES = ("irrelevant_findings",)

#: Categories whose members must be flagged as under-evidenced.
ABSTENTION_CATEGORIES = ("insufficient_evidence_examples",)

ALL_CATEGORIES = (
    "relevant_findings",
    "borderline_findings",
    "irrelevant_findings",
    "difficult_multilingual_examples",
    "keyword_missed_stories",
    "duplicate_and_evolving_stories",
    "insufficient_evidence_examples",
)


# --------------------------------------------------------------------------- #
# Benchmark loading and case -> Candidate conversion
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BenchmarkCase:
    """One benchmark row, normalized from the JSON document."""

    case_id: str
    category: str
    domain: str
    title: str
    url: str
    excerpt: str
    language: str
    source_type: str
    expected_label: str
    notes: str = ""


def load_benchmark(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and structurally validate the benchmark document."""
    benchmark_path = Path(path) if path is not None else DEFAULT_BENCHMARK
    if not benchmark_path.is_file():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    categories = data.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("Benchmark document has no 'categories' object")

    missing = [name for name in ALL_CATEGORIES if name not in categories]
    if missing:
        raise ValueError(f"Benchmark missing required categories: {', '.join(missing)}")

    return data


def iter_cases(data: Dict[str, Any]) -> Iterable[BenchmarkCase]:
    """Yield every benchmark case in document order, category by category."""
    categories = data["categories"]
    for category in ALL_CATEGORIES:
        for raw in categories[category]:
            yield BenchmarkCase(
                case_id=str(raw["id"]),
                category=category,
                domain=str(raw["domain"]),
                title=str(raw["title"]),
                url=str(raw.get("url") or ""),
                excerpt=str(raw.get("excerpt") or ""),
                language=str(raw.get("language") or "unknown"),
                source_type=str(raw.get("source_type") or "unknown"),
                expected_label=str(raw.get("expected_label") or "UNKNOWN"),
                notes=str(raw.get("notes") or ""),
            )


def case_to_candidate(case: BenchmarkCase) -> Candidate:
    """Convert a benchmark case into a ``Candidate`` with one attached ``Evidence``."""
    language = case.language if case.language in SUPPORTED_LANGUAGES else "unknown"
    excerpt = case.excerpt[:MAX_EXCERPT_LEN]
    url = case.url or f"https://benchmark.invalid/{case.case_id}"

    evidence = Evidence(
        id=f"src-{case.case_id}",
        url=url,
        publisher="benchmark",
        title=case.title[:MAX_EXCERPT_LEN],
        excerpt=excerpt,
        language=language,
        language_basis="benchmark_metadata",
        discovery_language=language,
        published_at=FIXED_PUBLISHED_AT,
        retrieved_at=FIXED_RETRIEVED_AT,
        primary=case.source_type in PRIMARY_SOURCE_TYPES,
        fresh=True,
        source_type=case.source_type,
    )

    return Candidate(
        id=f"cand-{case.case_id}",
        event_id=f"event-{case.case_id}",
        title=case.title,
        url=url,
        evidence=[evidence],
    )


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CaseResult:
    """Stage 1 outcome for a single benchmark case."""

    case_id: str
    category: str
    domain: str
    language: str
    expected_label: str
    priority_score: int
    protected: bool
    screened_out: bool
    evidence_quality: str
    evidence_reason: str

    @property
    def retained(self) -> bool:
        return not self.screened_out

    def as_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "domain": self.domain,
            "language": self.language,
            "expected_label": self.expected_label,
            "priority_score": self.priority_score,
            "protected": self.protected,
            "screened_out": self.screened_out,
            "retained": self.retained,
            "evidence_quality": self.evidence_quality,
            "evidence_reason": self.evidence_reason,
        }


def evaluate_case(case: BenchmarkCase) -> CaseResult:
    """Run the deterministic Stage 1 gate for one benchmark case."""
    candidate = case_to_candidate(case)
    score = calculate_priority_score(candidate, case.domain)
    protected = is_protected_candidate(candidate, case.domain)
    quality = evidence_quality(candidate)

    return CaseResult(
        case_id=case.case_id,
        category=case.category,
        domain=case.domain,
        language=case.language,
        expected_label=case.expected_label,
        priority_score=score,
        protected=protected,
        screened_out=(score < SCREEN_OUT_THRESHOLD and not protected),
        evidence_quality=str(quality["quality"]),
        evidence_reason=str(quality["reason"]),
    )


def evaluate_benchmark(data: Dict[str, Any]) -> List[CaseResult]:
    """Evaluate every case in the benchmark document."""
    return [evaluate_case(case) for case in iter_cases(data)]


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def _pct(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value * 100.0, 1)


@dataclass
class CategoryMetric:
    """Aggregate metric for one benchmark category."""

    category: str
    total: int = 0
    retained: int = 0
    screened_out: int = 0
    expected_retention: Optional[bool] = None
    recall_pct: Optional[float] = None
    rejection_pct: Optional[float] = None
    screen_out_ids: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "total": self.total,
            "retained": self.retained,
            "screened_out": self.screened_out,
            "expected_retention": self.expected_retention,
            "recall_pct": self.recall_pct,
            "rejection_pct": self.rejection_pct,
            "screen_out_ids": list(self.screen_out_ids),
        }


def category_metrics(results: Sequence[CaseResult]) -> List[CategoryMetric]:
    """Compute per-category retention/rejection metrics."""
    metrics: List[CategoryMetric] = []
    for category in ALL_CATEGORIES:
        rows = [r for r in results if r.category == category]
        if not rows:
            continue
        screened = [r for r in rows if r.screened_out]
        retained = len(rows) - len(screened)
        metric = CategoryMetric(
            category=category,
            total=len(rows),
            retained=retained,
            screened_out=len(screened),
            screen_out_ids=[r.case_id for r in screened],
        )
        if category in RETENTION_CATEGORIES:
            metric.expected_retention = True
            metric.recall_pct = _pct(_ratio(retained, len(rows)))
        elif category in REJECTION_CATEGORIES:
            metric.expected_retention = False
            metric.rejection_pct = _pct(_ratio(len(screened), len(rows)))
        metrics.append(metric)
    return metrics


def multilingual_metrics(results: Sequence[CaseResult]) -> Dict[str, Dict[str, Any]]:
    """Per-language retention accuracy on the difficult multilingual examples."""
    rows = [r for r in results if r.category == "difficult_multilingual_examples"]
    breakdown: Dict[str, Dict[str, Any]] = {}
    for language in ("en", "de", "fr"):
        subset = [r for r in rows if r.language == language]
        detected = sum(1 for r in subset if r.retained)
        breakdown[language] = {
            "total": len(subset),
            "retained": detected,
            "screened_out": len(subset) - detected,
            "accuracy_pct": _pct(_ratio(detected, len(subset))),
            "screen_out_ids": [r.case_id for r in subset if r.screened_out],
        }
    return breakdown


def evidence_quality_breakdown(results: Sequence[CaseResult]) -> Dict[str, int]:
    """Count evidence-quality verdicts across every case."""
    counts: Dict[str, int] = {}
    for result in results:
        counts[result.evidence_quality] = counts.get(result.evidence_quality, 0) + 1
    return dict(sorted(counts.items()))


@dataclass
class GateResult:
    """A single pass/fail gate derived from the metrics."""

    name: str
    passed: bool
    detail: str
    requirement: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "requirement": self.requirement,
            "detail": self.detail,
        }


def evaluate_gates(
    results: Sequence[CaseResult],
    metrics: Sequence[CategoryMetric],
    multilingual: Dict[str, Dict[str, Any]],
) -> List[GateResult]:
    """Derive the quality gates the benchmark is meant to protect."""
    by_category = {m.category: m for m in metrics}
    gates: List[GateResult] = []

    def gate(name: str, passed: bool, requirement: str, detail: str) -> None:
        gates.append(GateResult(name=name, passed=passed, requirement=requirement, detail=detail))

    relevant = by_category.get("relevant_findings")
    if relevant is not None:
        gate(
            "relevant_findings_recall",
            relevant.screened_out == 0,
            "100% recall on relevant_findings (0 false negatives)",
            f"{relevant.retained}/{relevant.total} retained"
            + (f"; screened out: {', '.join(relevant.screen_out_ids)}" if relevant.screen_out_ids else ""),
        )

    missed = by_category.get("keyword_missed_stories")
    if missed is not None:
        gate(
            "keyword_missed_stories_recall",
            missed.screened_out == 0,
            "100% recall on keyword_missed_stories (EU-China competitiveness, Iran-US peace talks, COP31)",
            f"{missed.retained}/{missed.total} retained"
            + (f"; screened out: {', '.join(missed.screen_out_ids)}" if missed.screen_out_ids else ""),
        )

    for language in ("en", "de", "fr"):
        entry = multilingual[language]
        if entry["total"] == 0:
            continue
        gate(
            f"multilingual_recall_{language}",
            entry["screened_out"] == 0,
            f"100% retention on difficult {language.upper()} examples",
            f"{entry['retained']}/{entry['total']} retained"
            + (f"; screened out: {', '.join(entry['screen_out_ids'])}" if entry["screen_out_ids"] else ""),
        )

    irrelevant = by_category.get("irrelevant_findings")
    if irrelevant is not None:
        gate(
            "irrelevant_findings_rejection",
            irrelevant.screened_out == irrelevant.total,
            "100% rejection of irrelevant sports / gadget / homonym articles",
            f"{irrelevant.screened_out}/{irrelevant.total} screened out"
            + (
                f"; leaked: {', '.join(r.case_id for r in results if r.category == 'irrelevant_findings' and r.retained)}"
                if irrelevant.screened_out != irrelevant.total
                else ""
            ),
        )

    abstain_rows = [r for r in results if r.category in ABSTENTION_CATEGORIES]
    if abstain_rows:
        unsupported = [r for r in abstain_rows if r.evidence_quality == "SUPPORTED"]
        gate(
            "insufficient_evidence_abstention",
            not unsupported,
            "Every insufficient_evidence_examples case flagged as under-evidenced (never SUPPORTED)",
            f"{len(abstain_rows) - len(unsupported)}/{len(abstain_rows)} flagged"
            + (f"; wrongly supported: {', '.join(r.case_id for r in unsupported)}" if unsupported else ""),
        )

    return gates


def build_report(data: Dict[str, Any], results: Sequence[CaseResult]) -> Dict[str, Any]:
    """Assemble the full structured evaluation report."""
    metrics = category_metrics(results)
    multilingual = multilingual_metrics(results)
    gates = evaluate_gates(results, metrics, multilingual)

    total = len(results)
    screened_out = sum(1 for r in results if r.screened_out)
    protected_count = sum(1 for r in results if r.protected)

    return {
        "benchmark": {
            "name": data.get("name"),
            "version": data.get("version"),
            "description": data.get("description"),
        },
        "configuration": {
            "screen_out_threshold": SCREEN_OUT_THRESHOLD,
            "screen_out_rule": "priority_score < threshold and not is_protected_candidate",
            "network_access": False,
            "provider_calls": 0,
        },
        "aggregate": {
            "cases": total,
            "retained": total - screened_out,
            "screened_out": screened_out,
            "protected": protected_count,
            "retention_pct": _pct(_ratio(total - screened_out, total)),
            "gates_passed": sum(1 for g in gates if g.passed),
            "gates_failed": sum(1 for g in gates if not g.passed),
        },
        "categories": [m.as_dict() for m in metrics],
        "multilingual": multilingual,
        "evidence_quality": evidence_quality_breakdown(results),
        "gates": [g.as_dict() for g in gates],
        "cases": [r.as_dict() for r in results],
    }


def run_evaluation(benchmark_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the benchmark, evaluate every case, and return the report."""
    data = load_benchmark(benchmark_path)
    results = evaluate_benchmark(data)
    return build_report(data, results)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[str]:
    """Render a plain-text table without third-party dependencies."""
    cells = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in cells:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(values: Sequence[str]) -> str:
        return "| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(values)) + " |"

    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    output = [separator, line(list(headers)), separator]
    for row in cells:
        output.append(line(row))
    output.append(separator)
    return output


def _fmt_pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def render_text(report: Dict[str, Any]) -> str:
    """Render the report as a human-readable text summary."""
    benchmark = report["benchmark"]
    aggregate = report["aggregate"]
    lines: List[str] = []

    lines.append(f"Two-stage relevance benchmark: {benchmark['name']} v{benchmark['version']}")
    lines.append(
        f"Stage 1 screen-out rule: {report['configuration']['screen_out_rule']} "
        f"(threshold={report['configuration']['screen_out_threshold']})"
    )
    lines.append("")
    lines.extend(
        _table(
            ["Category", "Cases", "Retained", "Screened out", "Recall", "Rejection"],
            [
                [
                    m["category"],
                    m["total"],
                    m["retained"],
                    m["screened_out"],
                    _fmt_pct(m["recall_pct"]),
                    _fmt_pct(m["rejection_pct"]),
                ]
                for m in report["categories"]
            ],
        )
    )
    lines.append("")
    lines.append(
        f"Aggregate: {aggregate['cases']} cases, {aggregate['retained']} retained, "
        f"{aggregate['screened_out']} screened out ({_fmt_pct(aggregate['retention_pct'])} retention), "
        f"{aggregate['protected']} protected by long-tail / in-scope rules."
    )
    lines.append("")
    lines.append("Multilingual robustness (difficult_multilingual_examples):")
    lines.extend(
        _table(
            ["Language", "Cases", "Retained", "Screened out", "Accuracy"],
            [
                [
                    language.upper(),
                    entry["total"],
                    entry["retained"],
                    entry["screened_out"],
                    _fmt_pct(entry["accuracy_pct"]),
                ]
                for language, entry in report["multilingual"].items()
            ],
        )
    )
    lines.append("")
    lines.append("Evidence quality breakdown:")
    lines.extend(
        _table(
            ["Quality", "Cases"],
            [[quality, count] for quality, count in report["evidence_quality"].items()],
        )
    )
    lines.append("")
    lines.append(
        f"Gates: {aggregate['gates_passed']} passed, {aggregate['gates_failed']} failed."
    )
    lines.extend(
        _table(
            ["Gate", "Status", "Requirement", "Detail"],
            [
                [gate["name"], "PASS" if gate["passed"] else "FAIL", gate["requirement"], gate["detail"]]
                for gate in report["gates"]
            ],
        )
    )
    return "\n".join(lines)


def render_markdown(report: Dict[str, Any]) -> str:
    """Render the report as a Markdown document suitable for a PR comment."""
    benchmark = report["benchmark"]
    aggregate = report["aggregate"]
    lines: List[str] = []

    lines.append(f"# Two-stage relevance benchmark: {benchmark['name']} v{benchmark['version']}")
    lines.append("")
    lines.append(
        f"Stage 1 screen-out rule: `{report['configuration']['screen_out_rule']}` "
        f"with threshold `{report['configuration']['screen_out_threshold']}`. "
        "Deterministic offline run: no network access, no provider calls."
    )
    lines.append("")
    lines.append("## Category metrics")
    lines.append("")
    lines.append("| Category | Cases | Retained | Screened out | Recall | Rejection |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for metric in report["categories"]:
        lines.append(
            f"| `{metric['category']}` | {metric['total']} | {metric['retained']} | "
            f"{metric['screened_out']} | {_fmt_pct(metric['recall_pct'])} | "
            f"{_fmt_pct(metric['rejection_pct'])} |"
        )
    lines.append("")
    lines.append(
        f"**Aggregate:** {aggregate['cases']} cases, {aggregate['retained']} retained, "
        f"{aggregate['screened_out']} screened out ({_fmt_pct(aggregate['retention_pct'])} retention), "
        f"{aggregate['protected']} protected."
    )
    lines.append("")
    lines.append("## Multilingual robustness")
    lines.append("")
    lines.append("| Language | Cases | Retained | Screened out | Accuracy |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for language, entry in report["multilingual"].items():
        lines.append(
            f"| {language.upper()} | {entry['total']} | {entry['retained']} | "
            f"{entry['screened_out']} | {_fmt_pct(entry['accuracy_pct'])} |"
        )
    lines.append("")
    lines.append("## Evidence quality")
    lines.append("")
    lines.append("| Quality | Cases |")
    lines.append("| --- | ---: |")
    for quality, count in report["evidence_quality"].items():
        lines.append(f"| `{quality}` | {count} |")
    lines.append("")
    lines.append(f"## Gates ({aggregate['gates_passed']} passed, {aggregate['gates_failed']} failed)")
    lines.append("")
    lines.append("| Gate | Status | Requirement | Detail |")
    lines.append("| --- | --- | --- | --- |")
    for gate in report["gates"]:
        status = "PASS" if gate["passed"] else "**FAIL**"
        lines.append(
            f"| `{gate['name']}` | {status} | {gate['requirement']} | {gate['detail']} |"
        )
    return "\n".join(lines)


def render_json(report: Dict[str, Any]) -> str:
    """Render the report as stable, sorted JSON."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)


RENDERERS = {
    "text": render_text,
    "json": render_json,
    "markdown": render_markdown,
}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.evaluate_benchmark",
        description=(
            "Evaluate the Stage 1 two-stage relevance gate against the permanent "
            "benchmark. Deterministic and fully offline."
        ),
    )
    parser.add_argument(
        "--format",
        choices=sorted(RENDERERS),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=None,
        help=f"Path to the benchmark JSON (default: {DEFAULT_BENCHMARK}).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any quality gate fails.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    report = run_evaluation(args.benchmark)
    print(RENDERERS[args.format](report))

    if args.strict and report["aggregate"]["gates_failed"] > 0:
        failed = ", ".join(g["name"] for g in report["gates"] if not g["passed"])
        print(f"\nFailed gates: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
