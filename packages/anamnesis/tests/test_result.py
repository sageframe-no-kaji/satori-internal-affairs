"""Tests for anamnesis.result — GenerationResult."""

from pathlib import Path

import pytest

from anamnesis.result import GenerationResult, _make_failure, _make_success, _with_path
from anamnesis.seed import CreativeSeed


@pytest.fixture
def minimal_seed() -> CreativeSeed:
    return CreativeSeed(diagnosis="test", difficulty="beginner", dramatic_tone="clinical")


class TestGenerationResultConstruction:
    """GenerationResult enforces its invariants."""

    def test_success_true_requires_case(self, minimal_seed: CreativeSeed) -> None:
        """success=True with case=None raises ValueError."""
        with pytest.raises(ValueError, match="success is True but case is None"):
            GenerationResult(
                success=True,
                case=None,
                raw_dict=None,
                case_path=None,
                attempts=1,
                errors=[],
                seed=minimal_seed,
            )

    def test_success_false_requires_no_case(self, minimal_seed: CreativeSeed) -> None:
        """success=False with a case object raises ValueError."""
        import json

        from satori.models import CaseDefinition

        # Load a real case to have a CaseDefinition instance
        repo_root = Path(__file__).parent.parent.parent.parent
        with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
            data = json.load(f)
        case = CaseDefinition.model_validate(data)

        with pytest.raises(ValueError, match="success is False but case is not None"):
            GenerationResult(
                success=False,
                case=case,
                raw_dict=None,
                case_path=None,
                attempts=1,
                errors=["some error"],
                seed=minimal_seed,
            )

    def test_attempts_must_be_at_least_one(self, minimal_seed: CreativeSeed) -> None:
        """attempts=0 raises ValueError."""
        with pytest.raises(ValueError, match="attempts must be >= 1"):
            GenerationResult(
                success=False,
                case=None,
                raw_dict=None,
                case_path=None,
                attempts=0,
                errors=["e"],
                seed=minimal_seed,
            )

    def test_frozen(self, minimal_seed: CreativeSeed) -> None:
        """GenerationResult is frozen — mutation raises."""
        result = GenerationResult(
            success=False,
            case=None,
            raw_dict=None,
            case_path=None,
            attempts=1,
            errors=["e"],
            seed=minimal_seed,
        )
        with pytest.raises(Exception):
            result.success = True  # type: ignore[misc]


class TestHelpers:
    """_make_success, _make_failure, _with_path helpers."""

    def test_make_success(self, minimal_seed: CreativeSeed) -> None:
        """_make_success produces a valid, unsaved, successful result."""
        import json

        repo_root = Path(__file__).parent.parent.parent.parent
        with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
            data = json.load(f)
        from satori.models import CaseDefinition

        case = CaseDefinition.model_validate(data)
        result = _make_success(case, data, 2, minimal_seed)
        assert result.success is True
        assert result.case is case
        assert result.raw_dict is data
        assert result.case_path is None
        assert result.attempts == 2
        assert result.errors == []
        assert result.seed is minimal_seed

    def test_make_failure(self, minimal_seed: CreativeSeed) -> None:
        result = _make_failure({"bad": "dict"}, 3, ["err1", "err2"], minimal_seed)
        assert result.success is False
        assert result.case is None
        assert result.attempts == 3
        assert result.errors == ["err1", "err2"]
        assert result.case_path is None
        assert result.seed is minimal_seed

    def test_make_failure_with_none_raw_dict(self, minimal_seed: CreativeSeed) -> None:
        """_make_failure accepts None for raw_dict."""
        result = _make_failure(None, 1, ["err"], minimal_seed)
        assert result.raw_dict is None
        assert result.success is False

    def test_with_path(self, minimal_seed: CreativeSeed) -> None:
        """_with_path creates a copy with case_path set."""
        import json

        repo_root = Path(__file__).parent.parent.parent.parent
        with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
            data = json.load(f)
        from satori.models import CaseDefinition

        case = CaseDefinition.model_validate(data)
        original = _make_success(case, data, 1, minimal_seed)
        assert original.case_path is None
        updated = _with_path(original, Path("/tmp/test.json"))
        assert updated.case_path == Path("/tmp/test.json")
        # Original unchanged
        assert original.case_path is None
