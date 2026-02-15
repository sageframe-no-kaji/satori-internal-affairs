"""Action string parsing utilities.

Handles the base_action:parameter convention for player actions.
"""


def parse_action(action: str) -> tuple[str, str | None]:
    """Parse a player action into (base_action, parameter).

    The base_action is used for time-cost lookup in case.action_costs.
    The parameter is matched against RevealRule.subcategory and
    InterventionEffect.treatment to determine effects.

    Args:
        action: Player action string, optionally with parameter

    Returns:
        Tuple of (base_action, parameter).
        If no colon present, parameter is None.

    Examples:
        "history_general" → ("history_general", None)
        "history_focused:dietary" → ("history_focused", "dietary")
        "order_labs:cbc" → ("order_labs", "cbc")
        "start_treatment:albendazole" → ("start_treatment", "albendazole")
    """
    if ":" in action:
        base, param = action.split(":", 1)
        return base, param
    return action, None
