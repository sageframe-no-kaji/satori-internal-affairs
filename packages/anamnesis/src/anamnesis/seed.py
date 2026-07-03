"""Creative seed models and YAML loader for case generation.

Provides CreativeSeed (Mode 2 rich creative brief) and load_seed_file().
Creative fields are prompt context only — they never appear in output case JSON.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from llm_client import CaseSeed


@dataclass(frozen=True)
class CreativeSeed:
    """Extended seed with narrative direction fields.

    Contains all CaseSeed fields plus creative fields that guide
    the LLM's narrative output. Creative fields are prompt context
    only — they never appear in the output case JSON.

    Mode 1 (Automated): Construct with just diagnosis, difficulty, dramatic_tone.
    Mode 2 (Creative): Add creative fields for rich narrative direction.
    """

    # === CaseSeed fields (required) ===
    diagnosis: str
    difficulty: str
    dramatic_tone: str

    # === CaseSeed fields (optional) ===
    patient_age_range: tuple[int, int] | None = None
    patient_sex: str | None = None
    setting: str | None = None
    complications: list[str] | None = None
    learning_objectives: list[str] | None = None
    content_boundaries: list[str] | None = None

    # === Creative fields (Mode 2 — all optional) ===
    dramatic_hook: str | None = None  # Opening scene / first impression
    red_herrings: list[str] | None = None  # Misleading clues to embed
    character_notes: str | None = None  # Personality, backstory, relationships
    narrative_inspiration: str | None = None  # Free text reference ("House S2E13")
    key_twists: list[str] | None = None  # Dramatic turns in the case
    emotional_core: str | None = None  # The human story beyond the medicine
    forbidden_tropes: list[str] | None = None  # Things to avoid in generation

    def to_case_seed(self) -> CaseSeed:
        """Extract the llm-client CaseSeed subset.

        Returns a CaseSeed containing only the fields the CaseGenerator
        interface understands. Creative-only fields are dropped here.
        """
        return CaseSeed(
            diagnosis=self.diagnosis,
            difficulty=self.difficulty,
            dramatic_tone=self.dramatic_tone,
            patient_age_range=self.patient_age_range,
            patient_sex=self.patient_sex,
            setting=self.setting,
            complications=self.complications,
            learning_objectives=self.learning_objectives,
            content_boundaries=self.content_boundaries,
        )

    def has_creative_fields(self) -> bool:
        """Return True if any Mode 2 creative fields are set."""
        return any(
            f is not None
            for f in (
                self.dramatic_hook,
                self.red_herrings,
                self.character_notes,
                self.narrative_inspiration,
                self.key_twists,
                self.emotional_core,
                self.forbidden_tropes,
            )
        )


def load_seed_file(path: Path) -> CreativeSeed:
    """Load a YAML seed file and return a CreativeSeed.

    Args:
        path: Path to the YAML seed file.

    Returns:
        CreativeSeed populated from the YAML file.

    Raises:
        ValueError: If required fields (diagnosis, difficulty, dramatic_tone) are missing,
                    if the file cannot be read, or if the YAML is malformed.
        FileNotFoundError: If the path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    try:
        with path.open(encoding="utf-8") as f:
            raw: Any = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML seed file {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ValueError(f"Seed file must be a YAML mapping, got {type(raw).__name__}: {path}")

    data: dict[str, Any] = raw

    # Validate required fields
    missing = [field for field in ("diagnosis", "difficulty", "dramatic_tone") if field not in data]
    if missing:
        raise ValueError(f"Seed file {path} is missing required fields: {', '.join(missing)}")

    # Validate types of required fields
    for field in ("diagnosis", "difficulty", "dramatic_tone"):
        if not isinstance(data[field], str):
            raise ValueError(
                f"Seed field '{field}' must be a string, got {type(data[field]).__name__}"
            )

    # Parse patient_age_range
    patient_age_range: tuple[int, int] | None = None
    if "patient_age_range" in data:
        raw_range = data["patient_age_range"]
        if isinstance(raw_range, (list, tuple)) and len(raw_range) == 2:  # noqa: UP006
            patient_age_range = (int(raw_range[0]), int(raw_range[1]))
        else:
            raise ValueError(
                f"patient_age_range must be a list of two integers, got: {raw_range!r}"
            )

    return CreativeSeed(
        diagnosis=data["diagnosis"],
        difficulty=data["difficulty"],
        dramatic_tone=data["dramatic_tone"],
        patient_age_range=patient_age_range,
        patient_sex=_opt_str(data, "patient_sex"),
        setting=_opt_str(data, "setting"),
        complications=_opt_str_list(data, "complications"),
        learning_objectives=_opt_str_list(data, "learning_objectives"),
        content_boundaries=_opt_str_list(data, "content_boundaries"),
        dramatic_hook=_opt_str(data, "dramatic_hook"),
        red_herrings=_opt_str_list(data, "red_herrings"),
        character_notes=_opt_str(data, "character_notes"),
        narrative_inspiration=_opt_str(data, "narrative_inspiration"),
        key_twists=_opt_str_list(data, "key_twists"),
        emotional_core=_opt_str(data, "emotional_core"),
        forbidden_tropes=_opt_str_list(data, "forbidden_tropes"),
    )


def _opt_str(data: dict[str, Any], key: str) -> str | None:
    """Return string value or None if key absent/null."""
    val = data.get(key)
    if val is None:
        return None
    return str(val).strip() or None


def _opt_str_list(data: dict[str, Any], key: str) -> list[str] | None:
    """Return list of strings or None if key absent/null."""
    val = data.get(key)
    if val is None:
        return None
    if not isinstance(val, list):  # noqa: UP006
        raise ValueError(f"Field '{key}' must be a list, got {type(val).__name__}")
    return [str(item) for item in val]
