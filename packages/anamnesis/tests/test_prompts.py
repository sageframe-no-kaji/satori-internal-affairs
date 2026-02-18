"""Tests for anamnesis.prompts — build_creative_prompt and build_repair_prompt."""

from anamnesis.prompts import build_creative_prompt, build_repair_prompt
from anamnesis.seed import CreativeSeed


class TestBuildCreativePrompt:
    """build_creative_prompt() produces correctly structured prompts."""

    def test_minimal_seed_contains_required_fields(self, minimal_seed: CreativeSeed) -> None:
        """Prompt includes all required seed field values."""
        prompt = build_creative_prompt(minimal_seed)
        assert "pneumothorax" in prompt
        assert "beginner" in prompt
        assert "clinical" in prompt

    def test_creative_fields_appear_in_prompt(self, rich_seed: CreativeSeed) -> None:
        """Mode 2 creative fields are embedded in the prompt."""
        prompt = build_creative_prompt(rich_seed)
        assert rich_seed.dramatic_hook is not None
        assert rich_seed.dramatic_hook[:20] in prompt
        assert "Red herrings" in prompt or "red herring" in prompt.lower()
        assert "character" in prompt.lower() or (
            rich_seed.character_notes is not None
            and rich_seed.character_notes[:20] in prompt
        )
        assert rich_seed.emotional_core is not None
        assert rich_seed.emotional_core[:20] in prompt

    def test_forbidden_tropes_noted(self, rich_seed: CreativeSeed) -> None:
        """Forbidden tropes section appears for Mode 2 seeds."""
        prompt = build_creative_prompt(rich_seed)
        assert "Forbidden" in prompt or "forbidden" in prompt
        assert rich_seed.forbidden_tropes is not None
        assert rich_seed.forbidden_tropes[0][:15] in prompt

    def test_structural_constraints_always_present(self, minimal_seed: CreativeSeed) -> None:
        """Structural constraints reminder is always included."""
        prompt = build_creative_prompt(minimal_seed)
        assert "node" in prompt.lower()
        assert "sorted" in prompt.lower() or "ascending" in prompt.lower()
        assert "JSON" in prompt

    def test_creative_section_absent_for_minimal_seed(self, minimal_seed: CreativeSeed) -> None:
        """Creative Direction section is omitted when no creative fields are set."""
        prompt = build_creative_prompt(minimal_seed)
        # Should have Medical Requirements and Structural Constraints, but no creative block
        assert "Medical Requirements" in prompt
        assert "Structural Constraints" in prompt
        # "Creative Direction" section header only appears if there are creative fields
        assert "dramatic_hook" not in prompt

    def test_age_range_formatted_humanly(self) -> None:
        """patient_age_range is formatted as a readable range."""
        seed = CreativeSeed(
            diagnosis="X",
            difficulty="beginner",
            dramatic_tone="clinical",
            patient_age_range=(20, 40),
        )
        prompt = build_creative_prompt(seed)
        assert "20" in prompt and "40" in prompt

    def test_complications_and_objectives_listed(self, rich_seed: CreativeSeed) -> None:
        """Complications and learning objectives appear as lists."""
        prompt = build_creative_prompt(rich_seed)
        assert rich_seed.complications is not None
        assert "language barrier" in prompt.lower()
        assert rich_seed.learning_objectives is not None
        assert "focal" in prompt.lower() or "seizure" in prompt.lower()

    def test_returns_non_empty_string(self, minimal_seed: CreativeSeed) -> None:
        """Prompt is always a non-empty string."""
        prompt = build_creative_prompt(minimal_seed)
        assert isinstance(prompt, str)
        assert len(prompt) > 50


class TestBuildRepairPrompt:
    """build_repair_prompt() embeds errors and previous output."""

    def test_contains_error_messages(self) -> None:
        """Validation errors appear in the repair prompt."""
        errors = ["[schema] nodes: field required", "[structural] Duplicate node id: 'n1'"]
        prompt = build_repair_prompt({}, errors)
        assert "[schema] nodes: field required" in prompt
        assert "[structural] Duplicate node id: 'n1'" in prompt

    def test_contains_previous_output(self) -> None:
        """The previous (invalid) dict is embedded as JSON."""
        raw = {"id": "bad-uuid", "version": "1.0.0"}
        prompt = build_repair_prompt(raw, ["[schema] foo: required"])
        assert "bad-uuid" in prompt
        assert "1.0.0" in prompt

    def test_instructs_json_only_output(self) -> None:
        """Prompt instructs the LLM to return only JSON."""
        prompt = build_repair_prompt({}, ["error1"])
        assert "JSON" in prompt
        assert "only" in prompt.lower() or "ONLY" in prompt

    def test_errors_are_numbered(self) -> None:
        """Each error is numbered in the prompt."""
        errors = ["err1", "err2", "err3"]
        prompt = build_repair_prompt({}, errors)
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt

    def test_handles_empty_dict(self) -> None:
        """Prompt is valid even when previous output is an empty dict."""
        prompt = build_repair_prompt({}, ["field required"])
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_handles_empty_errors_list(self) -> None:
        """Prompt works even with an empty errors list (degenerate case)."""
        prompt = build_repair_prompt({"id": "x"}, [])
        assert isinstance(prompt, str)

    def test_unserializable_dict_falls_back_to_str(self) -> None:
        """build_repair_prompt falls back to str() when json.dumps raises."""

        class _Unserializable:
            pass

        bad: dict[str, object] = {"key": _Unserializable()}
        # Should not raise — falls back to str(bad)
        prompt = build_repair_prompt(bad, ["some error"])  # type: ignore[arg-type]
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestBuildCreativePromptOptionalFields:
    """Optional medical and creative fields appear correctly in the prompt."""

    def test_content_boundaries_in_prompt(self) -> None:
        """content_boundaries items are reflected in the generated prompt."""
        seed = CreativeSeed(
            diagnosis="test",
            difficulty="intermediate",
            dramatic_tone="clinical",
            content_boundaries=["no graphic violence", "no explicit language"],
        )
        prompt = build_creative_prompt(seed)
        assert "no graphic violence" in prompt

    def test_setting_and_sex_in_prompt(self) -> None:
        """setting and patient_sex appear in the medical requirements section."""
        seed = CreativeSeed(
            diagnosis="test",
            difficulty="intermediate",
            dramatic_tone="clinical",
            setting="ICU",
            patient_sex="male",
        )
        prompt = build_creative_prompt(seed)
        assert "ICU" in prompt
        assert "male" in prompt

    def test_key_twists_in_prompt(self) -> None:
        """key_twists appear in the creative direction section."""
        seed = CreativeSeed(
            diagnosis="test",
            difficulty="intermediate",
            dramatic_tone="clinical",
            key_twists=["First test was false negative"],
        )
        prompt = build_creative_prompt(seed)
        assert "First test was false negative" in prompt
