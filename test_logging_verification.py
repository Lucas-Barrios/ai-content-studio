"""Verify backend logging produces a useful audit trail.

Run:
  python test_logging_verification.py
"""

from __future__ import annotations

from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from api_server import app
from src.io_helpers import load_json_file
from src.logging_config import LOG_PATH, configure_logging
from src.llm_integration import OpenAIWrapper


class FailingCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        raise RuntimeError("logging verification API failure")


class FakeChat:
    def __init__(self):
        self.completions = FailingCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def reset_log_file() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def assert_logged(expected: list[str]) -> None:
    content = LOG_PATH.read_text(encoding="utf-8")
    missing = [entry for entry in expected if entry not in content]
    if missing:
        raise AssertionError(f"Missing log entries {missing}. Log content:\n{content}")


def main() -> None:
    configure_logging()
    reset_log_file()

    with tempfile.TemporaryDirectory() as temp_dir:
        valid_json = Path(temp_dir) / "valid.json"
        valid_json.write_text('{"name": "Test"}', encoding="utf-8")
        load_json_file(valid_json)

    client = TestClient(app)
    client.get("/health")
    client.post("/generate", json={"contentType": "bad", "topic": "AI"})
    client.post("/compare", json={"content": "Meridian Core Portfolio", "topic": "Audit"})
    client.post(
        "/feedback",
        json={
            "generationId": "log-test",
            "status": "approved",
            "comment": "Looks good",
            "request": {},
            "response": {},
        },
    )

    wrapper = OpenAIWrapper(
        api_key="sk-test",
        model="test-model",
        max_retries=2,
        backoff_seconds=0,
        client=FakeClient(),
    )
    wrapper.generate_description("Trigger retry logging")

    assert_logged(
        [
            "Loading JSON file",
            "Loaded JSON file successfully",
            "Received /generate request",
            "Generate request validation failed",
            "Received /compare request",
            "Comparison completed",
            "Feedback saved",
            "Calling OpenAI chat completion",
            "Retrying OpenAI request",
            "OpenAI request failed",
        ]
    )
    print(f"logging verification passed: {LOG_PATH}")


if __name__ == "__main__":
    main()
