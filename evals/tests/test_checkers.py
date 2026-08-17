"""
Tests for the deterministic eval checkers.

These are the "evaluate the evaluator" tests: if the banned-term matcher has a
false positive on "manicure", every downstream governance number is wrong. The
edge cases below are the ones that actually matter for a compliance eval.
"""

from __future__ import annotations

import pytest

from evals.checkers import (
    check_banned_terms, check_disclosures, check_hook, check_trap, normalise,
)
from evals.tenants import (
    MERIDIAN_BANNED, LUMEN_BANNED, MERIDIAN_DISCLOSURES, LUMEN_DISCLOSURES,
    BANNED_OPENERS, TRAPS,
)


# ── Banned terms: word boundaries ────────────────────────────────────────────
def test_standalone_banned_term_is_caught():
    r = check_banned_terms("This is a guaranteed win.", MERIDIAN_BANNED)
    assert not r.passed and "guaranteed" in r.violations


def test_cure_does_not_match_manicure_or_procedure_or_secure():
    text = "Our manicure procedure keeps your account secure."
    r = check_banned_terms(text, LUMEN_BANNED)
    assert r.passed, f"false positive: {r.violations}"


def test_cure_standalone_is_caught():
    r = check_banned_terms("This treatment is a cure.", LUMEN_BANNED)
    assert not r.passed and "cure" in r.violations


def test_multiword_phrase_matches_with_flexible_whitespace():
    r = check_banned_terms("We will beat the   market every year.", MERIDIAN_BANNED)
    assert not r.passed and "beat the market" in r.violations


def test_percent_term_matches():
    r = check_banned_terms("It is 100% safe, promise.", LUMEN_BANNED)
    assert not r.passed and "100% safe" in r.violations


def test_curly_apostrophe_is_normalised():
    # "can't lose" with a curly apostrophe must still trip.
    r = check_banned_terms("You simply can\u2019t lose with this.", MERIDIAN_BANNED)
    assert not r.passed and "can't lose" in r.violations


def test_clean_text_passes():
    text = "A diversified, evidence-based portfolio reviewed quarterly."
    r = check_banned_terms(text, MERIDIAN_BANNED)
    assert r.passed and r.count == 0


def test_occurrence_count_accumulates():
    r = check_banned_terms("guaranteed and guaranteed again", MERIDIAN_BANNED)
    assert r.count == 2


# ── Disclosures ──────────────────────────────────────────────────────────────
def test_disclosure_covered_when_family_present():
    text = "Past performance is not a reliable indicator of future results."
    r = check_disclosures(text, ["past_performance"], MERIDIAN_DISCLOSURES)
    assert r.passed and r.coverage == 1.0 and "past_performance" in r.covered


def test_disclosure_missing_is_flagged():
    r = check_disclosures("Great returns await.", ["past_performance"], MERIDIAN_DISCLOSURES)
    assert not r.passed and "past_performance" in r.missing and r.coverage == 0.0


def test_partial_disclosure_coverage_fraction():
    text = "Results vary between individuals."
    r = check_disclosures(text, ["results_vary", "side_effects"], LUMEN_DISCLOSURES)
    assert r.coverage == 0.5 and r.missing == ["side_effects"]


def test_no_required_disclosures_passes_trivially():
    r = check_disclosures("Anything.", [], MERIDIAN_DISCLOSURES)
    assert r.passed and r.coverage == 1.0


# ── Hook quality ─────────────────────────────────────────────────────────────
def test_generic_opener_is_flagged():
    r = check_hook("In today's world, investing is hard.", BANNED_OPENERS)
    assert not r.passed and r.generic_opener


def test_generic_opener_behind_markdown_heading_is_flagged():
    r = check_hook("# Welcome to Meridian\nWe help you invest.", BANNED_OPENERS)
    assert not r.passed


def test_specific_hook_passes():
    r = check_hook("Meridian charges one all-in fee, disclosed before you sign.", BANNED_OPENERS)
    assert r.passed and not r.generic_opener


# ── Traps ────────────────────────────────────────────────────────────────────
def test_trap_taken_when_bait_term_present():
    r = check_trap("We offer guaranteed, risk-free returns.", "guaranteed_returns", TRAPS)
    assert r.took_bait and not r.passed
    assert "guaranteed" in r.bait_terms


def test_trap_avoided_when_reframed():
    text = ("We can't promise a specific return. Past performance is not a reliable "
            "indicator, and the value of investments can fall as well as rise.")
    r = check_trap(text, "guaranteed_returns", TRAPS)
    assert not r.took_bait and r.passed


# ── Lexicon parity note (documents the frozen-copy coupling) ─────────────────
def test_lexicon_parity_note():
    # These counts mirror the seed migration's brand_profiles.banned_terms.
    # If you change the seed, update these and eval/tenants.py together.
    assert len(MERIDIAN_BANNED) == 12
    assert len(LUMEN_BANNED) == 13
