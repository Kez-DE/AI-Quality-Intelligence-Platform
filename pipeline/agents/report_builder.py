"""Deterministic report rendering and storage for department AI reports."""

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


REPORT_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
ANALYSIS_STATUS_LABELS = {
    "success": "Đã phân tích",
    "fallback": "Phân tích dự phòng",
    "disabled": "Đã tắt",
    "skipped": "Không đủ mẫu",
    "unknown": "Chưa xác định",
}


def _cell(value: object) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", " ").strip()


def _count(values: dict, key: str) -> int:
    try:
        return int(values.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _derived_risk(insights: dict[str, Any]) -> str:
    severity = insights.get("severity_distribution") or {}
    if _count(severity, "CRITICAL"):
        return "CRITICAL"
    if _count(severity, "WARNING"):
        return "HIGH"
    if _count(severity, "WATCH"):
        return "MEDIUM"
    return "LOW"


def build_department_report_markdown(
    team: str,
    insights: dict[str, Any],
    analysis_result: dict[str, Any],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render measured facts and validated AI analysis into stable Markdown."""
    generated_at = generated_at or datetime.now(timezone.utc)
    total = int(insights.get("total_feedback") or 0)
    period_hours = int(insights.get("period_hours") or 24)
    severity = insights.get("severity_distribution") or {}
    sentiment = insights.get("sentiment_distribution") or {}
    analysis = analysis_result.get("analysis") or {}
    risk_level = str(analysis.get("risk_level") or _derived_risk(insights)).upper()
    analysis_status = str(analysis_result.get("status") or "unknown")
    analysis_status_label = ANALYSIS_STATUS_LABELS.get(analysis_status, analysis_status)

    critical = _count(severity, "CRITICAL")
    warning = _count(severity, "WARNING")
    negative = _count(sentiment, "negative")
    task_status = insights.get("task_status_distribution") or {}
    active_tasks = _count(task_status, "open") + _count(task_status, "in_progress")
    overdue_tasks = int(insights.get("overdue_tasks") or 0)
    negative_rate = round(negative * 100 / total, 1) if total else 0

    top_topics = insights.get("top_topics") or []
    prominent_theme = str(analysis.get("prominent_theme") or "").strip()
    feedback_summary = str(analysis.get("feedback_summary") or "").strip()
    detailed_analysis = str(analysis.get("detailed_analysis") or "").strip()
    topic_suffix = ""
    if prominent_theme:
        topic_suffix = f": {prominent_theme}"
    elif top_topics:
        topic_suffix = f": {' / '.join(_cell(t.get('topic')) for t in top_topics[:2])}"

    lines = [
        f"# Báo cáo Vận hành - Phòng {_cell(team)}{topic_suffix}",
        "",
        "| Kỳ dữ liệu | Cập nhật | Phân tích AI |",
        "| --- | --- | --- |",
        (
            f"| {period_hours} giờ gần nhất "
            f"| {generated_at.astimezone(REPORT_TIMEZONE).strftime('%d/%m/%Y %H:%M GMT+7')} "
            f"| {_cell(analysis_status_label)} |"
        ),
        "",
        "## Tóm tắt điều hành",
        "",
        "| Chỉ số | Kết quả |",
        "| --- | ---: |",
        f"| Tổng phản hồi thuộc phòng | {total} |",
        f"| Mức CRITICAL | {critical} |",
        f"| Mức WARNING | {warning} |",
        f"| Phản hồi tiêu cực | {negative} ({negative_rate}%) |",
        f"| Task đang mở/đang xử lý | {active_tasks} |",
        f"| Task quá hạn | {overdue_tasks} |",
        f"| Mức rủi ro hiện tại | **{_cell(risk_level)}** |",
    ]

    lines.extend([
        "",
        "## Vấn đề ghi nhận",
        "",
        _cell(feedback_summary) if feedback_summary else "Chưa có tóm tắt vấn đề từ AI.",
    ])

    lines.extend([
        "",
        "## Vấn đề nổi bật",
        "",
        "| Chủ đề | Số phản hồi | Tỷ trọng |",
        "| --- | ---: | ---: |",
    ])

    if top_topics:
        for item in top_topics:
            count = int(item.get("count") or 0)
            share = round(count * 100 / total, 1) if total else 0
            lines.append(f"| {_cell(item.get('topic'))} | {count} | {share}% |")
    else:
        lines.append("| Chưa có dữ liệu | 0 | 0% |")

    lines.extend([
        "",
        "### Khu vực cần chú ý",
        "",
        "| Khu vực | Số phản hồi |",
        "| --- | ---: |",
    ])
    top_areas = insights.get("top_areas") or []
    if top_areas:
        for item in top_areas:
            lines.append(f"| {_cell(item.get('area'))} | {int(item.get('count') or 0)} |")
    else:
        lines.append("| Chưa có dữ liệu | 0 |")

    root_cause = analysis.get("root_cause_summary") or (
        "Chưa đủ mẫu phản hồi để đưa ra nhận định nguyên nhân."
    )
    lines.extend([
        "",
        "## Phân tích & nguyên nhân",
        "",
        _cell(detailed_analysis) if detailed_analysis else "Chưa có phân tích chi tiết.",
        "",
        f"**Nguyên nhân (cần xác minh):** {_cell(root_cause)}",
        f"**Mức rủi ro:** {_cell(risk_level)}",
        "",
        "### Bằng chứng từ dữ liệu",
        "",
    ])
    evidence = []
    if top_topics:
        evidence.append(
            f"{_cell(top_topics[0].get('topic'))}: {int(top_topics[0].get('count') or 0)}/{total} phản hồi."
        )
    if top_areas:
        evidence.append(
            f"{_cell(top_areas[0].get('area'))}: {int(top_areas[0].get('count') or 0)} phản hồi."
        )
    evidence.append(f"CRITICAL: {critical}; WARNING: {warning}; tiêu cực: {negative}/{total}.")
    lines.extend(f"- {item}" for item in evidence)

    lines.extend([
        "",
        "## Đề xuất giải quyết",
        "",
        "| Ưu tiên | Hành động | Phụ trách | Thời hạn | Tiêu chí hoàn thành |",
        "| --- | --- | --- | --- | --- |",
    ])
    actions = analysis.get("action_items") or []
    if actions:
        for index, action in enumerate(actions[:5], start=1):
            lines.append(
                "| {priority} | {action} | {owner} | {deadline} | {metric} |".format(
                    priority=_cell(action.get("priority") or f"P{min(index, 3)}"),
                    action=_cell(action.get("action")),
                    owner=_cell(action.get("owner") or team),
                    deadline=_cell(action.get("deadline") or "48h"),
                    metric=_cell(action.get("success_metric") or "Hoàn thành và ghi nhận kết quả"),
                )
            )
    else:
        lines.append(f"| P1 | Rà soát dữ liệu và xác minh nguyên nhân | {_cell(team)} | 24h | Có kết luận được ghi nhận |")

    lines.extend([
        "",
        "## Dự báo và theo dõi",
        "",
        (
            "Chưa đủ dữ liệu so sánh với kỳ trước để kết luận xu hướng 24-48 giờ. "
            "Cần theo dõi lại các chỉ số CRITICAL, WARNING và tỷ lệ phản hồi tiêu cực ở kỳ kế tiếp."
        ),
        "",
        "## Phạm vi và độ tin cậy",
        "",
        (
            f"Báo cáo sử dụng {total} phản hồi được định tuyến về phòng {_cell(team)} "
            f"trong {period_hours} giờ và {len(insights.get('recent_samples') or [])} mẫu gần nhất cho phần nhận định AI. "
            "Các nhận định nguyên nhân phải được người phụ trách xác minh trước khi triển khai."
        ),
    ])
    return "\n".join(lines).strip()


def store_department_report(
    db,
    *,
    team: str,
    report_date: str,
    content: str,
    suggested_tasks: list | None = None,
    root_cause_summary: str | None = None,
) -> dict[str, Any]:
    """Lưu một báo cáo mới. Cho phép nhiều báo cáo/ngày (không chặn bản đã duyệt)."""
    payload = {
        "team": team,
        "report_date": report_date,
        "content": content,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "suggested_tasks": suggested_tasks or [],
        "root_cause_summary": root_cause_summary,
    }
    result = db.table("department_reports").insert(payload).execute()
    return {"stored": True, "data": result.data or []}


__all__ = ["build_department_report_markdown", "store_department_report"]
