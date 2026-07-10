"""Tests for AnthropicNarrator (P2-H08 plumbing).

The SDK client is stubbed after construction — these tests pin the plumbing
contract (dispatch, error taxonomy, text extraction), not provider behavior.
The live smoke test happens at H08 completion behind the live_llm marker.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest

anthropic = pytest.importorskip("anthropic")

from llm_client.anthropic_narrator import AnthropicNarrator  # noqa: E402
from llm_client.config import ModelConfig, Provider, create_narrator  # noqa: E402
from llm_client.exceptions import (  # noqa: E402
    LLMClientError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from llm_client.interfaces import ExplanationContext, NarrationContext, NarrationEvent  # noqa: E402

CONFIG = ModelConfig(
    provider=Provider.ANTHROPIC,
    model="claude-sonnet-4-6",
    api_key="test-key",
    timeout_seconds=5.0,
)

CONTEXT = NarrationContext(
    patient_name="Maria Santos",
    patient_age=28,
    patient_sex="female",
    setting="Emergency Department",
    current_vitals={"heart_rate": 92},
    elapsed_minutes=15,
)

EVENT = NarrationEvent(event_type="node_revealed", description="Eosinophils 8%.")


class _StubMessages:
    def __init__(self, result: Any = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def _narrator_with(messages: _StubMessages) -> AnthropicNarrator:
    narrator = AnthropicNarrator(CONFIG)
    narrator.client = SimpleNamespace(messages=messages)  # type: ignore[assignment]  # stubbing the SDK client for plumbing tests
    return narrator


def _text_response(*texts: str) -> Any:
    from anthropic.types import TextBlock

    return SimpleNamespace(content=[TextBlock(type="text", text=t) for t in texts])


def test_create_narrator_dispatches_anthropic():
    narrator = create_narrator(CONFIG)
    assert isinstance(narrator, AnthropicNarrator)


def test_create_narrator_still_rejects_openai():
    config = ModelConfig(provider=Provider.OPENAI, model="gpt", api_key="k")
    with pytest.raises(LLMClientError):
        create_narrator(config)


def test_missing_api_key_raises():
    with pytest.raises(ValueError):
        AnthropicNarrator(ModelConfig(provider=Provider.ANTHROPIC, model="m"))


def test_narrate_returns_stripped_text_and_passes_config():
    messages = _StubMessages(result=_text_response("  Maria's labs are back.  "))
    narrator = _narrator_with(messages)
    assert narrator.narrate(EVENT, CONTEXT) == "Maria's labs are back."
    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-4-6"
    assert "Eosinophils 8%" in call["messages"][0]["content"]
    assert len(call["system"]) > 0


def test_narrate_joins_multiple_text_blocks():
    messages = _StubMessages(result=_text_response("One.", " Two."))
    narrator = _narrator_with(messages)
    assert narrator.narrate(EVENT, CONTEXT) == "One. Two."


def test_empty_response_raises_response_error():
    messages = _StubMessages(result=SimpleNamespace(content=[]))
    narrator = _narrator_with(messages)
    with pytest.raises(LLMResponseError):
        narrator.narrate(EVENT, CONTEXT)


def test_timeout_maps_to_llm_timeout_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    messages = _StubMessages(error=anthropic.APITimeoutError(request=request))
    narrator = _narrator_with(messages)
    with pytest.raises(LLMTimeoutError):
        narrator.narrate(EVENT, CONTEXT)


def test_other_failures_map_to_provider_error():
    messages = _StubMessages(error=RuntimeError("connection reset"))
    narrator = _narrator_with(messages)
    with pytest.raises(LLMProviderError):
        narrator.narrate(EVENT, CONTEXT)


def test_explain_is_phase_5():
    narrator = _narrator_with(_StubMessages())
    with pytest.raises(NotImplementedError):
        narrator.explain(ExplanationContext(topic="neurocysticercosis", patient_context="x"))
