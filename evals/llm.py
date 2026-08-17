"""
evals/llm.py

A thin LLM caller for the eval harness that captures token usage and cost.

Why not reuse src.llm_integration.OpenAIWrapper? It discards response.usage — its
success dict only carries content/attempts/model. The eval needs real token counts
for the cost metric, so this uses the same model + env config (LLM_MODEL,
MAX_LLM_OUTPUT_TOKENS) but keeps the usage numbers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Approximate USD price per 1M tokens. These change; treat cost as an estimate and
# update if you switch models. (gpt-4o-mini / gpt-4o list prices as of early 2026.)
PRICES_PER_MTOK = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 2.50, "out": 10.00},
}


@dataclass
class LLMResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = PRICES_PER_MTOK.get(model, PRICES_PER_MTOK["gpt-4o-mini"])
    return round(prompt_tokens / 1e6 * price["in"] + completion_tokens / 1e6 * price["out"], 6)


class EvalLLM:
    """Same model/config as production generation, with usage capture."""

    def __init__(self, model: str | None = None, client=None, max_tokens: int | None = None):
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.max_tokens = max_tokens or int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "1800"))
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    def complete(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> LLMResult:
        kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
            temperature=temperature,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(**kwargs)
        usage = resp.usage
        pt = getattr(usage, "prompt_tokens", 0) or 0
        ct = getattr(usage, "completion_tokens", 0) or 0
        content = resp.choices[0].message.content or ""
        return LLMResult(
            content=content,
            model=self.model,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_usd=estimate_cost(self.model, pt, ct),
        )

    def complete_json(self, prompt: str, temperature: float = 0.0) -> tuple[dict, LLMResult]:
        """Judge call: temperature 0, JSON mode, tolerant parse. Returns ({}, res) on parse failure."""
        import json as _json
        import re as _re

        res = self.complete(prompt, temperature=temperature, json_mode=True)
        text = res.content.strip()
        try:
            return _json.loads(text), res
        except Exception:
            m = _re.search(r"\{.*\}", text, _re.DOTALL)
            if m:
                try:
                    return _json.loads(m.group(0)), res
                except Exception:
                    pass
            return {}, res
