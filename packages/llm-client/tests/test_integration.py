"""Integration tests for LLM providers (requires API keys).

These tests make real API calls and are skipped unless explicitly requested.
Run with: pytest -m integration

Environment variables required:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
"""

import os
from pathlib import Path

import pytest

from llm_client import CaseSeed, ModelConfig, Provider, create_case_generator

# Skip all integration tests by default
pytestmark = pytest.mark.integration


@pytest.fixture
def real_schema_path():
    """Path to the actual case definition schema."""
    # Navigate from tests/ to schemas/
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent.parent.parent
    schema_path = project_root / "schemas" / "case-definition.schema.json"

    if not schema_path.exists():
        pytest.skip(f"Schema file not found: {schema_path}")

    return str(schema_path)


@pytest.fixture
def openai_api_key():
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key


@pytest.fixture
def anthropic_api_key():
    """Get Anthropic API key from environment."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


@pytest.fixture
def simple_case_seed():
    """Simple case seed for integration testing."""
    return CaseSeed(
        diagnosis="acute_appendicitis",
        difficulty="beginner",
        dramatic_tone="clinical",
        patient_age_range=(20, 40),
        patient_sex="M",
    )


class TestOpenAIIntegration:
    """Integration tests for OpenAI provider."""

    def test_generate_case_real_api(self, openai_api_key, real_schema_path, simple_case_seed):
        """Test generating a case with real OpenAI API."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        generator = create_case_generator(config)
        result = generator.generate_case(simple_case_seed)

        # Verify we got a dict back
        assert isinstance(result, dict)

        # Verify required top-level keys
        required_keys = [
            "case_id",
            "metadata",
            "patient",
            "opening_presentation",
            "nodes",
            "action_costs",
            "timer_stages",
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Verify metadata has expected structure
        metadata = result["metadata"]
        assert "diagnosis" in metadata
        assert "difficulty" in metadata

        # Verify patient has basic fields
        patient = result["patient"]
        assert "age" in patient
        assert "sex" in patient

        # Verify nodes is a list
        assert isinstance(result["nodes"], list)
        assert len(result["nodes"]) > 0

    def test_generate_case_with_complications(self, openai_api_key, real_schema_path):
        """Test generating a case with complications specified."""
        seed = CaseSeed(
            diagnosis="pneumonia",
            difficulty="intermediate",
            dramatic_tone="serious",
            patient_age_range=(60, 80),
            complications=["sepsis", "respiratory_failure"],
            learning_objectives=["Recognize early sepsis", "Manage respiratory support"],
        )

        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        generator = create_case_generator(config)
        result = generator.generate_case(seed)

        assert isinstance(result, dict)
        assert "metadata" in result

        # Verify diagnosis matches seed
        assert result["metadata"]["diagnosis"] == seed.diagnosis


class TestAnthropicIntegration:
    """Integration tests for Anthropic provider."""

    def test_generate_case_real_api(self, anthropic_api_key, real_schema_path, simple_case_seed):
        """Test generating a case with real Anthropic API."""
        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key=anthropic_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        generator = create_case_generator(config)
        result = generator.generate_case(simple_case_seed)

        # Verify we got a dict back
        assert isinstance(result, dict)

        # Verify required top-level keys
        required_keys = [
            "case_id",
            "metadata",
            "patient",
            "opening_presentation",
            "nodes",
            "action_costs",
            "timer_stages",
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Verify metadata has expected structure
        metadata = result["metadata"]
        assert "diagnosis" in metadata
        assert "difficulty" in metadata

        # Verify patient has basic fields
        patient = result["patient"]
        assert "age" in patient
        assert "sex" in patient

        # Verify nodes is a list
        assert isinstance(result["nodes"], list)
        assert len(result["nodes"]) > 0

    def test_generate_case_female_patient(self, anthropic_api_key, real_schema_path):
        """Test generating a case with female patient specified."""
        seed = CaseSeed(
            diagnosis="urinary_tract_infection",
            difficulty="beginner",
            dramatic_tone="reassuring",
            patient_age_range=(25, 45),
            patient_sex="F",
        )

        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key=anthropic_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        generator = create_case_generator(config)
        result = generator.generate_case(seed)

        assert isinstance(result, dict)
        assert result["patient"]["sex"] == "F"

    def test_generate_case_specific_setting(self, anthropic_api_key, real_schema_path):
        """Test generating a case with specific clinical setting."""
        seed = CaseSeed(
            diagnosis="asthma_exacerbation",
            difficulty="intermediate",
            dramatic_tone="urgent",
            setting="emergency_department",
        )

        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key=anthropic_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        generator = create_case_generator(config)
        result = generator.generate_case(seed)

        assert isinstance(result, dict)
        assert "opening_presentation" in result


class TestProviderComparison:
    """Tests comparing behavior across providers."""

    def test_both_providers_same_seed(self, openai_api_key, anthropic_api_key, real_schema_path):
        """Test that both providers can generate from the same seed."""
        seed = CaseSeed(
            diagnosis="myocardial_infarction",
            difficulty="intermediate",
            dramatic_tone="serious",
            patient_age_range=(50, 70),
            patient_sex="M",
        )

        # OpenAI
        openai_config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        openai_generator = create_case_generator(openai_config)
        openai_result = openai_generator.generate_case(seed)

        # Anthropic
        anthropic_config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key=anthropic_api_key,
            temperature=0.7,
            max_tokens=16384,
            schema_path=real_schema_path,
        )

        anthropic_generator = create_case_generator(anthropic_config)
        anthropic_result = anthropic_generator.generate_case(seed)

        # Both should return valid dict structures
        assert isinstance(openai_result, dict)
        assert isinstance(anthropic_result, dict)

        # Both should have required keys
        assert "metadata" in openai_result
        assert "metadata" in anthropic_result

        # Both should reflect the seed diagnosis
        assert openai_result["metadata"]["diagnosis"] == seed.diagnosis
        assert anthropic_result["metadata"]["diagnosis"] == seed.diagnosis
