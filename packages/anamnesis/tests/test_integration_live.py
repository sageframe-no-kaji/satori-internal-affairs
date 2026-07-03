"""Integration tests for the Anamnesis pipeline with live LLM providers.

These tests are skipped by default. They require a real API key in the
environment and make actual network calls.

Run with:
    pytest -m live_llm packages/anamnesis/tests/test_integration_live.py -v

Environment variables:
    OPENAI_API_KEY      — enables OpenAI tests
    ANTHROPIC_API_KEY   — enables Anthropic tests
    CASE_SCHEMA_PATH    — path to the case JSON schema (required for live tests)
"""

import json
import os
from pathlib import Path

import pytest
from llm_client import ModelConfig, Provider
from satori.models import CaseDefinition

from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.seed import CreativeSeed

# ── Pytest markers ────────────────────────────────────────────────────────────

pytestmark = pytest.mark.live_llm

_SCHEMA_PATH = os.environ.get(
    "CASE_SCHEMA_PATH",
    str(Path(__file__).parent.parent.parent.parent / "schemas" / "case-definition.schema.json"),
)


def _openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _anthropic_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.fixture
def simple_seed() -> CreativeSeed:
    return CreativeSeed(
        diagnosis="pneumothorax",
        difficulty="beginner",
        dramatic_tone="clinical",
        setting="Emergency Department",
    )


@pytest.fixture
def rich_seed() -> CreativeSeed:
    seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
    from anamnesis.seed import load_seed_file

    return load_seed_file(seeds_dir / "example-neurocysticercosis-rich.yaml")


# ── OpenAI tests ──────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _openai_available(), reason="OPENAI_API_KEY not set")
class TestOpenAIIntegration:
    """Live integration tests against OpenAI."""

    def test_openai_generates_valid_case(self, simple_seed: CreativeSeed, tmp_path: Path) -> None:
        """OpenAI pipeline generates a case that passes CaseDefinition validation."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config, output_dir=tmp_path)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        assert isinstance(result.case, CaseDefinition)

    def test_openai_case_has_sufficient_nodes(self, simple_seed: CreativeSeed) -> None:
        """Generated case has at least 3 nodes (not trivially minimal)."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        assert len(result.case.nodes) >= 3, f"Expected >= 3 nodes, got {len(result.case.nodes)}"

    def test_openai_generated_case_loads_in_engine(self, simple_seed: CreativeSeed) -> None:
        """Generated case loads in SatoriEngine without CaseValidationError."""
        from satori.engine import SatoriEngine  # only in integration tests

        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        # This would raise CaseValidationError if the engine rejects the case
        engine = SatoriEngine(result.case)
        assert engine is not None

    def test_openai_save_and_reload(self, simple_seed: CreativeSeed, tmp_path: Path) -> None:
        """Saved OpenAI-generated case can be reloaded and validated."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config, output_dir=tmp_path)
        result = pipeline.generate(simple_seed)
        assert result.success
        path = pipeline.save(result)

        with path.open() as f:
            reloaded = json.load(f)
        case = CaseDefinition.model_validate(reloaded)
        assert isinstance(case, CaseDefinition)


# ── Anthropic tests ───────────────────────────────────────────────────────────


@pytest.mark.skipif(not _anthropic_available(), reason="ANTHROPIC_API_KEY not set")
class TestAnthropicIntegration:
    """Live integration tests against Anthropic Claude."""

    def test_anthropic_generates_valid_case(
        self, simple_seed: CreativeSeed, tmp_path: Path
    ) -> None:
        """Anthropic pipeline generates a case that passes CaseDefinition validation."""
        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key=os.environ["ANTHROPIC_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config, output_dir=tmp_path)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        assert isinstance(result.case, CaseDefinition)

    def test_anthropic_case_has_sufficient_nodes(self, simple_seed: CreativeSeed) -> None:
        """Generated case has at least 3 nodes."""
        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key=os.environ["ANTHROPIC_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        assert len(result.case.nodes) >= 3

    def test_anthropic_generated_case_loads_in_engine(self, simple_seed: CreativeSeed) -> None:
        """Generated case loads in SatoriEngine without CaseValidationError."""
        from satori.engine import SatoriEngine  # only in integration tests

        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            api_key=os.environ["ANTHROPIC_API_KEY"],
            schema_path=_SCHEMA_PATH,
        )
        pipeline = CaseGenerationPipeline(config)
        result = pipeline.generate(simple_seed)

        assert result.success, f"Generation failed: {result.errors}"
        assert result.case is not None
        engine = SatoriEngine(result.case)
        assert engine is not None
