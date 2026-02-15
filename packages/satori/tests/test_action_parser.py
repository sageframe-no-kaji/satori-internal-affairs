"""Unit tests for action_parser.parse_action.

Tests colon splitting, no colon, multiple colons, and edge cases.
"""

from satori.action_parser import parse_action


class TestParseAction:
    def test_no_colon(self):
        assert parse_action("history_general") == ("history_general", None)

    def test_single_colon(self):
        assert parse_action("history_focused:dietary") == ("history_focused", "dietary")

    def test_multiple_colons(self):
        """Only split on first colon."""
        assert parse_action("a:b:c") == ("a", "b:c")

    def test_empty_string(self):
        assert parse_action("") == ("", None)

    def test_colon_only(self):
        assert parse_action(":") == ("", "")

    def test_trailing_colon(self):
        assert parse_action("order_labs:") == ("order_labs", "")

    def test_leading_colon(self):
        assert parse_action(":albendazole") == ("", "albendazole")

    def test_treatment_action(self):
        assert parse_action("start_treatment:albendazole") == ("start_treatment", "albendazole")

    def test_order_labs(self):
        assert parse_action("order_labs:cbc") == ("order_labs", "cbc")

    def test_order_imaging(self):
        assert parse_action("order_imaging:brain_ct") == ("order_imaging", "brain_ct")
