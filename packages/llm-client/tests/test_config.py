"""Tests for configuration and factory functions."""

import pytest

from llm_client import (
    LLMClientError,
    MockActionInterpreter,
    MockCaseGenerator,
    MockNarrator,
    ModelConfig,
    Provider,
    create_action_interpreter,
    create_case_generator,
    create_narrator,
)


def test_provider_enum_values():
    """Test Provider enum has expected values."""
    assert Provider.OPENAI == "openai"
    assert Provider.ANTHROPIC == "anthropic"
    assert Provider.MOCK == "mock"


def test_model_config_minimal():
    """Test ModelConfig with minimal required fields."""
    config = ModelConfig(provider=Provider.MOCK, model="test-model")

    assert config.provider == Provider.MOCK
    assert config.model == "test-model"
    assert config.api_key is None
    assert config.temperature == 0.7
    assert config.max_tokens == 16384
    assert config.schema_path is None


def test_model_config_full():
    """Test ModelConfig with all fields."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test",
        temperature=0.5,
        max_tokens=8000,
        schema_path="/path/to/schema.json",
    )

    assert config.provider == Provider.OPENAI
    assert config.model == "gpt-4o"
    assert config.api_key == "sk-test"
    assert config.temperature == 0.5
    assert config.max_tokens == 8000
    assert config.schema_path == "/path/to/schema.json"


def test_model_config_immutable():
    """Test that ModelConfig is immutable."""
    config = ModelConfig(provider=Provider.MOCK, model="test")

    with pytest.raises(AttributeError):
        config.model = "modified"  # type: ignore


def test_create_case_generator_mock(mock_model_config):
    """Test creating mock case generator."""
    generator = create_case_generator(mock_model_config)

    assert isinstance(generator, MockCaseGenerator)


def test_create_case_generator_missing_api_key():
    """Test that non-mock generator requires api_key."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key=None,
        schema_path="/path/to/schema.json",
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_case_generator(config)


def test_create_case_generator_missing_schema_path():
    """Test that CaseGenerator requires schema_path."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test",
        schema_path=None,
    )

    with pytest.raises(LLMClientError, match="schema_path required"):
        create_case_generator(config)


def test_create_case_generator_openai_type(openai_model_config):
    """Test that OpenAI config creates OpenAI generator."""
    # We expect this to succeed in construction even without the SDK
    # (or fail with a clear import error if SDK not installed)
    try:
        generator = create_case_generator(openai_model_config)
        # Check it's the right type
        assert generator.__class__.__name__ == "OpenAICaseGenerator"
    except LLMClientError as e:
        # If openai not installed, expect helpful error
        assert "openai package not installed" in str(e)


def test_create_case_generator_anthropic_type(anthropic_model_config):
    """Test that Anthropic config creates Anthropic generator."""
    try:
        generator = create_case_generator(anthropic_model_config)
        assert generator.__class__.__name__ == "AnthropicCaseGenerator"
    except LLMClientError as e:
        # If anthropic not installed, expect helpful error
        assert "anthropic package not installed" in str(e)


def test_create_narrator_mock(mock_model_config):
    """Test creating mock narrator."""
    narrator = create_narrator(mock_model_config)

    assert isinstance(narrator, MockNarrator)


def test_create_narrator_missing_api_key():
    """Test that non-mock narrator requires api_key."""
    config = ModelConfig(provider=Provider.OPENAI, model="gpt-4o", api_key=None)

    with pytest.raises(LLMClientError, match="api_key required"):
        create_narrator(config)


def test_create_narrator_no_live_implementation():
    """Test that only mock narrator exists in Phase 1."""
    config = ModelConfig(provider=Provider.OPENAI, model="gpt-4o", api_key="sk-test")

    with pytest.raises(LLMClientError, match="No live Narrator implementation"):
        create_narrator(config)


def test_create_action_interpreter_mock(mock_model_config):
    """Test creating mock action interpreter."""
    interpreter = create_action_interpreter(mock_model_config)

    assert isinstance(interpreter, MockActionInterpreter)


def test_create_action_interpreter_missing_api_key():
    """Test that non-mock interpreter requires api_key."""
    config = ModelConfig(
        provider=Provider.ANTHROPIC, model="claude-sonnet-4-20250514", api_key=None
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_action_interpreter(config)


def test_create_action_interpreter_no_live_implementation():
    """Test that only mock interpreter exists in Phase 1."""
    config = ModelConfig(
        provider=Provider.ANTHROPIC, model="claude-sonnet-4-20250514", api_key="sk-ant-test"
    )

    with pytest.raises(LLMClientError, match="No live ActionInterpreter implementation"):
        create_action_interpreter(config)


def test_create_case_generator_unknown_provider():
    """Test that unknown provider raises error."""
    # Create a config with an invalid provider by manipulating the enum
    config = ModelConfig(
        provider="unknown_provider",  # type: ignore
        model="test",
        api_key="test",
        schema_path="/test",
    )

    with pytest.raises(LLMClientError, match="Unknown provider"):
        create_case_generator(config)
