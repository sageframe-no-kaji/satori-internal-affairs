"""Tests for the Anamnesis CLI (__main__.py).

Tests use subprocess-style invocation via main() directly.
"""

import json
from pathlib import Path

from anamnesis.__main__ import main


class TestCLIMode1:
    """Mode 1: CLI flags (--diagnosis, --difficulty, --tone)."""

    def test_generate_mock_mode1(self) -> None:
        """Mode 1 with mock provider succeeds (exit code 0)."""
        exit_code = main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--difficulty", "beginner",
            "--tone", "clinical",
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 0

    def test_generate_with_defaults(self) -> None:
        """Omitting --difficulty and --tone uses their defaults."""
        exit_code = main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 0

    def test_missing_diagnosis_fails(self) -> None:
        """Missing --diagnosis (and no --seed-file) → exit code 1."""
        exit_code = main([
            "generate",
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 1

    def test_saves_to_custom_output_dir(self, tmp_path: Path) -> None:
        """--output-dir controls where the case is saved."""
        exit_code = main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--provider", "mock",
            "--output-dir", str(tmp_path),
        ])
        assert exit_code == 0
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1

    def test_no_save_flag_does_not_write(self, tmp_path: Path) -> None:
        """--no-save: case generated but no file written."""
        exit_code = main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--provider", "mock",
            "--no-save",
            "--output-dir", str(tmp_path),
        ])
        assert exit_code == 0
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 0


class TestCLIMode2:
    """Mode 2: YAML seed file (--seed-file)."""

    def test_seed_file_example_pneumothorax(self) -> None:
        """The shipped example-pneumothorax.yaml works with mock provider."""
        seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
        exit_code = main([
            "generate",
            "--seed-file", str(seeds_dir / "example-pneumothorax.yaml"),
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 0

    def test_seed_file_example_rich(self) -> None:
        """The shipped rich neurocysticercosis seed works with mock provider."""
        seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
        exit_code = main([
            "generate",
            "--seed-file", str(seeds_dir / "example-neurocysticercosis-rich.yaml"),
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 0

    def test_seed_file_saves_output(self, tmp_path: Path) -> None:
        """--seed-file with output-dir saves the case."""
        seeds_dir = Path(__file__).parent.parent.parent.parent / "seeds"
        exit_code = main([
            "generate",
            "--seed-file", str(seeds_dir / "example-pneumothorax.yaml"),
            "--provider", "mock",
            "--output-dir", str(tmp_path),
        ])
        assert exit_code == 0
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1

    def test_nonexistent_seed_file_fails(self) -> None:
        """Non-existent --seed-file → exit code 1."""
        exit_code = main([
            "generate",
            "--seed-file", "/tmp/does-not-exist-12345.yaml",
            "--provider", "mock",
            "--no-save",
        ])
        assert exit_code == 1


class TestCLISavedOutput:
    """Verify the saved case JSON is valid."""

    def test_saved_case_is_valid_json(self, tmp_path: Path) -> None:
        """Saved case file is valid JSON."""
        main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--provider", "mock",
            "--output-dir", str(tmp_path),
        ])
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1
        with saved[0].open() as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_saved_case_validates_as_case_definition(self, tmp_path: Path) -> None:
        """Saved case JSON validates as a CaseDefinition."""
        from satori.models import CaseDefinition

        main([
            "generate",
            "--diagnosis", "pneumothorax",
            "--provider", "mock",
            "--output-dir", str(tmp_path),
        ])
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1
        with saved[0].open() as f:
            data = json.load(f)
        case = CaseDefinition.model_validate(data)
        assert isinstance(case, CaseDefinition)
