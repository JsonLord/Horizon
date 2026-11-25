"""Two-stage research filtering signal definitions, taxonomy, and quality gates.

This module provides Stage 1 deterministic prioritization, multilingual signals,
long-tail topic protection, domain completeness gating, evidence quality checks,
and reproducible comparison context for held-out research experiments.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# --- Token-Aware Normalization & Matching ---

# Words to specifically guard against substring false positives for 'us'
US_FALSE_POSITIVE_WORDS = {
    'business', 'must', 'status', 'russian', 'focus', 'industry',
    'campus', 'consensus', 'bonus', 'versus', 'minus', 'plus',
    'stimulus', 'syllabus', 'virus', 'discuss', 'issue', 'issues',
    'usage', 'user', 'users', 'useful', 'usually', 'austria', 'australia'
}

US_ALIASES = {
    'us', 'u.s.', 'u.s', 'usa', 'u.s.a.', 'united states',
    'vereinigte staaten', 'vereinigten staaten', 'états-unis', 'etats-unis',
    'us-china', 'us–china', 'us-eu', 'us–eu', 'iran-us', 'iran–us'
}

# 9 Broad Strategic World Intelligence Categories (EN, DE, FR)
WORLD_INTELLIGENCE_TAXONOMY = {
    'international_conflict': {
        'en': ('conflict', 'war', 'ceasefire', 'peace talks', 'military', 'defense', 'treaty', 'nato', 'missile', 'security alliance'),
        'de': ('konflikt', 'krieg', 'waffenstillstand', 'friedensgespräche', 'militär', 'verteidigung', 'nato', 'rakete'),
        'fr': ('conflit', 'guerre', 'cessez-le-feu', 'pourparlers de paix', 'militaire', 'défense', 'traité', 'otan'),
    },
    'foreign_influence_disinfo': {
        'en': ('foreign influence', 'disinformation', 'propaganda', 'cyber warfare', 'espionage', 'intelligence agency'),
        'de': ('ausländische einflussnahme', 'desinformation', 'propaganda', 'spionage', 'geheimdienst'),
        'fr': ('ingérence étrangère', 'désinformation', 'propagande', 'espionnage', 'services de renseignement'),
    },
    'sanctions_diplomacy': {
        'en': ('sanction', 'sanctions', 'embargo', 'diplomacy', 'diplomatic', 'ambassador', 'bilateral talks', 'summit'),
        'de': ('sanktion', 'sanktionen', 'embargo', 'diplomatie', 'diplomatisch', 'botschafter', 'gipfeltreffen'),
        'fr': ('sanction', 'sanctions', 'embargo', 'diplomatie', 'diplomatique', 'ambassadeur', 'sommet bilatéral'),
    },
    'elections_institutions': {
        'en': ('election', 'parliament', 'congress', 'presidential', 'constitutional', 'referendum', 'supreme court'),
        'de': ('wahl', 'bundestag', 'parlament', 'präsidentschaft', 'verfassung', 'referendum'),
        'fr': ('élection', 'parlement', 'présidentielle', 'constitutionnel', 'référendum', 'assemblée nationale'),
    },
    'trade_industrial_policy': {
        'en': ('trade policy', 'tariff', 'tariffs', 'industrial policy', 'competitiveness', 'manufacturing jobs',
               'supply chain dependency', 'eu-china', 'semiconductor subsidies', 'export controls', 'decoupling', 'de-risking'),
        'de': ('handelspolitik', 'zoll', 'zölle', 'industriepolitik', 'wettbewerbsfähigkeit', 'arbeitsplätze',
               'lieferkettensorgfaltspflichtengesetz', 'halbleiter', 'exportkontrollen'),
        'fr': ('politique commerciale', 'tarif douanier', 'droits de douane', 'politique industrielle',
               'compétitivité', 'emplois industriels', 'chaîne d\'approvisionnement', 'semi-conducteurs'),
    },
    'energy_security': {
        'en': ('energy security', 'oil pipeline', 'lng terminal', 'natural gas', 'nuclear energy', 'power grid vulnerability', 'opec'),
        'de': ('energiesicherheit', 'erdgas', 'pipelines', 'kernenergie', 'stromnetz', 'ölpreis'),
        'fr': ('sécurité énergétique', 'gaz naturel', 'oléoduc', 'énergie nucléaire', 'réseau électrique', 'opep'),
    },
    'macroeconomics_cross_border': {
        'en': ('central bank', 'inflation', 'sovereign debt', 'currency reserves', 'foreign direct investment', 'imf', 'world bank'),
        'de': ('zentralbank', 'inflation', 'staatsverschuldung', 'währungsreserven', 'direktinvestitionen', 'iwf', 'weltbank'),
        'fr': ('banque centrale', 'inflation', 'dette souveraine', 'réserves de change', 'investissements directs', 'fmi', 'banque mondiale'),
    },
    'climate_multilateral': {
        'en': ('cop31', 'cop 31', 'cop-31', 'climate summit', 'paris agreement', 'loss and damage fund', 'fossil fuel transition'),
        'de': ('cop31', 'klimagipfel', 'pariser abkommen', 'klimaverhandlungen', 'fossile brennstoffe'),
        'fr': ('cop31', 'sommet climatique', 'accord de paris', 'fonds pertes et préjudices', 'combustibles fossiles'),
    },
    'governance_rule_of_law': {
        'en': ('rule of law', 'corruption', 'state capture', 'civil liberties', 'human rights violations', 'transparency'),
        'de': ('rechtsstaatlichkeit', 'korruption', 'bürgerrechte', 'menschenrechte', 'transparenz'),
        'fr': ('état de droit', 'corruption', 'libertés civiles', 'droits de l\'homme', 'transparence'),
    },
}

# AUX in-scope core themes (Accessibility & AI-assisted Usability)
AUX_IN_SCOPE_TERMS = {
    'accessibility_standards': (
        'accessibility', 'accessible', 'wcag', 'section 508', 'ada compliance',
        'screen reader', 'assistive technology', 'aria', 'alt text'
    ),
    'german_accessibility': (
        'barrierefreiheit', 'barrierefrei', 'bitv', 'bgg', 'assistive technologien',
        'leichte sprache', 'gebärdensprache', 'sehbehinderung'
    ),
    'french_accessibility': (
        'accessibilité', 'accessibilité numérique', 'rgaa', 'lecteur d\'écran',
        'technologie d\'assistance', 'handicap'
    ),
    'usability_evaluation': (
        'usability testing', 'user research', 'inclusive ux', 'inclusive design',
        'cognitive accessibility', 'accessibility evaluation', 'heuristic evaluation',
        'ai-assisted usability', 'sus score', 'human-computer interaction'
    ),
}

# Weak or polysemous terms that must NOT trigger AUX eligibility on their own
AUX_WEAK_POLYSEMOUS_TERMS = {
    'testing', 'evaluation', 'design', 'ux', 'ui', 'interface', 'workflow',
    'announcement', 'launch', 'platform', 'tool', 'features', 'software'
}

# Technical Domains Vocabulary
TECH_DOMAIN_TERMS = {
    'agent-control-planes': {
        'en': ('agent', 'orchestration', 'control plane', 'mcp', 'workflow', 'durable execution', 'tool governance', 'agentic'),
        'de': ('agent', 'orchestrierung', 'steuerung', 'ablauf', 'auswertung', 'durable execution'),
        'fr': ('agent', 'orchestration', 'contrôle', 'flux', 'évaluation'),
    },
    'distributed-training': {
        'en': ('distributed', 'training', 'gpu', 'cuda', 'parallel', 'throughput', 'memory', 'pipeline parallelism', 'megatron'),
        'de': ('verteilt', 'training', 'gpu', 'parallel', 'durchsatz', 'speicher', 'pipeline-parallelismus'),
        'fr': ('distribué', 'entraînement', 'gpu', 'parallèle', 'débit', 'mémoire'),
    },
    'rag-memory': {
        'en': ('retrieval', 'rag', 'memory', 'vector', 'citation', 'grounding', 'search', 'reranking', 'chunking'),
        'de': ('suche', 'retrieval', 'speicher', 'vektor', 'zitat', 'beleg', 'reranking'),
        'fr': ('recherche', 'mémoire', 'vecteur', 'citation', 'preuve', 'récupération'),
    },
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words while preserving hyphens and periods in acronyms."""
    if not text:
        return []
    # Match words, hyphenated terms, and dotted acronyms
    tokens = re.findall(r'\b[A-Za-z0-9]+(?:[-–.][A-Za-z0-9]+)*\b', text.casefold())
    return tokens


def has_token_boundary(needle: str, text: str) -> bool:
    """Check if needle appears as a distinct word/token in text, preventing substring false positives."""
    if not needle or not text:
        return False
    needle_norm = needle.casefold()
    text_norm = text.casefold()

    # Direct token-boundary regex check
    pattern = rf'(?:^|[\s,;:!?"\'\(\)\[\]{{}}])' + re.escape(needle_norm) + rf'(?:$|[\s,;:!?"\'\(\)\[\]{{}}])'
    if re.search(pattern, text_norm):
        return True

    # Check hyphenated compounds (e.g. US-China, Iran-US)
    hyphen_pattern = rf'(?:^|[\s])([a-z0-9]+[-–][a-z0-9]+)(?:$|[\s])'
    for match in re.finditer(hyphen_pattern, text_norm):
        parts = re.split(r'[-–]', match.group(1))
        if needle_norm in parts:
            return True

    return False


def matches_us_reference(text: str) -> bool:
    """Accurately match legitimate US geopolitical references while ignoring false positives."""
    text_lower = text.casefold()
    tokens = set(tokenize(text))

    # Reject if only false positive occurrences exist
    for alias in US_ALIASES:
        if has_token_boundary(alias, text_lower):
            # Double check it is not part of a known false-positive word
            if alias == 'us' and not any(fp in tokens for fp in US_FALSE_POSITIVE_WORDS - {'us'}):
                return True
            elif alias != 'us':
                return True

    return False


def is_world_intelligence_long_tail(text: str) -> bool:
    """
    Check if text covers critical World Intelligence topics, including:
    - Iran-US peace talks & Middle East ceasefire
    - COP31 climate negotiations
    - EU-China industrial competitiveness & trade policy
    - Sanctions, international treaties & supply chain dependencies
    """
    text_lower = text.casefold()

    # 1. Iran - US / Middle East Peace talks
    has_iran = has_token_boundary('iran', text_lower)
    has_peace = any(has_token_boundary(w, text_lower) for w in ('peace', 'talks', 'ceasefire', 'friedensgespräche', 'pourparlers', 'waffenstillstand'))
    if has_iran and has_peace:
        return True
    if any(has_token_boundary(term, text_lower) for term in ('iran-us', 'iran–us', 'iran us', 'iran-usa')):
        return True

    # 2. COP31 climate summit
    if any(has_token_boundary(term, text_lower) for term in ('cop31', 'cop-31', 'cop 31')):
        return True
    if has_token_boundary('climate summit', text_lower) or has_token_boundary('klimagipfel', text_lower):
        return True

    # 3. EU-China Industrial Competitiveness / Manufacturing (e.g. Guardian Jens Eskelund article)
    has_eu = any(has_token_boundary(w, text_lower) for w in ('eu', 'european union', 'europa', 'europäische union', 'europe'))
    has_china = any(has_token_boundary(w, text_lower) for w in ('china', 'chinois', 'chinesisch', 'beijing', 'peking'))
    has_industry = any(has_token_boundary(w, text_lower) for w in (
        'manufacturers', 'manufacturing', 'competitiveness', 'industrial policy',
        'industriepolitik', 'wettbewerbsfähigkeit', 'compétitivité', 'supply chain',
        'industrie', 'export controls', 'tariffs'
    ))
    if has_eu and has_china and has_industry:
        return True

    return False


def is_world_intelligence_in_scope(text: str) -> bool:
    """Determine if a candidate genuinely belongs to the strategic World Intelligence remit."""
    if is_world_intelligence_long_tail(text):
        return True
    text_lower = text.casefold()
    for cat_name, cat_langs in WORLD_INTELLIGENCE_TAXONOMY.items():
        all_terms = [t for lang_terms in cat_langs.values() for t in lang_terms]
        if any(has_token_boundary(t, text_lower) for t in all_terms):
            return True
    return False


def is_aux_in_scope(text: str) -> bool:
    """Determine if a candidate genuinely belongs to the AUX / accessibility remit."""
    text_lower = text.casefold()

    # Check for direct primary accessibility / inclusive design terms
    for cat_name, terms in AUX_IN_SCOPE_TERMS.items():
        for term in terms:
            if has_token_boundary(term, text_lower):
                return True

    return False


def is_protected_candidate(row, domain: str) -> bool:
    """Evaluates whether a candidate qualifies for Stage 1 priority protection."""
    # Build unified text from title and evidence
    full_text = ' '.join([getattr(row, 'title', '')] + [
        (getattr(e, 'title', '') + ' ' + getattr(e, 'excerpt', ''))
        for e in getattr(row, 'evidence', [])
    ])

    if domain == 'world-intelligence':
        return is_world_intelligence_long_tail(full_text)
    elif domain == 'aux':
        return is_aux_in_scope(full_text)

    return False


def calculate_priority_score(row, domain: str) -> int:
    """Calculates deterministic, token-aware priority score (0-40)."""
    full_text = ' '.join([getattr(row, 'title', '')] + [
        (getattr(e, 'title', '') + ' ' + getattr(e, 'excerpt', ''))
        for e in getattr(row, 'evidence', [])
    ])

    score = 0

    if domain == 'world-intelligence':
        if is_world_intelligence_long_tail(full_text):
            score += 25
        # Add points for distinct taxonomy categories covered
        for cat_name, cat_langs in WORLD_INTELLIGENCE_TAXONOMY.items():
            all_terms = [t for lang_terms in cat_langs.values() for t in lang_terms]
            if any(has_token_boundary(t, full_text) for t in all_terms):
                score += 3
    elif domain == 'aux':
        if is_aux_in_scope(full_text):
            score += 25
        for cat_name, terms in AUX_IN_SCOPE_TERMS.items():
            if any(has_token_boundary(t, full_text) for t in terms):
                score += 4
    elif domain in TECH_DOMAIN_TERMS:
        terms = TECH_DOMAIN_TERMS[domain]
        all_terms = [t for lang_terms in terms.values() for t in lang_terms]
        for term in all_terms:
            if has_token_boundary(term, full_text):
                score += 4

    # Reward primary sources (GitHub/official releases)
    evidence = getattr(row, 'evidence', [])
    if evidence and getattr(evidence[0], 'primary', False):
        score += 5

    return min(40, max(0, score))


def evaluate_domain_completeness(candidates: List[Any], domain: str) -> Tuple[str, str]:
    """
    Evaluates domain status based on candidate count AND topical relevance coverage.
    Returns (status, reason).
    """
    if len(candidates) < 8:
        return (
            'INCOMPLETE_INSUFFICIENT_FRESH_UNSEEN_CANDIDATES',
            f'Found {len(candidates)}/8 fresh candidates.'
        )

    if domain == 'aux':
        in_scope_count = sum(1 for c in candidates if is_aux_in_scope(
            ' '.join([getattr(c, 'title', '')] + [getattr(e, 'title', '') + ' ' + getattr(e, 'excerpt', '') for e in getattr(c, 'evidence', [])])
        ))
        if in_scope_count < 3:
            return (
                'INSUFFICIENT_RELEVANT_COVERAGE',
                f'Only {in_scope_count}/8 candidates meet the AUX accessibility/usability scope criteria.'
            )

    elif domain == 'world-intelligence':
        valid_count = sum(1 for c in candidates if is_world_intelligence_in_scope(
            ' '.join([getattr(c, 'title', '')] + [getattr(e, 'title', '') + ' ' + getattr(e, 'excerpt', '') for e in getattr(c, 'evidence', [])])
        ))
        if valid_count < 2:
            return (
                'INSUFFICIENT_RELEVANT_COVERAGE',
                f'Only {valid_count}/8 candidates meet strategic World Intelligence scope criteria.'
            )

    return ('COMPLETE', f'Sufficient fresh candidates (8/8) and verified in-scope topical coverage.')


def evidence_quality(row: Any) -> Dict[str, Any]:
    """
    Evaluates evidence quality for a candidate to prevent headline-only claim support.
    """
    evidence_list = getattr(row, 'evidence', [])
    title = getattr(row, 'title', '').strip()

    if not evidence_list:
        return {
            'quality': 'MISSING',
            'has_article_excerpt': False,
            'is_headline_only': False,
            'reason': 'No evidence objects attached.'
        }

    total_excerpt_len = 0
    all_headline_only = True

    for ev in evidence_list:
        excerpt = getattr(ev, 'excerpt', '').strip()
        total_excerpt_len += len(excerpt)
        # Check if excerpt is just a repetition of the headline
        if excerpt and excerpt.casefold() != title.casefold() and len(excerpt) > len(title) + 30:
            all_headline_only = False

    if all_headline_only:
        return {
            'quality': 'HEADLINE_ONLY',
            'has_article_excerpt': False,
            'is_headline_only': True,
            'reason': 'Evidence excerpts merely repeat the headline.'
        }

    if total_excerpt_len < 100:
        return {
            'quality': 'WEAK',
            'has_article_excerpt': False,
            'is_headline_only': False,
            'reason': f'Total excerpt length ({total_excerpt_len} chars) below minimum evidentiary threshold.'
        }

    return {
        'quality': 'SUPPORTED',
        'has_article_excerpt': True,
        'is_headline_only': False,
        'reason': f'Verified article-level excerpt support ({total_excerpt_len} chars).'
    }


class ComparisonContextItem(dict):
    """Context item that supports both dict key access and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'ComparisonContextItem' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def get_comparison_context(domain: str, candidate: Any, base_dir: Optional[Path] = None, max_items: int = 10) -> List[Any]:
    """
    Constructs a deterministic, frozen comparison context for 'same-story' evaluation.
    Guarantees that control and treatment receive identical previous event contexts,
    strictly excluding the candidate under evaluation.
    """
    root = base_dir or Path(__file__).resolve().parent.parent.parent
    findings_file = root / 'data' / 'live-review' / domain / 'findings.json'

    if not findings_file.is_file():
        return []

    try:
        data = json.loads(findings_file.read_text(encoding='utf-8'))
        raw_candidates = data.get('candidates', [])
    except Exception:
        return []

    cand_id = getattr(candidate, 'id', '')
    event_id = getattr(candidate, 'event_id', '')

    context_items = []
    for item in raw_candidates:
        item_id = item.get('id', '')
        item_event_id = item.get('event_id', '')
        # Exclude candidate itself
        if item_id == cand_id or item_event_id == event_id:
            continue
        context_items.append(ComparisonContextItem({
            'event_id': item_event_id,
            'title': item.get('title', ''),
            'published_at': item.get('published_at', ''),
            'url': item.get('url', ''),
        }))

    # Sort deterministically by event_id for byte-for-byte reproducible comparison context
    context_items.sort(key=lambda x: (x.get('published_at', ''), x.get('event_id', '')))
    return context_items[:max_items]
