"""Tests cho GET /api/cockpit/overview — scope RBAC + aggregate cơ bản."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_guard import AuthUser
from main import cockpit_overview


def _user(role: str, department=None) -> AuthUser:
    return AuthUser(id="u1", email="u@example.com", role=role, department=department)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _query(data):
    """Mock chainable Supabase query trả về `data` khi execute()."""
    query = MagicMock()
    for method in ("select", "gte", "order", "limit", "neq", "eq"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=data)
    return query


def _database(feedback=None, tasks=None, alerts=None, corrections=None):
    db = MagicMock()
    table_map = {
        "feedback": _query(feedback or []),
        "tasks": _query(tasks or []),
        "alerts": _query(alerts or []),
        "correction_logs": _query(corrections or []),
    }
    db.table.side_effect = lambda name: table_map[name]
    return db


def test_unassigned_ops_returns_flag_not_403():
    # Ops chưa gán phòng -> không raise, trả unassigned=true.
    result = cockpit_overview(days=14, user=_user("staff", department=None))
    data = result["data"]
    assert data["scope"]["unassigned"] is True
    assert data["kpis"] == {}
    assert data["trend"] == []


def test_admin_sees_aggregate_and_ops_kpis():
    feedback = [
        {"id": "1", "topic": "App Issue", "sentiment": "negative", "severity": "P5",
         "area": "HCM-Q1", "created_at": _now_iso(), "needs_review": True, "overall_risk": 5},
        {"id": "2", "topic": "App Issue", "sentiment": "neutral", "severity": "P3",
         "area": "HN", "created_at": _now_iso(), "needs_review": False, "overall_risk": 3},
    ]
    tasks = [{"status": "open", "priority": "P5", "assigned_team": "IT"}]
    alerts = [{"id": "a1", "status": "open", "assigned_team": "IT", "created_at": _now_iso()}]
    with patch("main.get_supabase", return_value=_database(feedback, tasks, alerts, corrections=[{"id": "c1"}])):
        result = cockpit_overview(days=14, user=_user("admin"))
    data = result["data"]
    assert data["scope"]["team"] is None  # admin = toàn bộ
    assert data["kpis"]["feedback_today"] == 2
    assert data["kpis"]["needs_review"] == 1
    assert data["kpis"]["negative_rate"] == 50.0
    assert data["kpis"]["tickets_open"] == 1
    assert data["kpis"]["tickets_by_priority"] == {"P5": 1}
    assert data["kpis"]["alerts_open"] == 1
    assert data["kpis"]["corrections_7d"] == 1
    # category sort desc
    assert data["categories"][0]["topic"] == "App Issue"
    assert data["categories"][0]["count"] == 2


def test_ops_scoped_to_own_department():
    # 2 feedback định tuyến về phòng khác nhau; staff phòng IT chỉ thấy của IT.
    feedback = [
        {"id": "1", "topic": "App Issue", "sentiment": "negative", "severity": "P5",
         "area": "HCM", "created_at": _now_iso(), "needs_review": False, "overall_risk": 5},
        {"id": "2", "topic": "Driver Attitude", "sentiment": "negative", "severity": "P5",
         "area": "HN", "created_at": _now_iso(), "needs_review": False, "overall_risk": 5},
    ]

    def fake_team(row):
        return "IT" if row["topic"] == "App Issue" else "Vận hành"

    with patch("main.get_supabase", return_value=_database(feedback, tasks=[], alerts=[], corrections=[])), \
         patch("main._feedback_team", side_effect=fake_team):
        result = cockpit_overview(days=14, user=_user("staff", department="IT"))
    data = result["data"]
    assert data["scope"]["team"] == "IT"
    assert data["kpis"]["window_total"] == 1  # chỉ feedback của IT


def test_ops_payload_is_never_restricted():
    """The guest-only restricted payload is gone (decision 0017); the route now
    requires ops staff, so every caller gets the full ops payload for its scope."""
    feedback = [
        {"id": "1", "topic": "App Issue", "sentiment": "negative", "severity": "P3",
         "area": "HCM", "created_at": _now_iso(), "needs_review": False, "overall_risk": 3},
    ]
    with patch("main.get_supabase", return_value=_database(feedback)):
        result = cockpit_overview(days=14, user=_user("admin"))
    data = result["data"]
    assert data["scope"]["restricted"] is False
    assert "alerts_open" in data["kpis"]


def test_db_error_does_not_crash():
    db = MagicMock()
    db.table.side_effect = RuntimeError("boom")
    with patch("main.get_supabase", return_value=db):
        result = cockpit_overview(days=7, user=_user("admin"))
    data = result["data"]
    assert data["db_error"] is not None
    assert data["kpis"]["feedback_today"] == 0  # vẫn trả payload an toàn


def test_chart_fields_present_for_admin():
    """Admin thấy đủ 4 chart fields: trend_sentiment, risk_distribution, funnel, sankey_flows."""
    feedback = [
        {"id": "1", "topic": "App Issue", "sentiment": "negative", "severity": "P5",
         "area": "HCM", "created_at": _now_iso(), "needs_review": False, "overall_risk": 8},
        {"id": "2", "topic": "Driver Attitude", "sentiment": "positive", "severity": "P2",
         "area": "HN", "created_at": _now_iso(), "needs_review": False, "overall_risk": 2},
        {"id": "3", "topic": "App Issue", "sentiment": "neutral", "severity": "P3",
         "area": "HCM", "created_at": _now_iso(), "needs_review": False, "overall_risk": 5},
    ]
    tasks = [
        {"id": "t1", "status": "open", "priority": "P5", "assigned_team": "IT", "created_at": _now_iso()},
        {"id": "t2", "status": "resolved", "priority": "P2", "assigned_team": "CSKH", "created_at": _now_iso()},
    ]
    alerts = [{"id": "a1", "status": "open", "assigned_team": "IT", "created_at": _now_iso()}]
    with patch("main.get_supabase", return_value=_database(feedback, tasks, alerts, corrections=[])):
        result = cockpit_overview(days=14, user=_user("admin"))
    data = result["data"]

    # trend_sentiment: list có ngày hôm nay với 3 sentiment counts
    assert "trend_sentiment" in data
    today_sent = next((d for d in data["trend_sentiment"] if d["positive"] + d["neutral"] + d["negative"] > 0), None)
    assert today_sent is not None
    assert today_sent["negative"] == 1
    assert today_sent["positive"] == 1
    assert today_sent["neutral"] == 1

    # risk_distribution: luôn có đủ 10 scores
    assert len(data["risk_distribution"]) == 10
    score8 = next(d for d in data["risk_distribution"] if d["score"] == 8)
    assert score8["count"] == 1
    score2 = next(d for d in data["risk_distribution"] if d["score"] == 2)
    assert score2["count"] == 1
    # score không có trong data → count = 0
    score1 = next(d for d in data["risk_distribution"] if d["score"] == 1)
    assert score1["count"] == 0

    # funnel: có đủ 6 keys
    assert data["funnel"]["total"] == 3
    assert data["funnel"]["classified"] == 3   # cả 3 đều có topic
    assert data["funnel"]["tickets_created"] == 2
    assert data["funnel"]["resolved"] == 1

    # sankey_flows: có link sentiment → severity
    sent_sev_links = [f for f in data["sankey_flows"] if f["from"] in ("positive", "neutral", "negative")]
    assert len(sent_sev_links) > 0
    neg_p5 = next((f for f in sent_sev_links if f["from"] == "negative" and f["to"] == "P5"), None)
    assert neg_p5 is not None
    assert neg_p5["value"] == 1


def test_risk_distribution_missing_scores_fill_zero():
    """Scores không có trong data → count = 0, vẫn trả đủ 10 phần tử."""
    feedback = [
        {"id": "1", "topic": "App", "sentiment": "negative", "severity": "P5",
         "area": "HCM", "created_at": _now_iso(), "needs_review": False, "overall_risk": 10},
    ]
    with patch("main.get_supabase", return_value=_database(feedback)):
        result = cockpit_overview(days=7, user=_user("admin"))
    dist = result["data"]["risk_distribution"]
    assert len(dist) == 10
    assert dist[-1]["score"] == 10
    assert dist[-1]["count"] == 1
    assert dist[0]["score"] == 1
    assert dist[0]["count"] == 0


def test_risk_distribution_excludes_sentinel_zero():
    """overall_risk=0 là sentinel 'LLM chấm fail, chờ người' của worker_ml —
    không được đếm vào bucket 1 (báo sai 'rủi ro thấp đã xác minh')."""
    feedback = [
        {"id": "1", "topic": "App Issue", "sentiment": "negative", "severity": "P3",
         "area": "HCM", "created_at": _now_iso(), "needs_review": True, "overall_risk": 0},
        {"id": "2", "topic": "App Issue", "sentiment": "negative", "severity": "P2",
         "area": "HN", "created_at": _now_iso(), "needs_review": False, "overall_risk": 2},
    ]
    with patch("main.get_supabase", return_value=_database(feedback, [], [], corrections=[])):
        result = cockpit_overview(days=14, user=_user("admin"))
    dist = {d["score"]: d["count"] for d in result["data"]["risk_distribution"]}
    assert dist[1] == 0          # sentinel không rơi vào bucket 1
    assert dist[2] == 1
