"""
main.py — AI Content Studio
Demo entry point for the presentation.

Usage:
  python main.py --type blog    --topic "Evidence-based investing"
  python main.py --type social  --topic "Open Day June 2026" --extra "Join us on 14 June"
  python main.py --type program --topic "MSc Applied Data Science and AI"
  python main.py --type demo
"""

import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from src.content_pipeline import Pipeline
from src.llm_integration import ContentGeneratorError

OUTPUTS_DIR = "outputs"
DIVIDER = "\n" + "═" * 60 + "\n"

CONTENT_LABELS = {
    "blog":       "Blog Post",
    "social":     "Social Media Post",
    "program":    "Program Description",
    "newsletter": "Newsletter",
    "demo":       "Full Pipeline Demo",
}


def banner(title: str) -> str:
    return f"{DIVIDER}{title.upper()}{DIVIDER}"


def check_env() -> None:
    """Verify the environment is ready before any API calls are made."""
    load_dotenv()

    if not os.path.exists(".env"):
        print(
            "Warning: no .env file found in the current directory.\n"
            "  Fix: run  cp .env.example .env  then add your API key."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "\nError: OPENAI_API_KEY is not set.\n"
            "  Fix: open .env and set:  OPENAI_API_KEY=sk-...\n"
            "  Get a key at: https://platform.openai.com/api-keys"
        )
        sys.exit(1)

    if not api_key.startswith("sk-"):
        print(
            "\nError: OPENAI_API_KEY looks malformed (expected to start with 'sk-').\n"
            "  Fix: check the value in your .env file."
        )
        sys.exit(1)


LANG_CODE = {"english": "en", "german": "de"}


def save(content: str, content_type: str, topic: str, language: str = "english") -> str:
    try:
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = topic.lower().replace(" ", "_")[:40]
        lang = LANG_CODE.get(language, "en")
        filename = f"{OUTPUTS_DIR}/{content_type}_{slug}_{lang}_{timestamp}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"<!-- type: {content_type} | topic: {topic} | language: {language} | generated: {timestamp} -->\n\n")
            f.write(content)
        return filename
    except OSError as e:
        print(f"  Warning: could not save output — {e}")
        return "(not saved)"


def _publish_and_save(pipeline: Pipeline, content_type: str, topic: str, language: str = "english") -> None:
    """Shared publish + save logic with error handling for all run_* functions."""
    try:
        content = pipeline.publish()
    except ContentGeneratorError as e:
        print(f"\nContent generation failed:\n  {e}")
        sys.exit(1)

    print(content)
    path = save(content, content_type, topic, language)
    print(f"\n✓ Saved → {path}")


def run_blog(pipeline: Pipeline, topic: str, extra: str, language: str) -> None:
    print(banner("Stage 2 — Monitor"))
    print(pipeline.monitor(topic=topic, content_type="blog", audience="the brand's target audience", extra=extra))

    print(banner("Stage 3 — Brief"))
    print(pipeline.brief())

    print(banner("Stage 4 — Publish · Generating blog post..."))
    _publish_and_save(pipeline, "blog", topic, language)


def run_social(pipeline: Pipeline, topic: str, extra: str, language: str) -> None:
    announcement = extra or topic
    print(banner("Stage 2 — Monitor"))
    print(pipeline.monitor(topic=topic, content_type="social", audience="the brand's target audience", extra=announcement))

    print(banner("Stage 3 — Brief"))
    print(pipeline.brief())

    print(banner("Stage 4 — Publish · Generating social media posts..."))
    _publish_and_save(pipeline, "social", topic, language)


def run_program(pipeline: Pipeline, topic: str, extra: str, language: str) -> None:
    program_name = extra or topic
    print(banner("Stage 2 — Monitor"))
    print(pipeline.monitor(topic=topic, content_type="program", audience="the brand's target audience", extra=program_name))

    print(banner("Stage 3 — Brief"))
    print(pipeline.brief())

    print(banner("Stage 4 — Publish · Generating program description..."))
    _publish_and_save(pipeline, "program", topic, language)


def run_newsletter(pipeline: Pipeline, topic: str, language: str) -> None:
    print(banner("Stage 2 — Monitor"))
    print(pipeline.monitor(topic=topic, content_type="newsletter", audience="the brand's target audience"))

    print(banner("Stage 3 — Brief"))
    print(pipeline.brief())

    print(banner("Stage 4 — Publish · Generating newsletter..."))
    _publish_and_save(pipeline, "newsletter", topic, language)


def run_demo(pipeline: Pipeline, language: str) -> None:
    """Walk through all five pipeline stages with a preset topic."""
    topic = "Why fee-only advice changes the conversation"

    print(banner("Stage 2 — Monitor"))
    print(pipeline.monitor(topic=topic, content_type="blog", audience="the brand's target audience"))

    print(banner("Stage 3 — Brief"))
    print(pipeline.brief())

    print(banner("Stage 4 — Publish · Generating content..."))
    _publish_and_save(pipeline, "demo", topic, language)

    print(banner("Stage 5 — Iterate"))
    feedback = "Open with a specific student outcome stat. Avoid generic AI trend opener."
    print(pipeline.iterate(feedback=feedback))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Content Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py --type blog    --topic "Evidence-based investing"
  python main.py --type social  --topic "Open Day June 2026" --extra "Join us 14 June in Berlin"
  python main.py --type program --topic "MSc Applied Data Science and AI"
  python main.py --type demo
        """,
    )
    parser.add_argument(
        "--type",
        choices=["blog", "social", "program", "newsletter", "demo"],
        required=True,
        help="Content type to generate",
    )
    parser.add_argument("--topic", default="", help="Topic or subject for the content")
    parser.add_argument(
        "--extra",
        default="",
        help="Secondary input: announcement text (social) or program name (program)",
    )
    parser.add_argument(
        "--kb",
        default="knowledge_base/meridian_wealth/",
        help="Path to knowledge base directory (default: knowledge_base/meridian_wealth/)",
    )
    parser.add_argument(
        "--language",
        choices=["english", "german"],
        default="english",
        help="Output language (default: english)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_env()

    print(banner(f"AI Content Studio — {CONTENT_LABELS[args.type]}"))

    # Stage 1: Document (always runs)
    print(banner("Stage 1 — Document"))
    language = args.language

    try:
        pipeline = Pipeline(kb_dir=args.kb, language=language)
        print(pipeline.document())
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print(f"\nKnowledge base error:\n  {e}")
        sys.exit(1)

    if args.type == "demo":
        run_demo(pipeline, language)
    elif args.type == "blog":
        if not args.topic:
            print("Error: --topic is required for blog posts.")
            raise SystemExit(1)
        run_blog(pipeline, args.topic, args.extra, language)
    elif args.type == "social":
        if not args.topic:
            print("Error: --topic is required for social media posts.")
            raise SystemExit(1)
        run_social(pipeline, args.topic, args.extra, language)
    elif args.type == "program":
        if not args.topic:
            print("Error: --topic is required for program descriptions.")
            raise SystemExit(1)
        run_program(pipeline, args.topic, args.extra, language)
    elif args.type == "newsletter":
        if not args.topic:
            print("Error: --topic is required for newsletters.")
            raise SystemExit(1)
        run_newsletter(pipeline, args.topic, language)

    print(banner("Done"))


if __name__ == "__main__":
    main()
