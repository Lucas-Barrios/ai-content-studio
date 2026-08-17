"""
evals/arms.py

The two generation arms the harness compares.

  baseline : a naive generic prompt — no brand profile, no retrieval, no hook rule.
             This is the "generic ChatGPT wrapper" the system must beat.
  system   : the intended production pipeline — brand profile injected from Supabase
             + vector-RAG retrieval of the tenant's ingested knowledge base + the
             brand-neutral prompt template (which carries the compliance contract and
             hook rule).

Both arms call the SAME model (evals.llm.EvalLLM), so any measured difference comes
from brand conditioning + RAG grounding + the template, not from a model change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.llm import EvalLLM

# Map dataset content_type -> brand-neutral template. All four templates take
# (kb_context, subject, language) positionally, so one call site works for all.
_TEMPLATES = {
    "blog": "blog_post_template",
    "social": "social_media_template",
    "program": "program_description_template",
    "newsletter": "newsletter_template",
}


@dataclass
class Generation:
    arm: str
    case_id: str
    tenant: str
    content_type: str
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    retrieved_k: int = 0
    retrieved_context: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def baseline_prompt(case: dict) -> str:
    """Naive prompt: what a generic tool produces with no brand or grounding."""
    ct = case["content_type"]
    return (
        f"Write a {ct} for a company about the following topic. "
        f"Make it engaging and persuasive.\n\nTopic: {case['topic']}"
    )


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        title = c.get("title") or "source"
        lines.append(f"[{title}] {c.get('content', '').strip()}")
    return "\n\n".join(lines)


def system_prompt(case: dict) -> tuple[str, int, list[str], str]:
    """Full pipeline prompt: brand block + retrieved KB chunks + brand-neutral template.

    Returns (prompt, retrieved_k, warnings, retrieved_context). Warnings flag silent
    degradation — an empty brand block or zero retrieved chunks means the 'system' arm
    is not actually running as the system, and its scores should not be trusted.
    retrieved_context is the raw chunk text, used by the groundedness judge.
    """
    from src import prompt_templates as T
    from src.brand_intelligence import assemble_brand_block, retrieve_brand_context
    from src.rag_ingestion import search_knowledge_chunks

    topic = case["topic"]
    client_id = case["client_id"]
    warnings: list[str] = []

    ctx = retrieve_brand_context(topic=topic, client_id=client_id)
    brand_block = assemble_brand_block(ctx) if ctx else ""
    if not brand_block.strip():
        warnings.append("empty_brand_block")

    chunks = search_knowledge_chunks(
        query=topic,
        client_id=client_id,
        match_count=6,
        # The code default (0.72) is too strict for text-embedding-3-small, whose
        # on-topic cosine sims run ~0.3-0.5; at 0.72 retrieval returns almost nothing.
        # Favour recall here; Step 3 (reranking) restores precision.
        match_threshold=0.15,
    )
    if not chunks:
        warnings.append("zero_chunks_retrieved")
    kb_body = _format_chunks(chunks)

    kb_context = ""
    if brand_block:
        kb_context += brand_block + "\n\n"
    kb_context += "RETRIEVED KNOWLEDGE BASE:\n" + (kb_body or "(no chunks retrieved)")

    template_fn = getattr(T, _TEMPLATES.get(case["content_type"], "blog_post_template"))
    prompt = template_fn(kb_context, topic, case.get("language", "english"))
    return prompt, len(chunks), warnings, kb_body


def generate(arm: str, case: dict, llm: EvalLLM) -> Generation:
    """Run one arm for one case. Errors are captured, not raised, so a run completes."""
    base = dict(
        arm=arm, case_id=case["id"], tenant=case["tenant"],
        content_type=case["content_type"],
    )
    try:
        if arm == "baseline":
            res = llm.complete(baseline_prompt(case))
            k, warnings, retrieved = 0, [], ""
        elif arm == "system":
            prompt, k, warnings, retrieved = system_prompt(case)
            res = llm.complete(prompt)
        else:
            raise ValueError(f"unknown arm '{arm}'")
        return Generation(
            **base, content=res.content, model=res.model,
            prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
            cost_usd=res.cost_usd, retrieved_k=k, retrieved_context=retrieved, warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001 — a failed generation shouldn't kill the run
        return Generation(
            **base, content="", model=llm.model,
            prompt_tokens=0, completion_tokens=0, cost_usd=0.0, retrieved_k=0,
            error=f"{type(exc).__name__}: {exc}",
        )
