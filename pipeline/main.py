from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import os
from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

from ingest import ingest_dataset
from ingest import get_supabase
from agent import chat_completion, get_agent_status
from auth_guard import AuthUser, get_current_user, require_admin, require_ops_staff
from users_admin import router as users_router

PIPELINE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(PIPELINE_DIR, ".."))
DEFAULT_DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "seed_real_clean.json",
)

scheduler: BackgroundScheduler | None = None
live_stream_lock = Lock()
live_stream_tick_lock = Lock()
live_stream_state = {
    "running": False,
    "offset": 0,
    "batch_size": int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
    "interval_seconds": int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "10")),
    "loop": os.getenv("LIVE_STREAM_LOOP", "false").lower() == "true",
    "auto_ticket": os.getenv("AUTO_TICKET_ENABLED", "true").lower() == "true",
    "ticket_every_batches": int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "10")),
    "ticket_max_feedback": int(os.getenv("AUTO_TICKET_MAX_FEEDBACK", "1000")),
    "ticket_max_spikes": int(os.getenv("AUTO_TICKET_MAX_SPIKES", "1")),
    "ticket_running": False,
    "batches_ingested": 0,
    "last_ticket_result": None,
    "last_ticket_error": None,
    "last_ticket_at": None,
    "last_ticket_batch": None,
    "last_result": None,
    "last_error": None,
}
ticket_workflow_state = {
    "enabled": os.getenv("AUTO_TICKET_WORKFLOW_ENABLED", "true").lower() == "true",
    "in_progress_after_seconds": int(os.getenv("AUTO_TICKET_IN_PROGRESS_AFTER_SECONDS", "10")),
    "resolved_after_seconds": int(os.getenv("AUTO_TICKET_RESOLVED_AFTER_SECONDS", "30")),
    "last_run_at": None,
    "moved_to_in_progress": 0,
    "moved_to_resolved": 0,
    "last_error": None,
}

def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def advance_ticket_workflow():
    if not ticket_workflow_state["enabled"]:
        return
    try:
        db = get_supabase()
        rows = db.table("alerts") \
            .select("id,status,created_at") \
            .in_("status", ["open", "in_progress"]) \
            .order("created_at", desc=False) \
            .limit(200) \
            .execute() \
            .data or []
        now = datetime.now(timezone.utc)
        moved_to_in_progress = 0
        moved_to_resolved = 0

        for row in rows:
            created_at = parse_timestamp(row.get("created_at"))
            if not created_at:
                continue
            age_seconds = (now - created_at.astimezone(timezone.utc)).total_seconds()
            if row.get("status") == "open" and age_seconds >= ticket_workflow_state["in_progress_after_seconds"]:
                db.table("alerts").update({"status": "in_progress"}).eq("id", row["id"]).execute()
                moved_to_in_progress += 1
            elif row.get("status") == "in_progress" and age_seconds >= ticket_workflow_state["resolved_after_seconds"]:
                db.table("alerts").update({"status": "resolved"}).eq("id", row["id"]).execute()
                moved_to_resolved += 1

        ticket_workflow_state["last_run_at"] = now.isoformat()
        ticket_workflow_state["moved_to_in_progress"] = moved_to_in_progress
        ticket_workflow_state["moved_to_resolved"] = moved_to_resolved
        ticket_workflow_state["last_error"] = None
    except Exception as exc:
        ticket_workflow_state["last_error"] = str(exc)

def run_auto_ticket_detection():
    try:
        from spike_detector import detect_spikes

        with live_stream_lock:
            max_feedback = int(live_stream_state["ticket_max_feedback"])
            max_spikes = int(live_stream_state["ticket_max_spikes"])
            live_stream_state["last_ticket_error"] = None

        result = detect_spikes(max_feedback=max_feedback, max_spikes=max_spikes)
        with live_stream_lock:
            live_stream_state["last_ticket_result"] = result
            live_stream_state["last_ticket_error"] = None
            live_stream_state["last_ticket_at"] = datetime.now(timezone.utc).isoformat()
            live_stream_state["last_ticket_batch"] = live_stream_state["batches_ingested"]
    except Exception as exc:
        with live_stream_lock:
            live_stream_state["last_ticket_error"] = str(exc)
    finally:
        with live_stream_lock:
            live_stream_state["ticket_running"] = False

def live_stream_tick():
    if not live_stream_tick_lock.acquire(blocking=False):
        return
    try:
        _live_stream_tick()
    finally:
        live_stream_tick_lock.release()

def _live_stream_tick():
    dataset_file = os.getenv("REAL_DATA_FILE", DEFAULT_DATA_FILE)
    with live_stream_lock:
        if not live_stream_state["running"]:
            return
        offset = int(live_stream_state["offset"])
        batch_size = int(live_stream_state["batch_size"])

    try:
        result = ingest_dataset(
            dataset_file,
            limit=batch_size,
            batch_size=batch_size,
            offset=offset,
        )
        with live_stream_lock:
            live_stream_state["last_result"] = result
            live_stream_state["last_error"] = None
            if result.get("success"):
                live_stream_state["batches_ingested"] += 1
                should_detect = (
                    live_stream_state["auto_ticket"]
                    and not live_stream_state["ticket_running"]
                    and live_stream_state["batches_ingested"] % int(live_stream_state["ticket_every_batches"]) == 0
                )
                if should_detect:
                    live_stream_state["ticket_running"] = True
                if result.get("complete"):
                    if live_stream_state["loop"]:
                        live_stream_state["offset"] = 0
                    else:
                        live_stream_state["running"] = False
                        if scheduler and scheduler.get_job("live_feedback_stream"):
                            scheduler.remove_job("live_feedback_stream")
                else:
                    live_stream_state["offset"] = result.get("next_offset", offset + batch_size)
            else:
                live_stream_state["running"] = False
                should_detect = False
        if should_detect and scheduler:
            scheduler.add_job(
                run_auto_ticket_detection,
                id="auto_ticket_detection",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
    except Exception as exc:
        with live_stream_lock:
            live_stream_state["last_error"] = str(exc)
            live_stream_state["running"] = False
        if scheduler and scheduler.get_job("live_feedback_stream"):
            scheduler.remove_job("live_feedback_stream")

def start_live_stream(
    batch_size: int,
    interval_seconds: int,
    loop: bool,
    reset: bool = False,
    auto_ticket: bool = True,
    ticket_every_batches: int = 10,
    ticket_max_spikes: int = 1,
):
    if not scheduler:
        raise ValueError("Scheduler is not initialized")
    with live_stream_lock:
        if reset:
            live_stream_state["offset"] = 0
            live_stream_state["batches_ingested"] = 0
            live_stream_state["last_ticket_result"] = None
            live_stream_state["last_ticket_error"] = None
            live_stream_state["last_ticket_at"] = None
            live_stream_state["last_ticket_batch"] = None
        live_stream_state["batch_size"] = batch_size
        live_stream_state["interval_seconds"] = interval_seconds
        live_stream_state["loop"] = loop
        live_stream_state["auto_ticket"] = auto_ticket
        live_stream_state["ticket_every_batches"] = ticket_every_batches
        live_stream_state["ticket_max_spikes"] = ticket_max_spikes
        live_stream_state["running"] = True
        live_stream_state["ticket_running"] = False
        live_stream_state["last_error"] = None

    scheduler.add_job(
        live_stream_tick,
        "interval",
        seconds=interval_seconds,
        id="live_feedback_stream",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    return get_live_stream_status()

def stop_live_stream():
    with live_stream_lock:
        live_stream_state["running"] = False
    if scheduler and scheduler.get_job("live_feedback_stream"):
        scheduler.remove_job("live_feedback_stream")
    return get_live_stream_status()

def get_live_stream_status():
    with live_stream_lock:
        return dict(live_stream_state)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(
        advance_ticket_workflow,
        "interval",
        seconds=5,
        id="auto_ticket_workflow",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    print("APScheduler started successfully.")
    if os.getenv("LIVE_STREAM_ENABLED", "false").lower() == "true":
        start_live_stream(
            batch_size=int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
            interval_seconds=int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "10")),
            loop=os.getenv("LIVE_STREAM_LOOP", "false").lower() == "true",
            reset=os.getenv("LIVE_STREAM_RESET_ON_START", "false").lower() == "true",
            auto_ticket=os.getenv("AUTO_TICKET_ENABLED", "true").lower() == "true",
            ticket_every_batches=int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "10")),
            ticket_max_spikes=int(os.getenv("AUTO_TICKET_MAX_SPIKES", "1")),
        )
    yield
    scheduler.shutdown()

app = FastAPI(
    title="AI Quality Intelligence Platform API",
    description="Backend API for Smart Mobility Feedback Analytics",
    version="1.0.0",
    lifespan=lifespan
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


@app.get("/api/me")
def whoami(user: AuthUser = Depends(get_current_user)):
    """Trả về danh tính + role của user đang đăng nhập (frontend dùng để render nav theo quyền)."""
    return {"status": "success", "data": {"id": user.id, "email": user.email, "role": user.role}}


AGENT_SYSTEM_PROMPT = """Bạn là AI Assistant cho Quality Operation Cockpit của xanhSM.
Nhiệm vụ: phân tích feedback, alerts, spike, vận hành khu vực, chất lượng tài xế/xe/app/thanh toán/an toàn.
Trả lời tiếng Việt, ngắn gọn, có cấu trúc, ưu tiên hành động cụ thể và mức độ ưu tiên P0/P1/P2."""

def build_agent_data_context() -> str:
    try:
        db = get_supabase()
        feedback = db.table("feedback") \
            .select("area,severity,sentiment,topic,created_at") \
            .order("created_at", desc=True) \
            .limit(300) \
            .execute() \
            .data or []
        alerts = db.table("alerts") \
            .select("title,severity,area,status,created_at") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute() \
            .data or []
    except Exception as exc:
        return f"DATA_CONTEXT_ERROR: Không đọc được Supabase context: {str(exc)[:200]}"

    severity_counts = Counter(row.get("severity") or "unknown" for row in feedback)
    sentiment_counts = Counter(row.get("sentiment") or "unknown" for row in feedback)
    topic_counts = Counter(row.get("topic") or "unknown" for row in feedback)
    area_counts = Counter(row.get("area") or "unknown" for row in feedback)
    alert_status_counts = Counter(row.get("status") or "unknown" for row in alerts)

    def top(counter: Counter, n: int = 8) -> str:
        return ", ".join(f"{k}: {v}" for k, v in counter.most_common(n)) or "none"

    return f"""
DATA_CONTEXT:
- Nguồn: Supabase feedback/alerts + live stream state.
- Feedback gần nhất đã đọc: {len(feedback)} records.
- Severity: {top(severity_counts)}
- Sentiment: {top(sentiment_counts)}
- Topic top: {top(topic_counts)}
- Area top: {top(area_counts)}
- Alerts gần nhất đã đọc: {len(alerts)} records.
- Alert status: {top(alert_status_counts)}
- Live stream: {get_live_stream_status()}

Recent alerts:
{os.linesep.join([f"- [{a.get('severity')}] {a.get('status')} | {a.get('area')} | {a.get('title')}" for a in alerts[:10]]) or "- none"}
"""

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Quality Intelligence API"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend service is running"}

@app.get("/api/feedback/recent")
def recent_feedback(limit: int = Query(default=100, ge=1, le=500)):
    try:
        db = get_supabase()
        data = db.table("feedback") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read feedback: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/alerts/recent")
def recent_alerts(limit: int = Query(default=100, ge=1, le=500)):
    try:
        db = get_supabase()
        data = db.table("alerts") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read alerts: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}

@app.get("/api/alerts/workflow-status")
def alert_workflow_status():
    return {"status": "success", "data": dict(ticket_workflow_state)}

@app.patch("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, payload: dict, _: AuthUser = Depends(require_ops_staff)):
    new_status = payload.get("status")
    if new_status not in {"open", "in_progress", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid alert status")
    try:
        db = get_supabase()
        data = db.table("alerts") \
            .update({"status": new_status}) \
            .eq("id", alert_id) \
            .execute() \
            .data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update alert: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "data": data[0]}

@app.get("/api/agent/status")
def agent_status():
    return {"status": "success", "data": get_agent_status()}

@app.get("/api/agent/logs")
def agent_logs(limit: int = Query(default=50, ge=1, le=500)):
    log_file = get_agent_status()["log_file"]
    if not os.path.exists(log_file):
        return {"status": "success", "data": []}
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    return {"status": "success", "data": [line.rstrip("\n") for line in lines]}

@app.post("/api/agent/chat")
def agent_chat(payload: dict):
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    normalized = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "system", "content": build_agent_data_context()},
    ]
    for message in messages[-30:]:
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant", "system"} or not isinstance(content, str) or not content.strip():
            raise HTTPException(status_code=400, detail="Invalid chat message")
        normalized.append({"role": role, "content": content[:8000]})
    try:
        result = chat_completion(normalized, temperature=0.4)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent model error: {str(exc)[:300]}") from exc
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
    dataset_file = os.getenv("REAL_DATA_FILE", DEFAULT_DATA_FILE)
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
    interval_seconds: int = Query(default=10, ge=1, le=3600),
    loop: bool = Query(default=False),
    reset: bool = Query(default=False),
    auto_ticket: bool = Query(default=True),
    ticket_every_batches: int = Query(default=10, ge=1, le=100),
    ticket_max_spikes: int = Query(default=1, ge=1, le=10),
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
def live_feedback_stream_status():
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
    dataset_file = os.getenv("REAL_DATA_FILE", DEFAULT_DATA_FILE)
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
    _: AuthUser = Depends(require_ops_staff),
):
    """Chạy orchestrator: tổng hợp insight + root-cause cho mọi phòng ban."""
    from agents.orchestrator import run_agent_pipeline
    try:
        result = run_agent_pipeline(hours=hours)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent pipeline error: {str(exc)[:300]}") from exc
    return {"status": "success", "data": result}

@app.get("/api/insights/departments/{team}")
def get_department_insights(
    team: str,
    hours: int = Query(default=24, ge=1, le=720),
    with_analysis: bool = Query(default=True),
    _: AuthUser = Depends(require_ops_staff),
):
    """Insight cho 1 phòng ban; with_analysis=true thì gọi LLM phân tích root cause."""
    from agents.insight_agent import generate_department_insights
    from agents.analyst_agent import analyze_root_cause
    try:
        insights = generate_department_insights(team, hours)
        if with_analysis and insights.get("total_feedback", 0) > 0:
            insights["analysis"] = analyze_root_cause(team, insights)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Insight error: {str(exc)[:300]}") from exc
    return {"status": "success", "data": insights}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
