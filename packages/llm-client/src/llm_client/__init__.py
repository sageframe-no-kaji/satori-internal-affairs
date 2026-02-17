"""LLM abstraction layer for medical case generation and narrative."""

from llm_client.config import (
    ModelConfig,
    Provider,
    create_action_interpreter,
    create_case_generator,
    create_narrator,
)
from llm_client.exceptions import (
    LLMClientError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from llm_client.interfaces import (
    ActionInterpreter,
    CaseGenerator,
    CaseSeed,
    ExplanationContext,
    NarrationContext,
    NarrationEvent,
    Narrator,
    ParsedAction,
)
from llm_client.mock import MockActionInterpreter, MockCaseGenerator, MockNarrator

__version__ = "0.1.0"

__all__ = [
    # Config
    "Provider",
    "ModelConfig",
    "create_case_generator",
    "create_narrator",
    "create_action_interpreter",
    # Interfaces
    "CaseGenerator",
    "Narrator",
    "ActionInterpreter",
    # Boundary types
    "CaseSeed",
    "NarrationEvent",
    "NarrationContext",
    "ExplanationContext",
    "ParsedAction",
    # Exceptions
    "LLMClientError",
    "LLMProviderError",
    "LLMResponseError",
    "LLMTimeoutError",
    # Mocks
    "MockCaseGenerator",
    "MockNarrator",
    "MockActionInterpreter",
]
