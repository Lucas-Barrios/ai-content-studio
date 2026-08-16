from src.content_pipeline import Pipeline

DIVIDER = "\n" + "─" * 60 + "\n"

pipeline = Pipeline(kb_dir="knowledge_base/meridian_wealth/")

# ── Stage 1: Document ─────────────────────────────────────────────────────────
print(DIVIDER + "STAGE 1 — DOCUMENT\n")
result = pipeline.document()
print(result)

# ── Stage 2: Monitor ──────────────────────────────────────────────────────────
print(DIVIDER + "STAGE 2 — MONITOR\n")
result = pipeline.monitor(
    topic="Why fee-only advice changes the conversation",
    content_type="blog_post",
    audience="the brand's target audience",
)
print(result)

# ── Stage 3: Brief ────────────────────────────────────────────────────────────
print(DIVIDER + "STAGE 3 — BRIEF\n")
result = pipeline.brief()
print(result)

# ── Stage 4: Publish ──────────────────────────────────────────────────────────
print(DIVIDER + "STAGE 4 — PUBLISH\n")
print("Calling OpenAI... (this may take a few seconds)\n")
content = pipeline.publish()
print(content)

# Save output
output_path = "output_pipeline.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"\nSaved to {output_path}")

# ── Stage 5: Iterate ──────────────────────────────────────────────────────────
print(DIVIDER + "STAGE 5 — ITERATE\n")
result = pipeline.iterate(
    feedback="Good structure, but open with a student outcome stat rather than a general AI trend sentence."
)
print(result)

print(DIVIDER + "Pipeline complete.\n")
