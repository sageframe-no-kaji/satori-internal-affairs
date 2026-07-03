"""Tests for CaseGenerationPipeline retry and repair logic.

Uses a custom fake generator to inject invalid responses and test the
retry strategy: simple retries → error-feedback repair → failure.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from llm_client import ModelConfig, Provider
from llm_client.interfaces import CaseGenerator, CaseSeed

from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.seed import CreativeSeed

# ── Fake generator helpers ────────────────────────────────────────────────────


def _load_valid_dict() -> dict[str, Any]:
    """Load the canonical example case as a valid dict."""
    repo_root = Path(__file__).parent.parent.parent.parent
    with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
        return json.load(f)  # type: ignore[no-any-return]


class _CountingGenerator(CaseGenerator):
    """Returns a sequence of dicts (cycling on the last one). Counts calls."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.call_count = 0

    def generate_case(self, seed: CaseSeed) -> dict[str, Any]:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]


def _pipeline_with_generator(
    generator: CaseGenerator,
    output_dir: Path | None = None,
) -> CaseGenerationPipeline:
    """Build a pipeline patching its internal generator."""
    config = ModelConfig(provider=Provider.MOCK, model="mock")
    pipeline = CaseGenerationPipeline(config, output_dir=output_dir)
    pipeline._generator = generator  # type: ignore[assignment]
    return pipeline


@pytest.fixture
def minimal_seed() -> CreativeSeed:
    return CreativeSeed(diagnosis="pneumothorax", difficulty="beginner", dramatic_tone="clinical")


@pytest.fixture
def valid_dict() -> dict[str, Any]:
    return _load_valid_dict()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestSimpleRetries:
    """Pipeline retries simple calls before attempting repair."""

    def test_succeeds_on_second_attempt(
        self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]
    ) -> None:
        """Pipeline retries and succeeds on attempt 2."""
        gen = _CountingGenerator([{}, valid_dict])  # first invalid, second valid
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=3)
        assert result.success is True
        assert gen.call_count == 2
        assert result.attempts == 2

    def test_succeeds_on_last_simple_retry(
        self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]
    ) -> None:
        """Pipeline succeeds on the max_retries-th attempt."""
        invalid = [{}] * 2 + [valid_dict]
        gen = _CountingGenerator(invalid)
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=3)
        assert result.success is True
        assert result.attempts == 3

    def test_attempts_reflects_actual_calls(
        self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]
    ) -> None:
        """result.attempts == the actual number of LLM calls made."""
        gen = _CountingGenerator([{}, {}, valid_dict])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=3)
        assert result.attempts == gen.call_count


class TestRepairAttempt:
    """Pipeline escalates to error-feedback repair after simple retries."""

    def test_repair_attempt_after_exhausted_retries(
        self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]
    ) -> None:
        """After max_retries failures, one repair attempt is made."""
        max_retries = 3
        # First 3 invalid (simple retries), 4th valid (repair)
        invalid = [{}] * max_retries + [valid_dict]
        gen = _CountingGenerator(invalid)
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=max_retries)
        assert result.success is True
        # Repair attempt is attempt max_retries + 1
        assert result.attempts == max_retries + 1
        assert gen.call_count == max_retries + 1

    def test_repair_attempt_counted_in_attempts(self, minimal_seed: CreativeSeed) -> None:
        """When repair also fails, attempts reflects all calls including repair."""
        max_retries = 2
        gen = _CountingGenerator([{}])  # always returns invalid
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=max_retries)
        # max_retries simple + 1 repair
        assert result.attempts == max_retries + 1
        assert gen.call_count == max_retries + 1


class TestAllAttemptsFail:
    """Pipeline returns failure result when all attempts exhaust."""

    def test_failure_result_when_all_fail(self, minimal_seed: CreativeSeed) -> None:
        """success=False when all retries and repair fail."""
        gen = _CountingGenerator([{}])  # always invalid
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=3)
        assert result.success is False
        assert result.case is None

    def test_failure_result_has_errors(self, minimal_seed: CreativeSeed) -> None:
        """Failure result contains validation error messages."""
        gen = _CountingGenerator([{}])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=1)
        assert len(result.errors) > 0

    def test_failure_result_has_raw_dict(self, minimal_seed: CreativeSeed) -> None:
        """Failure result preserves the last raw dict from the LLM."""
        bad = {"partial": "output"}
        gen = _CountingGenerator([bad])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=1)
        assert result.raw_dict is not None

    def test_failure_result_attempts_equals_max_plus_one(self, minimal_seed: CreativeSeed) -> None:
        """Failure result: attempts == max_retries + 1 (repair included)."""
        gen = _CountingGenerator([{}])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=2)
        assert result.attempts == 3  # 2 simple + 1 repair


class TestCustomMaxRetries:
    """max_retries parameter controls retry behaviour."""

    def test_max_retries_zero_makes_one_simple_attempt(
        self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]
    ) -> None:
        """max_retries=0 means try once then repair."""
        gen = _CountingGenerator([valid_dict])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=0)
        # With max_retries=0 the loop doesn't run simple retries at all;
        # goes straight to repair (which also calls generate_case). But
        # actually with max_retries=0, the for loop range(1,1) is empty,
        # so repair runs immediately. Repair returns valid_dict → success.
        assert result.success is True

    def test_max_retries_one(self, minimal_seed: CreativeSeed, valid_dict: dict[str, Any]) -> None:
        """max_retries=1: one simple retry + one repair."""
        gen = _CountingGenerator([{}, valid_dict])
        pipeline = _pipeline_with_generator(gen)
        result = pipeline.generate(minimal_seed, max_retries=1)
        assert result.success is True
        assert result.attempts == 2
