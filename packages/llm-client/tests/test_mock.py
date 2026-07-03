"""Tests for mock implementations."""

import pytest

from llm_client import MockActionInterpreter, MockCaseGenerator, MockNarrator, ModelConfig, Provider


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return ModelConfig(provider=Provider.MOCK, model="mock-model")


def test_mock_case_generator_returns_dict(mock_config, sample_case_seed):
    """Test that MockCaseGenerator returns a dict."""
    generator = MockCaseGenerator(mock_config)
    result = generator.generate_case(sample_case_seed)

    assert isinstance(result, dict)
    # Check for either the new schema ("id") or fallback ("id")
    assert "id" in result or "case_id" in result
    assert "metadata" in result
    assert "patient" in result


def test_mock_case_generator_required_keys(mock_config, sample_case_seed):
    """Test that MockCaseGenerator includes major top-level keys."""
    generator = MockCaseGenerator(mock_config)
    result = generator.generate_case(sample_case_seed)

    # Check for major keys
    assert "metadata" in result
    assert "patient" in result
    assert "nodes" in result
    assert "action_costs" in result


def test_mock_case_generator_returns_valid_structure(mock_config, sample_case_seed):
    """Test that the mock generator returns a complete structure."""
    generator = MockCaseGenerator(mock_config)
    result = generator.generate_case(sample_case_seed)

    # Verify nested structure
    assert isinstance(result["metadata"], dict)
    assert isinstance(result["patient"], dict)
    assert isinstance(result["nodes"], list)
    assert isinstance(result["action_costs"], dict)


def test_mock_narrator_narrate(mock_config, sample_narration_event, sample_narration_context):
    """Test MockNarrator.narrate returns a string."""
    narrator = MockNarrator(mock_config)
    result = narrator.narrate(sample_narration_event, sample_narration_context)

    assert isinstance(result, str)
    assert len(result) > 0


def test_mock_narrator_narrate_includes_event_info(mock_config):
    """Test that narration includes event information."""
    from llm_client import NarrationContext, NarrationEvent

    narrator = MockNarrator(mock_config)

    event = NarrationEvent(
        event_type="OBSERVATION",
        description="Patient is coughing",
        structured_data=None,
    )

    context = NarrationContext(
        patient_name="Test Patient",
        patient_age=45,
        patient_sex="M",
        setting="emergency",
        elapsed_minutes=10,
        current_vitals={},
    )

    result = narrator.narrate(event, context)
    # Should include event type, description, or patient name
    assert (
        "coughing" in result.lower() or "observation" in result.lower() or "test" in result.lower()
    )


def test_mock_narrator_explain(mock_config, sample_explanation_context):
    """Test MockNarrator.explain returns a string."""
    narrator = MockNarrator(mock_config)
    result = narrator.explain(sample_explanation_context)

    assert isinstance(result, str)
    assert len(result) > 0


def test_mock_narrator_explain_mentions_topic(mock_config):
    """Test that explanation mentions the topic."""
    from llm_client import ExplanationContext

    narrator = MockNarrator(mock_config)

    context = ExplanationContext(
        topic="sepsis_management",
        patient_context="Patient showing signs of infection",
        detail_level="intermediate",
    )

    result = narrator.explain(context)
    assert "sepsis" in result.lower() or "topic" in result.lower()


def test_mock_action_interpreter_parse(mock_config):
    """Test MockActionInterpreter.parse returns ParsedAction."""
    from llm_client import ParsedAction

    interpreter = MockActionInterpreter(mock_config)
    result = interpreter.parse("examine the patient", ["examine", "order_labs"])

    assert isinstance(result, ParsedAction)
    assert result.action_type is not None
    assert 0.0 <= result.confidence <= 1.0
    assert result.raw_input == "examine the patient"


def test_mock_action_interpreter_matches_available_action(mock_config):
    """Test that parser matches available actions."""

    interpreter = MockActionInterpreter(mock_config)

    result = interpreter.parse("examine cardiovascular", ["examine", "order_labs", "discharge"])

    # Should match "examine" since "examine" is in the input
    assert result.action_type == "examine"
    assert result.confidence == 1.0


def test_mock_action_interpreter_no_match_low_confidence(mock_config):
    """Test that no match results in low confidence."""
    interpreter = MockActionInterpreter(mock_config)

    result = interpreter.parse("xyz completely unrelated", ["examine", "order_labs"])

    # First word "xyz" doesn't match, so confidence should be 0
    assert result.confidence == 0.0
