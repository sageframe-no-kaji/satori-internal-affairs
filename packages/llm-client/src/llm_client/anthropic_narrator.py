"""Anthropic implementation of Narrator (P2-H08 plumbing).

Voice content is NOT here — the system prompt comes from narration_prompts,
whose placeholder the practitioner's voice document replaces. This module is
pure plumbing: client construction, the narrate call, and the error taxonomy
the bridge's fallback path consumes.
"""

from llm_client.config import ModelConfig
from llm_client.exceptions import LLMProviderError, LLMResponseError, LLMTimeoutError
from llm_client.interfaces import ExplanationContext, NarrationContext, NarrationEvent, Narrator
from llm_client.narration_prompts import build_system_prompt, build_user_prompt


class AnthropicNarrator(Narrator):
    """Narrate game events using Anthropic's API."""

    def __init__(self, config: ModelConfig):
        """Initialize the narrator.

        Args:
            config: Model configuration with api_key; timeout_seconds bounds
                every request (a slow provider degrades to the bridge's
                fallback instead of hanging the game loop).

        Raises:
            ValueError: api_key missing.
            LLMProviderError: anthropic package missing or client init failed.
        """
        self.config = config

        if config.api_key is None:
            raise ValueError("api_key required for AnthropicNarrator")
        api_key = config.api_key  # Type narrowing for mypy

        # Late import to avoid requiring anthropic for mock usage
        try:
            import anthropic  # pyright: ignore[reportMissingImports]

            self.client = anthropic.Anthropic(api_key=api_key, timeout=config.timeout_seconds)
        except ImportError as e:
            raise LLMProviderError(
                "anthropic package not installed. Install with: pip install llm-client[anthropic]"
            ) from e
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Anthropic client: {e}") from e

    def narrate(self, event: NarrationEvent, context: NarrationContext) -> str:
        """Generate narration for one event.

        Raises:
            LLMTimeoutError: provider did not answer within the timeout.
            LLMProviderError: any other API failure.
            LLMResponseError: provider returned no usable text.
        """
        import anthropic  # pyright: ignore[reportMissingImports]
        from anthropic.types import TextBlock  # pyright: ignore[reportMissingImports]

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=build_system_prompt(),
                messages=[{"role": "user", "content": build_user_prompt(event, context)}],
            )
        except anthropic.APITimeoutError as e:
            timeout = self.config.timeout_seconds
            raise LLMTimeoutError(f"Narration timed out after {timeout}s") from e
        except Exception as e:
            raise LLMProviderError(f"Narration request failed: {e}") from e

        blocks = [block.text for block in response.content if isinstance(block, TextBlock)]
        text = "".join(blocks).strip()
        if not text:
            raise LLMResponseError("Narrator returned no text content")
        return text

    def explain(self, context: ExplanationContext) -> str:
        """Teaching explanations belong to the debrief phase (Phase 5)."""
        raise NotImplementedError("Narrator.explain is Phase 5 (debrief) work")
