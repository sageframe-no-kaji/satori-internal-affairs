"""Configuration and factory functions for LLM clients."""

from dataclasses import dataclass
from enum import StrEnum

from llm_client.exceptions import LLMClientError
from llm_client.interfaces import ActionInterpreter, CaseGenerator, Narrator


class Provider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for an LLM provider instance."""

    provider: Provider
    model: str
    api_key: str | None = None  # None for mock
    temperature: float = 0.7
    max_tokens: int = 16384
    # Request timeout — a slow provider must degrade to the fallback path,
    # not hang the game loop (P2-H08)
    timeout_seconds: float = 30.0
    # Path to JSON schema file for prompt inclusion (CaseGenerator only)
    schema_path: str | None = None


def create_case_generator(config: ModelConfig) -> CaseGenerator:
    """Create a CaseGenerator instance from config.

    Args:
        config: Model configuration

    Returns:
        CaseGenerator instance

    Raises:
        LLMClientError: If config is invalid for non-mock providers
    """
    if config.provider == Provider.MOCK:
        from llm_client.mock import MockCaseGenerator

        return MockCaseGenerator(config)

    # Validate non-mock config
    if config.api_key is None:
        raise LLMClientError(f"api_key required for provider {config.provider}")
    if config.schema_path is None:
        raise LLMClientError(
            f"schema_path required for CaseGenerator with provider {config.provider}"
        )

    if config.provider == Provider.OPENAI:
        from llm_client.openai_generator import OpenAICaseGenerator

        return OpenAICaseGenerator(config)
    elif config.provider == Provider.ANTHROPIC:
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        return AnthropicCaseGenerator(config)
    else:
        raise LLMClientError(f"Unknown provider: {config.provider}")


def create_narrator(config: ModelConfig) -> Narrator:
    """Create a Narrator instance from config.

    Args:
        config: Model configuration

    Returns:
        Narrator instance

    Raises:
        LLMClientError: If config is invalid for non-mock providers
    """
    if config.provider == Provider.MOCK:
        from llm_client.mock import MockNarrator

        return MockNarrator(config)

    # Validate non-mock config
    if config.api_key is None:
        raise LLMClientError(f"api_key required for provider {config.provider}")

    if config.provider == Provider.ANTHROPIC:
        from llm_client.anthropic_narrator import AnthropicNarrator

        return AnthropicNarrator(config)

    # OpenAI narrator: no implementation until a case for it exists (P2-H08
    # chose Anthropic; multi-provider failover is explicitly out of scope)
    raise LLMClientError(f"No live Narrator implementation for provider {config.provider}")


def create_action_interpreter(config: ModelConfig) -> ActionInterpreter:
    """Create an ActionInterpreter instance from config.

    Args:
        config: Model configuration

    Returns:
        ActionInterpreter instance

    Raises:
        LLMClientError: If config is invalid for non-mock providers
    """
    if config.provider == Provider.MOCK:
        from llm_client.mock import MockActionInterpreter

        return MockActionInterpreter(config)

    # Validate non-mock config
    if config.api_key is None:
        raise LLMClientError(f"api_key required for provider {config.provider}")

    # No live implementations yet — Phase 1 only has mocks
    raise LLMClientError(f"No live ActionInterpreter implementation for provider {config.provider}")
