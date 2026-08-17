"""
Offline tests for the LLM judges.

The judges call an LLM, but EvalLLM accepts an injected client, so we feed canned
JSON responses and verify the full judge logic (parsing, clamping, the la-adv-002
negation case) without any network calls.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from evals.judges import judge_brand_voice, judge_claims, judge_groundedness
from evals.llm import EvalLLM


class _FakeClient:
    """Minimal stand-in for the OpenAI client: returns a preset JSON string."""

    def __init__(self, payload: dict):
        self._payload = json.dumps(payload)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        msg = SimpleNamespace(content=self._payload)
        choice = SimpleNamespace(message=msg)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        return SimpleNamespace(choices=[choice], usage=usage)


def _llm(payload: dict) -> EvalLLM:
    return EvalLLM(model="mock", client=_FakeClient(payload))


# ── Claim judge ──────────────────────────────────────────────────────────────
def test_claim_judge_flags_asserted_violation():
    llm = _llm({"asserts_prohibited_claim": True, "prohibited_claims": ["guaranteed 12% returns"], "rationale": "x"})
    r = judge_claims("guaranteed 12% returns", ["guaranteed"], llm)
    assert r.asserts_prohibited_claim is True
    assert r.prohibited_claims == ["guaranteed 12% returns"]


def test_claim_judge_passes_negation_the_la_adv_002_case():
    # The whole reason judges exist: "not permanent" must NOT be a violation, even
    # though the deterministic checker flags the word "permanent".
    llm = _llm({"asserts_prohibited_claim": False, "prohibited_claims": [], "rationale": "used in negation"})
    r = judge_claims("Results are not permanent and are not flawless.", ["permanent", "flawless"], llm)
    assert r.asserts_prohibited_claim is False
    assert r.prohibited_claims == []


# ── Groundedness judge ───────────────────────────────────────────────────────
def test_groundedness_parses_and_clamps():
    llm = _llm({"score": 1.4, "unsupported_claims": [], "rationale": "all supported"})
    r = judge_groundedness("content", "kb text", llm)
    assert r.score == 1.0  # clamped to [0,1]


def test_groundedness_zero_without_context():
    # No LLM call should happen when there's no kb context.
    llm = _llm({"score": 0.9})  # would return 0.9 if called
    r = judge_groundedness("content", "   ", llm)
    assert r.score == 0.0 and "no knowledge base" in r.rationale


# ── Brand-voice judge ────────────────────────────────────────────────────────
def test_brand_voice_parses():
    llm = _llm({"score": 0.8, "issues": ["slightly salesy"], "rationale": "mostly on-voice"})
    r = judge_brand_voice("content", "sober, evidence-led", llm)
    assert r.score == 0.8 and r.issues == ["slightly salesy"]


def test_judge_tolerates_malformed_json():
    # complete_json returns {} on unparseable output; judges must degrade gracefully.
    class BadClient(_FakeClient):
        def _create(self, **kwargs):
            msg = SimpleNamespace(content="not json at all")
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                                   usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))

    llm = EvalLLM(model="mock", client=BadClient({}))
    r = judge_claims("x", ["guaranteed"], llm)
    assert r.asserts_prohibited_claim is False  # safe default
