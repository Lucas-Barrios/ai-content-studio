"""Independent tests for backend helper functions.

Run:
  python test_helpers.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from src.api_helpers import (
    build_chat_prompt,
    feedback_record_to_response,
    normalize_content_type,
    safe_download_filename,
    source_to_dict,
    uploaded_file_to_dict,
    validate_choice,
)
from src.content_pipeline import create_content_prompt, select_prompt_builder
from src.document_processor import (
    build_markdown_document,
    is_empty_document,
    list_markdown_files,
    read_markdown_document,
)
from src.generation_service import (
    build_source_files,
    combine_knowledge_base_sections,
    format_knowledge_base_document,
    format_knowledge_base_section,
    save_uploads,
    safe_upload_name,
    source_type_from_path,
)
from src.io_helpers import append_jsonl_record, load_json_file, read_text_without_metadata


@dataclass(frozen=True)
class Source:
    filename: str
    words: int
    source: str


@dataclass(frozen=True)
class UploadedFile:
    id: str
    name: str
    size: int
    contentType: str
    url: str | None = None


@dataclass(frozen=True)
class Feedback:
    id: str
    generation_id: str
    status: str
    created_at: str


@dataclass(frozen=True)
class Message:
    role: str
    content: str


def test_json_helpers() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = Path(temp_dir) / "config.json"
        json_path.write_text('{"name": "Test Product", "price": 99.99}', encoding="utf-8")
        assert load_json_file(json_path) == {"name": "Test Product", "price": 99.99}

        text_path = Path(temp_dir) / "baseline.md"
        text_path.write_text("<!-- metadata -->\nActual content", encoding="utf-8")
        assert read_text_without_metadata(text_path) == "Actual content"

        jsonl_path = Path(temp_dir) / "records.jsonl"
        append_jsonl_record(jsonl_path, {"status": "approved"})
        assert jsonl_path.read_text(encoding="utf-8").strip() == '{"status": "approved"}'


def test_validation_helpers() -> None:
    assert normalize_content_type("blog_post") == "blog"
    assert normalize_content_type(None) == "blog"
    assert validate_choice("blog", {"blog", "social"}, "contentType") == "blog"

    try:
        validate_choice("bad", {"blog", "social"}, "contentType")
    except ValueError as error:
        assert "Unsupported contentType" in str(error)
    else:
        raise AssertionError("validate_choice should reject unsupported values")


def test_formatting_helpers() -> None:
    assert source_to_dict(Source("brand.md", 120, "primary")) == {
        "filename": "brand.md",
        "words": 120,
        "source": "primary",
    }
    assert uploaded_file_to_dict(UploadedFile("1", "brief.md", 10, "text/markdown")) == {
        "id": "1",
        "name": "brief.md",
        "size": 10,
        "contentType": "text/markdown",
        "url": None,
    }
    assert feedback_record_to_response(Feedback("fb1", "gen1", "approved", "2026-05-05T00:00:00Z")) == {
        "id": "fb1",
        "generationId": "gen1",
        "status": "approved",
        "createdAt": "2026-05-05T00:00:00Z",
    }
    assert safe_download_filename("Brand Content: AI / Berlin") == "brand-content-ai-berlin"


def test_prompt_helper() -> None:
    prompt = build_chat_prompt([Message("user", "Make this shorter")])
    assert "brand marketing content assistant" in prompt
    assert "user: Make this shorter" in prompt

    content_prompt = create_content_prompt("blog", "Context", "AI Ethics", "english")
    assert "AI Ethics" in content_prompt
    assert callable(select_prompt_builder("newsletter"))


def test_document_helpers() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        doc_path = Path(temp_dir) / "source.md"
        doc_path.write_text("# Heading\nBody", encoding="utf-8")

        paths = list_markdown_files(temp_dir)
        assert paths == [doc_path]
        assert read_markdown_document(doc_path) == {
            "filename": "source.md",
            "path": str(doc_path),
            "content": "# Heading\nBody",
        }
        assert build_markdown_document(doc_path, "content")["filename"] == "source.md"
        assert is_empty_document("   ")


def test_generation_service_helpers() -> None:
    doc = {"filename": "brand.md", "content": "brand content"}
    assert format_knowledge_base_document(doc).startswith("### brand.md")
    assert format_knowledge_base_section("PRIMARY", [doc]).startswith("## PRIMARY")
    assert combine_knowledge_base_sections(["one", "two"]) == "one\n\n===\n\ntwo"
    assert source_type_from_path("knowledge_base/meridian_wealth") == "primary"
    assert source_type_from_path("knowledge_base/secondary") == "secondary"
    assert build_source_files([doc], "primary")[0].filename == "brand.md"
    assert safe_upload_name("../brief.md") == "brief.md"

    uploaded = save_uploads([("brief.md", b"hello", "text/markdown")], "/private/tmp/helper-upload-test")
    assert uploaded[0].name == "brief.md"
    assert uploaded[0].size == 5


def main() -> None:
    test_json_helpers()
    test_validation_helpers()
    test_formatting_helpers()
    test_prompt_helper()
    test_document_helpers()
    test_generation_service_helpers()
    print("helper tests passed")


if __name__ == "__main__":
    main()
