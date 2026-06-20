from agents.router_agent import route_ticket


def _team(topic: str, severity: str, sentiment: str = "negative") -> str:
    return route_ticket(topic, severity, sentiment, log_run=False)["team"]


def test_router_covers_all_six_departments():
    assert _team("Safety", "P5") == "Safety"
    assert _team("App Issue", "P3") == "IT"
    assert _team("Payment", "P3") == "CSKH"
    assert _team("Driver Behavior", "P3") == "Vận hành"
    assert _team("Pricing", "P3") == "Pricing"
    assert _team("Other", "P1", "positive") == "Marketing"


def test_p5_safety_override_wins_over_positive_sentiment():
    assert _team("Other", "P5", "positive") == "Safety"
    assert _team("App Issue", "5", "negative") == "Safety"


def test_valid_input_severity_becomes_ticket_priority():
    result = route_ticket("App Issue", 2, "negative", log_run=False)
    assert result["priority"] == "P2"


def test_unknown_topic_uses_cskh_default():
    assert _team("Unknown", "P2", "neutral") == "CSKH"
