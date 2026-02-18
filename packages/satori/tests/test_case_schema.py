"""Tests for case schema validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from satori.models import CaseDefinition, validate_case

# Path to example case
# From packages/satori/tests/ we go up to packages/, then up to root, then into cases/
EXAMPLE_CASE_PATH = Path(__file__).parent.parent.parent.parent / "cases" / "example-neurocysticercosis.json"


def test_example_case_loads() -> None:
    """Test that the example case loads successfully."""
    assert EXAMPLE_CASE_PATH.exists(), f"Example case not found at {EXAMPLE_CASE_PATH}"

    case = validate_case(EXAMPLE_CASE_PATH)
    assert isinstance(case, CaseDefinition)
    assert case.patient.name == "Maria Santos"
    assert case.ground_truth.diagnosis == "Neurocysticercosis (Taenia solium larvae in brain parenchyma)"


def test_example_case_has_unique_node_ids() -> None:
    """Test that all node IDs in the example case are unique."""
    case = validate_case(EXAMPLE_CASE_PATH)

    node_ids = [node.id for node in case.nodes]
    assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs found"


def test_flag_references_are_valid() -> None:
    """Test that all flag references in conditions and effects point to flags that are actually set."""
    case = validate_case(EXAMPLE_CASE_PATH)

    # Collect all flags that are set by any effect
    set_flags: set[str] = set()

    for node in case.nodes:
        # Check activation effects
        if node.activation.on_activate:
            for effect in node.activation.on_activate:
                if effect.type.value == "set_flag":
                    set_flags.add(effect.target)

        # Check reveal effects
        if node.effects and node.effects.on_reveal:
            for effect in node.effects.on_reveal:
                if effect.type.value == "set_flag":
                    set_flags.add(effect.target)

        # Check expire effects
        if node.effects and node.effects.on_expire:
            for effect in node.effects.on_expire:
                if effect.type.value == "set_flag":
                    set_flags.add(effect.target)

        # Check timer expire effects
        if node.timer and node.timer.on_expire:
            for effect in node.timer.on_expire:
                if effect.type.value == "set_flag":
                    set_flags.add(effect.target)

        # Check timer stage effects
        if node.timer and node.timer.stages:
            for stage in node.timer.stages:
                for effect in stage.effects:
                    if effect.type.value == "set_flag":
                        set_flags.add(effect.target)

        # Check intervention effects
        if node.effects and node.effects.on_intervene:
            for effect in node.effects.on_intervene.effects:
                if effect.type.value == "set_flag":
                    set_flags.add(effect.target)

    # Collect all flags that are referenced in conditions
    referenced_flags: set[str] = set()

    for node in case.nodes:
        # Check activation conditions
        if node.activation.paths:
            for path in node.activation.paths:
                for condition in path.conditions:
                    if condition.type.value in ("flag_set", "flag_not_set"):
                        referenced_flags.add(condition.target)

        # Check reveal conditions
        if node.reveal and node.reveal.conditions:
            for condition in node.reveal.conditions:
                if condition.type.value in ("flag_set", "flag_not_set"):
                    referenced_flags.add(condition.target)

        # Check timer pause conditions
        if node.timer and node.timer.pause_conditions:
            for condition in node.timer.pause_conditions:
                if condition.type.value in ("flag_set", "flag_not_set"):
                    referenced_flags.add(condition.target)

    # Check outcome evaluation flags
    for tier in case.outcome_evaluation.tiers:
        if tier.required_flags:
            referenced_flags.update(tier.required_flags)
        if tier.excluded_flags:
            referenced_flags.update(tier.excluded_flags)

    # Check that all referenced flags are set somewhere
    # Note: Some flags like "case_start" might be implicit system flags
    unset_flags = referenced_flags - set_flags
    # Filter out known system/implicit flags
    system_flags = {"case_start"}
    problematic_flags = unset_flags - system_flags

    assert not problematic_flags, f"Flags referenced but never set: {problematic_flags}"


def test_node_references_are_valid() -> None:
    """Test that all node ID references in conditions and effects point to nodes that exist."""
    case = validate_case(EXAMPLE_CASE_PATH)

    # Collect all node IDs
    node_ids = {node.id for node in case.nodes}

    # Collect all node references
    referenced_nodes: set[str] = set()

    for node in case.nodes:
        # Check activation conditions
        if node.activation.paths:
            for path in node.activation.paths:
                for condition in path.conditions:
                    if condition.type.value in ("node_active", "node_revealed", "node_expired"):
                        referenced_nodes.add(condition.target)

        # Check reveal conditions
        if node.reveal and node.reveal.conditions:
            for condition in node.reveal.conditions:
                if condition.type.value in ("node_active", "node_revealed", "node_expired"):
                    referenced_nodes.add(condition.target)

        # Check timer pause conditions
        if node.timer and node.timer.pause_conditions:
            for condition in node.timer.pause_conditions:
                if condition.type.value in ("node_active", "node_revealed", "node_expired"):
                    referenced_nodes.add(condition.target)

        # Check effects that reference nodes
        all_effects = []

        if node.activation.on_activate:
            all_effects.extend(node.activation.on_activate)

        if node.effects:
            if node.effects.on_reveal:
                all_effects.extend(node.effects.on_reveal)
            if node.effects.on_expire:
                all_effects.extend(node.effects.on_expire)
            if node.effects.on_intervene:
                all_effects.extend(node.effects.on_intervene.effects)

        if node.timer:
            if node.timer.on_expire:
                all_effects.extend(node.timer.on_expire)
            if node.timer.stages:
                for stage in node.timer.stages:
                    all_effects.extend(stage.effects)

        for effect in all_effects:
            if effect.type.value in ("activate_node", "deactivate_node", "modify_timer"):
                referenced_nodes.add(effect.target)

    # Check that all referenced nodes exist
    missing_nodes = referenced_nodes - node_ids
    assert not missing_nodes, f"Nodes referenced but don't exist: {missing_nodes}"


def test_at_least_one_node_starts_active() -> None:
    """Test that at least one node has starts_active=True."""
    case = validate_case(EXAMPLE_CASE_PATH)

    active_nodes = [node for node in case.nodes if node.activation.starts_active]
    assert len(active_nodes) > 0, "No nodes are marked as starting active"


def test_at_least_one_end_condition_exists() -> None:
    """Test that at least one end condition exists."""
    case = validate_case(EXAMPLE_CASE_PATH)

    assert len(case.outcome_evaluation.end_conditions) > 0, "No end conditions defined"


def test_case_has_required_metadata() -> None:
    """Test that case has all required metadata."""
    case = validate_case(EXAMPLE_CASE_PATH)

    assert case.metadata.difficulty
    assert case.metadata.estimated_duration_minutes > 0
    assert case.metadata.simulated_duration_minutes > 0
    assert len(case.metadata.learning_objectives) > 0
    assert case.metadata.dramatic_tone


def test_case_has_ground_truth() -> None:
    """Test that case has complete ground truth information."""
    case = validate_case(EXAMPLE_CASE_PATH)

    assert case.ground_truth.diagnosis
    assert len(case.ground_truth.differential) > 0
    assert case.ground_truth.mechanism
    assert case.ground_truth.key_insight
    assert len(case.ground_truth.optimal_path) > 0


def test_patient_has_baseline_vitals() -> None:
    """Test that patient has baseline vital signs."""
    case = validate_case(EXAMPLE_CASE_PATH)

    vitals = case.patient.arriving_vitals
    # At least one vital should be set
    vital_set = any(
        [
            vitals.heart_rate is not None,
            vitals.blood_pressure_systolic is not None,
            vitals.blood_pressure_diastolic is not None,
            vitals.temperature is not None,
            vitals.respiratory_rate is not None,
            vitals.o2_saturation is not None,
        ]
    )
    assert vital_set, "No baseline vitals are set"


def test_outcome_tiers_defined() -> None:
    """Test that outcome tiers are properly defined."""
    case = validate_case(EXAMPLE_CASE_PATH)

    assert len(case.outcome_evaluation.tiers) > 0

    # Should have at least optimal and failure tiers
    tier_levels = {tier.tier.value for tier in case.outcome_evaluation.tiers}
    assert "optimal" in tier_levels or "good" in tier_levels, "No positive outcome tier defined"
    assert "failure" in tier_levels, "No failure tier defined"


def test_invalid_json_raises_error(tmp_path: Path) -> None:
    """Test that invalid JSON raises an error."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid json}")

    with pytest.raises(Exception):  # JSONDecodeError
        validate_case(invalid_file)


def test_missing_required_field_raises_error(tmp_path: Path) -> None:
    """Test that missing required fields raise validation errors."""
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_file.write_text('{"id": "550e8400-e29b-41d4-a716-446655440000"}')

    with pytest.raises(ValidationError):
        validate_case(incomplete_file)


def test_nonexistent_file_raises_error() -> None:
    """Test that attempting to load a nonexistent file raises an error."""
    with pytest.raises(FileNotFoundError):
        validate_case("/nonexistent/path/to/case.json")
