import { strict as assert } from "node:assert";
import test from "node:test";

import { GenerationRouter } from "./generation-router";
import type { LegacyGenerationClient } from "./types";
import type { BrandProfile, GenerateRequest, GenerateResponse, KnowledgeMatch } from "@/lib/types";

const baseRequest: GenerateRequest = {
  organizationId: "00000000-0000-0000-0000-000000000001",
  clientId: "00000000-0000-0000-0000-000000000002",
  projectId: "00000000-0000-0000-0000-000000000003",
  contentType: "social",
  topic: "Flexible MBA for working professionals",
  audience: "Prospective Students",
  language: "english",
  tone: "Professional",
  length: "Medium",
  knowledgeBase: "hybrid",
};

function response(request: GenerateRequest, content: string, framework: GenerateResponse["metadata"]["framework"]): GenerateResponse {
  return {
    content,
    sources: [],
    metadata: {
      topic: request.topic,
      contentType: request.contentType,
      language: request.language,
      tone: request.tone,
      length: request.length,
      knowledgeBase: request.knowledgeBase,
      wordCount: content.split(/\s+/).filter(Boolean).length,
      generatedAt: new Date().toISOString(),
      generationId: "test-generation",
      framework,
    },
  };
}

class FakeGenerationClient implements LegacyGenerationClient {
  saved: Array<{ request: GenerateRequest; response: GenerateResponse; prompt?: string }> = [];
  throwOnGenerateText = false;

  async generate(payload: GenerateRequest): Promise<GenerateResponse> {
    return response(payload, "legacy output with concrete brand context", "legacy-python");
  }

  async generateText(input: { system?: string; prompt: string; metadata?: Record<string, unknown> }): Promise<string> {
    if (this.throwOnGenerateText) throw new Error("framework failed");
    return `new framework output using ${String(input.metadata?.variantId ?? "default")} with specific brand audience context`;
  }

  async getBrandProfile(): Promise<BrandProfile | null> {
    return null;
  }

  async searchKnowledge(): Promise<KnowledgeMatch[]> {
    return [];
  }

  async saveGeneratedOutput(input: { request: GenerateRequest; response: GenerateResponse; prompt?: string }): Promise<void> {
    this.saved.push(input);
  }
}

test("feature flag disabled routes to legacy Python", async () => {
  const client = new FakeGenerationClient();
  const router = new GenerationRouter(client, { enableTsPromptFramework: false, mode: "supported", abTestVariants: false });
  const result = await router.generate(baseRequest);
  assert.equal(result.metadata.framework, "legacy-python");
  assert.equal(client.saved[0].response.metadata.framework, "legacy-python");
});

test("feature flag enabled routes social content to TypeScript prompt framework", async () => {
  const client = new FakeGenerationClient();
  const router = new GenerationRouter(client, { enableTsPromptFramework: true, mode: "supported", abTestVariants: false });
  const result = await router.generate(baseRequest);
  assert.equal(result.metadata.framework, "ts-prompt-framework");
  assert.equal(result.metadata.variantId, "precision-v1");
});

test("unsupported content type falls back to legacy", async () => {
  const client = new FakeGenerationClient();
  const router = new GenerationRouter(client, { enableTsPromptFramework: true, mode: "supported", abTestVariants: false });
  const result = await router.generate({ ...baseRequest, contentType: "blog" });
  assert.equal(result.metadata.framework, "legacy-python");
});

test("TypeScript framework error falls back to legacy with fallback metadata", async () => {
  const client = new FakeGenerationClient();
  client.throwOnGenerateText = true;
  const router = new GenerationRouter(client, { enableTsPromptFramework: true, mode: "supported", abTestVariants: false });
  const result = await router.generate(baseRequest);
  assert.equal(result.metadata.framework, "legacy-python");
  assert.equal(result.metadata.fallbackReason, "ts_prompt_framework_failed");
});

test("comparison mode returns both outputs and winner metadata", async () => {
  const client = new FakeGenerationClient();
  const router = new GenerationRouter(client, { enableTsPromptFramework: true, mode: "supported", abTestVariants: false });
  const result = await router.generate({ ...baseRequest, compareWithLegacy: true });
  assert.ok(result.legacyOutput);
  assert.ok(result.newFrameworkOutput);
  assert.ok(result.metadata.comparison?.recommendedWinner);
});

test("variantId selection is passed into metadata", async () => {
  const client = new FakeGenerationClient();
  const router = new GenerationRouter(client, { enableTsPromptFramework: true, mode: "supported", abTestVariants: false });
  const result = await router.generate({ ...baseRequest, variantId: "evidence-led-v1" });
  assert.equal(result.metadata.variantId, "evidence-led-v1");
});
