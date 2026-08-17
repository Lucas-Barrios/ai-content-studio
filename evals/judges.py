"""
evals/judges.py

LLM-as-judge metrics that complement the deterministic checkers. All judges run at
temperature 0 via evals.llm.EvalLLM (JSON mode), so results are structured and the
token cost is captured.

Why these exist — the la-adv-002 lesson:
  The deterministic banned-term checker is context-blind: it flags "results are not
  permanent" as a "permanent" violation. For a compliance eval, the distinction
  between ASSERTING a prohibited claim and NEGATING/REFUSING it is the whole game.
  judge_claims makes that distinction. The other two judges add groundedness
  (are claims supported by the retrieved KB?) and brand-voice adherence.

Every judge takes an injected EvalLLM, so tests can supply a fake client and run
the full judge logic offline (see tests/test_judges.py).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


# ── Context-aware claim check (the important one) ────────────────────────────
@dataclass
class ClaimResult:
    asserts_prohibited_claim: bool = False
    prohibited_claims: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_CLAIM_PROMPT = """You are a compliance reviewer for regulated marketing content.

Decide whether the CONTENT actually ASSERTS any prohibited claim. A prohibited claim
is one where the content PROMISES or STATES, as true, something on this banned list:
{banned}

CRITICAL RULE — context matters. A banned term used in a NEGATION, WARNING, DISCLAIMER,
or REFUSAL is NOT a violation. Only an affirmative assertion counts.
Examples that are NOT violations:
- "results are not permanent" (negation)
- "we cannot guarantee returns" (refusal)
- "diversification does not guarantee against loss" (warning)
Examples that ARE violations:
- "guaranteed 12% annual returns" (asserted)
- "permanent, flawless results" (asserted)
- "our treatment is 100% safe" (asserted)

Return STRICT JSON only, no prose:
{{"asserts_prohibited_claim": true|false, "prohibited_claims": ["the specific asserted claims, [] if none"], "rationale": "one short sentence"}}

CONTENT:
\"\"\"
{content}
\"\"\"
"""


def judge_claims(content: str, banned_terms: list[str], llm) -> ClaimResult:
    prompt = _CLAIM_PROMPT.format(banned=", ".join(banned_terms), content=content)
    data, _ = llm.complete_json(prompt)
    return ClaimResult(
        asserts_prohibited_claim=bool(data.get("asserts_prohibited_claim", False)),
        prohibited_claims=list(data.get("prohibited_claims", []) or []),
        rationale=str(data.get("rationale", "")),
    )


# ── Groundedness / faithfulness (system arm only) ────────────────────────────
@dataclass
class GroundednessResult:
    score: float = 0.0
    unsupported_claims: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_GROUND_PROMPT = """You assess GROUNDEDNESS (faithfulness) of marketing content against a
knowledge base. Consider only factual, checkable claims (numbers, durations, product
facts, credentials). Ignore generic marketing phrasing and opinions.

score = fraction of factual claims that are supported by the KNOWLEDGE BASE (0.0-1.0).
List any factual claims that are NOT supported by the knowledge base.

Return STRICT JSON only:
{{"score": 0.0-1.0, "unsupported_claims": ["..."], "rationale": "one short sentence"}}

KNOWLEDGE BASE:
\"\"\"
{kb}
\"\"\"

CONTENT:
\"\"\"
{content}
\"\"\"
"""


def judge_groundedness(content: str, kb_context: str, llm) -> GroundednessResult:
    if not kb_context.strip():
        return GroundednessResult(score=0.0, unsupported_claims=[], rationale="no knowledge base context")
    data, _ = llm.complete_json(_GROUND_PROMPT.format(kb=kb_context, content=content))
    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    return GroundednessResult(
        score=max(0.0, min(1.0, score)),
        unsupported_claims=list(data.get("unsupported_claims", []) or []),
        rationale=str(data.get("rationale", "")),
    )


# ── Brand-voice adherence (both arms) ────────────────────────────────────────
@dataclass
class BrandVoiceResult:
    score: float = 0.0
    issues: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_VOICE_PROMPT = """You assess how well CONTENT matches a brand's intended VOICE.

BRAND VOICE:
{voice}

Score 0.0-1.0 (1.0 = strongly on-voice). List concrete voice issues (e.g. hype where
the brand is sober, salesy where it should be consent-first).

Return STRICT JSON only:
{{"score": 0.0-1.0, "issues": ["..."], "rationale": "one short sentence"}}

CONTENT:
\"\"\"
{content}
\"\"\"
"""


def judge_brand_voice(content: str, voice_summary: str, llm) -> BrandVoiceResult:
    data, _ = llm.complete_json(_VOICE_PROMPT.format(voice=voice_summary, content=content))
    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    return BrandVoiceResult(
        score=max(0.0, min(1.0, score)),
        issues=list(data.get("issues", []) or []),
        rationale=str(data.get("rationale", "")),
    )
