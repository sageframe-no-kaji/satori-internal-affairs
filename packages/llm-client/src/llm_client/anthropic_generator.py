"""Anthropic implementation of CaseGenerator."""

import json
from pathlib import Path
from typing import Any

from llm_client.config import ModelConfig
from llm_client.exceptions import LLMProviderError, LLMResponseError
from llm_client.interfaces import CaseGenerator, CaseSeed


class AnthropicCaseGenerator(CaseGenerator):
    """Generate cases using Anthropic's API."""

    def __init__(self, config: ModelConfig):
        """Initialize Anthropic generator.

        Args:
            config: Model configuration with api_key and schema_path

        Raises:
            LLMClientError: If schema_path doesn't exist
        """
        self.config = config

        # Load schema at construction time
        if config.schema_path is None:
            raise ValueError("schema_path required for AnthropicCaseGenerator")

        schema_path = Path(config.schema_path)
        if not schema_path.exists():
            raise LLMProviderError(f"Schema file not found: {config.schema_path}")

        with open(schema_path) as f:
            self.schema_text = f.read()

        # Validate api_key
        if config.api_key is None:
            raise ValueError("api_key required for AnthropicCaseGenerator")
        api_key = config.api_key  # Type narrowing for mypy

        # Late import to avoid requiring anthropic for mock usage
        try:
            import anthropic  # pyright: ignore[reportMissingImports]

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError as e:
            raise LLMProviderError(
                "anthropic package not installed. Install with: pip install llm-client[anthropic]"
            ) from e
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Anthropic client: {e}") from e

    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        """Generate a case using Anthropic's API.

        Args:
            seed: Case generation parameters

        Returns:
            Raw dict parsed from JSON response

        Raises:
            LLMProviderError: API call failed
            LLMResponseError: Response was not valid JSON
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(seed)

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )

            # Extract text content from response
            if not response.content or len(response.content) == 0:
                raise LLMResponseError("Anthropic returned empty content")

            # Get first content block (should be TextBlock with JSON)
            first_block = response.content[0]
            if not hasattr(first_block, "text"):
                raise LLMResponseError(f"Unexpected content block type: {type(first_block)}")
            content = first_block.text

            # Parse JSON
            try:
                case_dict: dict[str, Any] = json.loads(content)
                return case_dict
            except json.JSONDecodeError as e:
                raise LLMResponseError(f"Failed to parse JSON from Anthropic response: {e}") from e

        except LLMResponseError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Catch any Anthropic SDK errors
            raise LLMProviderError(f"Anthropic API call failed: {e}") from e

    def _build_system_prompt(self) -> str:
        """Build the system prompt including the schema."""
        prompt = (
            "You are a medical case generator. Generate a complete, valid JSON object "
            "conforming to the following schema. Return ONLY the JSON object itself, with no "
            "surrounding text, markdown formatting, or explanation.\n\n"
            f"Schema:\n\n{self.schema_text}\n\n"
            "Key requirements:\n"
            "- All node IDs must be unique\n"
            "- All flag references must be set somewhere in the case\n"
            "- All action references must exist in action_costs\n"
            "- Timer stages must be sorted by at_minutes ascending\n"
            "- The case must be medically plausible and educationally valuable\n"
            "- Return ONLY the JSON object, no markdown code blocks or other formatting"
        )
        return prompt

    def _build_user_prompt(self, seed: CaseSeed) -> str:
        """Build the user prompt from the seed.

        Args:
            seed: Case generation parameters

        Returns:
            User prompt string
        """
        prompt_parts = [
            "Generate a medical mystery case with the following specifications:",
            f"- Diagnosis: {seed.diagnosis}",
            f"- Difficulty: {seed.difficulty}",
            f"- Dramatic tone: {seed.dramatic_tone}",
        ]

        if seed.patient_age_range:
            min_age, max_age = seed.patient_age_range
            prompt_parts.append(f"- Patient age range: {min_age}-{max_age} years")

        if seed.patient_sex:
            prompt_parts.append(f"- Patient sex: {seed.patient_sex}")

        if seed.setting:
            prompt_parts.append(f"- Clinical setting: {seed.setting}")

        if seed.complications:
            prompt_parts.append(f"- Include complications: {', '.join(seed.complications)}")

        if seed.learning_objectives:
            prompt_parts.append(f"- Learning objectives: {', '.join(seed.learning_objectives)}")

        if seed.content_boundaries:
            prompt_parts.append(f"- Content boundaries: {', '.join(seed.content_boundaries)}")

        prompt_parts.append("\nReturn the complete case definition as a JSON object.")

        return "\n".join(prompt_parts)
