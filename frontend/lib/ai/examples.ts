import { evaluateUniqueness } from "./evaluation/uniqueness";
import { buildPrompt } from "./prompt-builder/prompt-builder";
import type { PromptBuildContext } from "./prompts/types";

export const campaignPromptExample: PromptBuildContext = {
  useCase: "campaign",
  userInput: {
    language: "english",
    tone: "Professional",
    contentType: "social",
    brief: "Launch a 4-week campaign for the Meridian Core Portfolio.",
    audience: "private clients comparing fee-only advisory options",
  },
  brand: {
    name: "Meridian Wealth",
    positioning: "Boutique DACH wealth advisory competing on rigor and transparency, not performance claims.",
    voice: "Precise, sober, evidence-led",
    toneGuidelines: "Every claim backed by a mechanism or source. State downside plainly. No hype adjectives.",
    audienceSummary: "Private clients and family offices; financially literate, time-poor, skeptical of hype.",
    approvedTerms: ["diversified", "evidence-based", "risk-adjusted", "capital preservation"],
    bannedTerms: ["guaranteed", "risk-free", "beat the market", "double your money"],
    complianceNotes: "Financial promotion. Past performance is not a reliable indicator of future results; value can fall as well as rise. Marketing only, not personal advice.",
  },
  campaign: {
    goal: "Increase portfolio-review consultations",
    offer: "Meridian Core Portfolio",
    audience: "private clients evaluating a fee-only advisory",
    channels: ["linkedin", "email"],
    startDate: "2026-06-01",
    endDate: "2026-06-30",
  },
  ragDocuments: [
    {
      id: "kb_1",
      title: "Fee structure",
      content: "Meridian charges a single all-in annual advisory fee in basis points, disclosed before onboarding. No performance fees, no product commissions, no retrocessions.",
      sourceKind: "brand",
      contentType: "program",
      language: "english",
      channel: "website",
      tags: ["fees", "transparency"],
      similarity: 0.84,
    },
  ],
};

export const socialPromptExample: PromptBuildContext = {
  ...campaignPromptExample,
  useCase: "social_post",
  userInput: {
    ...campaignPromptExample.userInput,
    channel: "linkedin",
    topic: "What a fee-only advisory fee actually covers",
  },
};

export const emailPromptExample: PromptBuildContext = {
  ...campaignPromptExample,
  useCase: "email",
  userInput: {
    ...campaignPromptExample.userInput,
    channel: "email",
    topic: "Invite private clients to a portfolio review",
  },
};

export function buildExamplePrompt() {
  return buildPrompt(socialPromptExample);
}

export function sampleUniquenessReport() {
  const systemOutput = `For a private investor, the real question is rarely "what return can I get?" It is "who is paying whom, and for what?"

Meridian's fee-only model means its revenue comes solely from a single disclosed advisory fee — no performance fees, no product commissions, no retrocessions. That structure removes the hidden incentive that can quietly shape advice elsewhere.

Past performance is not a reliable indicator of future results, and the value of investments can fall as well as rise. What Meridian offers instead is clarity: you always know what you own and why.

Book a portfolio review to see how a transparent, evidence-based mandate would fit your circumstances.`;

  const baselineOutput = `In today's fast-paced world, growing your wealth has never been more important. Our expert team offers innovative solutions with great returns for investors who want to get ahead. Contact us today to learn more!`;

  return evaluateUniqueness(systemOutput, baselineOutput);
}
