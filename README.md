# AI Content Studio

**Governed, multi-tenant AI content generation with brand-safe guardrails, RAG grounding, and reproducible evaluation.**

Most AI content generators are a prompt and a hope. In regulated industries that hope is a liability. A wealth manager cannot promise "guaranteed returns," an aesthetics clinic cannot promise "permanent, 100% safe results," and a generic model will write both without hesitation. This project is a reference implementation of a governed content pipeline (brand voice, banned-claim enforcement, and RAG grounding, served per client with tenant isolation) together with the evaluation harness that measures whether the governance actually holds.

The evaluation is the point. Shipping AI features without evals is a fast way to lose trust, and a system that claims to be brand-safe but cannot prove it is worth little. So the headline of this repository is not the application. It is the scorecard.

## Headline result

A reproducible evaluation over 32 cases across two regulated demo brands (16 each, including 8 adversarial cases engineered to elicit a compliance violation), comparing a naive baseline (generic prompt, no brand, no retrieval) against the system (brand profile, RAG grounding, and a compliance-aware template). Generation runs on `gpt-4o-mini`; judging runs on `gpt-4o`, a stronger and different model chosen to reduce self-preference bias; groundedness is independently cross-checked with ragas.

| Metric | baseline | system | notes |
|---|---|---|---|
| True violation rate (judge, context-aware) | 0.28 | 0.00 | asserted prohibited claims |
| Adversarial safe-reframing (judge) | 0.00 | 1.00 | 8 of 8 traps refused |
| Groundedness (LLM judge) | n/a | 0.95 | ragas faithfulness: 0.78 |
| Brand-voice adherence (judge) | 0.37 | 0.80 | |
| Disclosure coverage | 0.27 | 0.59 | genuine gap, see below |
| Banned-term rate (raw, context-blind) | 0.44 | 0.22 | mostly negations, see below |
| Generic-opener rate | 0.03 | 0.00 | anti-slop check |
| Cost per run (USD) | 0.012 | 0.018 | 32 generations |

Reproduce it:

```bash
python -m evals.run                 # generate and score, both arms
python -m evals.ragas_check         # independent faithfulness cross-check
python -m pytest evals/tests/ -q    # 27 tests; the evaluator is itself tested
```

### What the numbers say, including where the system is weak

Two figures in that table are deliberately unflattering, and they are what make it credible.

Disclosure coverage is only 0.59. The system is excellent at not asserting prohibited claims (0.00 true violations) but merely good at reliably including required disclosures such as "past performance is not a reliable indicator" or "results vary." That is a measured weakness and the next improvement target, not something averaged away.

The raw banned-term rate (0.22) sits above the judge-confirmed rate (0.00). That gap is not a violation. It is context-blindness: a substring checker flags "results are not permanent" as a "permanent" violation. The purpose of the LLM-judge layer is to distinguish asserting a claim from refusing one, and the scorecard reports both numbers so the difference is visible rather than laundered.

Groundedness reads 0.95 by the LLM judge and 0.78 by ragas. Both indicate strong grounding. The difference reflects the stricter atomic-claim decomposition ragas performs. Both are reported rather than the more flattering single number.

The design principle throughout: report the dual numbers, disclose the gaps, and cross-check your own metrics against your own interest.

## How the evaluation works

Three layers, from most objective to least.

Deterministic checkers (`evals/checkers.py`) handle banned-term matching with true word boundaries, so "cure" does not match "manicure" or "procedure," plus curly-quote normalization, required-disclosure coverage, and a generic-opener check for anti-slop. This layer is fully offline, needs no API, and is unit-tested.

LLM-as-judge (`evals/judges.py`, temperature 0) provides a context-aware claim check (assert versus negate), groundedness against retrieved context, and brand-voice adherence. The judge runs on a stronger and different model than the generator.

An independent cross-check (`evals/ragas_check.py`) runs ragas Faithfulness on the system arm, isolated in its own pinned dependency set so it can never break the core harness.

The golden dataset (`evals/datasets/*.jsonl`) holds 32 version-controlled cases across the two tenants, each declaring the disclosures it requires and spanning standard, hard, and adversarial difficulty. Silent degradation is guarded: if the system arm loses its brand block or retrieves zero chunks, the run flags it loudly rather than quietly scoring a broken pipeline as a valid result.

## The two demo tenants

Both are fictional, chosen because generic model output is a genuine compliance liability in each, which is what makes the governance delta large and legible.

Meridian Wealth is a DACH wealth advisory operating under financial-promotion rules: no "guaranteed," "risk-free," or "beat the market," and mandatory risk disclosures. Lumen Aesthetics is a Berlin aesthetics clinic operating under medical-advertising rules: no "permanent," "100% safe," or "cure," consent-first calls to action, and outcomes stated as temporary and variable.

They sit under one demo agency organization, Northlight Studio, with per-client isolation enforced by Postgres row-level security. The same platform serves opposite regulatory regimes, which is the multi-tenant story an agency or consultancy actually cares about.

## Architecture

```
Next.js frontend (TypeScript prompt framework, shadcn)
  -> Next.js API routes
  -> FastAPI backend
       -> brand profiles and banned-term governance
       -> RAG ingestion and retrieval (OpenAI embeddings, pgvector)
       -> generation (OpenAI)
  -> Supabase Postgres and pgvector (multi-tenant, row-level security on every table)
```

| Area | Key files |
|---|---|
| Evaluation harness | `evals/` |
| RAG ingestion and retrieval | `src/rag_ingestion.py` |
| Brand governance | `src/brand_intelligence.py` |
| Brand-neutral prompt templates | `src/prompt_templates.py` |
| Python API | `api_server.py` |
| Supabase schema and migrations | `supabase/migrations/` |
| Frontend | `frontend/app/`, `frontend/components/` |

## What is real, and what is roadmap

Honesty about maturity is part of the point.

Real and reproducible today: the full evaluation harness and every number above; a multi-tenant schema with row-level security, two seeded regulated tenants, and RAG ingestion with content-hash dedup; brand-profile governance (voice, approved and banned terms, compliance notes) injected at generation time; and vector retrieval (pgvector, HNSW cosine) over per-tenant knowledge bases.

On the roadmap, in order. Production RAG comes first: hybrid retrieval (BM25 with vector) and reranking, with the harness measuring whether it lifts groundedness above the current 0.95 judge and 0.78 ragas. Guardrails follow: prompt-injection defense, PII checks, and explicit OWASP-LLM and EU AI Act mapping, with disclosure coverage (0.59) as a named target. Then cost and observability: per-generation tracing and model routing. Finally, wiring vector retrieval into the primary generation endpoint, which currently grounds through a file-based path while the evaluation exercises the intended RAG pipeline directly, and consolidating the two generation paths.

## Run it

Full setup for backend, frontend, Supabase, and environment lives in [`docs/SETUP.md`](docs/SETUP.md). The short version:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# set OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in .env
python -m evals.ingest_kb        # embed the two tenants' knowledge bases
python -m evals.run              # run the evaluation
```

## Notes on method

Same-provider generate-and-judge (`gpt-4o` judging `gpt-4o-mini`) reduces but does not eliminate self-preference bias. A cross-provider judge is a supported configuration through `JUDGE_MODEL` and a natural next step.

No fabricated metrics, clients, or history. Every figure here is produced by a committed report in `evals/reports/` and is reproducible from the commands above.
