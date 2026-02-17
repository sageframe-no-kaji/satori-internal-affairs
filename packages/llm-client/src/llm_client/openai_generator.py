"""OpenAI implementation of CaseGenerator."""

import json
from pathlib import Path
from typing import Any

from llm_client.config import ModelConfig
from llm_client.exceptions import LLMProviderError, LLMResponseError
from llm_client.interfaces import CaseGenerator, CaseSeed


class OpenAICaseGenerator(CaseGenerator):
    """Generate cases using OpenAI's API."""

    def __init__(self, config: ModelConfig):
        """Initialize OpenAI generator.

        Args:
            config: Model configuration with api_key and schema_path

        Raises:
            LLMClientError: If schema_path doesn't exist
        """
        self.config = config

        # Load schema at construction time
        if config.schema_path is None:
            raise ValueError("schema_path required for OpenAICaseGenerator")

        schema_path = Path(config.schema_path)
        if not schema_path.exists():
            raise LLMProviderError(f"Schema file not found: {config.schema_path}")

        with open(schema_path) as f:
            self.schema_text = f.read()

        # Late import to avoid requiring openai for mock usage
        try:
            import openai

            self.client = openai.OpenAI(api_key=config.api_key)
        except ImportError as e:
            raise LLMProviderError(
                "openai package not installed. Install with: pip install llm-client[openai]"
            ) from e
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize OpenAI client: {e}") from e

    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        """Generate a case using OpenAI's API.

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
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise LLMResponseError("OpenAI returned empty content")

            # Parse JSON
            try:
                case_dict: dict[str, Any] = json.loads(content)
                return case_dict
            except json.JSONDecodeError as e:
                raise LLMResponseError(f"Failed to parse JSON from OpenAI response: {e}") from e

        except LLMResponseError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Catch any OpenAI SDK errors
            raise LLMProviderError(f"OpenAI API call failed: {e}") from e

    def _build_system_prompt(self) -> str:
        """Build the system prompt including the schema."""
        prompt = (
            "You are a medical case generator. Generate a complete, valid JSON object "
            "conforming to the following schema. Return ONLY the JSON, no surrounding text "
            "or explanation.\n\n"
            f"Schema:\n\n{self.schema_text}\n\n"
            "Key requirements:\n"
            "- All node IDs must be unique\n"
            "- All flag references must be set somewhere in the case\n"
            "- All action references must exist in action_costs\n"
            "- Timer stages must be sorted by at_minutes ascending\n"
            "- The case must be medically plausible and educationally valuable"
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
