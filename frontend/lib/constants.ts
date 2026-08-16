import type { ContentType, KnowledgeBaseSource, Language, Length } from "@/lib/types";

export const contentTypeOptions: Array<{ label: string; value: ContentType; description: string }> = [
  { label: "Blog Post", value: "blog", description: "Long-form admissions and thought leadership" },
  { label: "Social Media", value: "social", description: "LinkedIn and Instagram-ready copy" },
  { label: "Program", value: "program", description: "Prospectus and landing-page descriptions" },
  { label: "Newsletter", value: "newsletter", description: "Email campaigns with CTA structure" }
];

export const topicSuggestions: Record<ContentType, string[]> = {
  blog: ["Evidence-based investing", "What fee-only advice means", "Diversification and risk", "Planning for a liquidity event"],
  social: ["Fee transparency explained", "Why past performance isn't a promise", "Meet the investment committee", "Booking a portfolio review"],
  social_post: ["Fee transparency explained", "Why past performance isn't a promise", "Meet the investment committee", "Booking a portfolio review"],
  program: ["Meridian Core Portfolio", "Meridian Income", "Meridian Succession", "Injectable wrinkle relaxation"],
  newsletter: ["Quarterly market note", "Fee structure explainer", "Succession planning basics", "Consultation-first care"],
  email: ["Quarterly market note", "Fee structure explainer", "Succession planning basics", "Consultation-first care"],
  ad: ["Book a portfolio review", "Fee-only advisory", "Natural-looking results", "Book a consultation"],
  ad_copy: ["Book a portfolio review", "Fee-only advisory", "Natural-looking results", "Book a consultation"]
};

export const audienceOptions = [
  "Prospective Students",
  "Current Students",
  "Faculty & Staff",
  "Industry Partners",
  "Alumni"
];

export const toneOptions = ["Academic", "Formal", "Professional", "Friendly", "Conversational"];

export const lengthOptions: Length[] = ["Short", "Medium", "Long"];

export const languageOptions: Array<{ label: string; value: Language }> = [
  { label: "English", value: "english" },
  { label: "German", value: "german" }
];

export const knowledgeBaseOptions: Array<{ label: string; value: KnowledgeBaseSource; description: string }> = [
  { label: "Hybrid", value: "hybrid", description: "Primary brand sources plus market context" },
  { label: "Primary", value: "primary", description: "Official brand source material only" },
  { label: "Secondary", value: "secondary", description: "Market and benchmark context only" }
];

export const defaultRequest = {
  contentType: "blog" as ContentType,
  topic: "",
  audience: "Prospective Students",
  language: "english" as Language,
  tone: "Professional",
  length: "Medium" as Length,
  knowledgeBase: "hybrid" as KnowledgeBaseSource,
  files: []
};
