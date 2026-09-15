"""Hợp đồng Human-in-the-Loop sau đợt siết 2026-08-27.

Mỗi test khoá một lỗ hổng đã xác minh trên code/DB thật, không phải giả định.
"""
import inspect

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import main
from auth_guard import AuthUser, require_manager
from dispatch_utils import normalize_deadline
from _fakedb import FakeDB


def _user(role="staff", dept="CSKH", uid="u1"):
    return AuthUser(id=uid, email="u@x.vn", role=role, department=dept)


def _dependency_of(endpoint, param="user"):
    """Hàm gate thật sự nằm sau Depends(...) của một endpoint."""
    default = inspect.signature(endpoint).parameters[param].default
    return getattr(default, "dependency", None)


# ── Ai được duyệt báo cáo ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "endpoint",
    [main.approve_report, main.update_draft_tasks, main.approve_and_dispatch],
)
def test_report_approval_requires_manager(endpoint):
    """Tạo hàng loạt task cho cả phòng + khoá báo cáo vĩnh viễn không phải việc của staff."""
    assert _dependency_of(endpoint) is require_manager


# ── Bẫy "duyệt trơn" khoá luôn đường triển khai ─────────────────────────────

def test_plain_approve_rejected_when_report_still_has_draft_tasks(monkeypatch):
    db = FakeDB(department_reports=[
        {"id": "r1", "team": "IT", "approved": False,
         "suggested_tasks": [{"action": "Sửa lỗi thanh toán"}]}
    ])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.approve_report("r1", user=_user("manager", "IT"))
    assert ei.value.status_code == 409
    assert db.tables["department_reports"][0]["approved"] is False  # không khoá báo cáo


def test_plain_approve_ok_when_no_draft_tasks(monkeypatch):
    db = FakeDB(department_reports=[
        {"id": "r1", "team": "IT", "approved": False, "suggested_tasks": []}
    ])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    res = main.approve_report("r1", user=_user("manager", "IT"))
    assert res["status"] == "success"
    assert db.tables["department_reports"][0]["approved"] is True


def test_plain_approve_twice_conflicts(monkeypatch):
    db = FakeDB(department_reports=[
        {"id": "r1", "team": "IT", "approved": True, "suggested_tasks": []}
    ])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.approve_report("r1", user=_user("manager", "IT"))
    assert ei.value.status_code == 409


# ── Payload draft task phải có schema thật ─────────────────────────────────

def test_draft_task_rejects_free_text_priority():
    with pytest.raises(ValidationError):
        main.DraftTaskItem(action="Rà soát", priority="khẩn")


def test_draft_task_rejects_unparsable_deadline():
    """'trong 2 tuần' từng lọt qua rồi âm thầm thành +48h."""
    with pytest.raises(ValidationError):
        main.DraftTaskItem(action="Rà soát", deadline="trong 2 tuần")


def test_draft_task_rejects_empty_action():
    with pytest.raises(ValidationError):
        main.DraftTaskItem(action="")


@pytest.mark.parametrize("raw,expected", [
    ("7 ngày", "7d"), ("2 tuần", "2w"), ("48 tiếng", "48h"), ("24 giờ", "24h"),
    ("3 days", "3d"), ("1 week", "1w"), ("6 hours", "6h"),
    ("1 tháng", "4w"),                 # tháng quy về tuần
    ("24h", "24h"), (" 7 d ", "7d"),   # token hợp lệ giữ nguyên
    (None, "48h"), ("ngay lập tức", "48h"), ("", "48h"),  # không đọc được -> mặc định
])
def test_normalize_deadline_maps_free_text_to_tokens(raw, expected):
    """Tác tử phân tích sinh '7 ngày' — phải quy về token TRƯỚC khi lưu báo cáo.

    Đo được trên dữ liệu thật 2026-08-27: một báo cáo có deadline '7 ngày' khiến
    manager không lưu nổi bản nháp vì cổng duyệt từ chối (422).
    """
    assert normalize_deadline(raw) == expected


def test_normalized_deadline_passes_draft_task_validation():
    """Vòng khép kín: giá trị đã chuẩn hoá phải qua được chính cổng validate."""
    assert main.DraftTaskItem(action="X", deadline=normalize_deadline("7 ngày"))


def test_draft_task_accepts_valid_tokens():
    for token in ("24h", "7d", "2w", " 48H "):
        assert main.DraftTaskItem(action="X", deadline=token).deadline == token


def test_dispatch_rejects_empty_task_list():
    """Duyệt-và-triển-khai với 0 task chỉ khoá báo cáo mà không sinh việc nào."""
    with pytest.raises(ValidationError):
        main.ApproveDispatchReq(suggested_tasks=[])


def test_dispatch_rejects_oversized_task_list():
    items = [{"action": f"Việc {i}"} for i in range(main.MAX_DRAFT_TASKS + 1)]
    with pytest.raises(ValidationError):
        main.ApproveDispatchReq(suggested_tasks=items)


# ── Gửi báo cáo hoàn thành ─────────────────────────────────────────────────

def _completion_db(owner_id="u1", status="in_progress", pending=None):
    return FakeDB(
        tasks=[{"id": "t1", "assigned_team": "CSKH", "status": status,
                "owner_id": owner_id, "source": "agent"}],
        task_completion_reports=list(pending or []),
        task_events=[],
    )


def test_completion_report_blocked_for_non_owner(monkeypatch):
    db = _completion_db(owner_id="someone-else")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.submit_completion_report(
            "t1", main.CompletionReportReq(note="xong rồi"), user=_user(uid="u1")
        )
    assert ei.value.status_code == 403


def test_completion_report_rejects_second_pending(monkeypatch):
    db = _completion_db(pending=[{"id": "cr0", "task_id": "t1", "status": "submitted"}])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.submit_completion_report(
            "t1", main.CompletionReportReq(note="xong rồi"), user=_user(uid="u1")
        )
    assert ei.value.status_code == 409


def test_completion_report_owner_ok(monkeypatch):
    db = _completion_db()
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    res = main.submit_completion_report(
        "t1", main.CompletionReportReq(note="xong rồi"), user=_user(uid="u1")
    )
    assert res["status"] == "success"
    assert db.tables["tasks"][0]["status"] == "pending_review"


# ── Duyệt báo cáo hoàn thành ───────────────────────────────────────────────

def _review_db(level="completed", task_status="pending_review", report_status="submitted"):
    return FakeDB(
        task_completion_reports=[{
            "id": "cr1", "task_id": "t1", "team": "CSKH",
            "status": report_status, "completion_level": level,
        }],
        tasks=[{"id": "t1", "assigned_team": "CSKH", "status": task_status, "source": "agent"}],
        alerts=[{"id": "a1", "task_id": "t1", "status": "open"}],
        task_events=[],
    )


def test_approving_completed_report_resolves_task_and_alerts(monkeypatch):
    db = _review_db()
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    main.review_completion_report(
        "cr1", main.ReviewReportReq(status="approved", review_note="ok"),
        user=_user("manager", "CSKH"),
    )
    assert db.tables["tasks"][0]["status"] == "resolved"
    assert db.tables["alerts"][0]["status"] == "resolved"


def test_approving_blocked_report_acknowledges_without_resolving(monkeypatch):
    """Duyệt một báo cáo 'blocked' là ghi nhận vướng mắc, KHÔNG phải đóng việc.

    Bản cũ vẫn nhắm 'resolved'; transition in_progress->resolved không hợp lệ nên bị bỏ
    qua im lặng: manager thấy 'đã duyệt', task kẹt in_progress, ticket khách vẫn mở.
    """
    db = _review_db(level="blocked", task_status="in_progress")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    main.review_completion_report(
        "cr1", main.ReviewReportReq(status="approved", review_note="chờ đối tác"),
        user=_user("manager", "CSKH"),
    )
    assert db.tables["task_completion_reports"][0]["status"] == "approved"
    assert db.tables["tasks"][0]["status"] == "in_progress"   # ở nguyên, có chủ đích
    assert db.tables["alerts"][0]["status"] == "open"         # ticket khách chưa đóng


def test_rejecting_report_returns_task_to_staff(monkeypatch):
    db = _review_db()
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    main.review_completion_report(
        "cr1", main.ReviewReportReq(status="rejected", review_note="thiếu bằng chứng"),
        user=_user("manager", "CSKH"),
    )
    assert db.tables["tasks"][0]["status"] == "in_progress"


def test_cannot_review_the_same_report_twice(monkeypatch):
    db = _review_db(report_status="approved", task_status="resolved")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.review_completion_report(
            "cr1", main.ReviewReportReq(status="rejected", review_note="đổi ý"),
            user=_user("manager", "CSKH"),
        )
    assert ei.value.status_code == 409
    assert db.tables["tasks"][0]["status"] == "resolved"  # không lệch hai nguồn sự thật


def test_invalid_transition_reports_conflict_instead_of_silent_noop(monkeypatch):
    """Task chưa ở pending_review mà duyệt 'completed' -> phải 409, không im lặng bỏ qua."""
    db = _review_db(level="completed", task_status="open")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.review_completion_report(
            "cr1", main.ReviewReportReq(status="approved", review_note="ok"),
            user=_user("manager", "CSKH"),
        )
    assert ei.value.status_code == 409
    # Báo cáo KHÔNG được đánh dấu đã duyệt khi task không chuyển được.
    assert db.tables["task_completion_reports"][0]["status"] == "submitted"


def test_list_reports_returns_403_not_503_for_ops_without_department(monkeypatch):
    """Ops chưa gán phòng phải nhận 403 rõ ràng, không phải 503 'lỗi hạ tầng'.

    scoped_team() raise 403; nếu gọi bên trong try thì `except Exception` của endpoint
    nuốt mất và đổi thành 503 — đo được khi chạy ma trận RBAC thật 2026-08-27.
    """
    monkeypatch.setattr(main, "get_supabase", lambda: FakeDB(department_reports=[]))
    with pytest.raises(HTTPException) as ei:
        main.list_reports(team=None, page=1, limit=50, user=_user("staff", None))
    assert ei.value.status_code == 403


# ── Scope phòng ban trên đường GHI của Loop A (duyệt nhãn) ─────────────────

def test_label_correction_blocked_across_departments(monkeypatch):
    db = FakeDB(feedback=[{
        "id": "f1", "topic": "Payment", "sentiment": "negative",
        "severity": "P3", "overall_risk": None, "text": "trừ tiền sai",
    }])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    # Payment -> Tài chính & Thanh toán; staff IT không được sửa nhãn của phòng đó.
    with pytest.raises(HTTPException) as ei:
        main.correct_feedback_label("f1", {"severity": "P1"}, user=_user("staff", "IT"))
    assert ei.value.status_code == 403


def test_review_feedback_blocked_across_departments(monkeypatch):
    db = FakeDB(feedback=[{
        "id": "f1", "topic": "Payment", "sentiment": "negative",
        "severity": "P3", "overall_risk": None, "text": "trừ tiền sai",
    }])
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.review_feedback("f1", payload=None, user=_user("staff", "IT"))
    assert ei.value.status_code == 403
