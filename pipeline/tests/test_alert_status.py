import pytest
from main import _assert_alert_transition   # helper mới, thuần


def test_valid_alert_transitions():
    _assert_alert_transition("open", "in_progress")
    _assert_alert_transition("in_progress", "resolved")
    _assert_alert_transition("resolved", "in_progress")  # mở lại


def test_invalid_alert_transitions():
    for a, b in [("open", "resolved"), ("resolved", "open"), ("open", "open")]:
        with pytest.raises(Exception):
            _assert_alert_transition(a, b)
