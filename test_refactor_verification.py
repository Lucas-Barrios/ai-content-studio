"""Verification scenarios for the refactored backend.

Run:
  python test_refactor_verification.py
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from fastapi.testclient import TestClient

import api_server
from api_server import app
from src.generation_service import GenerateContentResult, SourceFile
from src.io_helpers import load_json_file
from src.llm_integration import ContentGeneratorError


def assert_contains(text: str, expected: list[str]) -> None:
    missing = [item for item in expected if item not in text]
    if missing:
        raise AssertionError(f"Expected {missing} in: {text}")


def test_valid_json_load() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "valid.json"
        path.write_text('{"topic": "Evidence-based investing", "price": 99.99}', encoding="utf-8")
        result = load_json_file(path)
        assert result == {"topic": "Evidence-based investing", "price": 99.99}


def test_missing_json_error() -> None:
    try:
        load_json_file("/tmp/does-not-exist/refactor-missing.json")
    except FileNotFoundError as error:
        assert_contains(str(error), ["refactor-missing.json", "Suggestion", "file exists"])
    else:
        raise AssertionError("Missing JSON file should raise FileNotFoundError")


def test_invalid_json_error() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "invalid.json"
        path.write_text('{"topic": "AI Ethics",\n', encoding="utf-8")
        try:
            load_json_file(path)
        except ValueError as error:
            assert_contains(str(error), ["Invalid JSON", "line", "column", "Suggestion"])
        else:
            raise AssertionError("Invalid JSON should raise ValueError")


def test_non_object_json_error() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "invalid_data.json"
        path.write_text('["not", "an", "object"]', encoding="utf-8")
        try:
            load_json_file(path)
        except ValueError as error:
            assert_contains(str(error), ["Expected JSON object", "Suggestion"])
        else:
            raise AssertionError("Non-object JSON should raise ValueError")


def test_valid_generate_endpoint_same_response_shape() -> None:
    client = TestClient(app)
    original_generate_content = api_server.generate_content

    def fake_generate_content(_request: Any) -> GenerateContentResult:
        return GenerateContentResult(
            content="Generated content",
            sources=[SourceFile(filename="brand_guidelines.md", words=100, source="primary")],
            brief="Brief content",
        )

    api_server.generate_content = fake_generate_content
    try:
        response = client.post(
            "/generate",
            json={
                "contentType": "blog",
                "topic": "Evidence-based investing",
                "audience": "Target Audience",
                "language": "english",
                "tone": "Professional",
                "length": "Medium",
                "knowledgeBase": "primary",
            },
        )
    finally:
        api_server.generate_content = original_generate_content

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "content": "Generated content",
        "sources": [{"filename": "brand_guidelines.md", "words": 100, "source": "primary"}],
        "brief": "Brief content",
    }


def test_invalid_request_data_error() -> None:
    client = TestClient(app)
    response = client.post("/generate", json={"contentType": "bad", "topic": "AI"})
    assert response.status_code == 400
    assert_contains(response.text, ["Unsupported contentType", "Allowed values"])


def test_missing_required_field_error() -> None:
    client = TestClient(app)
    response = client.post("/generate", json={"contentType": "blog"})
    assert response.status_code == 422
    assert_contains(response.text, ["topic", "Field required"])


def test_api_error_details() -> None:
    client = TestClient(app)
    original_generate_content = api_server.generate_content

    def failing_generate_content(_request: Any) -> GenerateContentResult:
        raise ContentGeneratorError("OpenAI rejected the request: test failure")

    api_server.generate_content = failing_generate_content
    try:
        response = client.post(
            "/generate",
            json={
                "contentType": "blog",
                "topic": "Evidence-based investing",
                "language": "english",
                "knowledgeBase": "primary",
                "length": "Medium",
            },
        )
    finally:
        api_server.generate_content = original_generate_content

    assert response.status_code == 502
    assert_contains(response.text, ["OpenAI rejected the request", "test failure"])


def run_test_case(name: str, test_fn, expectation: str) -> None:
    test_fn()
    print(f"PASS: {name} - {expectation}")


def main() -> None:
    test_cases = [
        ("valid.json", test_valid_json_load, "Should work"),
        ("missing.json", test_missing_json_error, "Should show file path and suggestion"),
        ("invalid.json", test_invalid_json_error, "Should show JSON line/column"),
        ("invalid_data.json", test_non_object_json_error, "Should show validation error"),
        ("valid /generate", test_valid_generate_endpoint_same_response_shape, "Should preserve API response shape"),
        ("invalid request data", test_invalid_request_data_error, "Should show invalid field and allowed values"),
        ("missing required field", test_missing_required_field_error, "Should show which field is invalid"),
        ("API error", test_api_error_details, "Should show API error details"),
    ]

    for name, test_fn, expectation in test_cases:
        run_test_case(name, test_fn, expectation)

    print("\nVerification complete: refactored code preserves behavior and improves error clarity.")


if __name__ == "__main__":
    main()
