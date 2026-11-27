"""Automated regression tests for two-stage filtering signals and quality gates."""
import json
import os
from pathlib import Path
import pytest

from src.research.live_review import Candidate, Evidence
from src.research.two_stage_signals import (
    calculate_priority_score,
    evaluate_domain_completeness,
    evidence_quality,
    get_comparison_context,
    has_token_boundary,
    is_aux_in_scope,
    is_protected_candidate,
    is_world_intelligence_long_tail,
    matches_us_reference,
    tokenize,
)
from src.research.two_stage_experiment import (
    validate_provider_contract,
    provider_contract,
)


def make_candidate(
    cid: str,
    title: str,
    excerpt: str = "",
    domain: str = "world-intelligence",
    language: str = "en",
    source_type: str = "news",
    primary: bool = False,
) -> Candidate:
    ev = Evidence(
        id=f"src-{cid}",
        url=f"https://example.org/{cid}",
        publisher="TestPub",
        title=title,
        excerpt=excerpt or (title + " provides detailed factual reporting and context. " * 3),
        language=language,
        language_basis="source_metadata",
        discovery_language=language,
        published_at="2026-11-20T10:00:00Z",
        retrieved_at="2026-11-20T11:00:00Z",
        primary=primary,
        fresh=True,
        source_type=source_type,
    )
    return Candidate(
        id=f"cand-{cid}",
        event_id=f"event-{cid}",
        title=title,
        url=ev.url,
        evidence=[ev],
    )


def test_us_acronym_false_positive_prevention():
    """Verify that substring false positives (business, must, status, Russian) are not matched as US."""
    false_positives = [
        "Small business owners navigate changing retail status and customer focus",
        "The team must address the software virus and syllabus requirements",
        "Russian diplomatic statements discuss international bilateral issues",
        "Industrial manufacturing campus reports increased energy usage",
    ]
    for text in false_positives:
        assert not matches_us_reference(text), f"False positive triggered for text: '{text}'"
        assert not has_token_boundary("us", text), f"Boundary match failed to reject 'us' in: '{text}'"


def test_us_acronym_positive_variants():
    """Verify that legitimate US references and aliases are recognized accurately."""
    positive_examples = [
        "US announces new bilateral diplomatic initiative",
        "U.S. delegations arrive in Geneva for consultations",
        "USA manufacturing output expands in quarterly report",
        "United States signs multilateral trade security pact",
        "US-China negotiations continue regarding industrial tariffs",
        "US–EU critical mineral agreement signed in Brussels",
        "Les États-Unis et leurs partenaires européens renforcent la coopération",
        "Die Vereinigten Staaten kündigen neue Richtlinien an",
    ]
    for text in positive_examples:
        assert matches_us_reference(text), f"Failed to match valid US reference in: '{text}'"


def test_guardian_eu_china_competitiveness_protected():
    """Verify the Guardian EU-China competitiveness article is protected from screenout."""
    title = "EU manufacturers face existential challenge against China by 2030, warns Chamber of Commerce president"
    excerpt = (
        "Jens Eskelund, head of the European Union Chamber of Commerce in China, warned that European manufacturing "
        "companies face a systemic loss of competitiveness against state-backed Chinese production capacity by 2030, "
        "threatening hundreds of thousands of high-wage jobs in Germany and across the continent."
    )
    candidate = make_candidate("guardian-01", title, excerpt, domain="world-intelligence")
    assert is_world_intelligence_long_tail(title + " " + excerpt)
    assert is_protected_candidate(candidate, "world-intelligence")
    score = calculate_priority_score(candidate, "world-intelligence")
    assert score >= 25, f"Expected priority >= 25, got {score}"


def test_iran_peace_talks_and_cop31_protected():
    """Verify Iran-US peace talks and COP31 negotiations remain protected."""
    iran = make_candidate(
        "iran-01",
        "Iran and US resume diplomatic peace negotiations in Muscat amid regional ceasefire verification",
        domain="world-intelligence",
    )
    cop = make_candidate(
        "cop-01",
        "COP31 climate summit opens with critical clash over global carbon pricing targets",
        domain="world-intelligence",
    )
    assert is_protected_candidate(iran, "world-intelligence")
    assert is_protected_candidate(cop, "world-intelligence")


def test_sports_and_generic_tech_not_protected():
    """Verify that sports and consumer gadget articles are NOT protected despite containing country names."""
    sports = make_candidate(
        "sport-01",
        "US Men's National Soccer Team Defeats Costa Rica 2-1 in International Friendly Match",
        domain="world-intelligence",
    )
    gadget = make_candidate(
        "gadget-01",
        "TechGizmo Announces RGB Mechanical Gaming Keyboard with Hot-Swappable Switches",
        domain="aux",
    )
    assert not is_protected_candidate(sports, "world-intelligence")
    assert not is_protected_candidate(gadget, "aux")


def test_aux_topical_scoping_and_completeness():
    """Verify that 8 irrelevant AI announcements do NOT produce COMPLETE in AUX."""
    irrelevant_candidates = [
        make_candidate(
            f"aux-irr-{i}",
            f"AI Startup {i} Announces General Platform Feature Launch and Model Upgrade",
            f"Startup {i} released an enterprise dashboard with workflow automation tools.",
            domain="aux",
        )
        for i in range(8)
    ]
    status, reason = evaluate_domain_completeness(irrelevant_candidates, "aux")
    assert status == "INSUFFICIENT_RELEVANT_COVERAGE", f"Expected INSUFFICIENT_RELEVANT_COVERAGE, got {status}"

    # Adding valid cognitive accessibility and usability candidates restores COMPLETE
    valid_candidates = [
        make_candidate(
            f"aux-val-{i}",
            f"BITV 2.0 Barrierefreiheit Audit and Inclusive UX Usability Evaluation {i}",
            f"Empirical usability testing with screen reader assistive technologies and cognitive accessibility heuristics.",
            domain="aux",
        )
        for i in range(4)
    ] + irrelevant_candidates[:4]
    status2, _ = evaluate_domain_completeness(valid_candidates, "aux")
    assert status2 == "COMPLETE"


def test_deterministic_comparison_context(tmp_path):
    """Verify that comparison_context is reproducible, deterministic, and candidate-excluding."""
    domain = "world-intelligence"
    review_dir = tmp_path / "data" / "live-review" / domain
    review_dir.mkdir(parents=True, exist_ok=True)
    findings = {
        "domain": domain,
        "candidates": [
            {"id": "c1", "event_id": "ev-1", "title": "First Event", "published_at": "2026-11-01T00:00:00Z"},
            {"id": "c2", "event_id": "ev-2", "title": "Second Event", "published_at": "2026-11-02T00:00:00Z"},
            {"id": "c3", "event_id": "ev-3", "title": "Third Event", "published_at": "2026-11-03T00:00:00Z"},
        ],
    }
    (review_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")

    current_candidate = make_candidate("c2", "Second Event")
    current_candidate.event_id = "ev-2"

    ctx1 = get_comparison_context(domain, current_candidate, base_dir=tmp_path)
    ctx2 = get_comparison_context(domain, current_candidate, base_dir=tmp_path)

    # Identical across calls
    assert ctx1 == ctx2
    # Current candidate is excluded
    event_ids = [item["event_id"] for item in ctx1]
    assert "ev-2" not in event_ids
    assert event_ids == ["ev-1", "ev-3"]


def test_evidence_quality_distinguishes_headlines():
    """Verify evidence_quality correctly flags headline-only vs supported excerpts."""
    title = "Diplomatic sources indicate ongoing talks in Vienna regarding bilateral treaties"
    # Headline-only: excerpt is identical to title
    headline_only = make_candidate("hl-1", title, excerpt=title)
    q1 = evidence_quality(headline_only)
    assert q1["quality"] == "HEADLINE_ONLY"
    assert q1["is_headline_only"] is True

    # Substantial excerpt
    supported = make_candidate(
        "sup-1",
        title,
        excerpt=(
            "Detailed reporting from Vienna confirms that delegations met for three days behind closed doors. "
            "A draft communique outlines mutual verification schedules, inspection access, and phased tariff reductions."
        ),
    )
    q2 = evidence_quality(supported)
    assert q2["quality"] == "SUPPORTED"
    assert q2["has_article_excerpt"] is True


def test_permanent_benchmark_integrity():
    """Verify that the permanent benchmark JSON exists and contains all 7 required categories."""
    benchmark_path = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "two_stage_relevance_benchmark.json"
    assert benchmark_path.is_file(), "Permanent benchmark file must exist"

    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    assert "categories" in data
    cats = data["categories"]

    expected_categories = [
        "relevant_findings",
        "borderline_findings",
        "irrelevant_findings",
        "difficult_multilingual_examples",
        "keyword_missed_stories",
        "duplicate_and_evolving_stories",
        "insufficient_evidence_examples",
    ]

    for cat in expected_categories:
        assert cat in cats, f"Benchmark missing required category: {cat}"
        assert len(cats[cat]) >= 4, f"Category {cat} should have at least 4 items"
        for item in cats[cat]:
            assert "id" in item
            assert "domain" in item
            assert "expected_label" in item
            assert "title" in item


def test_provider_contract_validation(monkeypatch):
    """Verify that validate_provider_contract fails closed if expected mode is missing or mismatched."""
    monkeypatch.setenv("HORIZON_EXPERIMENT_EXPECTED_API_MODE", "systemone")
    monkeypatch.setenv("HORIZON_DECISION_API_MODE", "systemone")
    # Should not raise
    validate_provider_contract()

    # Mismatched mode fails closed
    monkeypatch.setenv("HORIZON_DECISION_API_MODE", "openai_chat")
    with pytest.raises(RuntimeError, match="Provider contract violation"):
        validate_provider_contract()

    # 'off' mode fails closed
    monkeypatch.setenv("HORIZON_DECISION_API_MODE", "off")
    with pytest.raises(RuntimeError, match="Provider contract violation"):
        validate_provider_contract()
