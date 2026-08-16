# Prompt Engineering Framework

This framework lives in `frontend/lib/ai` and is designed for server-side Next.js usage with the Vercel AI SDK. It does not replace the current Python backend yet; it creates the reusable prompt layer needed for campaign generation, social posts, emails, ads, repurposing, A/B testing, uniqueness scoring, and future prompt observability.

## Structure

- `frontend/lib/ai/prompts/types.ts`
  Shared TypeScript interfaces for templates, variants, prompt context, pipeline steps, and uniqueness reports.
- `frontend/lib/ai/prompts/templates.ts`
  Versioned template registry for `campaign`, `social_post`, `email`, `ad`, and `repurpose`.
- `frontend/lib/ai/prompts/constraints.ts`
  Anti-generic language rules, tracked generic phrases, and reusable quality constraints.
- `frontend/lib/ai/prompt-builder/prompt-builder.ts`
  Dynamic prompt assembly from brand profile, RAG documents, campaign context, and user input.
- `frontend/lib/ai/orchestration/pipeline.ts`
  Multi-step prompt flow: strategy, angle selection, generation, refinement, evaluation.
- `frontend/lib/ai/evaluation/uniqueness.ts`
  Baseline comparison using lexical diversity, sentence variation, term overlap, generic phrase counts, and cosine similarity over term vectors.
- `frontend/lib/ai/examples.ts`
  Example campaign, social, and email prompt contexts plus a sample uniqueness report.

## Prompt Architecture

Each prompt has:

- System role and constraints
- Context block for brand, RAG, campaign, and user input
- Task definition
- Strategy step
- Distinctiveness block
- Output format
- Quality bar

Templates are versioned with `id` and `version`. Prompt variants are separate from templates so A/B tests can change style, distinctiveness, or reasoning emphasis without duplicating the full template.

## Example Usage

```ts
import { buildPrompt, runPromptPipeline, socialPromptExample } from "@/lib/ai";

const prompt = buildPrompt(socialPromptExample);

const result = await runPromptPipeline(socialPromptExample, {
  async generate({ system, prompt, metadata }) {
    // TO BE: call Vercel AI SDK here with your selected model.
    // Store metadata.promptRunId, templateId, templateVersion, and variantId.
    return `${system ?? ""}\n${prompt}`;
  },
});
```

## Sample Uniqueness Report

The example in `sampleUniquenessReport()` compares a brand-specific output with a generic baseline and returns:

```json
{
  "score": 71,
  "cosineSimilarity": 0.4775,
  "recommendation": "refine",
  "notes": [
    "Output separates from the generic baseline.",
    "No tracked generic phrases detected.",
    "Distinct term ratio is acceptable."
  ]
}
```

Exact scores may shift as the copy changes, but the report structure is stable.

## A/B Testing

`runPromptPipeline()` evaluates all selected prompt variants by default and chooses the highest uniqueness score:

```ts
await runPromptPipeline(context, modelClient, {
  variantIds: ["precision-v1", "opinionated-v1"],
  autoSelectBestVariant: true,
  includeBaseline: true,
});
```

Selection is currently based on uniqueness quality metrics. TO BE: combine this score with feedback events, approval rate, edit distance, conversion data, and client-specific brand compliance outcomes once these are persisted in Supabase.

## Observability

Every assembled prompt includes an `observability` object with:

- `runId`
- `templateId`
- `templateVersion`
- `variantId`
- `useCase`
- `promptText`
- retrieved context snapshots
- brand and campaign snapshots
- timestamp

TO BE in Supabase:

- Add or extend a `prompt_runs` table.
- Store prompt version, variant, model, retrieved chunk IDs, final output ID, uniqueness score, and user feedback.
- Link `generated_outputs.metadata.promptRunId` to the prompt run.

## Extending

1. Add a new `PromptUseCase` in `prompts/types.ts`.
2. Add a template to `PROMPT_TEMPLATES`.
3. Reuse `DISTINCTIVENESS_BLOCK` unless the new use case needs stricter rules.
4. Add examples in `examples.ts`.
5. Run `npm run typecheck`.

Keep prompt templates focused on reusable behavior. Client-specific facts should come from brand profiles, campaign context, and RAG documents, not hardcoded template text.
