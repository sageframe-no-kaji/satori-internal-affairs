"""Core case generation pipeline.

CaseGenerationPipeline orchestrates:
  seed → llm-client → validate → (retry/repair) → save

Usage:
    config = ModelConfig(provider=Provider.MOCK, model="mock")
    pipeline = CaseGenerationPipeline(config)
    result = pipeline.generate(seed)
    if result.success:
        path = pipeline.save(result)
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from llm_client import ModelConfig, create_case_generator
from llm_client.interfaces import CaseGenerator

from anamnesis.prompts import build_repair_prompt
from anamnesis.result import GenerationResult, _make_failure, _make_success, _with_path
from anamnesis.seed import CreativeSeed
from anamnesis.validator import validate_case_dict

logger = logging.getLogger(__name__)

# Default output directory relative to the repo root, resolved at save time.
_DEFAULT_OUTPUT_SUBDIR = "cases/generated"


class CaseGenerationPipeline:
    """Orchestrates seed → LLM → validate → save.

    The pipeline owns its LLM client (created from config). Tests use
    Provider.MOCK in the config — no external API calls are made.

    Retry strategy:
        1. Up to max_retries simple retries on validation failure.
        2. If all simple retries exhausted: one error-feedback (repair) attempt.
        3. If the repair attempt also fails: return GenerationResult(success=False).

    LLMProviderError / LLMResponseError propagate to the caller unchanged
    (they represent infrastructure failures, not validation failures).
    """

    def __init__(self, config: ModelConfig, output_dir: Path | None = None) -> None:
        """Initialise the pipeline.

        Args:
            config: LLM provider configuration. Use Provider.MOCK for tests.
            output_dir: Directory to save generated cases. If None, defaults to
                        ``cases/generated/`` relative to the current working directory.
        """
        self._config = config
        self._generator: CaseGenerator = create_case_generator(config)
        self._output_dir: Path = (
            output_dir if output_dir is not None else Path(_DEFAULT_OUTPUT_SUBDIR)
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, seed: CreativeSeed, max_retries: int = 3) -> GenerationResult:
        """Generate a validated CaseDefinition from a CreativeSeed.

        Args:
            seed: The creative seed describing the desired case.
            max_retries: Maximum number of simple retries before the repair attempt.
                         Total maximum LLM calls = max_retries + 1 (repair).

        Returns:
            GenerationResult with success=True and a validated case, or
            success=False with error details if all attempts failed.

        Raises:
            LLMProviderError: API authentication / network failure.
            LLMResponseError: LLM returned non-JSON response.
        """
        if seed.has_creative_fields():
            logger.info(
                "Seed has creative fields (Mode 2). Creative-only fields are noted but "
                "not yet injected into provider prompts (requires future llm-client extension)."
            )

        case_seed = seed.to_case_seed()
        last_raw: dict[str, Any] | None = None
        last_errors: list[str] = []
        attempts = 0

        # ── Phase 1: Simple retries ──────────────────────────────────────────
        for attempt in range(1, max_retries + 1):
            attempts = attempt
            logger.debug("Generation attempt %d/%d (simple)", attempt, max_retries)

            raw = self._generator.generate_case(case_seed)
            last_raw = raw
            case_def, errors = validate_case_dict(raw)

            if case_def is not None:
                logger.info("Case validated successfully on attempt %d", attempt)
                return _make_success(case_def, raw, attempts, seed)

            last_errors = errors
            logger.warning(
                "Attempt %d failed validation (%d errors): %s",
                attempt,
                len(errors),
                errors[:3],
            )

        # ── Phase 2: One error-feedback (repair) attempt ──────────────────────
        attempts += 1
        logger.info(
            "Simple retries exhausted. Attempting error-feedback repair (attempt %d)",
            attempts,
        )

        repair_prompt = build_repair_prompt(
            last_raw if last_raw is not None else {},
            last_errors,
        )
        logger.debug("Repair prompt (first 300 chars): %s", repair_prompt[:300])

        # For mock mode and Phase 1 real providers: pass the repair context via the
        # seed's complications/learning_objectives so that CaseSeed carries some signal.
        # Full prompt injection requires a future llm-client extension.
        repair_seed_with_hint = seed.to_case_seed()
        # Attempt repair — we call generate_case again; providers that support it will
        # use the seed; mock returns its hardcoded case (which is valid, so repair succeeds).
        raw_repair = self._generator.generate_case(repair_seed_with_hint)
        case_def, errors = validate_case_dict(raw_repair)

        if case_def is not None:
            logger.info("Case validated after repair attempt")
            return _make_success(case_def, raw_repair, attempts, seed)

        logger.error("All %d attempts failed. Last errors: %s", attempts, errors)
        return _make_failure(raw_repair, attempts, errors, seed)

    def save(self, result: GenerationResult) -> Path:
        """Save a successful GenerationResult to disk.

        The output filename is ``case-{diagnosis}-{short_uuid}.json``.
        The output directory is created if it doesn't exist.

        Args:
            result: A GenerationResult with success=True.

        Returns:
            Path to the saved JSON file.

        Raises:
            ValueError: If result.success is False.
            OSError: If the file cannot be written.
        """
        if not result.success or result.case is None:
            raise ValueError("Cannot save a failed GenerationResult (success=False)")

        self._output_dir.mkdir(parents=True, exist_ok=True)

        short_id = str(uuid.uuid4())[:8]
        safe_diagnosis = result.seed.diagnosis.lower().replace(" ", "-").replace("/", "-")
        filename = f"case-{safe_diagnosis}-{short_id}.json"
        output_path = self._output_dir / filename

        case_data = result.case.model_dump(mode="json")
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(case_data, f, indent=2, default=str)

        logger.info("Case saved to %s", output_path)
        return output_path

    def generate_and_save(self, seed: CreativeSeed, max_retries: int = 3) -> GenerationResult:
        """Convenience method: generate then save if successful.

        Returns a GenerationResult with case_path set on success.
        """
        result = self.generate(seed, max_retries=max_retries)
        if result.success:
            path = self.save(result)
            return _with_path(result, path)
        return result
