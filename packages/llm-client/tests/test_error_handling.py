"""Tests for error handling and exception wrapping."""

import pytest

from llm_client import (
    CaseSeed,
    LLMProviderError,
    ModelConfig,
    Provider,
    create_case_generator,
)


@pytest.fixture
def openai_config():
    """OpenAI configuration for testing."""
    return ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test-key",
        schema_path="/fake/schema.json",
    )


@pytest.fixture
def anthropic_config():
    """Anthropic configuration for testing."""
    return ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
        schema_path="/fake/schema.json",
    )


@pytest.fixture
def sample_seed():
    """Sample case seed."""
    return CaseSeed(
        diagnosis="test",
        difficulty="intermediate",
        dramatic_tone="clinical",
    )


def test_openai_missing_package_or_schema_error(openai_config):
    """Missing openai package or schema file raises LLMProviderError with helpful message."""
    # Try to create generator - if openai not installed or schema missing, should get error
    try:
        generator = create_case_generator(openai_config)
        # If we get here, check that it's actually an OpenAI generator
        assert generator.__class__.__name__ == "OpenAICaseGenerator"
    except LLMProviderError as e:
        # Should be one of: package not installed OR schema file not found
        error_msg = str(e).lower()
        assert "openai package not installed" in error_msg or "schema file not found" in error_msg


def test_anthropic_missing_package_or_schema_error(anthropic_config):
    """Missing anthropic package or schema file raises LLMProviderError with helpful message."""
    try:
        generator = create_case_generator(anthropic_config)
        assert generator.__class__.__name__ == "AnthropicCaseGenerator"
    except LLMProviderError as e:
        error_msg = str(e).lower()
        assert (
            "anthropic package not installed" in error_msg or "schema file not found" in error_msg
        )


def test_missing_api_key_for_openai_generator():
    """OpenAI generator with missing API key raises LLMClientError."""
    from llm_client import LLMClientError

    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key=None,  # Missing
        schema_path="/fake/schema.json",
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_case_generator(config)


def test_missing_schema_path_for_openai_generator():
    """OpenAI generator with missing schema_path raises LLMClientError."""
    from llm_client import LLMClientError

    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test",
        schema_path=None,  # Missing
    )

    with pytest.raises(LLMClientError, match="schema_path required"):
        create_case_generator(config)


def test_missing_api_key_for_anthropic_generator():
    """Anthropic generator with missing API key raises LLMClientError."""
    from llm_client import LLMClientError

    config = ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key=None,  # Missing
        schema_path="/fake/schema.json",
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_case_generator(config)


def test_missing_schema_path_for_anthropic_generator():
    """Anthropic generator with missing schema_path raises LLMClientError."""
    from llm_client import LLMClientError

    config = ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test",
        schema_path=None,  # Missing
    )

    with pytest.raises(LLMClientError, match="schema_path required"):
        create_case_generator(config)


def test_provider_error_is_subclass_of_client_error():
    """LLMProviderError is a subclass of LLMClientError."""
    from llm_client import LLMClientError

    assert issubclass(LLMProviderError, LLMClientError)


def test_response_error_is_subclass_of_client_error():
    """LLMResponseError is a subclass of LLMClientError."""
    from llm_client import LLMClientError, LLMResponseError

    assert issubclass(LLMResponseError, LLMClientError)
