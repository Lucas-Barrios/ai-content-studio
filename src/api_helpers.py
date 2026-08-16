"""Pure helpers for API validation, prompt construction, and response formatting."""

from __future__ import annotations

from typing import Any, Iterable, Protocol, TypeVar

T = TypeVar("T", bound=str)


class SourceLike(Protocol):
    filename: str
    words: int
    source: str


class UploadedFileLike(Protocol):
    id: str
    name: str
    size: int
    contentType: str
    url: str | None


class FeedbackRecordLike(Protocol):
    id: str
    generation_id: str
    status: str
    created_at: str


class ChatMessageLike(Protocol):
    role: str
    content: str


def validate_choice(value: str, allowed_values: Iterable[T], field_name: str) -> T:
    """Validate a string against an allowed value set and return the typed value."""
    allowed = tuple(allowed_values)
    if value not in allowed:
        allowed_display = ", ".join(allowed)
        raise ValueError(f"Unsupported {field_name}: {value}. Allowed values: {allowed_display}")
    return value  # type: ignore[return-value]


def normalize_content_type(content_type: str | None) -> str:
    """Normalize frontend/legacy content type names to backend content type IDs."""
    normalized = content_type or "blog"
    if normalized == "blog_post":
        return "blog"
    if normalized == "social_post":
        return "social"
    if normalized == "ad_copy":
        return "ad"
    return normalized


def source_to_dict(source: SourceLike) -> dict[str, Any]:
    """Serialize a source object for API responses."""
    return {
        "filename": source.filename,
        "words": source.words,
        "source": source.source,
    }


def sources_to_dicts(sources: Iterable[SourceLike]) -> list[dict[str, Any]]:
    """Serialize source objects for API responses."""
    return [source_to_dict(source) for source in sources]


def uploaded_file_to_dict(file: UploadedFileLike) -> dict[str, Any]:
    """Serialize an uploaded file reference for API responses."""
    return {
        "id": file.id,
        "name": file.name,
        "size": file.size,
        "contentType": file.contentType,
        "url": file.url,
    }


def uploaded_files_to_dicts(files: Iterable[UploadedFileLike]) -> list[dict[str, Any]]:
    """Serialize uploaded file references for API responses."""
    return [uploaded_file_to_dict(file) for file in files]


def feedback_record_to_response(record: FeedbackRecordLike) -> dict[str, Any]:
    """Serialize a saved feedback record for the frontend."""
    return {
        "id": record.id,
        "generationId": record.generation_id,
        "status": record.status,
        "createdAt": record.created_at,
    }


def safe_download_filename(topic: str, fallback: str = "brand-content") -> str:
    """Create a conservative download filename stem from a topic."""
    source = topic.strip().lower() or fallback
    filename = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in source)
    return "-".join(part for part in filename.split("-") if part) or fallback


def build_chat_prompt(messages: list[ChatMessageLike], max_messages: int = 8) -> str:
    """Create the chat assistant prompt from recent messages."""
    if not messages:
        raise ValueError("At least one chat message is required.")

    transcript = "\n".join(f"{message.role}: {message.content}" for message in messages[-max_messages:])
    return (
        "You are a brand marketing content assistant. Help revise, shorten, repurpose, "
        "or improve content while staying professional and specific.\n\n"
        f"Conversation:\n{transcript}\n\nAssistant:"
    )
