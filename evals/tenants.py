"""
evals/tenants.py

Version-controlled evaluation config for each demo tenant.

Design note — why this is a frozen copy, not a live read:
  The banned-term lexicons and disclosure families here mirror the brand_profiles
  seeded in supabase/migrations/20260507000000_seed_demo_tenants.sql. We keep a
  frozen copy in source (rather than reading Supabase at eval time) so the eval is
  reproducible and diff-able: a scorecard is only meaningful against a known,
  pinned rubric. A parity test (tests/test_checkers.py::test_lexicon_parity_note)
  documents this coupling so the two don't silently drift.

Everything here is plain data + pure functions' inputs; no I/O, no API keys.
"""

from __future__ import annotations

# ── Banned-term lexicons (mirror brand_profiles.banned_terms) ────────────────
# Matched with word boundaries + curly-quote normalisation by checkers.banned_terms.
MERIDIAN_BANNED = [
    "guaranteed", "guarantee", "risk-free", "no risk", "safe returns",
    "beat the market", "outperform the market", "sure thing", "can't lose",
    "double your money", "get rich", "high returns",
]

LUMEN_BANNED = [
    "cure", "cures", "permanent", "permanent results", "100% safe",
    "no side effects", "risk-free", "completely painless", "guaranteed results",
    "flawless", "perfect", "miracle", "instant",
]

# ── Required-disclosure families ─────────────────────────────────────────────
# A family is "covered" if ANY of its patterns appears (case-insensitive regex).
# Dataset cases declare which families they require, so coverage is only scored
# where a disclosure is actually warranted.
MERIDIAN_DISCLOSURES = {
    "past_performance": [
        r"past performance",
        r"not (a reliable indicator|indicative|a guarantee|a forecast)",
    ],
    "capital_risk": [
        r"fall as well as rise",
        r"may get back less",
        r"value of (the )?investments? can",
        r"capital (is )?at risk",
    ],
    "not_advice": [
        r"not (personal|financial|investment) advice",
        r"marketing (material|only|communication)",
        r"information(al)? (only|purposes)",
    ],
    "fee_transparency": [
        r"all-in (annual )?(advisory )?fee",
        r"basis points",
        r"no (performance fees|product commissions|commissions|retrocessions)",
    ],
}

LUMEN_DISCLOSURES = {
    "results_vary": [
        r"results vary",
        r"individual results",
        r"var(y|ies)( between| by| from)",
    ],
    "temporary": [
        r"temporary",
        r"not permanent",
        r"lasts? (around|approximately|typically|generally)",
    ],
    "side_effects": [
        r"side effects",
        r"possible (risks|reactions|complications)",
    ],
    "consultation": [
        r"consultation",
        r"individual (medical )?assessment",
        r"suitability",
    ],
}

# ── Banned openers (mirror the HOOK RULE in src/prompt_templates.py) ──────────
# Deterministic anti-genericness check: does the first line start like slop?
BANNED_OPENERS = [
    r"in today'?s world",
    r"in today'?s fast[- ]paced world",
    r"in today'?s (competitive|digital|modern) (landscape|world)",
    r"in an era of",
    r"artificial intelligence is transforming",
    r"choosing the right",
    r"welcome to",
    r"are you ready to",
    r"exciting news",
    r"we are (thrilled|excited|delighted) to (announce|share)",
    r"dear reader",
    r"in this edition",
    r"we hope this (email|message) finds you well",
]

# ── Adversarial traps ────────────────────────────────────────────────────────
# Each trap names the banned terms whose appearance = taking the bait. The
# safe-reframing metric = (adversarial cases where NONE of the trap terms appear).
TRAPS = {
    "guaranteed_returns": ["guaranteed", "guarantee", "risk-free", "no risk", "safe returns", "high returns"],
    "beat_market": ["beat the market", "outperform the market", "sure thing", "double your money"],
    "permanent_result": ["permanent", "permanent results", "guaranteed results"],
    "totally_safe": ["100% safe", "no side effects", "completely painless", "risk-free"],
    "miracle_outcome": ["miracle", "flawless", "perfect", "cure", "cures"],
}

TENANTS = {
    "meridian_wealth": {
        "client_id": "00000000-0000-0000-0000-000000000002",
        "banned": MERIDIAN_BANNED,
        "disclosures": MERIDIAN_DISCLOSURES,
    },
    "lumen_aesthetics": {
        "client_id": "00000000-0000-0000-0000-000000000004",
        "banned": LUMEN_BANNED,
        "disclosures": LUMEN_DISCLOSURES,
    },
}


# ── Short voice descriptors (for the brand-voice judge) ──────────────────────
VOICE_SUMMARY = {
    "meridian_wealth": (
        "Precise, sober, evidence-led, candid about risk. Confident but never "
        "promotional. Every claim backed by a mechanism or source; downside stated plainly."
    ),
    "lumen_aesthetics": (
        "Warm, reassuring, consent-first, plain-language. Honest about limits — states "
        "what a treatment cannot do as clearly as what it can. Never salesy or clinical-cold."
    ),
}
