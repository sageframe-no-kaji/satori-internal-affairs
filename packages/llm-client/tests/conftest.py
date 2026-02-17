"""Pytest configuration and fixtures for llm-client tests."""

import pytest

from llm_client import (
    CaseSeed,
    ExplanationContext,
    ModelConfig,
    NarrationContext,
    NarrationEvent,
    Provider,
)


@pytest.fixture
def mock_model_config() -> ModelConfig:
    """Basic mock model configuration."""
    return ModelConfig(
        provider=Provider.MOCK,
        model="mock-model",
        temperature=0.7,
        max_tokens=1024,
    )


@pytest.fixture
def openai_model_config(tmp_path) -> ModelConfig:
    """OpenAI model configuration with schema path."""
    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"type": "object"}')

    return ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test-key",
        temperature=0.7,
        max_tokens=4096,
        schema_path=str(schema_file),
    )


@pytest.fixture
def anthropic_model_config(tmp_path) -> ModelConfig:
    """Anthropic model configuration with schema path."""
    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"type": "object"}')

    return ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
        temperature=0.7,
        max_tokens=8192,
        schema_path=str(schema_file),
    )


@pytest.fixture
def sample_case_seed() -> CaseSeed:
    """Sample case seed for testing."""
    return CaseSeed(
        diagnosis="pneumonia",
        difficulty="intermediate",
        dramatic_tone="clinical",
        patient_age_range=(25, 35),
        patient_sex="M",
        setting="emergency_department",
        complications=["sepsis"],
        learning_objectives=["recognize early sepsis"],
        content_boundaries=["no graphic violence"],
    )


@pytest.fixture
def sample_narration_event() -> NarrationEvent:
    """Sample narration event."""
    return NarrationEvent(
        event_type="OBSERVATION",
        description="Patient appears diaphoretic",
        structured_data={"severity": "moderate"},
    )


@pytest.fixture
def sample_narration_context() -> NarrationContext:
    """Sample narration context."""
    return NarrationContext(
        patient_name="John Doe",
        patient_age=45,
        patient_sex="M",
        setting="emergency_department",
        elapsed_minutes=15,
        current_vitals={"heart_rate": 110, "bp_systolic": 90},
    )


@pytest.fixture
def sample_explanation_context() -> ExplanationContext:
    """Sample explanation context for action interpretation."""
    return ExplanationContext(
        topic="chest_pain_evaluation",
        patient_context="Patient presenting with chest pain",
        detail_level="intermediate",
    )
