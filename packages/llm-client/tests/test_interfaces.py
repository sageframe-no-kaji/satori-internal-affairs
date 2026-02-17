"""Tests for interface definitions and boundary types."""

import pytest

from llm_client import (
    ActionInterpreter,
    CaseGenerator,
    CaseSeed,
    ExplanationContext,
    NarrationContext,
    NarrationEvent,
    Narrator,
    ParsedAction,
)


def test_case_seed_creation():
    """Test CaseSeed dataclass creation."""
    seed = CaseSeed(
        diagnosis="cellulitis",
        difficulty="beginner",
        dramatic_tone="reassuring",
    )

    assert seed.diagnosis == "cellulitis"
    assert seed.difficulty == "beginner"
    assert seed.dramatic_tone == "reassuring"
    assert seed.patient_age_range is None
    assert seed.patient_sex is None


def test_case_seed_optional_fields():
    """Test CaseSeed with all optional fields."""
    seed = CaseSeed(
        diagnosis="tuberculosis",
        difficulty="advanced",
        dramatic_tone="serious",
        patient_age_range=(40, 60),
        patient_sex="F",
        setting="outpatient_clinic",
        complications=["hiv_coinfection"],
        learning_objectives=["recognize tb in immunocompromised"],
        content_boundaries=["no pediatric cases"],
    )

    assert seed.patient_age_range == (40, 60)
    assert seed.patient_sex == "F"
    assert seed.setting == "outpatient_clinic"
    assert seed.complications == ["hiv_coinfection"]
    assert len(seed.learning_objectives) == 1
    assert len(seed.content_boundaries) == 1


def test_case_seed_immutable():
    """Test that CaseSeed is immutable."""
    seed = CaseSeed(diagnosis="test", difficulty="test", dramatic_tone="test")

    with pytest.raises(AttributeError):
        seed.diagnosis = "modified"  # type: ignore


def test_narration_event_observation():
    """Test NarrationEvent for observation."""
    event = NarrationEvent(
        event_type="OBSERVATION",
        description="Patient has elevated temperature",
        structured_data=None,
    )

    assert event.event_type == "OBSERVATION"
    assert event.description is not None
    assert event.structured_data is None


def test_narration_event_action():
    """Test NarrationEvent with structured data."""
    event = NarrationEvent(
        event_type="ACTION",
        description="Oxygen administered",
        structured_data={"action": "administer_oxygen", "result": "O2 sat improved to 95%"},
    )

    assert event.event_type == "ACTION"
    assert event.description == "Oxygen administered"
    assert event.structured_data is not None
    assert "action" in event.structured_data


def test_narration_event_immutable():
    """Test that NarrationEvent is immutable."""
    event = NarrationEvent(event_type="TEST", description="Test description")

    with pytest.raises(AttributeError):
        event.event_type = "MODIFIED"  # type: ignore


def test_narration_context_creation():
    """Test NarrationContext dataclass."""
    context = NarrationContext(
        patient_name="Jane Doe",
        patient_age=30,
        patient_sex="F",
        setting="emergency_department",
        elapsed_minutes=30,
        current_vitals={"temp": 38.5, "hr": 95},
    )

    assert context.patient_name == "Jane Doe"
    assert context.patient_age == 30
    assert context.elapsed_minutes == 30
    assert context.current_vitals["temp"] == 38.5


def test_explanation_context_creation():
    """Test ExplanationContext dataclass."""
    context = ExplanationContext(
        topic="sepsis_management",
        patient_context="Patient is showing signs of septic shock",
        detail_level="advanced",
    )

    assert context.topic == "sepsis_management"
    assert "septic shock" in context.patient_context
    assert context.detail_level == "advanced"


def test_parsed_action_creation():
    """Test ParsedAction dataclass."""
    action = ParsedAction(
        action_type="examine",
        parameter="respiratory",
        confidence=0.85,
        raw_input="examine the respiratory system",
    )

    assert action.action_type == "examine"
    assert action.parameter == "respiratory"
    assert action.confidence == 0.85
    assert "respiratory" in action.raw_input


def test_parsed_action_immutable():
    """Test that ParsedAction is immutable."""
    action = ParsedAction(action_type="test", raw_input="test input")

    with pytest.raises(AttributeError):
        action.action_type = "modified"  # type: ignore


def test_case_generator_is_abstract():
    """Test that CaseGenerator cannot be instantiated."""
    with pytest.raises(TypeError):
        CaseGenerator()  # type: ignore


def test_narrator_is_abstract():
    """Test that Narrator cannot be instantiated."""
    with pytest.raises(TypeError):
        Narrator()  # type: ignore


def test_action_interpreter_is_abstract():
    """Test that ActionInterpreter cannot be instantiated."""
    with pytest.raises(TypeError):
        ActionInterpreter()  # type: ignore
