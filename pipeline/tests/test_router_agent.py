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
    assert _team("Payment", "P3") == "Tài chính & Thanh toán"
    assert _team("Driver Behavior", "P3") == "Vận hành"
    # Pricing giờ về Quản lý Rủi ro & Gian lận (lạm dụng KM, giá bất thường).
    assert _team("Pricing", "P3") == "Quản lý Rủi ro & Gian lận"
    assert _team("Other", "P1", "positive") == "Sản phẩm"


def test_positive_sentiment_routes_san_pham_for_other_and_app_issue():
    # Positive CHUNG (Other) hoặc góp ý app (App Issue) -> Sản phẩm để nâng cấp UX.
    assert _team("Other", "P3", "positive") == "Sản phẩm"
    assert _team("App Issue", "P3", "positive") == "Sản phẩm"
    # Positive gắn chủ đề chuyên môn khác KHÔNG bị ép về Sản phẩm — route theo topic.
    assert _team("Payment", "P3", "positive") == "Tài chính & Thanh toán"
    assert _team("Driver Behavior", "P3", "positive") == "Vận hành"
    assert _team("Pricing", "P3", "positive") == "Quản lý Rủi ro & Gian lận"


def test_sentiment_override_without_topics_is_ignored():
    # Override thiếu "topics" KHÔNG được ép về Marketing (chống tái sinh bug cũ);
    # ticket rơi xuống topic match như bình thường.
    config = {
        "default_team": "CSKH",
        "routes": [{"topic": "App Issue", "team": "IT", "sla_hours": 12, "priority_default": "P3"}],
        "severity_overrides": [],
        "sentiment_overrides": [{"sentiment": "positive", "team": "Sản phẩm", "sla_hours": 48}],
    }
    with patch("agents.router_agent.load_routing_table", return_value=config):
        assert _team("App Issue", "P3", "positive") == "IT"


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
