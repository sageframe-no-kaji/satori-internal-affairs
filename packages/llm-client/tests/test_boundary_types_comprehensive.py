"""Additional tests for boundary type construction and behavior."""

import pytest

from llm_client import (
    CaseSeed,
    ExplanationContext,
    NarrationContext,
    NarrationEvent,
    ParsedAction,
)


def test_case_seed_fields():
    """Test CaseSeed can be constructed with expected fields."""
    seed = CaseSeed(
        diagnosis="pneumonia",
        difficulty="intermediate",
        dramatic_tone="clinical",
    )

    assert seed.diagnosis == "pneumonia"
    assert seed.difficulty == "intermediate"
    assert seed.dramatic_tone == "clinical"


def test_case_seed_with_all_optional_fields():
    """Test CaseSeed with all optional fields populated."""
    seed = CaseSeed(
        diagnosis="sepsis",
        difficulty="advanced",
        dramatic_tone="serious",
        patient_age_range=(50, 70),
        patient_sex="M",
        setting="ICU",
        complications=["multi-organ failure"],
        learning_objectives=["Recognize septic shock", "Manage vasopressors"],
        content_boundaries=["No pediatric content"],
    )

    assert seed.patient_age_range == (50, 70)
    assert seed.patient_sex == "M"
    assert seed.setting == "ICU"
    assert seed.complications is not None and len(seed.complications) == 1
    assert seed.learning_objectives is not None and len(seed.learning_objectives) == 2
    assert seed.content_boundaries is not None and len(seed.content_boundaries) == 1


def test_parsed_action_fields():
    """Test ParsedAction can be constructed with expected fields."""
    action = ParsedAction(
        action_type="examine",
        parameter="chest",
        confidence=0.95,
        raw_input="listen to lungs",
    )

    assert action.action_type == "examine"
    assert action.parameter == "chest"
    assert action.confidence == 0.95
    assert action.raw_input == "listen to lungs"


def test_parsed_action_minimal():
    """Test ParsedAction with minimal fields."""
    action = ParsedAction(action_type="unknown")

    assert action.action_type == "unknown"
    assert action.parameter is None
    assert action.confidence == 1.0
    assert action.raw_input == ""


def test_parsed_action_confidence_range():
    """Test ParsedAction can represent different confidence levels."""
    action_high = ParsedAction(action_type="examine", confidence=0.99)
    action_medium = ParsedAction(action_type="examine", confidence=0.5)
    action_low = ParsedAction(action_type="examine", confidence=0.1)
    action_zero = ParsedAction(action_type="unknown", confidence=0.0)

    assert action_high.confidence == 0.99
    assert action_medium.confidence == 0.5
    assert action_low.confidence == 0.1
    assert action_zero.confidence == 0.0


def test_narration_event_minimal():
    """Test NarrationEvent with minimal fields."""
    event = NarrationEvent(
        event_type="VITAL_CHANGE",
        description="Heart rate increased",
    )

    assert event.event_type == "VITAL_CHANGE"
    assert event.description == "Heart rate increased"
    assert event.structured_data is None


def test_narration_event_with_structured_data():
    """Test NarrationEvent with structured data."""
    event = NarrationEvent(
        event_type="VITAL_CHANGE",
        description="Heart rate increased to 120 bpm",
        structured_data={"vital": "heart_rate", "value": 120, "unit": "bpm"},
    )

    assert event.event_type == "VITAL_CHANGE"
    assert event.structured_data is not None
    assert event.structured_data["vital"] == "heart_rate"
    assert event.structured_data["value"] == 120


def test_narration_context_fields():
    """Test NarrationContext construction."""
    context = NarrationContext(
        patient_name="John Doe",
        patient_age=45,
        patient_sex="M",
        setting="Emergency Department",
        current_vitals={"hr": 95, "bp_sys": 130, "temp": 38.2},
        elapsed_minutes=25,
    )

    assert context.patient_name == "John Doe"
    assert context.patient_age == 45
    assert context.patient_sex == "M"
    assert context.setting == "Emergency Department"
    assert context.elapsed_minutes == 25
    assert context.current_vitals["hr"] == 95


def test_narration_context_empty_vitals():
    """Test NarrationContext with empty vitals dict."""
    context = NarrationContext(
        patient_name="Jane Doe",
        patient_age=30,
        patient_sex="F",
        setting="Clinic",
        current_vitals={},
        elapsed_minutes=0,
    )

    assert context.current_vitals == {}
    assert context.elapsed_minutes == 0


def test_explanation_context_fields():
    """Test ExplanationContext construction."""
    context = ExplanationContext(
        topic="diabetic_ketoacidosis",
        patient_context="Patient with type 1 diabetes presenting with altered mental status",
        detail_level="advanced",
    )

    assert context.topic == "diabetic_ketoacidosis"
    assert "altered mental status" in context.patient_context
    assert context.detail_level == "advanced"


def test_explanation_context_default_detail_level():
    """Test ExplanationContext uses default detail_level."""
    context = ExplanationContext(
        topic="pneumonia_treatment",
        patient_context="Community-acquired pneumonia",
    )

    assert context.detail_level == "intermediate"


def test_explanation_context_different_detail_levels():
    """Test ExplanationContext with different detail levels."""
    beginner = ExplanationContext(
        topic="influenza",
        patient_context="Flu symptoms",
        detail_level="beginner",
    )
    intermediate = ExplanationContext(
        topic="influenza",
        patient_context="Flu symptoms",
        detail_level="intermediate",
    )
    advanced = ExplanationContext(
        topic="influenza",
        patient_context="Flu symptoms",
        detail_level="advanced",
    )

    assert beginner.detail_level == "beginner"
    assert intermediate.detail_level == "intermediate"
    assert advanced.detail_level == "advanced"


def test_all_boundary_types_are_frozen():
    """Test that all boundary types are immutable (frozen dataclasses)."""
    seed = CaseSeed(diagnosis="test", difficulty="test", dramatic_tone="test")
    action = ParsedAction(action_type="test")
    event = NarrationEvent(event_type="test", description="test")
    context = NarrationContext(
        patient_name="test",
        patient_age=30,
        patient_sex="M",
        setting="test",
        current_vitals={},
        elapsed_minutes=0,
    )
    explanation = ExplanationContext(topic="test", patient_context="test")

    # All should be frozen
    with pytest.raises(AttributeError):
        seed.diagnosis = "modified"  # type: ignore

    with pytest.raises(AttributeError):
        action.action_type = "modified"  # type: ignore

    with pytest.raises(AttributeError):
        event.event_type = "modified"  # type: ignore

    with pytest.raises(AttributeError):
        context.patient_name = "modified"  # type: ignore

    with pytest.raises(AttributeError):
        explanation.topic = "modified"  # type: ignore
