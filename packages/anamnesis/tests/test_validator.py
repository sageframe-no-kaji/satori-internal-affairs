"""Tests for anamnesis.validator — validate_case_dict()."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from satori.models import CaseDefinition

from anamnesis.validator import validate_case_dict


def _load_example_case() -> dict[str, Any]:
    """Load the canonical example neurocysticercosis case as a dict."""
    repo_root = Path(__file__).parent.parent.parent.parent
    path = repo_root / "cases" / "example-neurocysticercosis.json"
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestValidCaseDict:
    """validate_case_dict() returns (CaseDefinition, []) for valid input."""

    def test_example_case_passes(self) -> None:
        """The canonical example case validates without errors."""
        raw = _load_example_case()
        case_def, errors = validate_case_dict(raw)
        assert case_def is not None
        assert errors == []
        assert isinstance(case_def, CaseDefinition)

    def test_returns_case_definition_instance(self) -> None:
        """The returned object is a CaseDefinition."""
        raw = _load_example_case()
        case_def, _ = validate_case_dict(raw)
        assert isinstance(case_def, CaseDefinition)

    def test_case_has_nodes(self) -> None:
        """The validated case has at least one node."""
        raw = _load_example_case()
        case_def, _ = validate_case_dict(raw)
        assert case_def is not None
        assert len(case_def.nodes) >= 1


class TestInvalidCaseDict:
    """validate_case_dict() returns (None, errors) for invalid input."""

    def test_empty_dict_fails(self) -> None:
        """Empty dict fails validation with pydantic errors."""
        case_def, errors = validate_case_dict({})
        assert case_def is None
        assert len(errors) > 0
        assert all("[schema]" in e for e in errors)

    def test_missing_required_field_fails(self) -> None:
        """Dict missing 'nodes' fails validation."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        del data["nodes"]
        case_def, errors = validate_case_dict(data)
        assert case_def is None
        assert any("nodes" in e.lower() for e in errors)

    def test_invalid_node_type_fails(self) -> None:
        """Dict with invalid node type enum value fails validation."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        data["nodes"][0]["type"] = "not_a_real_type"
        case_def, errors = validate_case_dict(data)
        assert case_def is None
        assert len(errors) > 0

    def test_invalid_version_format_fails(self) -> None:
        """Non-semver version string fails validation."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        data["version"] = "not-semver"
        case_def, errors = validate_case_dict(data)
        assert case_def is None
        assert len(errors) > 0


class TestStructuralChecks:
    """validate_case_dict() runs structural checks beyond Pydantic."""

    def test_duplicate_node_ids_fail(self) -> None:
        """Duplicate node IDs are caught as a structural error."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        # Duplicate the first node ID into the second node
        if len(data["nodes"]) >= 2:
            data["nodes"][1]["id"] = data["nodes"][0]["id"]
            case_def, errors = validate_case_dict(data)
            assert case_def is None
            assert any("[structural]" in e and "Duplicate" in e for e in errors)

    def test_invalid_action_ref_fails(self) -> None:
        """Reveal action ref not in action_costs is a structural error."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        # Find a node with a reveal.action and set it to a non-existent action
        for node in data["nodes"]:
            if node.get("reveal") and node["reveal"].get("action"):
                node["reveal"]["action"] = "nonexistent_action_zzz"
                break
        case_def, errors = validate_case_dict(data)
        assert case_def is None
        assert any("[structural]" in e and "nonexistent_action_zzz" in e for e in errors)

    def test_unsorted_timer_stages_fail(self) -> None:
        """Timer stages not sorted ascending by at_minutes is a structural error."""
        raw = _load_example_case()
        data = copy.deepcopy(raw)
        # Find a node with timer stages and reverse them
        for node in data["nodes"]:
            timer = node.get("timer") or {}
            stages = timer.get("stages")
            if stages and len(stages) >= 2:
                # Swap first two stages to break ascending order
                stages[0], stages[1] = stages[1], stages[0]
                case_def, errors = validate_case_dict(data)
                assert case_def is None
                assert any("[structural]" in e and "sorted" in e for e in errors)
                return
        pytest.skip("No node with multiple timer stages found in example case")

    def test_error_messages_include_prefix(self) -> None:
        """Errors are prefixed with [schema] or [structural] for disambiguation."""
        case_def, errors = validate_case_dict({})
        assert case_def is None
        assert all(e.startswith("[schema]") or e.startswith("[structural]") for e in errors)


class TestValidatorEdgeCases:
    """Edge cases and additional branches in validate_case_dict."""

    def test_non_dict_input_handled(self) -> None:
        """Passing a non-dict (e.g. a list) fails gracefully rather than crashing."""
        case_def, errors = validate_case_dict([])  # type: ignore[arg-type]
        assert case_def is None
        assert len(errors) > 0

    def test_returns_empty_errors_on_success(self) -> None:
        """On success the errors list is exactly empty, not just falsy."""
        import copy
        import json
        from pathlib import Path

        repo_root = Path(__file__).parent.parent.parent.parent
        with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
            raw = json.load(f)
        case_def, errors = validate_case_dict(copy.deepcopy(raw))
        assert errors == []
        assert case_def is not None

    def test_multiple_structural_errors_all_reported(self) -> None:
        """All structural errors are collected, not just the first."""
        import copy
        import json
        from pathlib import Path

        repo_root = Path(__file__).parent.parent.parent.parent
        with (repo_root / "cases" / "example-neurocysticercosis.json").open() as f:
            data = json.load(f)
        data = copy.deepcopy(data)
        # Introduce two distinct structural errors at once:
        # 1. Duplicate node ID
        if len(data["nodes"]) >= 2:
            data["nodes"][1]["id"] = data["nodes"][0]["id"]
        # 2. Invalid action ref
        for node in data["nodes"]:
            if node.get("reveal") and node["reveal"].get("action"):
                node["reveal"]["action"] = "nonexistent_zzz"
                break
        case_def, errors = validate_case_dict(data)
        assert case_def is None
        assert len(errors) >= 2
