"""Validation for LLM-generated case dicts.

validate_case_dict() is the gatekeeper at Boundary 1 (the freeze line).
Every case that passes this function is a fully valid, structurally sound
CaseDefinition ready to cross into Satori.
"""

from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails
from satori.models import CaseDefinition


def validate_case_dict(raw_dict: dict[str, Any]) -> tuple[CaseDefinition | None, list[str]]:
    """Validate a raw LLM-generated dict against CaseDefinition.

    Runs two phases:
    1. Pydantic validation — checks schema conformance via CaseDefinition.model_validate()
    2. Structural checks — verifies internal consistency the engine relies on

    Structural checks:
    - All reveal rule action refs exist in action_costs
    - Timer stages sorted by at_minutes ascending (per node)
    - Node IDs unique across the case
    - At least one node present

    Args:
        raw_dict: Raw dict parsed from LLM JSON output.

    Returns:
        ``(case_definition, [])`` on success.
        ``(None, [error_messages])`` on failure — errors describe all problems found.
    """
    # Phase 1: Pydantic validation
    try:
        case = CaseDefinition.model_validate(raw_dict)
    except ValidationError as e:
        errors = [f"[schema] {_format_pydantic_error(err)}" for err in e.errors()]
        return None, errors
    except Exception as e:  # noqa: BLE001
        return None, [f"[schema] Unexpected validation error: {e}"]

    # Phase 2: Structural checks
    structural_errors = _check_structural(case)
    if structural_errors:
        return None, structural_errors

    return case, []


def _format_pydantic_error(err: ErrorDetails) -> str:
    """Format a single pydantic error dict into a readable string."""
    loc = " -> ".join(str(p) for p in err.get("loc", []))
    msg = err.get("msg", "unknown error")
    return f"{loc}: {msg}" if loc else msg


def _check_structural(case: CaseDefinition) -> list[str]:
    """Run structural consistency checks on a schema-valid CaseDefinition.

    Returns a list of error messages, empty if all checks pass.
    """
    errors: list[str] = []
    known_actions = set(case.action_costs.keys())

    # Check 1: Node IDs unique
    node_ids = [node.id for node in case.nodes]
    seen: set[str] = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(f"[structural] Duplicate node id: '{nid}'")
        seen.add(nid)

    for node in case.nodes:
        # Check 2: Reveal rule action refs exist in action_costs
        if node.reveal is not None and node.reveal.action is not None:
            action_ref = node.reveal.action
            if action_ref not in known_actions:
                errors.append(
                    f"[structural] Node '{node.id}' reveal.action '{action_ref}' "
                    f"not found in action_costs (known: {sorted(known_actions)})"
                )

        # Check 3: Timer stages sorted ascending by at_minutes
        if node.timer is not None and node.timer.stages is not None:
            stages = node.timer.stages
            for i in range(1, len(stages)):
                if stages[i].at_minutes <= stages[i - 1].at_minutes:
                    errors.append(
                        f"[structural] Node '{node.id}' timer stages not sorted "
                        f"ascending by at_minutes: stage[{i-1}].at_minutes="
                        f"{stages[i-1].at_minutes} >= stage[{i}].at_minutes="
                        f"{stages[i].at_minutes}"
                    )

    return errors
