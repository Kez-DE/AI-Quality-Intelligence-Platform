"""_compute_sla_summary: đúng hạn/trễ/đang quá hạn + MTTA/MTTR."""
from main import _compute_sla_summary


def test_sla_summary_counts_and_times():
    alerts = [
        # resolved đúng hạn (resolved_at <= sla_due_at)
        {"status": "resolved", "sla_due_at": "2026-07-01T10:00:00+00:00",
         "created_at": "2026-07-01T08:00:00+00:00", "in_progress_at": "2026-07-01T08:30:00+00:00",
         "resolved_at": "2026-07-01T09:00:00+00:00"},
        # resolved trễ (resolved_at > sla_due_at)
        {"status": "resolved", "sla_due_at": "2026-07-01T10:00:00+00:00",
         "created_at": "2026-07-01T08:00:00+00:00", "resolved_at": "2026-07-01T12:00:00+00:00"},
        # chưa resolve mà đã quá hạn
        {"status": "open", "sla_due_at": "2000-01-01T00:00:00+00:00",
         "created_at": "2026-07-01T08:00:00+00:00"},
        # resolved cũ (timer) không có resolved_at + quá hạn → KHÔNG tính overdue
        {"status": "resolved", "sla_due_at": "2000-01-01T00:00:00+00:00",
         "created_at": "2026-07-01T08:00:00+00:00"},
    ]
    s = _compute_sla_summary(alerts)
    assert s["on_time"] == 1
    assert s["late"] == 1
    assert s["overdue_open"] == 1
    assert s["resolved_total"] == 2
    # MTTR = trung bình (resolved_at - created_at) của 2 ca resolved = (1h + 4h)/2 = 2.5h
    assert abs(s["mttr_seconds"] - 2.5 * 3600) < 1
    # MTTA = (in_progress_at - created_at) chỉ ca 1 có = 30 phút
    assert abs(s["mtta_seconds"] - 30 * 60) < 1


def test_sla_summary_empty():
    s = _compute_sla_summary([])
    assert s["on_time"] == 0 and s["late"] == 0 and s["overdue_open"] == 0
    assert s["mttr_seconds"] is None and s["mtta_seconds"] is None
