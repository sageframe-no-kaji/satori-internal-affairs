"""Generation result type for the Anamnesis pipeline.

GenerationResult is returned by CaseGenerationPipeline.generate().
Callers inspect result.success rather than catching exceptions.
"""

from dataclasses import dataclass
from pathlib import Path

from satori.models import CaseDefinition

from anamnesis.seed import CreativeSeed


@dataclass(frozen=True)
class GenerationResult:
    """Result of a case generation attempt.

    Attributes:
        success: True if a valid CaseDefinition was produced.
        case: Validated case definition, or None if failed.
        raw_dict: Raw dict returned by the LLM (even if invalid).
        case_path: Path the case was saved to, or None if not saved.
        attempts: Total number of LLM calls made (1 = success on first try).
        errors: Validation error messages from the final failed attempt.
        seed: The CreativeSeed that was used for generation.
    """

    success: bool
    case: CaseDefinition | None
    raw_dict: dict[str, object] | None
    case_path: Path | None
    attempts: int
    errors: list[str]
    seed: CreativeSeed

    def __post_init__(self) -> None:
        """Enforce consistency invariants."""
        if self.success and self.case is None:
            raise ValueError("GenerationResult.success is True but case is None")
        if not self.success and self.case is not None:
            raise ValueError("GenerationResult.success is False but case is not None")
        if self.attempts < 1:
            raise ValueError(f"attempts must be >= 1, got {self.attempts}")


def _make_success(
    case: CaseDefinition,
    raw_dict: dict[str, object],
    attempts: int,
    seed: CreativeSeed,
) -> GenerationResult:
    """Convenience constructor for a successful result (not saved yet)."""
    return GenerationResult(
        success=True,
        case=case,
        raw_dict=raw_dict,
        case_path=None,
        attempts=attempts,
        errors=[],
        seed=seed,
    )


def _make_failure(
    raw_dict: dict[str, object] | None,
    attempts: int,
    errors: list[str],
    seed: CreativeSeed,
) -> GenerationResult:
    """Convenience constructor for a failed result."""
    return GenerationResult(
        success=False,
        case=None,
        raw_dict=raw_dict,
        case_path=None,
        attempts=attempts,
        errors=errors,
        seed=seed,
    )


def _with_path(result: GenerationResult, path: Path) -> GenerationResult:
    """Return a copy of a successful result with case_path set."""
    return GenerationResult(
        success=result.success,
        case=result.case,
        raw_dict=result.raw_dict,
        case_path=path,
        attempts=result.attempts,
        errors=result.errors,
        seed=result.seed,
    )
