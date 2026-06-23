from pathlib import Path
from unittest.mock import patch

import pytest

from agents.router_agent import load_routing_table, route_ticket


def _team(topic: str, severity: str, sentiment: str = "negative") -> str:
    return route_ticket(topic, severity, sentiment, log_run=False)["team"]


def test_router_topic_routing_per_department():
    # Safety topic giờ do Vận hành xử lý (P3 để tránh P5-override kéo về Vận hành theo đường khác).
    assert _team("Safety", "P3") == "Vận hành"
    assert _team("App Issue", "P3") == "IT"
    assert _team("Payment", "P3") == "CSKH"
    assert _team("Driver Behavior", "P3") == "Vận hành"
    # Pricing giờ về CSKH (front-line), phối hợp IT — không còn đội Pricing riêng.
    assert _team("Pricing", "P3") == "CSKH"
    assert _team("Other", "P1", "positive") == "Marketing"


def test_p5_override_routes_to_van_hanh_and_wins_over_positive_sentiment():
    assert _team("Other", "P5", "positive") == "Vận hành"
    assert _team("App Issue", "5", "negative") == "Vận hành"


def test_valid_input_severity_becomes_ticket_priority():
    result = route_ticket("App Issue", 2, "negative", log_run=False)
    assert result["priority"] == "P2"


def test_unknown_topic_uses_cskh_default():
    assert _team("Unknown", "P2", "neutral") == "CSKH"


def test_missing_routing_taxonomy_fails_instead_of_defaulting_everything_to_cskh():
    with patch("agents.router_agent.ROUTING_TABLE_PATH", Path("/missing/routing_table.json")):
        with pytest.raises(FileNotFoundError):
            load_routing_table()
