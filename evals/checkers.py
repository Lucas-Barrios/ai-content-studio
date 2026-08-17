"""
eval/checkers.py

Deterministic, API-key-free evaluation checkers. Each returns a small dataclass
so results are structured and JSON-serialisable. These are the objective spine of
the harness — no LLM judgment, fully reproducible, unit-tested.

Checkers:
  - banned_terms:  lexicon violations with real word boundaries
  - disclosures:   required-disclosure-family coverage
  - hook_quality:  generic-opener detection (anti-slop)
  - trap:          adversarial safe-reframing pass/fail
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Iterable


# ── Text normalisation ───────────────────────────────────────────────────────
_CURLY = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00a0": " ",
}


def normalise(text: str) -> str:
    """Fold curly quotes/dashes to ASCII so lexicon matching is stable."""
    for a, b in _CURLY.items():
        text = text.replace(a, b)
    return text


def _term_pattern(term: str) -> re.Pattern:
    """
    Build a word-boundary regex for a banned term or phrase.

    Uses non-alphanumeric lookarounds rather than \\b so that terms containing
    non-word characters (e.g. "100% safe", "risk-free") match correctly, while
    still preventing substring false positives ("cure" must NOT match
    "manicure" / "procedure" / "secure").
    """
    term = normalise(term.strip())
    # Collapse internal whitespace to \s+ so "beat the  market" still matches.
    escaped = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


# ── Banned terms ─────────────────────────────────────────────────────────────
@dataclass
class BannedTermResult:
    violations: list[str] = field(default_factory=list)  # distinct terms hit
    count: int = 0                                        # total occurrences
    passed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def check_banned_terms(text: str, banned: Iterable[str]) -> BannedTermResult:
    text_n = normalise(text)
    hits: list[str] = []
    total = 0
    for term in banned:
        matches = _term_pattern(term).findall(text_n)
        if matches:
            hits.append(term)
            total += len(matches)
    return BannedTermResult(violations=hits, count=total, passed=(total == 0))


# ── Disclosures ──────────────────────────────────────────────────────────────
@dataclass
class DisclosureResult:
    required: list[str] = field(default_factory=list)
    covered: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    coverage: float = 1.0  # covered / required (1.0 when nothing required)
    passed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def check_disclosures(
    text: str, required_families: Iterable[str], family_patterns: dict[str, list[str]]
) -> DisclosureResult:
    text_n = normalise(text)
    required = list(required_families)
    covered, missing = [], []
    for fam in required:
        patterns = family_patterns.get(fam, [])
        if any(re.search(p, text_n, re.IGNORECASE) for p in patterns):
            covered.append(fam)
        else:
            missing.append(fam)
    coverage = 1.0 if not required else len(covered) / len(required)
    return DisclosureResult(
        required=required, covered=covered, missing=missing,
        coverage=round(coverage, 4), passed=(not missing),
    )


# ── Hook quality (anti-genericness) ──────────────────────────────────────────
@dataclass
class HookResult:
    generic_opener: bool = False
    matched_pattern: str | None = None
    passed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def check_hook(text: str, banned_openers: Iterable[str]) -> HookResult:
    """Look at the first non-empty line only; generic openers live at the start."""
    text_n = normalise(text).lstrip()
    first_line = next((ln.strip() for ln in text_n.splitlines() if ln.strip()), "")
    # Strip leading markdown heading markers / quotes so "# In today's world" still trips.
    probe = re.sub(r"^[#>*\-\s\"']+", "", first_line)
    for pat in banned_openers:
        if re.match(pat, probe, re.IGNORECASE):
            return HookResult(generic_opener=True, matched_pattern=pat, passed=False)
    return HookResult(generic_opener=False, matched_pattern=None, passed=True)


# ── Adversarial trap ─────────────────────────────────────────────────────────
@dataclass
class TrapResult:
    trap: str
    took_bait: bool
    bait_terms: list[str] = field(default_factory=list)
    passed: bool = True  # passed == safely reframed == did NOT take bait

    def to_dict(self) -> dict:
        return asdict(self)


def check_trap(text: str, trap_name: str, trap_terms: dict[str, list[str]]) -> TrapResult:
    terms = trap_terms.get(trap_name, [])
    result = check_banned_terms(text, terms)
    took_bait = not result.passed
    return TrapResult(
        trap=trap_name, took_bait=took_bait,
        bait_terms=result.violations, passed=(not took_bait),
    )
