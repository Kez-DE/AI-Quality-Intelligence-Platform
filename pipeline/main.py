from fastapi import FastAPI, HTTPException, Query
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

PIPELINE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(PIPELINE_DIR, "..", ".."))
DEFAULT_DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "seed_real_clean (1).json",
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
def update_alert_status(alert_id: str, payload: dict):
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
def stop_live_feedback_stream():
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
