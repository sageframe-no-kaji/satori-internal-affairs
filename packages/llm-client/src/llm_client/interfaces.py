"""Interface definitions for LLM interactions.

Three separate interfaces for three distinct concerns:
- CaseGenerator: structured case generation
- Narrator: narrative text generation
- ActionInterpreter: natural language parsing
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseSeed:
    """Input for case generation. Owned by llm-client, not satori."""

    diagnosis: str
    difficulty: str  # matches Difficulty enum values
    dramatic_tone: str  # matches DramaticTone enum values
    patient_age_range: tuple[int, int] | None = None
    patient_sex: str | None = None
    setting: str | None = None
    complications: list[str] | None = None
    learning_objectives: list[str] | None = None
    content_boundaries: list[str] | None = None


@dataclass(frozen=True)
class NarrationEvent:
    """Lightweight event data for narration. Owned by llm-client."""

    event_type: str
    description: str
    structured_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class NarrationContext:
    """Current game context for narration. Owned by llm-client."""

    patient_name: str
    patient_age: int
    patient_sex: str
    setting: str
    current_vitals: dict[str, Any]
    elapsed_minutes: int


@dataclass(frozen=True)
class ExplanationContext:
    """Context for teaching explanations. Owned by llm-client."""

    topic: str
    patient_context: str
    detail_level: str = "intermediate"


@dataclass(frozen=True)
class ParsedAction:
    """Result of natural language intent parsing. Owned by llm-client."""

    action_type: str
    parameter: str | None = None
    confidence: float = 1.0
    raw_input: str = ""


class CaseGenerator(ABC):
    """Generate structured case definitions from seeds."""

    @abstractmethod
    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        """Generate a case definition as raw parsed JSON.

        Returns a dict — NOT a CaseDefinition. Validation is the caller's job.

        Args:
            seed: Case generation parameters

        Returns:
            Raw dict parsed from JSON response

        Raises:
            LLMProviderError: API call failed
            LLMResponseError: Response was not valid JSON
        """
        ...


class Narrator(ABC):
    """Generate narrative text from game events."""

    @abstractmethod
    def narrate(self, event: NarrationEvent, context: NarrationContext) -> str:
        """Generate narrative text for a game event.

        Args:
            event: The event to narrate
            context: Current game context

        Returns:
            Narrative text describing the event
        """
        ...

    @abstractmethod
    def explain(self, context: ExplanationContext) -> str:
        """Generate a teaching explanation.

        Args:
            context: The topic and context for explanation

        Returns:
            Educational explanation text
        """
        ...


class ActionInterpreter(ABC):
    """Parse natural language input into structured actions."""

    @abstractmethod
    def parse(self, raw_input: str, available_actions: list[str]) -> ParsedAction:
        """Parse free-text player input into a structured action.

        Args:
            raw_input: Natural language input from player
            available_actions: List of valid action identifiers

        Returns:
            Parsed structured action with confidence score
        """
        ...
