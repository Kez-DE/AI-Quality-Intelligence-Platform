from datetime import datetime, timezone
from unittest.mock import MagicMock

from agents.analyst_agent import derive_risk_level
from agents.report_builder import build_department_report_markdown, store_department_report


def _insights():
    return {
        "period_hours": 24,
        "total_feedback": 20,
        "severity_distribution": {"CRITICAL": 1, "WARNING": 3, "WATCH": 10, "INFO": 6},
        "sentiment_distribution": {"negative": 12, "neutral": 3, "positive": 5},
        "task_status_distribution": {"open": 2, "in_progress": 1, "resolved": 4},
        "overdue_tasks": 1,
        "top_topics": [{"topic": "App Issue", "count": 12}, {"topic": "Other", "count": 8}],
        "top_areas": [{"area": "HCM-Q1", "count": 9}],
        "recent_samples": [{"text": "Ứng dụng bị treo"}, {"text": "Không mở được app"}],
    }


def test_report_uses_measured_metrics_and_structured_action_table():
    analysis = {
        "status": "success",
        "analysis": {
            "risk_level": "CRITICAL",
            "root_cause_summary": "Khả năng có lỗi ứng dụng cần được xác minh qua log.",
            "evidence": ["12/20 phản hồi thuộc App Issue"],
            "action_items": [{
                "priority": "P1",
                "action": "Kiểm tra log lỗi",
                "owner": "IT",
                "deadline": "4h",
                "success_metric": "Xác định được error signature",
            }],
        },
    }

    report = build_department_report_markdown(
        "IT",
        _insights(),
        analysis,
        generated_at=datetime(2026, 6, 20, 2, 0, tzinfo=timezone.utc),
    )

    assert "| Tổng phản hồi thuộc phòng | 20 |" in report
    assert "| App Issue | 12 | 60.0% |" in report
    assert "| Phản hồi tiêu cực | 12 (60.0%) |" in report
    assert "| Task đang mở/đang xử lý | 3 |" in report
    assert "| Task quá hạn | 1 |" in report
    assert "| P1 | Kiểm tra log lỗi | IT | 4h | Xác định được error signature |" in report
    assert "Chưa đủ dữ liệu so sánh với kỳ trước" in report
    assert "Theo xu hướng hiện tại" not in report


def test_risk_level_is_derived_from_measured_severity():
    assert derive_risk_level(_insights()) == "CRITICAL"
    assert derive_risk_level({"severity_distribution": {"WARNING": 2}}) == "HIGH"
    assert derive_risk_level({"severity_distribution": {"WATCH": 2}}) == "MEDIUM"
    assert derive_risk_level({"severity_distribution": {"INFO": 2}}) == "LOW"


def test_approved_report_is_not_overwritten():
    db = MagicMock()
    query = db.table.return_value.select.return_value
    query.eq.return_value = query
    query.limit.return_value = query
    query.execute.return_value = MagicMock(data=[{"id": "r1", "approved": True}])

    result = store_department_report(
        db,
        team="IT",
        report_date="2026-06-20",
        content="new report",
    )

    assert result == {"stored": False, "reason": "approved_report_locked", "id": "r1"}
    db.table.return_value.upsert.assert_not_called()
