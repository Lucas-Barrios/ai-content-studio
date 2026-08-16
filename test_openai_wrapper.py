"""Independent tests for the reusable OpenAI wrapper.

Run:
  python test_openai_wrapper.py
"""

from __future__ import annotations

from dataclasses import dataclass

from src.logging_config import configure_logging
from src.llm_integration import ContentGenerator, ContentGeneratorError, OpenAIWrapper


@dataclass
class FakeMessage:
    content: str


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeResponse:
    choices: list[FakeChoice]


class FakeCompletions:
    def __init__(self, failures_before_success: int = 0, content: str = "Generated content"):
        self.failures_before_success = failures_before_success
        self.content = content
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError("temporary API failure")
        return FakeResponse(choices=[FakeChoice(message=FakeMessage(content=self.content))])


class FakeChat:
    def __init__(self, completions: FakeCompletions):
        self.completions = completions


class FakeClient:
    def __init__(self, completions: FakeCompletions):
        self.chat = FakeChat(completions)


def make_wrapper(completions: FakeCompletions, max_retries: int = 3) -> OpenAIWrapper:
    return OpenAIWrapper(
        api_key="sk-test",
        model="test-model",
        max_retries=max_retries,
        backoff_seconds=0,
        client=FakeClient(completions),
    )


def test_success_response() -> None:
    completions = FakeCompletions(content="generated content")
    wrapper = make_wrapper(completions)
    result = wrapper.generate_description("Write content")

    assert result["status"] == "success"
    assert result["content"] == "generated content"
    assert result["attempts"] == 1
    assert result["model"] == "test-model"


def test_retry_success() -> None:
    completions = FakeCompletions(failures_before_success=1, content="Recovered content")
    wrapper = make_wrapper(completions, max_retries=3)
    result = wrapper.generate_description("Write content")

    assert result["status"] == "success"
    assert result["content"] == "Recovered content"
    assert result["attempts"] == 2
    assert completions.calls == 2


def test_standardized_error_response() -> None:
    completions = FakeCompletions(failures_before_success=3)
    wrapper = make_wrapper(completions, max_retries=2)
    result = wrapper.generate_description("Write content")

    assert result["status"] == "error"
    assert result["error_type"] == "RuntimeError"
    assert "temporary API failure" in result["error"]
    assert result["attempts"] == 2


def test_empty_prompt_error_response() -> None:
    wrapper = make_wrapper(FakeCompletions())
    result = wrapper.generate_description("   ")

    assert result["status"] == "error"
    assert result["error_type"] == "ContentGeneratorError"
    assert "Prompt is empty" in result["error"]
    assert result["attempts"] == 0


def test_prompt_size_guardrail() -> None:
    wrapper = make_wrapper(FakeCompletions())
    wrapper.max_prompt_chars = 5
    result = wrapper.generate_description("This prompt is too long")

    assert result["status"] == "error"
    assert result["error_type"] == "ContentGeneratorError"
    assert "Prompt is too large" in result["error"]
    assert result["attempts"] == 0


def test_content_generator_uses_wrapper() -> None:
    wrapper = make_wrapper(FakeCompletions(content="Compatibility content"))
    generator = ContentGenerator(wrapper=wrapper)
    assert generator.generate_content("Write content") == "Compatibility content"


def test_content_generator_raises_standard_error() -> None:
    wrapper = make_wrapper(FakeCompletions(failures_before_success=3), max_retries=1)
    generator = ContentGenerator(wrapper=wrapper)

    try:
        generator.generate_content("Write content")
    except ContentGeneratorError as error:
        assert "temporary API failure" in str(error)
    else:
        raise AssertionError("ContentGenerator should raise ContentGeneratorError on wrapper errors")


def main() -> None:
    configure_logging()
    test_success_response()
    test_retry_success()
    test_standardized_error_response()
    test_empty_prompt_error_response()
    test_prompt_size_guardrail()
    test_content_generator_uses_wrapper()
    test_content_generator_raises_standard_error()
    print("openai wrapper tests passed")


if __name__ == "__main__":
    main()
