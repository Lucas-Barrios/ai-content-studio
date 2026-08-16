"""
main.py

CLI entry point for the AI Content Studio.
Usage:
  python -m src.main --type blog_post --topic "Applied AI programs" --audience "the brand's target audience"

Responsibilities:
  - Parse command-line arguments
  - Load environment variables from .env
  - Optionally rebuild the knowledge base index
  - Invoke the content pipeline
  - Print or save the result
"""

import argparse
from dotenv import load_dotenv

from src.content_pipeline import run
from src.knowledge_base import refresh_index


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    pass


def main() -> None:
    """Load config, run the pipeline, and output the result."""
    load_dotenv()
    args = parse_args()

    if getattr(args, "refresh_kb", False):
        refresh_index("knowledge_base")

    content = run(
        content_type=args.type,
        topic=args.topic,
        audience=args.audience,
        output_path=getattr(args, "output", None),
    )

    print(content)


if __name__ == "__main__":
    main()
