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


def test_store_uses_insert_not_upsert():
    db = MagicMock()
    insert_mock = db.table.return_value.insert
    insert_mock.return_value.execute.return_value.data = [{"id": "r1"}]
    out = store_department_report(
        db, team="IT", report_date="2026-06-26", content="# x",
        suggested_tasks=[{"action": "a"}], root_cause_summary="rc",
    )
    assert out["stored"] is True
    insert_mock.assert_called_once()
    db.table.return_value.upsert.assert_not_called()


def test_analyst_analysis_optional_new_fields():
    from agents.schemas import AnalystAnalysis
    # Thiếu các trường mới vẫn parse được (default rỗng)
    a = AnalystAnalysis(root_cause_summary="x", risk_level="LOW")
    assert a.prominent_theme is None
    assert a.feedback_summary == ""
    assert a.detailed_analysis == ""
    # Có trường mới thì giữ nguyên
    b = AnalystAnalysis(
        root_cause_summary="x", risk_level="LOW",
        prominent_theme="Sự cố hiệu năng App", feedback_summary="App treo",
        detailed_analysis="Phân tích chi tiết",
    )
    assert b.prominent_theme == "Sự cố hiệu năng App"


def test_fallback_analysis_has_new_fields():
    from agents.analyst_agent import _fallback_analysis
    insights = {"top_topics": [{"topic": "App Issue", "count": 5}], "total_feedback": 5}
    out = _fallback_analysis("IT", insights)
    analysis = out["analysis"]
    assert analysis["prominent_theme"]
    assert analysis["feedback_summary"]
    assert analysis["detailed_analysis"]
    assert analysis["root_cause_summary"]


def test_markdown_has_three_sections_and_title():
    from agents.report_builder import build_department_report_markdown
    analysis_result = {"status": "success", "analysis": {
        "prominent_theme": "Sự cố hiệu năng App",
        "feedback_summary": "Khách báo app treo khi đặt xe.",
        "detailed_analysis": "Tần suất tăng ở khung giờ cao điểm.",
        "root_cause_summary": "Nghi do tải máy chủ.",
        "risk_level": "HIGH",
        "action_items": [{"action": "Rà soát server", "priority": "P2", "deadline": "48h"}],
        "evidence": ["App Issue: 12/20"],
    }}
    md = build_department_report_markdown("IT", _insights(), analysis_result)
    assert md.startswith("# Báo cáo Vận hành - Phòng IT: Sự cố hiệu năng App")
    assert "## Vấn đề ghi nhận" in md
    assert "Khách báo app treo" in md
    assert "## Phân tích & nguyên nhân" in md
    assert "## Đề xuất giải quyết" in md
    assert "Rà soát server" in md
