"""
Shared service layer for HTTP and UI content generation.

This keeps request parsing, knowledge-base loading, and pipeline execution out of
framework-specific files such as FastAPI routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from src.brand_intelligence import assemble_brand_block, retrieve_brand_context
from src.content_pipeline import Pipeline
from src.document_processor import MarkdownProcessor

load_dotenv()
logger = logging.getLogger(__name__)

ContentType = Literal["blog", "social", "program", "newsletter"]
KnowledgeBaseSource = Literal["hybrid", "primary", "secondary"]
Language = Literal["english", "german"]
Length = Literal["Short", "Medium", "Long"]

LENGTH_HINTS: dict[str, str] = {
    "Short": "~300 words",
    "Medium": "~650 words",
    "Long": "~1,000 words",
}

KB_DIRS: dict[str, list[tuple[str, str]]] = {
    "primary": [("PRIMARY SOURCES", "knowledge_base/meridian_wealth/")],
    "secondary": [("SECONDARY SOURCES", "knowledge_base/secondary/")],
    "hybrid": [
        ("PRIMARY SOURCES", "knowledge_base/meridian_wealth/"),
        ("SECONDARY SOURCES", "knowledge_base/secondary/"),
    ],
}


@dataclass(frozen=True)
class SourceFile:
    filename: str
    words: int
    source: Literal["primary", "secondary"]


@dataclass(frozen=True)
class UploadedFileRef:
    id: str
    name: str
    size: int
    contentType: str
    url: str | None = None


@dataclass(frozen=True)
class GenerateContentRequest:
    contentType: ContentType
    topic: str
    audience: str = "Target Audience"
    language: Language = "english"
    tone: str = "Professional"
    length: Length = "Medium"
    knowledgeBase: KnowledgeBaseSource = "hybrid"
    files: list[UploadedFileRef] = field(default_factory=list)
    feedback: str = ""
    previousContent: str = ""
    brand_profile_id: str | None = None


@dataclass(frozen=True)
class GenerateContentResult:
    content: str
    sources: list[SourceFile]
    brief: str


def load_knowledge_base(source: KnowledgeBaseSource) -> tuple[str, list[SourceFile]]:
    """Load one or both Markdown knowledge-base folders into prompt context."""
    logger.info("Loading knowledge base source=%s", source)
    sections = []
    sources = []

    for label, kb_dir in KB_DIRS[source]:
        docs = load_knowledge_base_documents(kb_dir)
        sections.append(format_knowledge_base_section(label, docs))
        sources.extend(build_source_files(docs, source_type_from_path(kb_dir)))

    context = combine_knowledge_base_sections(sections)
    logger.info("Loaded knowledge base source=%s sections=%s sources=%s chars=%s", source, len(sections), len(sources), len(context))
    return context, sources


def load_knowledge_base_documents(kb_dir: str) -> list[dict]:
    """Load Markdown documents from one knowledge-base directory."""
    logger.info("Loading knowledge base documents from %s", kb_dir)
    docs = MarkdownProcessor(kb_dir).process_all()
    logger.info("Loaded knowledge base documents from %s count=%s", kb_dir, len(docs))
    return docs


def format_knowledge_base_document(doc: dict) -> str:
    """Format one knowledge-base document for prompt context."""
    return f"### {doc['filename']}\n{doc['content']}"


def format_knowledge_base_section(label: str, docs: list[dict]) -> str:
    """Format one labelled knowledge-base section for prompt context."""
    block = "\n\n---\n\n".join(format_knowledge_base_document(doc) for doc in docs)
    return f"## {label}\n\n{block}"


def combine_knowledge_base_sections(sections: list[str]) -> str:
    """Combine formatted knowledge-base sections."""
    return "\n\n===\n\n".join(sections)


def source_type_from_path(kb_dir: str) -> Literal["primary", "secondary"]:
    """
    Infer source type from a knowledge-base path.

    Primary sources live in a per-tenant folder (e.g. knowledge_base/meridian_wealth/),
    so anything that is not the shared secondary folder is treated as primary.
    """
    return "secondary" if "secondary" in kb_dir else "primary"


def source_file_from_document(doc: dict, source_type: Literal["primary", "secondary"]) -> SourceFile:
    """Build source metadata for one knowledge-base document."""
    return SourceFile(
        filename=doc["filename"],
        words=len(doc["content"].split()),
        source=source_type,
    )


def build_source_files(docs: list[dict], source_type: Literal["primary", "secondary"]) -> list[SourceFile]:
    """Build source metadata for loaded knowledge-base documents."""
    return [source_file_from_document(doc, source_type) for doc in docs]


def build_style_preamble(request: GenerateContentRequest) -> str:
    """Convert UI controls into explicit prompt instructions."""
    uploaded_files = ", ".join(file.name for file in request.files) or "None"
    feedback_block = ""
    if request.feedback.strip() and request.previousContent.strip():
        feedback_block = (
            "\nREVISION CONTEXT:\n"
            "Use the previous draft and reviewer feedback to produce a better version.\n"
            f"Reviewer feedback: {request.feedback.strip()}\n\n"
            "Previous draft:\n"
            f"{request.previousContent.strip()}\n\n"
        )

    return (
        "GENERATION SETTINGS - follow these precisely:\n"
        f"  Tone             : {request.tone}\n"
        f"  Target length    : {LENGTH_HINTS.get(request.length, request.length)}\n"
        f"  Audience         : {request.audience}\n"
        f"  Knowledge base   : {request.knowledgeBase}\n"
        f"  Uploaded files   : {uploaded_files}\n\n"
        f"{feedback_block}"
    )


def _build_brand_prefix(request: GenerateContentRequest) -> str:
    """Retrieve and format brand context when a profile ID is provided."""
    if not request.brand_profile_id:
        return ""
    try:
        ctx = retrieve_brand_context(topic=request.topic, profile_id=request.brand_profile_id)
        if ctx is None:
            logger.warning("Brand profile not found id=%s — generating without brand context", request.brand_profile_id)
            return ""
        block = assemble_brand_block(ctx)
        logger.info("Brand context injected profile_id=%s chars=%s", request.brand_profile_id, len(block))
        return block
    except Exception as exc:
        logger.warning("Brand context retrieval failed (non-fatal): %s", exc)
        return ""


def generate_content(request: GenerateContentRequest) -> GenerateContentResult:
    """Run the content pipeline for a typed frontend request."""
    logger.info("Starting content generation topic='%s' type=%s kb=%s brand_profile=%s",
                request.topic, request.contentType, request.knowledgeBase, request.brand_profile_id)
    topic = request.topic.strip()
    if not topic:
        logger.error("Content generation validation failed: topic is required")
        raise ValueError("Topic is required.")

    kb_context, sources = load_knowledge_base(request.knowledgeBase)
    brand_prefix = _build_brand_prefix(request)

    pipeline = Pipeline(language=request.language)
    pipeline.kb_context = brand_prefix + build_style_preamble(request) + kb_context
    pipeline.monitor(
        topic=topic,
        content_type=request.contentType,
        audience=request.audience,
        extra=topic,
    )
    brief = pipeline.brief()
    logger.info("Generated content brief topic='%s' chars=%s", topic, len(brief))
    content = pipeline.publish()
    logger.info("Completed content generation topic='%s' content_chars=%s sources=%s", topic, len(content), len(sources))

    return GenerateContentResult(content=content, sources=sources, brief=brief)


def save_uploads(files: list[tuple[str, bytes, str]], upload_dir: str = "uploads") -> list[UploadedFileRef]:
    """Persist uploaded files for demo/session traceability and return frontend metadata."""
    logger.info("Saving uploaded files count=%s upload_dir=%s", len(files), upload_dir)
    output_dir = Path(upload_dir)
    output_dir.mkdir(exist_ok=True)
    uploaded = [save_uploaded_file(output_dir, file, index) for index, file in enumerate(files)]
    logger.info("Saved uploaded files count=%s upload_dir=%s", len(uploaded), upload_dir)
    return uploaded


def safe_upload_name(filename: str) -> str:
    """Return a safe upload filename without path components."""
    return Path(filename).name or "upload"


def write_uploaded_file(output_dir: Path, filename: str, content: bytes) -> Path:
    """Write uploaded file bytes and return the saved path."""
    target = output_dir / safe_upload_name(filename)
    logger.info("Writing uploaded file target=%s bytes=%s", target, len(content))
    target.write_bytes(content)
    logger.info("Wrote uploaded file target=%s", target)
    return target


def build_uploaded_file_ref(target: Path, content: bytes, content_type: str, index: int) -> UploadedFileRef:
    """Build uploaded-file metadata from a saved file."""
    return UploadedFileRef(
        id=f"{target.stat().st_mtime_ns}-{index}",
        name=target.name,
        size=len(content),
        contentType=content_type or "application/octet-stream",
        url=None,
    )


def save_uploaded_file(output_dir: Path, file: tuple[str, bytes, str], index: int) -> UploadedFileRef:
    """Save one uploaded file and return its metadata."""
    filename, content, content_type = file
    target = write_uploaded_file(output_dir, filename, content)
    return build_uploaded_file_ref(target, content, content_type, index)
