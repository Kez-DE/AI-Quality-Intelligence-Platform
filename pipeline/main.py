from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import logging
import os
import time
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from typing import Optional

from ingest import ingest_dataset
from ingest import get_supabase
from agent import chat_completion, get_agent_status, run_chat_agent
from agent.rag_engine import rag_chat
from auth_guard import AuthUser, can_view_team, get_current_user, require_admin, require_manager, require_ops_staff, scoped_team
from dispatch_utils import parse_deadline
from users_admin import router as users_router, audit_router
from rate_limiter import RateLimiter, check_rate_limit
from clean import mask_pii
from env_config import get_settings
from core.paths import DEFAULT_DATA_FILE
from departments import alert_department
from agents.router_agent import route_ticket
from services.agent_context import AGENT_SYSTEM_PROMPT, GUEST_SYSTEM_PROMPT, build_agent_data_context, build_agent_system_prompt
from services.live_stream import get_live_stream_status, set_scheduler, start_live_stream, stop_live_stream
from services.ticket_workflow import ticket_workflow_state

START_TIME = time.time()


class ChatMessageReq(BaseModel):
    role: str
    content: str = Field(..., max_length=15000)


class ChatReq(BaseModel):
    messages: list[ChatMessageReq]


class StatusUpdateReq(BaseModel):
    status: str


class AssignTaskReq(BaseModel):
    owner_id: Optional[str] = None
    due_at: Optional[str] = None


class CompletionReportReq(BaseModel):
    note: str = Field(..., min_length=1, max_length=5000)
    completion_level: str = "completed"  # completed | partial | blocked


class SupportResolveReq(BaseModel):
    reply: str = Field(..., min_length=1, max_length=5000)


class ReviewReportReq(BaseModel):
    status: str  # approved | rejected
    review_note: Optional[str] = Field(default=None, max_length=2000)


class DraftTasksReq(BaseModel):
    suggested_tasks: list[dict]


class ApproveDispatchReq(BaseModel):
    suggested_tasks: list[dict]


_s = get_settings()

feedback_rate_limit = RateLimiter(max_requests=_s.rate_limit_feedback_guest, window_seconds=3600, scope="feedback_submit")
chat_rate_limit = RateLimiter(max_requests=_s.rate_limit_chat_guest, window_seconds=3600, scope="agent_chat")
chat_rate_limit_staff = RateLimiter(max_requests=_s.rate_limit_chat_staff, window_seconds=3600, scope="agent_chat_staff")

scheduler: BackgroundScheduler | None = None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# Vòng đời task hợp lệ. Reassign (đổi owner) đưa task active về 'assigned' để nhận lại.
ALLOWED_TASK_TRANSITIONS = {
    ("open", "assigned"),
    ("assigned", "assigned"),
    ("in_progress", "assigned"),
    ("assigned", "in_progress"),
    ("in_progress", "pending_review"),
    ("pending_review", "resolved"),
    ("pending_review", "in_progress"),
}


def _assert_transition(from_status: str | None, to_status: str) -> None:
    """Chặn chuyển trạng thái task không hợp lệ. No-op nếu giữ nguyên trạng thái."""
    if from_status == to_status:
        return
    if (from_status, to_status) not in ALLOWED_TASK_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Chuyển trạng thái không hợp lệ: {from_status} -> {to_status}",
        )


def _log_task_event(
    db, *, task_id, actor, team, action,
    from_status=None, to_status=None, completion_report_id=None, note=None,
):
    """Ghi một mốc vòng đời task vào task_events. Audit là phụ trợ: lỗi ghi không
    được làm hỏng thao tác chính (bọc try/except)."""
    try:
        db.table("task_events").insert({
            "task_id": task_id,
            "actor_id": getattr(actor, "id", None),
            "actor_email": getattr(actor, "email", None),
            "actor_role": getattr(actor, "role", None),
            "team": team,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "completion_report_id": completion_report_id,
            "note": note,
        }).execute()
    except Exception as exc:  # noqa: BLE001 — audit không chặn nghiệp vụ
        logging.getLogger("task_events").warning("Không ghi được task_event: %s", str(exc)[:200])


def _feedback_team(feedback: dict) -> str:
    """Resolve feedback ownership with the same rules used to create tickets."""
    severity = feedback.get("severity", "P3")
    try:
        overall_risk = int(feedback.get("overall_risk"))
        if 1 <= overall_risk <= 5:
            severity = f"P{overall_risk}"
    except (TypeError, ValueError):
        pass
    return route_ticket(
        str(feedback.get("topic") or "Other"),
        severity,
        str(feedback.get("sentiment") or "neutral"),
        log_run=False,
    )["team"]


# Khung giờ dùng cho heatmap khu vực × giờ trên cockpit.
COCKPIT_HOUR_BUCKETS = ["06", "09", "12", "15", "18", "21"]


def _hour_bucket(dt: datetime) -> str:
    """Gom giờ trong ngày về một trong các mốc COCKPIT_HOUR_BUCKETS (mốc <= giờ)."""
    hour = dt.hour
    chosen = 6
    for bucket in (6, 9, 12, 15, 18, 21):
        if hour >= bucket:
            chosen = bucket
    return f"{chosen:02d}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    # Web API keeps a scheduler ONLY for on-demand manual jobs (e.g.
    # /api/live-stream/start). Recurring jobs (ticket workflow, auto live
    # stream) run in their dedicated worker services — NOT here — to avoid
    # double-scheduling when web + workers run against the same database.
    scheduler = BackgroundScheduler()
    set_scheduler(scheduler)
    scheduler.start()
    print("Web API scheduler ready (on-demand only; recurring jobs run in workers).")
    yield
    scheduler.shutdown()
    set_scheduler(None)

app = FastAPI(
    title="AI Quality Intelligence Platform API",
    description="Backend API for Smart Mobility Feedback Analytics",
    version="1.0.0",
    lifespan=lifespan
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
                "details": exc.errors(),
            }
        },
    )

# CORS config to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# User-management (admin only) — định danh + RBAC ở tầng API vì service role bypass RLS.
app.include_router(users_router)
app.include_router(audit_router)


@app.get("/api/me")
def whoami(user: AuthUser = Depends(get_current_user)):
    """Trả về danh tính + role của user đang đăng nhập (frontend dùng để render nav theo quyền)."""
    return {"status": "success", "data": {"id": user.id, "email": user.email, "role": user.role, "department": user.department}}


@app.get("/")
def read_root():
    return {"message": "Welcome to AI Quality Intelligence API"}

@app.get("/health")
def health_check():
    from core.paths import DEFAULT_DATA_FILE
    from agents.router_agent import load_routing_table
    from pathlib import Path
    agent_info = get_agent_status()
    try:
        routing_routes = len(load_routing_table().get("routes", []))
    except (FileNotFoundError, ValueError):
        routing_routes = 0
    return {
        "status": "ok",
        "message": "Backend service is running",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "data_file_exists": Path(DEFAULT_DATA_FILE).exists(),
        "routing_taxonomy_loaded": routing_routes > 0,
        "routing_routes": routing_routes,
        "llm_provider": agent_info.get("provider"),
        "llm_has_key": agent_info.get("has_key"),
    }

@app.get("/api/feedback/recent")
def recent_feedback(
    limit: int = Query(default=100, ge=1, le=500),
    needs_review: bool | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    user: AuthUser = Depends(get_current_user),
):
    """Đọc feedback gần nhất.

    - Guest: chỉ xem feedback của chính mình.
    - Staff/Manager: chỉ xem feedback được định tuyến về phòng của mình.
    - Admin: xem toàn bộ feedback.
    """
    try:
        db = get_supabase()
        q = db.table("feedback").select("*")
        feedback_team = None
        fetch_limit = limit
        if user.role == "guest":
            # Guest chỉ xem feedback do chính mình gửi
            q = q.eq("user_id", user.id)
        else:
            if user.role in ("staff", "manager"):
                feedback_team = scoped_team(user, None)
                fetch_limit = 500
            if needs_review is not None:
                q = q.eq("needs_review", needs_review)
            if reviewed is not None:
                q = q.eq("reviewed", reviewed)
        data = q.order("created_at", desc=True).limit(fetch_limit).execute().data or []
        if feedback_team:
            data = [row for row in data if _feedback_team(row) == feedback_team][:limit]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read feedback: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/alerts/recent")
def recent_alerts(limit: int = Query(default=100, ge=1, le=500), user: AuthUser = Depends(require_ops_staff)):
    """Alerts chỉ dành cho ops staff (staff/manager/admin). Guest không được xem.

    Admin xem tất cả; ops khác chỉ xem alert có assigned_team thuộc phòng mình.
    Ticket cũ chưa có field này được fallback qua Markdown/task_id."""
    try:
        db = get_supabase()
        fetch_limit = limit if user.role == "admin" else 500
        data = db.table("alerts") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(fetch_limit) \
            .execute() \
            .data or []
        if user.role != "admin":
            own_team = scoped_team(user, None)
            task_rows = db.table("tasks").select("id").eq("assigned_team", own_team).execute().data or []
            task_ids = {t["id"] for t in task_rows if t.get("id")}
            data = [
                alert for alert in data
                if alert_department(alert) == own_team or alert.get("task_id") in task_ids
            ][:limit]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read alerts: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/tasks")
def list_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    team: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    area: str | None = Query(default=None),
    overdue: bool = Query(default=False),
    mine: bool = Query(default=False),
    assigned: bool | None = Query(default=None),
    user: AuthUser = Depends(require_ops_staff),
):
    """Liệt kê task. mine=true -> chỉ task giao cho user hiện tại ("Việc của tôi").

    assigned=true/false -> lọc task đã/chưa có người nhận (dùng cho hàng đợi dispatch).
    """
    # scoped_team có thể raise 403 (ops chưa gán phòng) — gọi NGOÀI try để không bị
    # except Exception bọc nhầm thành 503.
    effective_team = scoped_team(user, team)
    try:
        db = get_supabase()
        q = db.table("tasks").select("*")
        if status:
            q = q.eq("status", status)
        if effective_team:
            q = q.eq("assigned_team", effective_team)
        if priority:
            q = q.eq("priority", priority)
        if area:
            q = q.eq("area", area)
        if mine:
            q = q.eq("owner_id", user.id)
        if assigned is True:
            q = q.not_.is_("owner_id", "null")
        elif assigned is False:
            q = q.is_("owner_id", "null")
        if overdue:
            q = q.lt("due_at", datetime.now(timezone.utc).isoformat()).neq("status", "resolved")
        data = q.order("created_at", desc=True).limit(limit).execute().data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read tasks: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/tasks/{task_id}/alerts")
def list_task_alerts(task_id: str, _: AuthUser = Depends(require_ops_staff)):
    try:
        db = get_supabase()
        data = db.table("alerts") \
            .select("*") \
            .eq("task_id", task_id) \
            .order("created_at", desc=True) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read task alerts: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.patch("/api/tasks/{task_id}/status")
def update_task_status(task_id: str, payload: StatusUpdateReq, user: AuthUser = Depends(require_manager)):
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ manager hoặc admin được đổi trạng thái task.")
    new_status = payload.status
    if new_status not in {"open", "assigned", "in_progress", "pending_review", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid task status")
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật task của phòng ban khác.")
        _assert_transition(cur_status, new_status)
        data = db.table("tasks") \
            .update({"status": new_status, "updated_at": "now()"}) \
            .eq("id", task_id) \
            .execute() \
            .data or []
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        _log_task_event(
            db, task_id=task_id, actor=user, team=task_team, action="status_changed",
            from_status=cur_status, to_status=new_status,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update task: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0]}

@app.post("/api/tasks/{task_id}/support-resolve")
def support_resolve(task_id: str, payload: SupportResolveReq, user: AuthUser = Depends(require_ops_staff)):
    """Bàn CSKH đóng ticket khách trực tiếp (staff/manager/admin trong phòng).

    Tách khỏi vòng duyệt nội bộ update_task_status: đây là quy trình khách-hàng-đối-mặt,
    nhân viên CSKH được đóng ticket khách trực tiếp, không qua bước manager duyệt.
    """
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không thể đóng ticket của phòng ban khác.")
        if cur_status == "resolved":
            raise HTTPException(status_code=409, detail="Ticket đã được đóng.")
        if cur_status not in {"open", "assigned", "in_progress", "pending_review"}:
            raise HTTPException(status_code=400, detail=f"Không thể đóng ticket ở trạng thái {cur_status}.")
        data = db.table("tasks").update({"status": "resolved", "updated_at": "now()"}).eq("id", task_id).execute().data or []
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        _log_task_event(
            db, task_id=task_id, actor=user, team=task_team, action="support_resolved",
            from_status=cur_status, to_status="resolved", note=payload.reply[:500],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot resolve ticket: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0]}

@app.patch("/api/tasks/{task_id}/assign")
def assign_task(task_id: str, payload: AssignTaskReq, user: AuthUser = Depends(require_manager)):
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ manager hoặc admin được giao task.")
    update_fields: dict = {}
    if payload.due_at is not None:
        update_fields["due_at"] = payload.due_at
    if payload.owner_id is None and not update_fields:
        raise HTTPException(status_code=400, detail="Must provide owner_id or due_at")
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if user.role != "admin" and not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không có quyền gán task của phòng ban khác.")
        new_status = cur_status
        if payload.owner_id is not None:
            owners = db.table("profiles").select("role,department").eq("id", payload.owner_id).limit(1).execute().data or []
            if not owners:
                raise HTTPException(status_code=404, detail="Không tìm thấy người nhận.")
            owner = owners[0]
            if owner.get("role") != "staff":
                raise HTTPException(status_code=400, detail="Người nhận task phải là nhân viên (staff).")
            if task_team and owner.get("department") != task_team:
                raise HTTPException(
                    status_code=400,
                    detail=f"Người nhận phải thuộc phòng ban '{task_team}' của task.",
                )
            _assert_transition(cur_status, "assigned")
            update_fields["owner_id"] = payload.owner_id
            update_fields["status"] = "assigned"
            new_status = "assigned"
        update_fields["updated_at"] = "now()"
        data = db.table("tasks").update(update_fields).eq("id", task_id).execute().data or []
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        if payload.owner_id is not None:
            _log_task_event(
                db, task_id=task_id, actor=user, team=task_team, action="assigned",
                from_status=cur_status, to_status=new_status,
                note=f"owner={payload.owner_id}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot assign task: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0]}


@app.post("/api/tasks/{task_id}/accept")
def accept_task(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Nhân viên được giao bấm nhận việc: assigned -> in_progress."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status,owner_id").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task = rows[0]
        if task.get("owner_id") != user.id:
            raise HTTPException(status_code=403, detail="Chỉ người được giao mới nhận được task này.")
        cur_status = task.get("status")
        _assert_transition(cur_status, "in_progress")
        data = db.table("tasks").update({"status": "in_progress", "updated_at": "now()"}).eq("id", task_id).execute().data or []
        _log_task_event(
            db, task_id=task_id, actor=user, team=task.get("assigned_team"),
            action="accepted", from_status=cur_status, to_status="in_progress",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot accept task: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "data": data[0]}

@app.get("/api/leaderboard")
def get_leaderboard(_: AuthUser = Depends(require_ops_staff)):
    """Team leaderboard from resolved tasks."""
    try:
        db = get_supabase()
        rows = db.table("tasks") \
            .select("assigned_team,created_at,updated_at") \
            .eq("status", "resolved") \
            .execute() \
            .data or []
        team_stats: dict[str, dict] = {}
        for row in rows:
            team = row.get("assigned_team") or "Unknown"
            stats = team_stats.setdefault(team, {"resolved_count": 0, "total_time_seconds": 0})
            stats["resolved_count"] += 1
            created = _parse_timestamp(row.get("created_at"))
            updated = _parse_timestamp(row.get("updated_at"))
            if created and updated and updated > created:
                stats["total_time_seconds"] += (updated - created).total_seconds()
        result = []
        for team, stats in team_stats.items():
            count = stats["resolved_count"]
            avg_seconds = stats["total_time_seconds"] / count if count else 0
            result.append({
                "team": team,
                "resolved_count": count,
                "avg_resolution_hours": round(avg_seconds / 3600, 2),
            })
        result.sort(key=lambda item: (-item["resolved_count"], item["avg_resolution_hours"]))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot calculate leaderboard: {str(exc)[:300]}") from exc
    return {"status": "success", "data": result}


@app.get("/api/reports")
def list_reports(
    team: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthUser = Depends(require_ops_staff),
):
    try:
        db = get_supabase()
        q = db.table("department_reports").select("*", count="exact")
        effective_team = scoped_team(user, team)
        if effective_team:
            q = q.eq("team", effective_team)
        offset = (page - 1) * limit
        response = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        data = response.data or []
        total_items = response.count if response.count is not None else 0
        pagination = {
            "page": page,
            "pageSize": limit,
            "totalItems": total_items,
            "totalPages": (total_items + limit - 1) // limit,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read reports: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data, "pagination": pagination}


@app.patch("/api/reports/{report_id}/approve")
def approve_report(report_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Trưởng phòng duyệt báo cáo trước khi chia việc."""
    db = get_supabase()
    existing = db.table("department_reports").select("team").eq("id", report_id).limit(1).execute().data or []
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    if not can_view_team(user, existing[0].get("team")):
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt báo cáo của phòng ban khác.")
    try:
        data = db.table("department_reports").update({
            "approved": True,
            "approved_by": user.id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", report_id).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot approve report: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "data": data[0]}


@app.put("/api/reports/{report_id}/draft-tasks")
def update_draft_tasks(
    report_id: str,
    payload: DraftTasksReq,
    user: AuthUser = Depends(require_ops_staff),
):
    """Manager lưu nháp danh sách Draft Task. 409 nếu báo cáo đã duyệt."""
    db = get_supabase()
    existing = db.table("department_reports").select("team,approved").eq("id", report_id).limit(1).execute().data or []
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    if not can_view_team(user, existing[0].get("team")):
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa báo cáo của phòng ban khác.")
    if existing[0].get("approved"):
        raise HTTPException(status_code=409, detail="Báo cáo đã duyệt, không thể sửa.")
    try:
        data = db.table("department_reports").update(
            {"suggested_tasks": payload.suggested_tasks}
        ).eq("id", report_id).eq("approved", False).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot save draft: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=409, detail="Báo cáo đã duyệt, không thể sửa.")
    return {"status": "success", "data": data[0]}


@app.post("/api/reports/{report_id}/approve-and-dispatch")
def approve_and_dispatch(
    report_id: str,
    payload: ApproveDispatchReq,
    user: AuthUser = Depends(require_ops_staff),
):
    """Duyệt báo cáo + tạo task chính thức (atomic qua RPC)."""
    db = get_supabase()
    existing = db.table("department_reports").select("team,approved").eq("id", report_id).limit(1).execute().data or []
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    if not can_view_team(user, existing[0].get("team")):
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt báo cáo của phòng ban khác.")
    if existing[0].get("approved"):
        raise HTTPException(status_code=409, detail="Báo cáo đã được duyệt.")

    enriched = []
    for t in payload.suggested_tasks:
        item = dict(t)
        item["due_at"] = parse_deadline(item.get("deadline")).isoformat()
        enriched.append(item)

    try:
        res = db.rpc("approve_report_and_dispatch", {
            "p_report_id": report_id,
            "p_tasks": enriched,
            "p_approver": user.id,
        }).execute()
        tasks_created = res.data if isinstance(res.data, int) else (res.data or 0)
    except Exception as exc:
        if "report_not_found_or_already_approved" in str(exc):
            raise HTTPException(status_code=409, detail="Báo cáo đã được duyệt.") from exc
        raise HTTPException(status_code=503, detail=f"Cannot dispatch: {str(exc)[:300]}") from exc

    report = db.table("department_reports").select("*").eq("id", report_id).limit(1).execute().data or []
    return {"status": "success", "tasks_created": tasks_created, "report": report[0] if report else None}


@app.get("/api/users/assignable")
def list_assignable_users(
    team: str | None = Query(default=None),
    user: AuthUser = Depends(require_ops_staff),
):
    """Danh sách user có thể gán task (chỉ staff cùng phòng ban).

    RBAC: manager/staff chỉ thấy staff CÙNG phòng ban của mình (không thể gán task
    cho người phòng khác). Admin thấy tất cả staff, hoặc lọc theo ?team nếu truyền.
    Ops chưa được gán phòng → 403 (qua scoped_team).
    """
    # scoped_team raise 403 cho ops chưa gán phòng; trả None cho admin (xem tất cả).
    effective_team = scoped_team(user, team)
    try:
        db = get_supabase()
        q = db.table("profiles") \
            .select("id,email,role,full_name,department") \
            .eq("role", "staff")
        if effective_team:
            # Chỉ giữ người thuộc đúng phòng ban. Admin vẫn nằm trong phòng nào đó
            # nếu được gán; nếu cần admin xuyên phòng, không truyền ?team.
            q = q.eq("department", effective_team)
        data = q.order("role", desc=False).order("email", desc=False).execute().data or []
        # Sort: admin first, then manager, then staff
        role_order = {"admin": 0, "manager": 1, "staff": 2}
        data.sort(key=lambda u: (role_order.get(u.get("role"), 99), (u.get("email") or "")))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read assignable users: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/tasks/{task_id}/suggest-assignee")
def suggest_task_assignee(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Agent gợi ý người nhận cho task (rule-based, cân bằng tải trong phòng ban).

    Cùng triết lý với router_agent (rule, không LLM): chọn nhân viên CÙNG phòng của
    task đang nhận ÍT việc mở nhất (load balancing), ưu tiên staff hơn manager khi
    điều phối thực thi. Giúp quản lý dispatch nhanh và hợp lý.
    """
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Không có quyền xem gợi ý của phòng ban khác.")
        candidates = db.table("profiles") \
            .select("id,email,full_name,role,department") \
            .eq("department", task_team).in_("role", ["staff", "manager"]).execute().data or []
        if not candidates:
            return {"status": "success", "data": {
                "suggested": None,
                "reason": f"Phòng {task_team} chưa có nhân viên để giao việc.",
                "candidates": [],
            }}
        # Đếm số việc đang mở (chưa resolved) của mỗi người trong phòng.
        open_tasks = db.table("tasks").select("owner_id,status") \
            .eq("assigned_team", task_team).neq("status", "resolved").execute().data or []
        load: dict = {}
        for t in open_tasks:
            oid = t.get("owner_id")
            if oid:
                load[oid] = load.get(oid, 0) + 1
        role_rank = {"staff": 0, "manager": 1}
        ranked = sorted(
            candidates,
            key=lambda c: (load.get(c["id"], 0), role_rank.get(c.get("role"), 9), c.get("email") or ""),
        )
        enriched = [{**c, "open_tasks": load.get(c["id"], 0)} for c in ranked]
        best = enriched[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot suggest assignee: {str(exc)[:300]}") from exc
    return {"status": "success", "data": {
        "suggested": best,
        "reason": f"Đang nhận {best['open_tasks']} việc mở — ít nhất trong phòng {task_team}.",
        "candidates": enriched,
    }}

# ---------------------------------------------------------------------------
# Luồng "Báo cáo hoàn thành" (staff -> manager). Tách biệt với task & department_reports.
# ---------------------------------------------------------------------------

@app.post("/api/tasks/{task_id}/completion-report")
def submit_completion_report(
    task_id: str, payload: CompletionReportReq, user: AuthUser = Depends(require_ops_staff)
):
    """Nhân viên gửi báo cáo hoàn thành cho một task của phòng mình."""
    if payload.completion_level not in {"completed", "partial", "blocked"}:
        raise HTTPException(status_code=400, detail="completion_level không hợp lệ")
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không thể báo cáo task của phòng ban khác.")
        record = {
            "task_id": task_id,
            "staff_id": user.id,
            "staff_email": user.email,
            "team": task_team,
            "completion_level": payload.completion_level,
            "note": payload.note,
            "status": "submitted",
        }
        inserted = db.table("task_completion_reports").insert(record).execute().data or []
        if not inserted:
            raise HTTPException(status_code=503, detail="Không tạo được báo cáo hoàn thành")
        report = inserted[0]
        # 'completed' -> chuyển task sang chờ duyệt (KHÔNG auto-resolve). partial/blocked giữ nguyên.
        new_status = cur_status
        if payload.completion_level == "completed":
            _assert_transition(cur_status, "pending_review")
            db.table("tasks").update({"status": "pending_review", "updated_at": "now()"}).eq("id", task_id).execute()
            new_status = "pending_review"
        _log_task_event(
            db, task_id=task_id, actor=user, team=task_team, action="completion_submitted",
            from_status=cur_status, to_status=new_status,
            completion_report_id=report.get("id"),
            note=f"{payload.completion_level}: {payload.note[:200]}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot submit completion report: {str(exc)[:300]}") from exc
    return {"status": "success", "data": report}


def _attach_task_titles(rows: list[dict], titles: dict) -> list[dict]:
    """Gắn task_title vào mỗi báo cáo dựa trên map {task_id: title}."""
    for r in rows:
        r["task_title"] = titles.get(r.get("task_id")) or None
    return rows


def _load_task_titles(db, rows: list[dict]) -> dict:
    """Nạp map {task_id: title} cho danh sách báo cáo (batch theo task_id)."""
    task_ids = list({r.get("task_id") for r in rows if r.get("task_id")})
    if not task_ids:
        return {}
    trows = db.table("tasks").select("id,title").in_("id", task_ids).execute().data or []
    return {t["id"]: t.get("title") for t in trows}


@app.get("/api/tasks/{task_id}/completion-reports")
def list_task_completion_reports(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Danh sách báo cáo hoàn thành của một task (scope theo phòng)."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_view_team(user, rows[0].get("assigned_team")):
            raise HTTPException(status_code=403, detail="Không có quyền xem báo cáo phòng ban khác.")
        data = db.table("task_completion_reports") \
            .select("*").eq("task_id", task_id) \
            .order("created_at", desc=True).execute().data or []
        data = _attach_task_titles(data, _load_task_titles(db, data))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read completion reports: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}


@app.get("/api/tasks/{task_id}/events")
def list_task_events(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Audit trail vòng đời của một task (scope theo phòng)."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_view_team(user, rows[0].get("assigned_team")):
            raise HTTPException(status_code=403, detail="Không có quyền xem nhật ký phòng ban khác.")
        data = db.table("task_events").select("*").eq("task_id", task_id) \
            .order("created_at", desc=True).execute().data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read task events: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}


@app.get("/api/completion-reports")
def list_completion_reports(
    status: str | None = Query(default=None),
    team: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(require_ops_staff),
):
    """Quản lý theo dõi mọi báo cáo hoàn thành của phòng mình (admin: tất cả)."""
    effective_team = scoped_team(user, team)
    try:
        db = get_supabase()
        q = db.table("task_completion_reports").select("*")
        if effective_team:
            q = q.eq("team", effective_team)
        if status:
            q = q.eq("status", status)
        data = q.order("created_at", desc=True).limit(limit).execute().data or []
        data = _attach_task_titles(data, _load_task_titles(db, data))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read completion reports: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}


@app.patch("/api/completion-reports/{report_id}/review")
def review_completion_report(
    report_id: str, payload: ReviewReportReq, user: AuthUser = Depends(require_ops_staff)
):
    """Quản lý/admin duyệt (approved) hoặc trả lại (rejected) báo cáo hoàn thành."""
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="status phải là approved hoặc rejected")
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ quản lý hoặc admin được duyệt báo cáo.")
    try:
        db = get_supabase()
        rows = db.table("task_completion_reports").select("team,task_id").eq("id", report_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Report not found")
        team = rows[0].get("team")
        rep_task_id = rows[0].get("task_id")
        if not can_view_team(user, team):
            raise HTTPException(status_code=403, detail="Không có quyền duyệt báo cáo phòng ban khác.")
        # NOTE: report update and task transition below are intentionally non-atomic
        # (Supabase REST has no transaction here; acceptable — partial failure is
        # surfaced via audit log and retry is safe).
        data = db.table("task_completion_reports").update({
            "status": payload.status,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": "now()",
        }).eq("id", report_id).execute().data or []
        # Lái trạng thái task theo kết quả duyệt.
        task_rows = db.table("tasks").select("status").eq("id", rep_task_id).limit(1).execute().data or []
        cur = task_rows[0].get("status") if task_rows else None
        target = "resolved" if payload.status == "approved" else "in_progress"
        action = "completion_approved" if payload.status == "approved" else "completion_rejected"
        to_status = cur
        if cur is not None and (cur, target) in ALLOWED_TASK_TRANSITIONS:
            db.table("tasks").update({"status": target, "updated_at": "now()"}).eq("id", rep_task_id).execute()
            to_status = target
        _log_task_event(
            db, task_id=rep_task_id, actor=user, team=team, action=action,
            from_status=cur, to_status=to_status, completion_report_id=report_id,
            note=payload.review_note,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot review completion report: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "data": data[0]}

@app.get("/api/alerts/workflow-status")
def alert_workflow_status(_: AuthUser = Depends(require_ops_staff)):
    """Trạng thái workflow ticket — chỉ ops staff."""
    return {"status": "success", "data": dict(ticket_workflow_state)}

@app.patch("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, payload: dict, user: AuthUser = Depends(require_ops_staff)):
    new_status = payload.get("status")
    if new_status not in {"open", "in_progress", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid alert status")
    try:
        db = get_supabase()
        if user.role != "admin":
            rows = db.table("alerts").select("*").eq("id", alert_id).limit(1).execute().data or []
            if not rows:
                raise HTTPException(status_code=404, detail="Alert not found")
            alert = rows[0]
            task_id = alert.get("task_id")
            task_team = alert_department(alert)
            if not task_team and task_id:
                task = db.table("tasks").select("assigned_team").eq("id", task_id).limit(1).execute().data or []
                task_team = task[0].get("assigned_team") if task else None
            if not can_view_team(user, task_team):
                raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật alert của phòng ban khác.")
        data = db.table("alerts") \
            .update({"status": new_status}) \
            .eq("id", alert_id) \
            .execute() \
            .data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update alert: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "data": data[0]}

@app.get("/api/agent/status")
def agent_status(_: AuthUser = Depends(require_ops_staff)):
    return {"status": "success", "data": get_agent_status()}

@app.get("/api/agent/logs")
def agent_logs(limit: int = Query(default=50, ge=1, le=500), _: AuthUser = Depends(require_ops_staff)):
    log_file = get_agent_status()["log_file"]
    if not os.path.exists(log_file):
        return {"status": "success", "data": []}
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    return {"status": "success", "data": [line.rstrip("\n") for line in lines]}

@app.get("/api/agent/ai-log")
def agent_ai_log(
    limit: int = Query(default=100, ge=1, le=500),
    agent: str = Query(default=""),
    team: str = Query(default=""),
    user: AuthUser = Depends(require_ops_staff),
):
    """AI-log vận hành (6 agent nghiệp vụ + chat agent), bóc theo phòng ban.

    - admin: xem mọi phòng; lọc theo ?team nếu truyền (vd team=guest, team=Safety).
    - ops đã gán phòng: CHỈ thấy log phòng mình (ép team, bỏ qua ?team).
    - ops chưa gán phòng: 403."""
    from agents.ai_log import read_recent
    if user.role == "admin":
        scope = team or ""  # admin: tôn trọng filter tùy chọn (rỗng = tất cả)
    else:
        scope = scoped_team(user, None)  # ép phòng của ops; raise 403 nếu chưa gán
    return {"status": "success", "data": read_recent(limit=limit, agent_name=agent, team=scope)}


# Tên + cờ env của 6 agent nghiệp vụ — khớp orchestrator._agent_enabled.
AGENT_REGISTRY = [
    {"name": "ingestion_agent", "label": "Ingestion / Classifier", "step": 1, "flag": None,
     "desc": "Làm sạch PII, phân loại topic/sentiment/severity", "uses_llm": False},
    {"name": "router_agent", "label": "Router", "step": 2, "flag": None,
     "desc": "Định tuyến ticket về đúng phòng ban", "uses_llm": False},
    {"name": "ticket_agent", "label": "Ticket", "step": 3, "flag": "AGENT_ALERT_ENABLED",
     "desc": "Tạo/cập nhật/dedup ticket, gán SLA + priority", "uses_llm": False},
    {"name": "task_agent", "label": "Task", "step": 4, "flag": "AGENT_TASK_ENABLED",
     "desc": "Gom cụm alert thành task", "uses_llm": True},
    {"name": "insight_agent", "label": "Insight", "step": 5, "flag": "AGENT_INSIGHT_ENABLED",
     "desc": "Tổng hợp metric feedback theo phòng ban", "uses_llm": False},
    {"name": "analyst_agent", "label": "Analyst", "step": 6, "flag": "AGENT_ANALYST_ENABLED",
     "desc": "Phân tích root-cause bằng LLM, đề xuất action", "uses_llm": True},
    {"name": "alert_agent", "label": "Alert / Escalation", "step": 7, "flag": "AGENT_ALERT_ENABLED",
     "desc": "Phân cấp WATCH/WARNING/CRITICAL, cooldown dedup", "uses_llm": True},
]


def _flag_enabled(flag: str | None) -> bool:
    """Đọc cờ env per-agent (mặc định bật) — khớp orchestrator._agent_enabled."""
    if not flag:
        return True
    val = os.getenv(flag)
    if val is None:
        return True
    return val.strip().lower() in {"1", "true", "yes", "on"}


@app.get("/api/agent/stats")
def agent_stats(
    hours: int = Query(default=24, ge=1, le=720),
    _: AuthUser = Depends(require_admin),
):
    """Thống kê vận hành từng agent từ bảng agent_run_logs (chỉ admin).

    Trả về cho mỗi agent: tổng lượt chạy, success/failed/fallback, error_rate,
    latency trung bình, lần chạy gần nhất, và trạng thái bật/tắt (cờ env).
    """
    from agents.common import get_db

    worker_enabled = _flag_enabled("WORKER_AGENT_ENABLED")
    interval = int(os.getenv("WORKER_AGENT_INTERVAL_SECONDS", "300"))

    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows: list[dict] = []
    db_error = None
    try:
        db = get_db()
        resp = db.table("agent_run_logs") \
            .select("agent_name,status,latency_ms,created_at") \
            .gte("created_at", since) \
            .order("created_at", desc=True) \
            .limit(5000) \
            .execute()
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001 - stats không được làm vỡ trang
        db_error = str(exc)[:200]

    # Gom nhóm theo agent_name
    by_agent: dict[str, dict] = {}
    for r in rows:
        name = r.get("agent_name") or "unknown"
        b = by_agent.setdefault(name, {"runs": 0, "success": 0, "failed": 0,
                                       "fallback": 0, "latency_sum": 0, "latency_n": 0,
                                       "last_run": None})
        b["runs"] += 1
        st = r.get("status") or "success"
        if st in b:
            b[st] += 1
        lat = r.get("latency_ms")
        if isinstance(lat, (int, float)) and lat > 0:
            b["latency_sum"] += lat
            b["latency_n"] += 1
        ts = r.get("created_at")
        if ts and (b["last_run"] is None or ts > b["last_run"]):
            b["last_run"] = ts

    agents_out = []
    for meta in AGENT_REGISTRY:
        b = by_agent.get(meta["name"], {})
        runs = b.get("runs", 0)
        failed = b.get("failed", 0)
        avg_lat = round(b["latency_sum"] / b["latency_n"]) if b.get("latency_n") else 0
        agents_out.append({
            "name": meta["name"],
            "label": meta["label"],
            "step": meta["step"],
            "description": meta["desc"],
            "uses_llm": meta["uses_llm"],
            "enabled": worker_enabled and _flag_enabled(meta["flag"]),
            "flag": meta["flag"],
            "runs": runs,
            "success": b.get("success", 0),
            "failed": failed,
            "fallback": b.get("fallback", 0),
            "error_rate": round(failed / runs, 3) if runs else 0.0,
            "avg_latency_ms": avg_lat,
            "last_run": b.get("last_run"),
        })

    return {"status": "success", "data": {
        "window_hours": hours,
        "worker_enabled": worker_enabled,
        "interval_seconds": interval,
        "total_runs": len(rows),
        "db_error": db_error,
        "agents": agents_out,
    }}


def _log_chat_event(team: str, status: str, latency_ms: int, *, provider: str = "", model: str = "", error: str = ""):
    """Ghi ai-log cho 1 lượt chat agent, gắn phòng ban của account (guest/admin/tên phòng).

    Best-effort — không bao giờ làm vỡ request chat."""
    try:
        from agents.ai_log import log_agent_event
        log_agent_event(
            agent_name="chat_agent",
            status=status,
            team=team,
            source="chat",
            latency_ms=latency_ms,
            provider=provider,
            model=model,
            error_message=error,
        )
    except Exception:
        pass


CHAT_HISTORY_LIMIT = 30
CLIENT_CHAT_ROLES = {"user", "assistant"}


def _append_safe_client_history(normalized: list[dict], messages: list[ChatMessageReq]) -> None:
    """Append user-visible chat history, ignoring client-supplied system prompts."""
    for message in messages[-CHAT_HISTORY_LIMIT:]:
        role = message.role
        content = message.content.strip()
        if role == "system":
            continue
        if role not in CLIENT_CHAT_ROLES or not content:
            raise HTTPException(status_code=400, detail="Invalid chat message")
        # OWASP LLM: mask PII from user input before injecting into prompt.
        safe_content = mask_pii(content) if role == "user" else content
        normalized.append({"role": role, "content": safe_content[:8000]})


@app.post("/api/agent/chat")
def agent_chat(payload: ChatReq, user: AuthUser = Depends(get_current_user)):
    if user.role == "guest":
        check_rate_limit(chat_rate_limit, user.id)
        if not payload.messages:
            raise HTTPException(status_code=400, detail="messages must be a non-empty list")

        # --- Import guest tool support ---
        from agent.chat_tools import GUEST_TOOLS_DEFINITIONS, execute_guest_tool

        # RAG công khai: lấy câu hỏi cuối của khách -> tra public KB (chính sách/FAQ).
        last_user_q = next(
            (m.content for m in reversed(payload.messages) if m.role == "user" and m.content.strip()),
            "",
        )
        normalized = [{"role": "system", "content": GUEST_SYSTEM_PROMPT}]
        if last_user_q:
            try:
                from agent.public_kb import search_public_knowledge, format_public_for_prompt
                kb = format_public_for_prompt(search_public_knowledge(mask_pii(last_user_q), top_k=3))
                normalized.append({"role": "system", "content": kb})
            except Exception as exc:
                print(f"[agent_chat] public KB lookup failed: {exc}", flush=True)
        _append_safe_client_history(normalized, payload.messages)
        _t0 = time.time()
        try:
            # Chạy ReAct agent nhưng CHỈ với GUEST_TOOLS (submit_feedback).
            # Truyền tools_override và execute_fn để agent không có quyền gọi OPS tools.
            result = run_chat_agent(
                normalized,
                temperature=0.4,
                tools_override=GUEST_TOOLS_DEFINITIONS,
                execute_fn=lambda name, args: execute_guest_tool(name, args, user_id=user.id),
            )
        except Exception as exc:
            _log_chat_event("guest", "error", int((time.time() - _t0) * 1000), error=str(exc)[:200])
            raise HTTPException(status_code=502, detail=f"Agent model error: {str(exc)[:300]}") from exc
        if isinstance(result.get("content"), str):
            result["content"] = mask_pii(result["content"])
        _log_chat_event("guest", "success", int((time.time() - _t0) * 1000),
                        provider=result.get("provider", ""), model=result.get("model", ""))
        return {"status": "success", "data": result}

    # Staff / manager / admin — apply a higher rate limit to prevent LLM API key abuse
    check_rate_limit(chat_rate_limit_staff, user.id)

    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    if user.role in {"manager", "staff"} and not user.department:
        raise HTTPException(status_code=403, detail="Bạn chưa được gán phòng ban. Vui lòng liên hệ admin.")
    # ops đã gán phòng -> scope mọi dữ liệu/tool về đúng phòng; admin -> None (toàn hệ thống)
    scope_team = user.department if (user.role != "admin" and user.department) else None
    normalized = [
        {"role": "system", "content": build_agent_system_prompt(user)},
        {"role": "system", "content": build_agent_data_context(user)},
    ]
    _append_safe_client_history(normalized, payload.messages)
    # Log theo phòng: ops -> phòng của mình; admin -> "admin" (toàn hệ thống).
    log_team = scope_team or ("admin" if user.role == "admin" else "unassigned")
    _t0 = time.time()
    try:
        result = run_chat_agent(normalized, temperature=0.4, scope_team=scope_team)
    except Exception as exc:
        _log_chat_event(log_team, "error", int((time.time() - _t0) * 1000), error=str(exc)[:200])
        raise HTTPException(status_code=502, detail=f"Agent model error: {str(exc)[:300]}") from exc
    # OWASP LLM: mask PII from LLM output before returning to client
    if isinstance(result.get("content"), str):
        result["content"] = mask_pii(result["content"])
    _log_chat_event(log_team, "success", int((time.time() - _t0) * 1000),
                    provider=result.get("provider", ""), model=result.get("model", ""))
    return {"status": "success", "data": result}


@app.post("/api/agent/rag-chat")
def agent_rag_chat(payload: ChatReq, user: AuthUser = Depends(require_ops_staff)):
    check_rate_limit(chat_rate_limit_staff, user.id)

    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    
    scope_team = user.department if (user.role != "admin" and user.department) else None
    log_team = scope_team or ("admin" if user.role == "admin" else "unassigned")
    
    msg_dicts = [{"role": m.role, "content": m.content.strip()} for m in payload.messages[-CHAT_HISTORY_LIMIT:]]
    
    _t0 = time.time()
    try:
        result = rag_chat(msg_dicts, scope_team=scope_team)
    except Exception as exc:
        _log_chat_event(log_team, "error", int((time.time() - _t0) * 1000), error=str(exc)[:200])
        raise HTTPException(status_code=502, detail=f"RAG engine error: {str(exc)[:300]}") from exc
    
    _log_chat_event(log_team, "success", int((time.time() - _t0) * 1000),
                    provider=result.get("provider", ""), model=result.get("model", ""))
    return {"status": "success", "data": result}

@app.post("/api/ingest-real-dataset")
def ingest_real_dataset(
    limit: int | None = Query(default=None, ge=1),
    batch_size: int = Query(default=150, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: AuthUser = Depends(require_admin),
):
    """
    Ingest dataset thật từ thư mục /data. Không truyền limit thì chạy toàn bộ file.
    """
    dataset_file = _s.real_data_file or DEFAULT_DATA_FILE
    try:
        result = ingest_dataset(dataset_file, limit=limit, batch_size=batch_size, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if result["success"]:
        return {"status": "success", "data": result}
    else:
        return {"status": "error", "message": result["error"]}

@app.post("/api/live-stream/start")
def start_live_feedback_stream(
    batch_size: int = Query(default=150, ge=1, le=500),
    interval_seconds: int = Query(default=5, ge=1, le=3600),
    loop: bool = Query(default=False),
    reset: bool = Query(default=False),
    auto_ticket: bool = Query(default=True),
    ticket_every_batches: int = Query(default=2, ge=1, le=100),
    ticket_max_spikes: int = Query(default=6, ge=1, le=10),
    _: AuthUser = Depends(require_admin),
):
    """
    Bắt đầu live stream feedback từ dataset thật trong /data.
    Mỗi interval sẽ ingest một batch tiếp theo.
    """
    try:
        result = start_live_stream(
            batch_size,
            interval_seconds,
            loop,
            reset,
            auto_ticket,
            ticket_every_batches,
            ticket_max_spikes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "success", "data": result}

@app.post("/api/live-stream/stop")
def stop_live_feedback_stream(_: AuthUser = Depends(require_admin)):
    return {"status": "success", "data": stop_live_stream()}

@app.get("/api/live-stream/status")
def live_feedback_stream_status(_: AuthUser = Depends(require_ops_staff)):
    return {"status": "success", "data": get_live_stream_status()}

@app.post("/api/run-real-pipeline")
def run_real_pipeline(
    limit: int | None = Query(default=None, ge=1),
    batch_size: int = Query(default=150, ge=1, le=500),
    max_feedback: int = Query(default=1000, ge=1, le=5000),
    max_spikes: int = Query(default=3, ge=1, le=20),
    _: AuthUser = Depends(require_admin),
):
    """
    Chạy luồng thật: ingest dataset từ /data rồi detect spike/agent.
    """
    dataset_file = _s.real_data_file or DEFAULT_DATA_FILE
    try:
        ingest_result = ingest_dataset(dataset_file, limit=limit, batch_size=batch_size)
        if not ingest_result["success"]:
            return {"status": "error", "stage": "ingest", "message": ingest_result["error"]}

        from spike_detector import detect_spikes

        spike_result = detect_spikes(max_feedback=max_feedback, max_spikes=max_spikes)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "ingest": ingest_result,
            "spike": spike_result,
        },
    }

@app.post("/api/trigger-spike-detect")
def trigger_spike_detect(
    max_feedback: int = Query(default=1000, ge=1, le=5000),
    max_spikes: int = Query(default=3, ge=1, le=20),
    _: AuthUser = Depends(require_admin),
):
    """
    Endpoint để kích hoạt thủ công tiến trình Spike Detection
    """
    from spike_detector import detect_spikes
    try:
        result = detect_spikes(max_feedback=max_feedback, max_spikes=max_spikes)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"status": "success", "data": result}

@app.post("/api/feedback/submit")
def submit_feedback(payload: dict, user: AuthUser = Depends(get_current_user)):
    """Người dùng gửi phản hồi: CHỈ nhập text + kênh + khu vực.

    Topic / sentiment / severity / confidence do AI tự phân tích (classifier +
    rule Safety) — KHÔNG cho người gửi tự chọn, tránh làm hỏng dữ liệu nhãn.
    """
    if user.role == "guest":
        check_rate_limit(feedback_rate_limit, user.id)

    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Thiếu nội dung phản hồi (text)")

    channel = (payload.get("channel") or "app").strip() or "app"
    from regions import region_code
    area = region_code((payload.get("area") or "").strip())

    from clean import clean_text
    from classifier import predict_feedback

    cleaned = clean_text(text)
    prediction = predict_feedback(cleaned)

    severity = prediction["severity"]
    severity_value = severity if isinstance(severity, str) and severity.upper().startswith("P") else f"P{int(severity)}"

    row = {
        "user_id": user.id,
        "source": "manual",
        "channel": channel,
        "text": cleaned,
        "topic": prediction["topic"],
        "sentiment": prediction["sentiment"],
        "severity": severity_value,
        "confidence": prediction["confidence"],
        "area": area,
        "needs_review": prediction.get("needs_review", False),
        "review_reason": prediction.get("review_reason"),
    }
    try:
        db = get_supabase()
        data = db.table("feedback").insert(row).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot save feedback: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0] if data else row}

@app.patch("/api/feedback/{feedback_id}/label")
def correct_feedback_label(
    feedback_id: str,
    payload: dict,
    user: AuthUser = Depends(require_ops_staff),
):
    """Human-in-the-loop: nhân viên sửa nhãn AI gán sai.

    Nhận các field muốn sửa (topic / sentiment / severity). Ghi lại giá trị
    cũ -> mới vào correction_logs (audit), rồi cập nhật feedback. Sau khi người
    sửa, confidence được set = 1.0 (nhãn do người xác nhận, không cần duyệt nữa).
    """
    ALLOWED = {"topic", "sentiment", "severity"}
    changes = {k: v for k, v in payload.items() if k in ALLOWED and isinstance(v, str) and v.strip()}
    if not changes:
        raise HTTPException(status_code=400, detail="Không có nhãn hợp lệ để sửa (topic/sentiment/severity)")

    db = get_supabase()
    rows = db.table("feedback").select("*").eq("id", feedback_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Feedback not found")
    current = rows[0]

    # Ghi audit cho từng field thực sự đổi.
    log_entries = []
    for field, new_val in changes.items():
        old_val = current.get(field)
        if str(old_val) == str(new_val):
            continue
        log_entries.append({
            "feedback_id": feedback_id,
            "corrected_by": user.id,
            "field": field,
            "old_value": str(old_val) if old_val is not None else None,
            "new_value": new_val,
        })

    if not log_entries:
        return {"status": "success", "data": current, "note": "Không có thay đổi"}

    update = {k: changes[k] for k in changes}
    update["confidence"] = 1.0  # nhãn do người xác nhận
    update["reviewed"] = True   # đã có người sửa = đã duyệt
    update["needs_review"] = False
    try:
        db.table("correction_logs").insert(log_entries).execute()
        updated = db.table("feedback").update(update).eq("id", feedback_id).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot correct label: {str(exc)[:300]}") from exc
    return {"status": "success", "data": updated[0] if updated else current, "corrections": len(log_entries)}


@app.patch("/api/feedback/{feedback_id}/review")
def review_feedback(
    feedback_id: str,
    payload: dict | None = None,
    user: AuthUser = Depends(require_ops_staff),
):
    """Duyệt / đánh dấu đã xử lý: chuyển feedback khỏi Review Queue.

    action='approve'  -> reviewed=true, needs_review=false (xác nhận nhãn AI đúng).
    action='handled'  -> như approve (đã xử lý xong). Giữ đơn giản cho demo.
    """
    db = get_supabase()
    rows = db.table("feedback").select("id").eq("id", feedback_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Feedback not found")
    try:
        updated = db.table("feedback").update(
            {"reviewed": True, "needs_review": False}
        ).eq("id", feedback_id).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot review feedback: {str(exc)[:300]}") from exc
    return {"status": "success", "data": updated[0] if updated else None}


@app.post("/api/feedback/reclassify")
def reclassify_feedback(
    limit: int = Query(default=5000, ge=1, le=10000),
    _: AuthUser = Depends(require_admin),
):
    """Phân loại lại feedback cũ bằng rule engine mới (admin only).

    Đọc text từng feedback -> predict_feedback -> cập nhật topic/sentiment/
    severity/confidence/needs_review/review_reason. Bỏ qua bản đã có người duyệt
    (reviewed=true) để không ghi đè nhãn người đã sửa.
    """
    from classifier import predict_feedback
    from regions import region_code

    db = get_supabase()
    rows = db.table("feedback").select("id,text,area,reviewed").limit(limit).execute().data or []
    updated_count = 0
    needs_review_count = 0
    for r in rows:
        if r.get("reviewed"):
            continue
        pred = predict_feedback(r.get("text") or "")
        sev = pred["severity"]
        sev_val = sev if isinstance(sev, str) and sev.upper().startswith("P") else f"P{int(sev)}"
        upd = {
            "topic": pred["topic"],
            "sentiment": pred["sentiment"],
            "severity": sev_val,
            "confidence": pred["confidence"],
            "needs_review": pred.get("needs_review", False),
            "review_reason": pred.get("review_reason"),
            "area": region_code(r.get("area")),
        }
        try:
            db.table("feedback").update(upd).eq("id", r["id"]).execute()
            updated_count += 1
            if upd["needs_review"]:
                needs_review_count += 1
        except Exception:
            continue
    return {
        "status": "success",
        "data": {"updated": updated_count, "needs_review": needs_review_count, "scanned": len(rows)},
    }

# ============================================================
# Multi-agent layer: insight theo phòng ban + root-cause analysis
# ============================================================

@app.get("/api/insights/departments")
def list_department_insights(
    hours: int = Query(default=24, ge=1, le=720),
    user: AuthUser = Depends(require_ops_staff),
):
    """Chạy orchestrator: tổng hợp insight + root-cause cho mọi phòng ban.

    Admin thấy mọi phòng; ops khác chỉ thấy phòng của mình (chưa gán phòng -> 403)."""
    from agents.orchestrator import run_agent_pipeline
    try:
        result = run_agent_pipeline(hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent pipeline error: {str(exc)[:300]}") from exc
    if user.role != "admin":
        own_team = scoped_team(user, None)  # raise 403 nếu chưa gán phòng
        data = result.get("data") if isinstance(result, dict) else None
        if isinstance(data, dict):
            result["data"] = {k: v for k, v in data.items() if k == own_team}
    return {"status": "success", "data": result}

@app.get("/api/insights/departments/{team}")
def get_department_insights(
    team: str,
    hours: int = Query(default=24, ge=1, le=720),
    with_analysis: bool = Query(default=True),
    user: AuthUser = Depends(require_ops_staff),
):
    """Insight cho 1 phòng ban; with_analysis=true thì gọi LLM phân tích root cause."""
    if not can_view_team(user, team):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem dữ liệu của phòng ban này.")
    from agents.insight_agent import generate_department_insights
    from agents.analyst_agent import analyze_root_cause
    try:
        insights = generate_department_insights(team, hours)
        if with_analysis and insights.get("total_feedback", 0) > 0:
            insights["analysis"] = analyze_root_cause(team, insights)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Insight error: {str(exc)[:300]}") from exc
    return {"status": "success", "data": insights}

@app.get("/api/cockpit/overview")
def cockpit_overview(
    days: int = Query(default=14, ge=1, le=90),
    user: AuthUser = Depends(get_current_user),
):
    """Số liệu tổng hợp cho Quality Cockpit, scope theo RBAC phòng ban.

    - admin: toàn bộ phòng.
    - manager/staff đã gán phòng: chỉ phòng mình.
    - manager/staff chưa gán phòng: trả unassigned=true (frontend hiện thông báo).
    - guest: payload rút gọn (kpis cơ bản + trend + categories; không alerts/tickets/heatmap).

    Mọi truy vấn bọc try/except — lỗi DB không làm vỡ trang (trả field rỗng + db_error).
    """
    role = user.role
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days)
    empty_heatmap = {"areas": [], "hours": COCKPIT_HOUR_BUCKETS, "cells": []}

    # ----- Scope theo RBAC -----
    restricted = role == "guest"
    if role == "admin":
        team = None
    elif role in ("manager", "staff"):
        if not user.department:
            # Khác /api/insights: cockpit không 403, trả cờ unassigned để frontend hiện thông báo.
            return {"status": "success", "data": {
                "scope": {"team": None, "role": role, "unassigned": True, "restricted": False},
                "window_days": days,
                "generated_at": now.isoformat(),
                "kpis": {}, "trend": [], "trend_sentiment": [], "categories": [],
                "heatmap": empty_heatmap, "risk_distribution": [],
                "funnel": {}, "sankey_flows": [],
                "db_error": None,
            }}
        team = user.department
    else:  # guest
        team = None

    # ----- Lấy feedback trong cửa sổ (1 lượt), filter theo phòng nếu là ops -----
    db_error = None
    feedback_rows: list[dict] = []
    try:
        db = get_supabase()
        rows = db.table("feedback") \
            .select("id,topic,sentiment,severity,area,created_at,needs_review,overall_risk") \
            .gte("created_at", window_start.isoformat()) \
            .order("created_at", desc=True) \
            .limit(5000) \
            .execute().data or []
        if team:
            rows = [r for r in rows if _feedback_team(r) == team]
        feedback_rows = rows
    except Exception as exc:  # noqa: BLE001 - stats không được làm vỡ trang
        db_error = str(exc)[:200]

    # ----- Aggregate feedback -----
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    feedback_today = feedback_yesterday = neg_today = needs_review = 0
    total_window = neg_window = 0

    trend_map: dict[str, dict] = {}
    for i in range(days):
        d = (today_start - timedelta(days=days - 1 - i)).date().isoformat()
        trend_map[d] = {"date": d, "total": 0, "negative": 0}

    # trend_sentiment: cùng cấu trúc trend_map nhưng tách theo sentiment
    sentiment_map: dict[str, dict] = {}
    for d in trend_map:
        sentiment_map[d] = {"date": d, "positive": 0, "neutral": 0, "negative": 0}

    cat_counts: dict[str, int] = {}
    heat: dict[tuple, int] = {}
    area_neg_total: dict[str, int] = {}
    risk_counter: dict[int, int] = {}          # overall_risk 1-10
    classified_count = 0                         # có topic != null
    sankey_sent_sev: dict[tuple, int] = {}      # (sentiment, severity) → count

    for r in feedback_rows:
        dt = _parse_timestamp(r.get("created_at"))
        if not dt:
            continue
        sent = r.get("sentiment") or "neutral"
        is_neg = sent == "negative"
        total_window += 1
        if is_neg:
            neg_window += 1
        dkey = dt.date().isoformat()
        if dkey in trend_map:
            trend_map[dkey]["total"] += 1
            if is_neg:
                trend_map[dkey]["negative"] += 1
        if dkey in sentiment_map:
            key = sent if sent in ("positive", "neutral", "negative") else "neutral"
            sentiment_map[dkey][key] += 1
        if dt >= today_start:
            feedback_today += 1
            if is_neg:
                neg_today += 1
        elif dt >= yesterday_start:
            feedback_yesterday += 1
        if r.get("needs_review"):
            needs_review += 1
        topic = r.get("topic") or "Khác"
        if r.get("topic"):
            classified_count += 1
        cat_counts[topic] = cat_counts.get(topic, 0) + 1
        if is_neg:
            area = r.get("area") or "Khác"
            hb = _hour_bucket(dt)
            heat[(area, hb)] = heat.get((area, hb), 0) + 1
            area_neg_total[area] = area_neg_total.get(area, 0) + 1
        # risk distribution
        risk_raw = r.get("overall_risk")
        if risk_raw is not None:
            try:
                score = max(1, min(10, int(risk_raw)))
                risk_counter[score] = risk_counter.get(score, 0) + 1
            except (ValueError, TypeError):
                pass
        # sankey layer1: sentiment × severity
        sev = r.get("severity") or ""
        if sent in ("positive", "neutral", "negative") and sev:
            sankey_sent_sev[(sent, sev)] = sankey_sent_sev.get((sent, sev), 0) + 1

    feedback_today_delta_pct = (
        round((feedback_today - feedback_yesterday) / feedback_yesterday * 100, 1)
        if feedback_yesterday else None
    )
    negative_rate = round(neg_window / total_window * 100, 1) if total_window else 0.0
    negative_rate_today = round(neg_today / feedback_today * 100, 1) if feedback_today else 0.0

    categories = [
        {"topic": t, "count": c, "pct": round(c / total_window * 100, 1) if total_window else 0.0}
        for t, c in sorted(cat_counts.items(), key=lambda kv: -kv[1])
    ]

    top_areas = [a for a, _ in sorted(area_neg_total.items(), key=lambda kv: -kv[1])[:7]]
    cells = [
        {"area": a, "hour": hb, "negative_count": c}
        for (a, hb), c in heat.items() if a in top_areas
    ]

    kpis = {
        "feedback_today": feedback_today,
        "feedback_today_delta_pct": feedback_today_delta_pct,
        "negative_rate": negative_rate,
        "negative_rate_today": negative_rate_today,
        "needs_review": needs_review,
        "window_total": total_window,
    }

    # ----- KPI từ tasks/alerts/correction_logs (chỉ ops/admin) -----
    if not restricted and db_error is None:
        alerts_open = tickets_open = corrections_7d = 0
        tickets_by_priority: dict[str, int] = {}
        try:
            db = get_supabase()
            tq = db.table("tasks").select("status,priority,assigned_team").neq("status", "resolved").limit(2000)
            if team:
                tq = tq.eq("assigned_team", team)
            for t in tq.execute().data or []:
                tickets_open += 1
                p = t.get("priority") or "P3"
                tickets_by_priority[p] = tickets_by_priority.get(p, 0) + 1
            arows = db.table("alerts").select("*").neq("status", "resolved") \
                .order("created_at", desc=True).limit(2000).execute().data or []
            if team:
                arows = [a for a in arows if alert_department(a) == team]
            alerts_open = len(arows)
            corrections_7d = len(
                db.table("correction_logs").select("id")
                .gte("created_at", (now - timedelta(days=7)).isoformat())
                .limit(5000).execute().data or []
            )
        except Exception as exc:  # noqa: BLE001
            db_error = str(exc)[:200]
        kpis.update({
            "alerts_open": alerts_open,
            "tickets_open": tickets_open,
            "tickets_by_priority": tickets_by_priority,
            "corrections_7d": corrections_7d,
        })

    # ----- Chart data: risk_distribution -----
    risk_distribution = [
        {"score": s, "count": risk_counter.get(s, 0)} for s in range(1, 11)
    ]

    # ----- Chart data: trend_sentiment -----
    trend_sentiment = list(sentiment_map.values())

    # ----- Chart data: funnel + sankey (chỉ ops/admin) -----
    funnel: dict = {}
    sankey_flows: list = []
    if not restricted and db_error is None:
        try:
            db2 = get_supabase()
            # Funnel: alerts + tasks trong cửa sổ
            alerts_triggered = len(
                db2.table("alerts").select("id")
                .gte("created_at", window_start.isoformat())
                .limit(5000).execute().data or []
            )
            all_tasks = db2.table("tasks").select("id,status,priority,assigned_team") \
                .gte("created_at", window_start.isoformat()) \
                .limit(5000).execute().data or []
            if team:
                all_tasks = [t for t in all_tasks if t.get("assigned_team") == team]
            tickets_created = len(all_tasks)
            resolved_count = sum(1 for t in all_tasks if t.get("status") == "resolved")
            funnel = {
                "total": total_window,
                "classified": classified_count,
                "needs_review": needs_review,
                "alerts_triggered": alerts_triggered,
                "tickets_created": tickets_created,
                "resolved": resolved_count,
            }
            # Sankey layer 2: severity × status từ tasks
            sankey_sev_status: dict[tuple, int] = {}
            for t in all_tasks:
                p = t.get("priority") or ""
                s = t.get("status") or ""
                if p and s:
                    sankey_sev_status[(p, s)] = sankey_sev_status.get((p, s), 0) + 1
            # Merge flows
            for (sent, sev), v in sankey_sent_sev.items():
                if v > 0:
                    sankey_flows.append({"from": sent, "to": sev, "value": v})
            for (sev, st), v in sankey_sev_status.items():
                if v > 0:
                    sankey_flows.append({"from": sev, "to": st, "value": v})
        except Exception as exc:  # noqa: BLE001
            db_error = str(exc)[:200]

    return {"status": "success", "data": {
        "scope": {"team": team, "role": role, "unassigned": False, "restricted": restricted},
        "window_days": days,
        "generated_at": now.isoformat(),
        "kpis": kpis,
        "trend": list(trend_map.values()),
        "trend_sentiment": trend_sentiment,
        "categories": categories,
        "heatmap": empty_heatmap if restricted else {
            "areas": top_areas, "hours": COCKPIT_HOUR_BUCKETS, "cells": cells,
        },
        "risk_distribution": risk_distribution,
        "funnel": funnel,
        "sankey_flows": sankey_flows,
        "db_error": db_error,
    }}


@app.post("/api/agent/run")
def run_multi_agent_pipeline(
    hours: int = Query(default=24, ge=1, le=720),
    _: AuthUser = Depends(require_admin),
):
    """Kích hoạt thủ công toàn bộ multi-agent pipeline (admin only)."""
    from agents.orchestrator import run_agent_pipeline
    try:
        result = run_agent_pipeline(hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent pipeline error: {str(exc)[:300]}") from exc
    return {"status": "success", "data": result}

@app.post("/api/agent/generate-report")
def trigger_daily_report(
    team: str,
    user: AuthUser = Depends(require_ops_staff),
):
    """Generate the latest report; managers are restricted to their department."""
    if user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Chỉ Manager hoặc Admin được tạo báo cáo.")
    effective_team = scoped_team(user, team)
    if not effective_team:
        raise HTTPException(status_code=400, detail="Vui lòng chọn phòng ban cần tạo báo cáo.")
    from agents.task_agent import generate_daily_report
    try:
        result = generate_daily_report(effective_team)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Report generation error: {str(exc)[:300]}") from exc
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("error", "Report generation failed"))
    return {"status": "success", "data": result}

@app.get("/api/health/services")
def health_services(_: AuthUser = Depends(require_ops_staff)):
    """System health check — trạng thái tất cả services + LLM providers (ops staff+)."""
    from datetime import datetime, timezone
    import time

    # API Gateway latency — đo thời gian xử lý nội bộ (round-trip nhẹ)
    api_start = time.perf_counter()

    # DB connectivity + latency
    db_status = "ok"
    db_error = None
    db_latency_ms = None
    try:
        db = get_supabase()
        db_t0 = time.perf_counter()
        db.table("feedback").select("id").limit(1).execute()
        db_latency_ms = round((time.perf_counter() - db_t0) * 1000)
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)[:200]

    # LLM provider status
    agent_info = get_agent_status()
    llm_configured = agent_info.get("configured", {})
    active_provider = agent_info.get("provider", "unknown")
    active_model = agent_info.get("model", "unknown")
    llm_has_key = agent_info.get("has_key", False)
    llm_latency_ms = agent_info.get("last_latency_ms")

    # Worker status via ticket_workflow_state (only backend-worker reports state here)
    workflow = dict(ticket_workflow_state)

    # Live stream state
    stream = get_live_stream_status()

    # Rate limit settings (no counts — just config for visibility)
    rate_limits = {
        "chat_guest_per_hour": _s.rate_limit_chat_guest,
        "chat_staff_per_hour": _s.rate_limit_chat_staff,
        "feedback_guest_per_hour": _s.rate_limit_feedback_guest,
    }

    api_latency_ms = round((time.perf_counter() - api_start) * 1000)

    return {
        "status": "success",
        "data": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "api_gateway": {
                "status": "ok",
                "latency_ms": api_latency_ms,
                "error_rate": 0,
            },
            "database": {
                "status": db_status,
                "error": db_error,
                "latency_ms": db_latency_ms,
                "error_rate": 0 if db_status == "ok" else 100,
            },
            "llm": {
                "active_provider": active_provider,
                "active_model": active_model,
                "configured_providers": llm_configured,
                "has_key": llm_has_key,
                "latency_ms": llm_latency_ms,
            },
            "ticket_workflow": workflow,
            "live_stream": stream,
            "rate_limits": rate_limits,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
