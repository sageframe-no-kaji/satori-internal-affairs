"""Additional factory tests for comprehensive coverage."""

import pytest

from llm_client import (
    LLMClientError,
    MockActionInterpreter,
    MockNarrator,
    ModelConfig,
    Provider,
    create_action_interpreter,
    create_narrator,
)


def test_create_narrator_mock_returns_mock_narrator():
    """Factory with MOCK provider returns MockNarrator."""
    config = ModelConfig(provider=Provider.MOCK, model="mock-model")
    narrator = create_narrator(config)

    assert isinstance(narrator, MockNarrator)
    assert narrator.config == config


def test_create_narrator_openai_not_implemented():
    """Factory with OPENAI provider raises — no real Narrator provider in Phase 1."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test-key",
    )

    with pytest.raises(LLMClientError, match="No live Narrator implementation.*openai"):
        create_narrator(config)


def test_create_narrator_anthropic_dispatches_live_narrator():
    """Factory with ANTHROPIC provider builds the live narrator (P2-H08;
    superseded the Phase-1 'not implemented' pin)."""
    pytest.importorskip("anthropic")
    from llm_client.anthropic_narrator import AnthropicNarrator

    config = ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )

    assert isinstance(create_narrator(config), AnthropicNarrator)


def test_create_action_interpreter_mock_returns_mock():
    """Factory with MOCK provider returns MockActionInterpreter."""
    config = ModelConfig(provider=Provider.MOCK, model="mock-model")
    interpreter = create_action_interpreter(config)

    assert isinstance(interpreter, MockActionInterpreter)
    assert interpreter.config == config


def test_create_action_interpreter_openai_not_implemented():
    """Factory with OPENAI provider raises — no real ActionInterpreter in Phase 1."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test-key",
    )

    with pytest.raises(LLMClientError, match="No live ActionInterpreter implementation.*openai"):
        create_action_interpreter(config)


def test_create_action_interpreter_anthropic_not_implemented():
    """Factory with ANTHROPIC provider raises — no real ActionInterpreter in Phase 1."""
    config = ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )

    with pytest.raises(LLMClientError, match="No live ActionInterpreter implementation.*anthropic"):
        create_action_interpreter(config)


def test_create_narrator_requires_api_key_for_non_mock():
    """Non-mock narrator requires api_key."""
    config = ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key=None,  # Missing API key
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_narrator(config)


def test_create_action_interpreter_requires_api_key_for_non_mock():
    """Non-mock action interpreter requires api_key."""
    config = ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key=None,  # Missing API key
    )

    with pytest.raises(LLMClientError, match="api_key required"):
        create_action_interpreter(config)


def test_create_narrator_mock_works_without_api_key():
    """Mock narrator doesn't require api_key."""
    config = ModelConfig(
        provider=Provider.MOCK,
        model="mock-model",
        api_key=None,  # No API key needed for mock
    )

    narrator = create_narrator(config)
    assert isinstance(narrator, MockNarrator)


def test_create_action_interpreter_mock_works_without_api_key():
    """Mock action interpreter doesn't require api_key."""
    config = ModelConfig(
        provider=Provider.MOCK,
        model="mock-model",
        api_key=None,  # No API key needed for mock
    )

    interpreter = create_action_interpreter(config)
    assert isinstance(interpreter, MockActionInterpreter)
