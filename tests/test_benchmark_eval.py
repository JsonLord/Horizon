"""Regression tests for the offline benchmark evaluation runner.

These tests pin the *behaviour of the harness* as well as the current Stage 1
outcome. The signals now meet every benchmark gate, so the expected state is
asserted explicitly (see ``test_stage1_recall_gaps_are_closed``): a regression
that screens out a relevant case fails here as loudly as it fails the gate.
"""
from __future__ import annotations

import ast
import json
import socket
from pathlib import Path

import pytest

from scripts import evaluate_benchmark as eb
from src.research.live_review import Candidate, Evidence


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "data" / "benchmarks" / "two_stage_relevance_benchmark.json"


@pytest.fixture(scope="module")
def benchmark_data():
    return eb.load_benchmark(BENCHMARK_PATH)


@pytest.fixture(scope="module")
def results(benchmark_data):
    return eb.evaluate_benchmark(benchmark_data)


@pytest.fixture(scope="module")
def report(benchmark_data, results):
    return eb.build_report(benchmark_data, results)


def _by_id(results):
    return {r.case_id: r for r in results}


# --------------------------------------------------------------------------- #
# 1. Runs cleanly with no network and no provider access
# --------------------------------------------------------------------------- #
def test_runs_without_network_access(monkeypatch):
    """The runner must complete with sockets disabled and no provider configured."""

    def no_network(*args, **kwargs):
        raise AssertionError("benchmark evaluation attempted network access")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    # Any provider credential in the environment must be irrelevant to the run.
    monkeypatch.setenv("HORIZON_DECISION_API_MODE", "off")
    monkeypatch.setenv("HORIZON_DECISION_API_KEY", "must-not-be-used")

    exit_code = eb.main(["--format", "json", "--benchmark", str(BENCHMARK_PATH)])
    assert exit_code == 0


def test_report_declares_zero_provider_calls(report):
    assert report["configuration"]["provider_calls"] == 0
    assert report["configuration"]["network_access"] is False


def test_module_does_not_import_network_or_provider_clients():
    """Guard against a future edit wiring the harness to a live provider."""
    tree = ast.parse(Path(eb.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)

    forbidden_roots = {"httpx", "requests", "urllib", "anthropic", "openai", "aiohttp"}
    for name in imported:
        root = name.split(".")[0]
        assert root not in forbidden_roots, f"evaluation runner must stay offline: imports {name!r}"

    # The provider module must never be imported, only pure signal functions.
    assert not any("filtering.provider" in name for name in imported), imported
    assert not any("DecisionModelProvider" in name for name in imported), imported


# --------------------------------------------------------------------------- #
# 2. All 33 benchmark cases are parsed and evaluated
# --------------------------------------------------------------------------- #
def test_all_33_cases_are_parsed_and_evaluated(benchmark_data, report, results):
    declared = sum(len(cases) for cases in benchmark_data["categories"].values())
    assert declared == 33

    assert len(results) == 33
    assert report["aggregate"]["cases"] == 33
    assert len({r.case_id for r in results}) == 33, "case IDs must be unique"


@pytest.mark.parametrize(
    "category,expected",
    [
        ("relevant_findings", 5),
        ("borderline_findings", 5),
        ("irrelevant_findings", 5),
        ("difficult_multilingual_examples", 6),
        ("keyword_missed_stories", 4),
        ("duplicate_and_evolving_stories", 4),
        ("insufficient_evidence_examples", 4),
    ],
)
def test_category_counts_match_benchmark_metadata(benchmark_data, report, category, expected):
    assert len(benchmark_data["categories"][category]) == expected
    assert benchmark_data["metadata"]["category_counts"][category] == expected
    metric = next(m for m in report["categories"] if m["category"] == category)
    assert metric["total"] == expected


def test_every_case_has_a_score_and_evidence_verdict(results):
    for result in results:
        assert isinstance(result.priority_score, int)
        assert 0 <= result.priority_score <= 40
        assert result.evidence_quality in {"SUPPORTED", "WEAK", "HEADLINE_ONLY", "MISSING"}
        assert isinstance(result.protected, bool)
        assert isinstance(result.screened_out, bool)


def test_evidence_quality_breakdown_covers_every_case(report):
    assert sum(report["evidence_quality"].values()) == 33
    # Every insufficient-evidence case must be flagged as under-evidenced (HEADLINE_ONLY or WEAK).
    eq = report["evidence_quality"]
    under_evidenced = eq.get("HEADLINE_ONLY", 0) + eq.get("WEAK", 0) + eq.get("MISSING", 0)
    assert under_evidenced >= 4
    assert eq.get("HEADLINE_ONLY", 0) >= 2
    assert eq.get("WEAK", 0) >= 2


# --------------------------------------------------------------------------- #
# 3. Critical long-tail stories have zero screen-outs
# --------------------------------------------------------------------------- #
def test_keyword_missed_stories_have_zero_screen_outs(results):
    rows = [r for r in results if r.category == "keyword_missed_stories"]
    assert len(rows) == 4
    screened = [r.case_id for r in rows if r.screened_out]
    assert screened == [], f"long-tail stories must never be screened out, got {screened}"


@pytest.mark.parametrize(
    "case_id,story",
    [
        ("miss-01", "EU-China manufacturing competitiveness (Guardian / Eskelund)"),
        ("miss-02", "Iran-US peace talks in Muscat"),
        ("miss-03", "COP31 climate summit"),
    ],
)
def test_named_long_tail_stories_are_protected(results, case_id, story):
    result = _by_id(results)[case_id]
    assert result.protected, f"{case_id} ({story}) must be protected by Stage 1"
    assert not result.screened_out, f"{case_id} ({story}) must not be screened out"
    assert result.priority_score >= eb.SCREEN_OUT_THRESHOLD


def test_keyword_missed_recall_gate_passes(report):
    gate = next(g for g in report["gates"] if g["name"] == "keyword_missed_stories_recall")
    assert gate["passed"] is True, gate["detail"]


def test_multilingual_breakdown_reports_en_de_fr(report):
    assert set(report["multilingual"]) == {"en", "de", "fr"}
    # The benchmark's difficult examples are DE and FR only.
    assert report["multilingual"]["de"]["total"] == 3
    assert report["multilingual"]["fr"]["total"] == 3
    for entry in report["multilingual"].values():
        if entry["total"]:
            assert 0.0 <= entry["accuracy_pct"] <= 100.0


# --------------------------------------------------------------------------- #
# 4. Irrelevant cases are properly filtered
# --------------------------------------------------------------------------- #
def test_irrelevant_findings_are_all_screened_out(results):
    rows = [r for r in results if r.category == "irrelevant_findings"]
    assert len(rows) == 5
    leaked = [r.case_id for r in rows if not r.screened_out]
    assert leaked == [], f"irrelevant articles must be rejected, leaked {leaked}"


@pytest.mark.parametrize("case_id", ["irr-01", "irr-02"])
def test_sports_and_gadget_articles_rejected(results, case_id):
    result = _by_id(results)[case_id]
    assert result.screened_out
    assert not result.protected
    assert result.priority_score < eb.SCREEN_OUT_THRESHOLD


def test_irrelevant_rejection_gate_passes(report):
    gate = next(g for g in report["gates"] if g["name"] == "irrelevant_findings_rejection")
    assert gate["passed"] is True, gate["detail"]


# --------------------------------------------------------------------------- #
# 5. Screen-out rule and determinism
# --------------------------------------------------------------------------- #
def test_screen_out_rule_is_threshold_and_protection(results):
    for result in results:
        expected = result.priority_score < eb.SCREEN_OUT_THRESHOLD and not result.protected
        assert result.screened_out is expected, result.case_id


def test_evaluation_is_deterministic(benchmark_data):
    first = eb.build_report(benchmark_data, eb.evaluate_benchmark(benchmark_data))
    second = eb.build_report(benchmark_data, eb.evaluate_benchmark(benchmark_data))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_case_to_candidate_attaches_evidence(benchmark_data):
    case = next(eb.iter_cases(benchmark_data))
    candidate = eb.case_to_candidate(case)
    assert isinstance(candidate, Candidate)
    assert len(candidate.evidence) == 1
    assert isinstance(candidate.evidence[0], Evidence)
    assert candidate.evidence[0].title == case.title
    assert candidate.evidence[0].language in {"en", "de", "fr", "unknown"}


def test_evidence_excerpt_respects_model_limit(benchmark_data):
    for case in eb.iter_cases(benchmark_data):
        candidate = eb.case_to_candidate(case)
        assert len(candidate.evidence[0].excerpt) <= 500


# --------------------------------------------------------------------------- #
# 6. Renderers and CLI contract
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fmt", ["text", "json", "markdown"])
def test_every_format_renders(fmt, report):
    rendered = eb.RENDERERS[fmt](report)
    assert rendered.strip()
    if fmt == "json":
        assert json.loads(rendered)["aggregate"]["cases"] == 33
    else:
        assert "relevant_findings" in rendered
        assert "irrelevant_findings" in rendered


def test_strict_mode_exit_code_tracks_gate_status(report):
    failed = report["aggregate"]["gates_failed"]
    exit_code = eb.main(["--format", "json", "--benchmark", str(BENCHMARK_PATH), "--strict"])
    assert exit_code == (1 if failed else 0)


def test_cli_rejects_unknown_format():
    with pytest.raises(SystemExit):
        eb.main(["--format", "yaml"])


def test_missing_benchmark_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        eb.load_benchmark(tmp_path / "absent.json")


# --------------------------------------------------------------------------- #
# 7. Stage 1 recall is complete (explicit, so it cannot silently drift)
# --------------------------------------------------------------------------- #
def test_stage1_recall_gaps_are_closed(report):
    """Pin full Stage 1 recall across every retention category.

    The deterministic signals previously dropped technical-domain releases
    (``rel-01``/``rel-03``), a critical-raw-materials accord (``rel-05``) and
    German/French long-tail stories (``multi-02``, ``multi-03``, ``multi-06``).
    Those gaps are now closed; this test records the fixed state so that any
    regression re-introducing a screen-out fails here as well as in the gates.
    """
    relevant = next(m for m in report["categories"] if m["category"] == "relevant_findings")
    assert relevant["screen_out_ids"] == []
    assert relevant["retained"] == 5
    assert relevant["recall_pct"] == 100.0

    missed = next(m for m in report["categories"] if m["category"] == "keyword_missed_stories")
    assert missed["screen_out_ids"] == []
    assert missed["recall_pct"] == 100.0

    multilingual = {
        language: entry["screen_out_ids"] for language, entry in report["multilingual"].items()
    }
    assert multilingual == {"en": [], "de": [], "fr": []}
    assert report["multilingual"]["de"]["retained"] == 3
    assert report["multilingual"]["de"]["accuracy_pct"] == 100.0
    assert report["multilingual"]["fr"]["retained"] == 3
    assert report["multilingual"]["fr"]["accuracy_pct"] == 100.0

    irrelevant = next(m for m in report["categories"] if m["category"] == "irrelevant_findings")
    assert irrelevant["rejection_pct"] == 100.0

    assert report["aggregate"]["gates_passed"] == 6
    assert report["aggregate"]["gates_failed"] == 0

    gates = {g["name"]: g["passed"] for g in report["gates"]}
    assert gates == {
        "relevant_findings_recall": True,
        "keyword_missed_stories_recall": True,
        "multilingual_recall_de": True,
        "multilingual_recall_fr": True,
        "irrelevant_findings_rejection": True,
        "insufficient_evidence_abstention": True,
    }
