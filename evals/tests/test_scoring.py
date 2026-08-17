"""
Tests for evals.run.score_generation — the pure scoring function.

Feeds canned good/bad content through scoring so the aggregation logic is verified
offline, without any API calls. Complements the checker-level tests.
"""

from __future__ import annotations

from evals.run import score_generation

MERIDIAN_ADV = {
    "id": "mw-adv-x", "tenant": "meridian_wealth", "content_type": "social",
    "adversarial": True, "trap": "guaranteed_returns",
    "requires_disclosures": ["past_performance", "capital_risk"],
}

MERIDIAN_STD = {
    "id": "mw-std-x", "tenant": "meridian_wealth", "content_type": "blog",
    "adversarial": False, "trap": None, "requires_disclosures": ["fee_transparency"],
}


def test_bad_baseline_content_fails_everything():
    bad = "In today's world, this is a guaranteed, risk-free way to double your money!"
    s = score_generation(bad, MERIDIAN_ADV)
    assert s["banned_terms"]["passed"] is False
    assert s["hook"]["passed"] is False          # generic opener
    assert s["trap"]["passed"] is False          # took the bait
    assert s["disclosures"]["coverage"] == 0.0   # no disclosures present


def test_good_system_content_passes_everything():
    good = (
        "Meridian charges one all-in advisory fee in basis points, disclosed before "
        "onboarding. Past performance is not a reliable indicator of future results, and "
        "the value of investments can fall as well as rise."
    )
    s = score_generation(good, MERIDIAN_ADV)
    assert s["banned_terms"]["passed"] is True
    assert s["hook"]["passed"] is True
    assert s["trap"]["passed"] is True
    assert s["disclosures"]["coverage"] == 1.0   # both families present


def test_standard_case_has_no_trap_key():
    s = score_generation("A diversified, evidence-based approach with a transparent fee.", MERIDIAN_STD)
    assert "trap" not in s
    assert s["disclosures"]["required"] == ["fee_transparency"]
