"""Tests for CaseGenerationPipeline in mock mode.

Mock mode: zero network calls, exercises the full pipeline mechanics.
"""

import json
from pathlib import Path

import pytest
from llm_client import ModelConfig, Provider
from satori.models import CaseDefinition

from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.result import GenerationResult
from anamnesis.seed import CreativeSeed


@pytest.fixture
def mock_config() -> ModelConfig:
    return ModelConfig(provider=Provider.MOCK, model="mock")


@pytest.fixture
def minimal_seed() -> CreativeSeed:
    return CreativeSeed(diagnosis="pneumothorax", difficulty="beginner", dramatic_tone="clinical")


@pytest.fixture
def rich_seed() -> CreativeSeed:
    return CreativeSeed(
        diagnosis="neurocysticercosis",
        difficulty="intermediate",
        dramatic_tone="medical_mystery",
        patient_age_range=(25, 35),
        patient_sex="female",
        dramatic_hook="Patient collapses mid-sentence.",
        red_herrings=["job stress"],
        forbidden_tropes=["No stereotyping"],
    )


class TestPipelineGenerate:
    """pipeline.generate() with mock provider."""

    def test_generate_returns_result(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert isinstance(result, GenerationResult)

    def test_generate_succeeds(self, mock_config: ModelConfig, minimal_seed: CreativeSeed) -> None:
        """Mock provider always returns a valid case on first attempt."""
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.success is True

    def test_result_case_is_case_definition(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.case is not None
        assert isinstance(result.case, CaseDefinition)

    def test_first_attempt_success_attempts_is_one(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        """Mock produces valid output on first try → attempts == 1."""
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.attempts == 1

    def test_result_errors_empty_on_success(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.errors == []

    def test_result_has_seed(self, mock_config: ModelConfig, minimal_seed: CreativeSeed) -> None:
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.seed is minimal_seed

    def test_result_has_raw_dict(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.raw_dict is not None
        assert isinstance(result.raw_dict, dict)

    def test_generate_with_rich_seed(
        self, mock_config: ModelConfig, rich_seed: CreativeSeed
    ) -> None:
        """Pipeline handles Mode 2 rich seed without error."""
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(rich_seed)
        assert result.success is True
        assert result.case is not None


class TestPipelineSave:
    """pipeline.save() writes the case to disk."""

    def test_save_writes_file(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        result = pipeline.generate(minimal_seed)
        assert result.success
        path = pipeline.save(result)
        assert path.exists()

    def test_saved_file_is_valid_json(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        result = pipeline.generate(minimal_seed)
        path = pipeline.save(result)
        with path.open() as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_saved_file_validates_as_case_definition(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        """Saved JSON can be loaded back by CaseDefinition.model_validate()."""
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        result = pipeline.generate(minimal_seed)
        path = pipeline.save(result)
        with path.open() as f:
            data = json.load(f)
        reloaded = CaseDefinition.model_validate(data)
        assert isinstance(reloaded, CaseDefinition)

    def test_save_filename_contains_diagnosis(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        result = pipeline.generate(minimal_seed)
        path = pipeline.save(result)
        assert "pneumothorax" in path.name

    def test_save_raises_on_failure_result(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        """save() raises ValueError when result.success is False."""
        from anamnesis.result import _make_failure

        failure = _make_failure(None, 1, ["error"], minimal_seed)
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        with pytest.raises(ValueError, match="Cannot save"):
            pipeline.save(failure)

    def test_save_creates_output_dir(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        """Output directory is created automatically if it doesn't exist."""
        output_dir = tmp_path / "new" / "nested" / "dir"
        pipeline = CaseGenerationPipeline(mock_config, output_dir=output_dir)
        result = pipeline.generate(minimal_seed)
        pipeline.save(result)
        assert output_dir.exists()

    def test_case_path_none_before_save(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed
    ) -> None:
        """generate() returns result with case_path=None (not saved yet)."""
        pipeline = CaseGenerationPipeline(mock_config)
        result = pipeline.generate(minimal_seed)
        assert result.case_path is None


class TestGenerateAndSave:
    """pipeline.generate_and_save() convenience method."""

    def test_generate_and_save_returns_path(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        result = pipeline.generate_and_save(minimal_seed)
        assert result.success
        assert result.case_path is not None

    def test_generate_and_save_failure_returns_no_path(
        self, mock_config: ModelConfig, minimal_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        """If generation fails, generate_and_save returns the failure result (no path)."""
        from typing import Any

        from llm_client.interfaces import CaseGenerator
        from llm_client.interfaces import CaseSeed as LLMCaseSeed

        from anamnesis.result import GenerationResult

        class _AlwaysInvalidGen(CaseGenerator):
            def generate_case(self, seed: LLMCaseSeed) -> dict[str, Any]:
                return {}  # always invalid

        pipeline = CaseGenerationPipeline(mock_config, output_dir=tmp_path)
        pipeline._generator = _AlwaysInvalidGen()  # type: ignore[assignment]
        result = pipeline.generate_and_save(minimal_seed, max_retries=1)
        assert isinstance(result, GenerationResult)
        assert result.success is False
        assert result.case_path is None
        # Nothing written to disk
        assert list(tmp_path.glob("*.json")) == []


class TestPipelineDefaultOutputDir:
    """Pipeline uses cases/generated/ as the default output dir."""

    def test_default_output_dir_is_cases_generated(self, mock_config: ModelConfig) -> None:
        """Default output_dir resolves to Path('cases/generated')."""
        from pathlib import Path

        pipeline = CaseGenerationPipeline(mock_config)
        assert pipeline._output_dir == Path("cases/generated")
