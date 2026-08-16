"""
knowledge_base.py

Manages the vector store and retrieval layer for brand content.
Responsibilities:
  - Index processed document chunks (primary and secondary sources)
  - Store and load embeddings from disk
  - Retrieve the most relevant chunks for a given query
  - Distinguish between primary (brand/program) and secondary (trends/competitor) sources
"""


def build_index(chunks: list[dict], source_type: str = "primary") -> None:
    """Embed chunks and add them to the vector index."""
    pass


def load_index(index_path: str) -> object:
    """Load a persisted vector index from disk."""
    pass


def save_index(index: object, index_path: str) -> None:
    """Persist the vector index to disk."""
    pass


def retrieve(query: str, top_k: int = 5, source_type: str | None = None) -> list[dict]:
    """Return the top-k most relevant chunks for a query, optionally filtered by source type."""
    pass


def refresh_index(knowledge_base_dir: str) -> None:
    """Re-process all documents in the knowledge base directory and rebuild the index."""
    pass
