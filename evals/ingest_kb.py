"""
evals/ingest_kb.py

One-off, idempotent ingester that embeds each demo tenant's knowledge-base folder
into Supabase, so the eval harness's "system" arm has grounded context to retrieve.

There is no folder-level ingester in the codebase (rag_ingestion works one document
at a time), so this walks the two tenant folders and calls RagIngestionService.ingest
per file with the correct tenant IDs. Ingestion is idempotent: rag_ingestion dedups
on SHA-256 of cleaned text scoped to (client_id, project_id), so re-running is safe.

The shared knowledge_base/secondary/eu_ai_act_guidelines.md is intentionally NOT
ingested — it is policy/market context with no tenant owner, and ingesting it into a
tenant would pollute that tenant's retrieval and the eval.

Env required (loaded from repo-root .env): OPENAI_API_KEY, SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY.

Usage (from repo root, with the project venv active):
    python -m evals.ingest_kb            # ingest both tenants
    python -m evals.ingest_kb --tenant meridian_wealth
    python -m evals.ingest_kb --dry-run  # list what would be ingested, no API calls
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # repo-root .env

ORG_ID = "00000000-0000-0000-0000-000000000001"

# tenant -> config. Each file carries its own source_kind so retrieval metadata is honest.
TENANTS: dict[str, dict] = {
    "meridian_wealth": {
        "client_id": "00000000-0000-0000-0000-000000000002",
        "project_id": "00000000-0000-0000-0000-000000000003",
        "folder": "knowledge_base/meridian_wealth",
        "files": [
            ("brand_guidelines.md", "brand"),
            ("products_and_disclosures.md", "product"),
        ],
    },
    "lumen_aesthetics": {
        "client_id": "00000000-0000-0000-0000-000000000004",
        "project_id": "00000000-0000-0000-0000-000000000005",
        "folder": "knowledge_base/lumen_aesthetics",
        "files": [
            ("brand_guidelines.md", "brand"),
            ("treatments_and_aftercare.md", "product"),
        ],
    },
}


def _title_from_filename(name: str) -> str:
    return name.rsplit(".", 1)[0].replace("_", " ").title()


def ingest_tenant(name: str, cfg: dict, dry_run: bool) -> tuple[int, int]:
    """Ingest one tenant's files. Returns (documents, chunks)."""
    # Import (and construct) the Supabase/OpenAI-backed service only for a real
    # run, so --dry-run works with nothing but the standard library + dotenv.
    if not dry_run:
        from src.rag_ingestion import KnowledgeSourceInput, RagIngestionService
        service = RagIngestionService()

    docs = chunks = 0

    for filename, source_kind in cfg["files"]:
        path = Path(cfg["folder"]) / filename
        if not path.exists():
            print(f"  ! MISSING {path} — skipped")
            continue

        text = path.read_text(encoding="utf-8")
        title = _title_from_filename(filename)

        if dry_run:
            print(f"  · would ingest {path}  (title='{title}', source_kind={source_kind}, {len(text)} chars)")
            continue

        source = KnowledgeSourceInput(
            organization_id=ORG_ID,
            client_id=cfg["client_id"],
            project_id=cfg["project_id"],
            title=title,
            source_kind=source_kind,
            language="english",
            tags=[name, source_kind],
            text=text,
            metadata={"origin": "evals/ingest_kb.py", "path": str(path)},
        )
        result = service.ingest(source)
        flag = "DUPLICATE (skipped)" if result.duplicate else result.status.upper()
        print(f"  ✓ {title:<28} chunks={result.chunk_count:<3} embeddings={result.embedding_count:<3} [{flag}]")
        docs += 1
        chunks += result.chunk_count

    return docs, chunks


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest demo tenant knowledge bases into Supabase.")
    ap.add_argument("--tenant", choices=list(TENANTS), help="Ingest only one tenant (default: both).")
    ap.add_argument("--dry-run", action="store_true", help="List what would be ingested; no API calls.")
    args = ap.parse_args()

    targets = [args.tenant] if args.tenant else list(TENANTS)
    total_docs = total_chunks = 0

    for name in targets:
        print(f"\n=== {name} ===")
        d, c = ingest_tenant(name, TENANTS[name], args.dry_run)
        total_docs += d
        total_chunks += c

    if not args.dry_run:
        print(f"\nDone. Ingested {total_docs} documents, {total_chunks} chunks across {len(targets)} tenant(s).")
        print("Note: re-running is idempotent (dedup on content hash per client/project).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
