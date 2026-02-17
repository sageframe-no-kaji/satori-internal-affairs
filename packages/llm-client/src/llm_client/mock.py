"""Mock implementations of LLM interfaces for testing without API calls."""

import json
from pathlib import Path
from typing import Any

from llm_client.config import ModelConfig
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


class MockCaseGenerator(CaseGenerator):
    """Mock case generator returning a hardcoded example case."""

    def __init__(self, config: ModelConfig):
        """Initialize mock generator.

        Args:
            config: Model configuration (unused for mock)
        """
        self.config = config
        # Try to load the example case, or use a minimal hardcoded dict
        self._case_dict = self._load_example_case()

    def _load_example_case(self) -> dict[str, Any]:
        """Load the example neurocysticercosis case or return a minimal dict."""
        # Try to find the example case file relative to the package root
        possible_paths = [
            (
                Path(__file__).parent.parent.parent.parent.parent
                / "cases"
                / "example-neurocysticercosis.json"
            ),
            Path.cwd() / "cases" / "example-neurocysticercosis.json",
        ]

        for path in possible_paths:
            if path.exists():
                with open(path) as f:
                    data: dict[str, Any] = json.load(f)
                    # Remove the _comment field if present
                    if "_comment" in data:
                        del data["_comment"]
                    return data

        # Fallback to minimal valid case dict
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "version": "1.0.0",
            "metadata": {
                "difficulty": "beginner",
                "estimated_duration_minutes": 20,
                "simulated_duration_minutes": 180,
                "learning_objectives": ["Mock case for testing"],
                "dramatic_tone": "medical_mystery",
            },
            "patient": {
                "name": "Test Patient",
                "age": 35,
                "sex": "male",
                "setting": "Emergency Department",
                "chief_complaint": "Test complaint",
                "appearance": "Test appearance",
                "arriving_vitals": {
                    "heart_rate": 80,
                    "blood_pressure_systolic": 120,
                    "blood_pressure_diastolic": 80,
                    "temperature": 98.6,
                    "respiratory_rate": 16,
                    "o2_saturation": 98,
                },
            },
            "ground_truth": {
                "diagnosis": "Mock diagnosis",
                "differential": ["Alternative 1", "Alternative 2"],
                "mechanism": "Mock mechanism",
                "key_insight": "Mock insight",
                "optimal_path": [],
                "narrative_hooks": [],
            },
            "action_costs": {
                "history_general": {"action_minutes": 10},
            },
            "nodes": [
                {
                    "id": "mock_node",
                    "type": "medical_finding",
                    "content": {"narrative_text": "Mock finding"},
                    "activation": {"starts_active": True},
                    "reveal": {"auto_reveal": True},
                }
            ],
            "outcome_evaluation": {
                "tiers": [
                    {
                        "tier": "optimal",
                        "narrative": "Mock optimal outcome",
                    }
                ],
                "end_conditions": [
                    {
                        "type": "time_elapsed",
                        "value": 180,
                        "description": "Case times out",
                    }
                ],
            },
        }

    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        """Return the hardcoded example case.

        Args:
            seed: Case seed (ignored for mock)

        Returns:
            Hardcoded case dict
        """
        return self._case_dict


class MockNarrator(Narrator):
    """Mock narrator returning templated strings."""

    def __init__(self, config: ModelConfig):
        """Initialize mock narrator.

        Args:
            config: Model configuration (unused for mock)
        """
        self.config = config

    def narrate(self, event: NarrationEvent, context: NarrationContext) -> str:
        """Return a templated narrative string.

        Args:
            event: Event to narrate
            context: Current game context

        Returns:
            Templated narrative text
        """
        return (
            f"[Mock Narration] {context.patient_name} experiences {event.event_type}: "
            f"{event.description} (Time: {context.elapsed_minutes} minutes)"
        )

    def explain(self, context: ExplanationContext) -> str:
        """Return a templated explanation string.

        Args:
            context: Explanation context

        Returns:
            Templated explanation text
        """
        return (
            f"[Mock Explanation] Topic: {context.topic} "
            f"(Detail level: {context.detail_level}). "
            f"Context: {context.patient_context}"
        )


class MockActionInterpreter(ActionInterpreter):
    """Mock action interpreter using simple string matching."""

    def __init__(self, config: ModelConfig):
        """Initialize mock interpreter.

        Args:
            config: Model configuration (unused for mock)
        """
        self.config = config

    def parse(self, raw_input: str, available_actions: list[str]) -> ParsedAction:
        """Parse input using simple string matching.

        Args:
            raw_input: Player input
            available_actions: Valid action identifiers

        Returns:
            Parsed action with confidence
        """
        # Simple matching: split input on whitespace, check first word
        words = raw_input.strip().split()
        if not words:
            return ParsedAction(
                action_type="unknown",
                parameter=None,
                confidence=0.0,
                raw_input=raw_input,
            )

        first_word = words[0].lower()

        # Try to match against available actions
        for action in available_actions:
            if first_word in action.lower():
                # If action has parameter format (action:param), extract both parts
                if ":" in action:
                    base, param = action.split(":", 1)
                    return ParsedAction(
                        action_type=base,
                        parameter=param,
                        confidence=1.0,
                        raw_input=raw_input,
                    )
                else:
                    return ParsedAction(
                        action_type=action,
                        parameter=None,
                        confidence=1.0,
                        raw_input=raw_input,
                    )

        # No match found
        return ParsedAction(
            action_type=first_word,
            parameter=None,
            confidence=0.0,
            raw_input=raw_input,
        )
