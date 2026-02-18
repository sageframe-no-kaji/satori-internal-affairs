"""Tests for anamnesis.seed — CreativeSeed and load_seed_file."""

import textwrap
from pathlib import Path

import pytest
import yaml
from llm_client import CaseSeed

from anamnesis.seed import CreativeSeed, load_seed_file


class TestCreativeSeedConstruction:
    """CreativeSeed can be built with required or all fields."""

    def test_minimal_required_fields(self) -> None:
        """CreativeSeed constructs with only the three required fields."""
        seed = CreativeSeed(
            diagnosis="pneumothorax",
            difficulty="beginner",
            dramatic_tone="clinical",
        )
        assert seed.diagnosis == "pneumothorax"
        assert seed.difficulty == "beginner"
        assert seed.dramatic_tone == "clinical"
        # All optional fields default to None
        assert seed.patient_age_range is None
        assert seed.dramatic_hook is None
        assert seed.red_herrings is None

    def test_all_fields_populated(self, rich_seed: CreativeSeed) -> None:
        """CreativeSeed constructs with all fields populated."""
        assert rich_seed.diagnosis == "neurocysticercosis"
        assert rich_seed.patient_age_range == (25, 35)
        assert rich_seed.dramatic_hook is not None
        assert rich_seed.red_herrings is not None
        assert len(rich_seed.red_herrings) == 2  # type: ignore[arg-type]
        assert rich_seed.key_twists is not None
        assert rich_seed.forbidden_tropes is not None

    def test_frozen_immutable(self, minimal_seed: CreativeSeed) -> None:
        """CreativeSeed is frozen — mutation raises FrozenInstanceError."""
        with pytest.raises(Exception):
            minimal_seed.diagnosis = "changed"  # type: ignore[misc]

    def test_has_creative_fields_false_for_minimal(self, minimal_seed: CreativeSeed) -> None:
        assert minimal_seed.has_creative_fields() is False

    def test_has_creative_fields_true_for_rich(self, rich_seed: CreativeSeed) -> None:
        assert rich_seed.has_creative_fields() is True


class TestToCaseSeed:
    """CreativeSeed.to_case_seed() produces correct CaseSeed."""

    def test_required_fields_transfer(self, minimal_seed: CreativeSeed) -> None:
        case_seed = minimal_seed.to_case_seed()
        assert isinstance(case_seed, CaseSeed)
        assert case_seed.diagnosis == minimal_seed.diagnosis
        assert case_seed.difficulty == minimal_seed.difficulty
        assert case_seed.dramatic_tone == minimal_seed.dramatic_tone

    def test_optional_medical_fields_transfer(self, rich_seed: CreativeSeed) -> None:
        case_seed = rich_seed.to_case_seed()
        assert case_seed.patient_age_range == (25, 35)
        assert case_seed.patient_sex == "female"
        assert case_seed.setting == "Emergency Department"
        assert case_seed.complications is not None
        assert "language barrier" in case_seed.complications[0]

    def test_creative_fields_absent_from_case_seed(self, rich_seed: CreativeSeed) -> None:
        """Creative-only fields must NOT appear in CaseSeed."""
        case_seed = rich_seed.to_case_seed()
        assert not hasattr(case_seed, "dramatic_hook")
        assert not hasattr(case_seed, "red_herrings")
        assert not hasattr(case_seed, "character_notes")
        assert not hasattr(case_seed, "narrative_inspiration")
        assert not hasattr(case_seed, "key_twists")
        assert not hasattr(case_seed, "emotional_core")
        assert not hasattr(case_seed, "forbidden_tropes")


class TestLoadSeedFile:
    """load_seed_file() loads YAML files into CreativeSeed."""

    def test_load_example_pneumothorax(self) -> None:
        """The shipped example-pneumothorax.yaml is loadable."""
        seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
        seed = load_seed_file(seeds_dir / "example-pneumothorax.yaml")
        assert seed.diagnosis == "pneumothorax"
        assert seed.difficulty == "beginner"
        assert seed.dramatic_tone == "clinical"
        assert seed.patient_age_range == (18, 35)

    def test_load_example_neurocysticercosis_rich(self) -> None:
        """The shipped rich example seed file is loadable."""
        seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
        seed = load_seed_file(seeds_dir / "example-neurocysticercosis-rich.yaml")
        assert seed.diagnosis == "neurocysticercosis"
        assert seed.has_creative_fields() is True
        assert seed.dramatic_hook is not None
        assert seed.red_herrings is not None
        assert len(seed.red_herrings) >= 2  # type: ignore[arg-type]
        assert seed.forbidden_tropes is not None

    def test_load_minimal_yaml(self, tmp_path: Path) -> None:
        """Minimal YAML with required fields only parses correctly."""
        yaml_content = textwrap.dedent("""\
            diagnosis: sepsis
            difficulty: advanced
            dramatic_tone: urgent
        """)
        p = tmp_path / "minimal.yaml"
        p.write_text(yaml_content)
        seed = load_seed_file(p)
        assert seed.diagnosis == "sepsis"
        assert seed.difficulty == "advanced"
        assert seed.dramatic_tone == "urgent"
        assert seed.has_creative_fields() is False

    def test_load_all_creative_fields(self, tmp_path: Path) -> None:
        """All creative fields parse into the correct CreativeSeed attributes."""
        data = {
            "diagnosis": "meningitis",
            "difficulty": "intermediate",
            "dramatic_tone": "medical_mystery",
            "dramatic_hook": "Patient collapses.",
            "red_herrings": ["headache", "stress"],
            "character_notes": "Quiet, reserved.",
            "narrative_inspiration": "House S3E08",
            "key_twists": ["CT was normal initially"],
            "emotional_core": "Fear of loss.",
            "forbidden_tropes": ["No stereotyping"],
        }
        p = tmp_path / "creative.yaml"
        p.write_text(yaml.dump(data))
        seed = load_seed_file(p)
        assert seed.dramatic_hook == "Patient collapses."
        assert seed.red_herrings == ["headache", "stress"]
        assert seed.character_notes == "Quiet, reserved."
        assert seed.narrative_inspiration == "House S3E08"
        assert seed.key_twists == ["CT was normal initially"]
        assert seed.emotional_core == "Fear of loss."
        assert seed.forbidden_tropes == ["No stereotyping"]

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        """ValueError is raised when a required field is missing."""
        p = tmp_path / "bad.yaml"
        p.write_text("difficulty: beginner\ndramatic_tone: clinical\n")
        with pytest.raises(ValueError, match="diagnosis"):
            load_seed_file(p)

    def test_all_required_fields_missing(self, tmp_path: Path) -> None:
        """ValueError lists all missing required fields."""
        p = tmp_path / "empty.yaml"
        p.write_text("setting: ICU\n")
        with pytest.raises(ValueError, match="missing required fields"):
            load_seed_file(p)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError):
            load_seed_file(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        """ValueError is raised for malformed YAML."""
        p = tmp_path / "malformed.yaml"
        p.write_text("diagnosis: [\nunot closed")
        with pytest.raises(ValueError, match="Failed to parse"):
            load_seed_file(p)

    def test_age_range_parses_correctly(self, tmp_path: Path) -> None:
        """patient_age_range list parses into a tuple of ints."""
        p = tmp_path / "age.yaml"
        p.write_text(
            "diagnosis: x\ndifficulty: beginner\ndramatic_tone: clinical\n"
            "patient_age_range: [20, 40]\n"
        )
        seed = load_seed_file(p)
        assert seed.patient_age_range == (20, 40)

    def test_invalid_age_range_raises(self, tmp_path: Path) -> None:
        """ValueError for a patient_age_range that isn't a two-element list."""
        p = tmp_path / "bad_age.yaml"
        p.write_text(
            "diagnosis: x\ndifficulty: beginner\ndramatic_tone: clinical\n"
            "patient_age_range: 30\n"
        )
        with pytest.raises(ValueError, match="patient_age_range"):
            load_seed_file(p)

    def test_non_dict_yaml_raises(self, tmp_path: Path) -> None:
        """ValueError when YAML root is not a mapping (e.g. a bare list)."""
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="mapping"):
            load_seed_file(p)

    def test_non_list_field_for_list_key_raises(self, tmp_path: Path) -> None:
        """ValueError when a list field (e.g. complications) is a scalar string."""
        p = tmp_path / "bad_list.yaml"
        p.write_text(
            "diagnosis: x\ndifficulty: beginner\ndramatic_tone: clinical\n"
            "complications: should-be-a-list\n"
        )
        with pytest.raises(ValueError, match="complications"):
            load_seed_file(p)

    def test_whitespace_only_string_opt_field_is_none(self, tmp_path: Path) -> None:
        """_opt_str returns None when the value is blank/whitespace."""
        p = tmp_path / "blank.yaml"
        p.write_text(
            "diagnosis: x\ndifficulty: beginner\ndramatic_tone: clinical\n"
            "setting: '   '\n"
        )
        seed = load_seed_file(p)
        assert seed.setting is None
