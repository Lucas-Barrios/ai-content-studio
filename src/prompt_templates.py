"""
prompt_templates.py

Centralised library of prompt templates for each content type.

Responsibilities:
  - Provide structured, brand-neutral prompts for blog posts, social media,
    service/offering descriptions, and newsletters.
  - Inject retrieved context (RAG chunks) and user-supplied variables.
  - Defer all brand voice, positioning, and banned-term enforcement to the
    BRAND PROFILE block supplied at runtime.

Design note — brand neutrality:
  These templates never hardcode a client brand. Brand voice reaches the model
  two ways depending on the path:
    - Production API path: brand_intelligence.assemble_brand_block() injects a
      structured BRAND PROFILE section (voice, approved/banned terms, compliance
      notes) ahead of the template.
    - File-based CLI path: the active tenant's brand_guidelines.md is part of the
      retrieved knowledge-base context.
  The templates instruct the model to obey whichever brand guidance is present
  and to ground every claim in the KNOWLEDGE BASE CONTEXT.
"""

SUPPORTED_LANGUAGES = {"english", "german"}

BRAND_VOICE_CONTRACT = """
BRAND & COMPLIANCE CONTRACT (applies to every piece of content):
- Follow the BRAND PROFILE block if one is provided above; otherwise follow the
  brand guidelines found in the KNOWLEDGE BASE CONTEXT.
- Never use any term listed as banned/prohibited for the brand. If a natural
  phrasing would use a banned term, rewrite it — do not use a near-synonym that
  breaks the same rule.
- Ground every factual claim, statistic, name, or figure in the KNOWLEDGE BASE
  CONTEXT below. Do not invent facts, outcomes, or numbers.
- Honour the brand's compliance notes exactly (e.g. required disclosures, risk
  statements, consent-first CTAs). When in doubt, state limits plainly rather
  than overclaiming.
- Match the brand's voice and reading level. Avoid hollow superlatives
  ("world-class", "cutting-edge"), passive voice, and filler.
"""

GERMAN_VOICE_ADDENDUM = """
German Language Rules (apply in addition to all brand rules above):
- Write entirely in German — headings, body, CTA, and meta description.
- Use formal "Sie" address throughout (not "du").
- Adapt idioms naturally — do not translate English phrases word-for-word.
- Lead with practical outcomes and relevance; de-emphasise prestige language.
"""


def _validate_language(language: str) -> str:
    """Normalise and validate the language parameter. Returns the lowercased value."""
    normalised = language.strip().lower()
    if normalised not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Choose one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )
    return normalised


def _language_block(language: str) -> str:
    """Return the language instruction block to append to any template."""
    if language == "german":
        return f"\nOUTPUT LANGUAGE: German{GERMAN_VOICE_ADDENDUM}"
    return "\nOUTPUT LANGUAGE: English (British spelling throughout)"


def blog_post_template(kb_context: str, topic: str, language: str = "english") -> str:
    """
    Generate a long-form blog post grounded in the retrieved knowledge base.

    Brand-neutral: voice and compliance come from the BRAND PROFILE block or the
    brand guidelines present in kb_context. Aim for 700–1,000 words; cite only
    facts drawn from kb_context.

    Args:
        kb_context: Relevant chunks retrieved for the active brand.
        topic: The specific angle or question the post should address.
        language: Output language — 'english' or 'german'. Defaults to 'english'.
    """
    language = _validate_language(language)
    return f"""You are a senior content strategist writing for the client brand described in the BRAND PROFILE / knowledge base below.
Produce an engaging, expert-led blog post on the topic below.

{BRAND_VOICE_CONTRACT}

--- KNOWLEDGE BASE CONTEXT ---
{kb_context}
--- END CONTEXT ---

TOPIC: {topic}

OUTPUT REQUIREMENTS:
- Length: 700–1,000 words.
- Structure: brand-specific hook, 2–4 body sections with subheadings, closing CTA consistent with the brand's CTA conventions.
- Back every claim with evidence from the context above — no invented statistics.
- End with a one-sentence meta description (prefixed "Meta:") suitable for SEO.
- Format in Markdown.

HOOK RULE — this is the most important instruction:
- The very first sentence must be a concrete, brand-specific hook drawn from the context above
  (a named proof point, a specific figure with its source/period, or a distinctive detail).
- NEVER open with: "In today's world…", "Artificial intelligence is transforming…",
  "Choosing the right…", "In an era of…", or any generic scene-setting sentence.
- If you cannot find a suitable hook in the context, open with the most specific brand fact
  available rather than a generic statement.
{_language_block(language)}"""


def social_media_template(kb_context: str, announcement: str, language: str = "english") -> str:
    """
    Create a dual-format LinkedIn and Instagram post for a brand announcement.

    Returns two posts: one for LinkedIn (~150 words) and one for Instagram
    (~60 words), both anchored to a concrete brand proof point from kb_context.

    Args:
        kb_context: Relevant chunks retrieved for the active brand.
        announcement: The specific news or message to promote.
        language: Output language — 'english' or 'german'. Defaults to 'english'.
    """
    language = _validate_language(language)
    return f"""You are the social media manager for the client brand described in the BRAND PROFILE / knowledge base below.
Write two posts for the announcement below — one for LinkedIn, one for Instagram.

{BRAND_VOICE_CONTRACT}

--- KNOWLEDGE BASE CONTEXT ---
{kb_context}
--- END CONTEXT ---

ANNOUNCEMENT: {announcement}

HOOK RULE — applies to both posts:
- The opening line must be a concrete, brand-specific hook drawn from the context above.
- NEVER open with: "Exciting news!", "We are thrilled to announce…", "In today's competitive landscape…", or any generic marketing phrase.

## LinkedIn Post
- Length: 100–150 words.
- First line: brand-specific hook (see above).
- Highlight one specific brand differentiator or proof point from the context.
- Close with a CTA consistent with the brand's CTA conventions.
- Include 3–5 relevant hashtags at the end.

## Instagram Post
- Length: 50–70 words.
- First line: punchy brand-specific hook — write as if paired with a strong image.
- Use 1–2 emojis maximum; no emoji spam.
- Include 5–8 hashtags on a separate line.
{_language_block(language)}"""


def program_description_template(kb_context: str, program_name: str, language: str = "english") -> str:
    """
    Write a polished description of a single offering (a service, product, or
    programme) for a website or one-pager.

    Brand-neutral and vertical-agnostic: works for a service line, a product,
    or a programme. All specifics — sections, outcomes, requirements — must come
    from kb_context. `program_name` is the offering name.

    Args:
        kb_context: Relevant chunks retrieved for the active brand.
        program_name: Name of the offering to describe.
        language: Output language — 'english' or 'german'. Defaults to 'english'.
    """
    language = _validate_language(language)
    return f"""You are a senior copywriter producing official offering copy for the client brand described in the BRAND PROFILE / knowledge base below.
Write a complete description of the offering specified below.

{BRAND_VOICE_CONTRACT}

--- KNOWLEDGE BASE CONTEXT ---
{kb_context}
--- END CONTEXT ---

OFFERING: {program_name}

OUTPUT STRUCTURE (use these exact headings, format in Markdown):

HOOK RULE — applies to the Headline and Overview:
- The headline and first sentence of the Overview must be grounded in a specific fact,
  outcome, or detail about this offering from the context above.
- NEVER open with: "Welcome to…", "Are you ready to…", "In today's … world…", or any
  phrase that could apply to any brand.

## [Offering Name] — Headline
A single punchy headline (max 12 words) that leads with the reader's outcome, not the brand.

## Overview
2–3 sentences: what the offering is, who it is for, and what makes the brand's approach
distinctive. Grounded in context; no invented facts; honour all compliance notes.

## What's Included
Bullet list of 4–6 concrete elements, features, or steps drawn from the context.

## Who It's For
2–3 sentences describing the intended audience and when this offering is (and is not) a fit.

## What To Expect
2–3 sentences on the process, timeline, or outcomes — stated factually and, where the brand's
compliance notes require it, with the appropriate caveats (e.g. results vary, risk statements).

## Next Step
One-sentence CTA consistent with the brand's CTA conventions.
{_language_block(language)}"""


def newsletter_template(kb_context: str, topic: str, language: str = "english") -> str:
    """
    Write ready-to-send newsletter copy for the active brand.

    Structured email copy with a subject line, scannable sections, and a CTA.
    All facts come from kb_context; voice and compliance come from the brand.

    Args:
        kb_context: Relevant chunks retrieved for the active brand.
        topic: The newsletter edition theme.
        language: Output language — 'english' or 'german'. Defaults to 'english'.
    """
    language = _validate_language(language)
    return f"""You are the email marketing manager for the client brand described in the BRAND PROFILE / knowledge base below.
Produce complete, ready-to-send newsletter copy on the topic below.

{BRAND_VOICE_CONTRACT}

--- KNOWLEDGE BASE CONTEXT ---
{kb_context}
--- END CONTEXT ---

TOPIC / EDITION THEME: {topic}

OUTPUT STRUCTURE (use these exact headings, format in Markdown):

HOOK RULE:
- The subject line and opening sentence must be grounded in a specific fact or event from the
  context — not a generic "We hope this email finds you well" opener.
- NEVER open with: "Dear reader,", "We are excited to share…", "In this edition…", or any
  generic newsletter filler.

## Subject Line
One punchy subject line (max 9 words). Write a second option prefixed "A/B:".

## Preview Text
One sentence (max 12 words) shown in the inbox before opening — complement the subject line.

## Opening
2–3 sentences. Start with a specific brand hook from the context. Warm but direct.

## Section 1 — News & Updates
2–3 short paragraphs covering the most relevant items from the context, with a subheading each.
Include dates and specifics where available.

## Section 2 — Spotlight
One concrete story, proof point, or offering drawn from the knowledge base. 100–150 words.

## Section 3 — Offering Highlight
Spotlight one offering relevant to the topic. Lead with a concrete, context-grounded benefit.
80–120 words. End with a one-line CTA consistent with the brand's CTA conventions.

## Call to Action
One primary CTA button label + URL placeholder, e.g.:
**[Book a conversation →](#)**
One secondary CTA, e.g.: **[Learn more →](#)**

## Footer
- Use the brand's real contact details from the context if present; otherwise leave a
  [contact] placeholder. Never invent an address or email.
- Unsubscribe placeholder: [Unsubscribe](#)
{_language_block(language)}"""
