import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from core.paths import DEFAULT_DATA_FILE
from ingest import ingest_dataset

scheduler: BackgroundScheduler | None = None
live_stream_lock = Lock()
live_stream_tick_lock = Lock()
live_stream_state: dict[str, Any] = {
    "running": False,
    "offset": 0,
    "batch_size": int(os.getenv("LIVE_STREAM_BATCH_SIZE", "150")),
    "interval_seconds": int(os.getenv("LIVE_STREAM_INTERVAL_SECONDS", "5")),
    "loop": os.getenv("LIVE_STREAM_LOOP", "false").lower() == "true",
    "auto_ticket": os.getenv("AUTO_TICKET_ENABLED", "true").lower() == "true",
    "ticket_every_batches": int(os.getenv("AUTO_TICKET_EVERY_BATCHES", "2")),
    "ticket_max_feedback": int(os.getenv("AUTO_TICKET_MAX_FEEDBACK", "1000")),
    "ticket_max_spikes": int(os.getenv("AUTO_TICKET_MAX_SPIKES", "6")),
    "ticket_running": False,
    "batches_ingested": 0,
    "batch_running": False,
    "last_batch_started_at": None,
    "last_batch_completed_at": None,
    "last_ticket_result": None,
    "last_ticket_error": None,
    "last_ticket_at": None,
    "last_ticket_batch": None,
    "final_detection_requested": False,
    "last_result": None,
    "last_error": None,
}


def set_scheduler(active_scheduler: BackgroundScheduler | None):
    global scheduler
    scheduler = active_scheduler


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


def schedule_auto_ticket_detection():
    """Queue one detector run after state has been marked ticket_running."""
    if scheduler:
        scheduler.add_job(
            run_auto_ticket_detection,
            id="auto_ticket_detection",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        return
    with live_stream_lock:
        live_stream_state["ticket_running"] = False
        live_stream_state["last_ticket_error"] = "Scheduler is not initialized"


def claim_final_detection_request() -> bool:
    """Atomically claim a pending final scan when no equivalent scan is running."""
    with live_stream_lock:
        if not live_stream_state["final_detection_requested"]:
            return False
        current_batch = int(live_stream_state["batches_ingested"])
        if live_stream_state["ticket_running"]:
            # The active detector already reads all feedback committed so far.
            live_stream_state["final_detection_requested"] = False
            return False
        if (
            not live_stream_state["auto_ticket"]
            or current_batch <= 0
            or live_stream_state.get("last_ticket_batch") == current_batch
        ):
            live_stream_state["final_detection_requested"] = False
            return False
        live_stream_state["final_detection_requested"] = False
        live_stream_state["ticket_running"] = True
        return True


def live_stream_tick():
    if not live_stream_tick_lock.acquire(blocking=False):
        return
    detect_after_tick = False
    try:
        _live_stream_tick()
    finally:
        detect_after_tick = claim_final_detection_request()
        live_stream_tick_lock.release()
    if detect_after_tick:
        schedule_auto_ticket_detection()


def _live_stream_tick():
    dataset_file = os.getenv("REAL_DATA_FILE", DEFAULT_DATA_FILE)
    with live_stream_lock:
        if not live_stream_state["running"]:
            return
        offset = int(live_stream_state["offset"])
        batch_size = int(live_stream_state["batch_size"])
        live_stream_state["batch_running"] = True
        live_stream_state["last_batch_started_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = ingest_dataset(
            dataset_file,
            limit=batch_size,
            batch_size=batch_size,
            offset=offset,
            defer_llm_scoring=True,
        )
        with live_stream_lock:
            live_stream_state["last_result"] = result
            live_stream_state["last_error"] = None
            live_stream_state["batch_running"] = False
            live_stream_state["last_batch_completed_at"] = datetime.now(timezone.utc).isoformat()
            if result.get("success"):
                live_stream_state["batches_ingested"] += 1
                periodic_detection = (
                    live_stream_state["batches_ingested"]
                    % int(live_stream_state["ticket_every_batches"])
                    == 0
                )
                final_detection = bool(result.get("complete") and not live_stream_state["loop"])
                should_detect = (
                    live_stream_state["auto_ticket"]
                    and not live_stream_state["ticket_running"]
                    and (periodic_detection or final_detection)
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
        if should_detect:
            schedule_auto_ticket_detection()
    except Exception as exc:
        with live_stream_lock:
            live_stream_state["last_error"] = str(exc)
            live_stream_state["running"] = False
            live_stream_state["batch_running"] = False
            live_stream_state["last_batch_completed_at"] = datetime.now(timezone.utc).isoformat()
        if scheduler and scheduler.get_job("live_feedback_stream"):
            scheduler.remove_job("live_feedback_stream")


def start_live_stream(
    batch_size: int,
    interval_seconds: int,
    loop: bool,
    reset: bool = False,
    auto_ticket: bool = True,
    ticket_every_batches: int = 2,
    ticket_max_spikes: int = 6,
):
    if not scheduler:
        raise ValueError("Scheduler is not initialized")
    with live_stream_lock:
        previous_complete = bool((live_stream_state.get("last_result") or {}).get("complete"))
        if reset or (previous_complete and not loop):
            live_stream_state["offset"] = 0
            live_stream_state["batches_ingested"] = 0
            live_stream_state["last_result"] = None
            live_stream_state["last_error"] = None
            live_stream_state["last_ticket_result"] = None
            live_stream_state["last_ticket_error"] = None
            live_stream_state["last_ticket_at"] = None
            live_stream_state["last_ticket_batch"] = None
            live_stream_state["final_detection_requested"] = False
            live_stream_state["last_batch_started_at"] = None
            live_stream_state["last_batch_completed_at"] = None
        live_stream_state["batch_size"] = batch_size
        live_stream_state["interval_seconds"] = interval_seconds
        live_stream_state["loop"] = loop
        live_stream_state["auto_ticket"] = auto_ticket
        live_stream_state["ticket_every_batches"] = ticket_every_batches
        live_stream_state["ticket_max_spikes"] = ticket_max_spikes
        live_stream_state["running"] = True
        live_stream_state["batch_running"] = False
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
    if scheduler and scheduler.get_job("live_feedback_stream"):
        scheduler.remove_job("live_feedback_stream")
    with live_stream_lock:
        live_stream_state["running"] = False
        live_stream_state["final_detection_requested"] = True
    # Nếu không có batch đang chạy, claim ngay; nếu có, live_stream_tick sẽ claim
    # sau khi batch commit xong để nút Dừng không bị block.
    should_detect = False
    if not live_stream_tick_lock.locked():
        should_detect = claim_final_detection_request()
    if should_detect:
        schedule_auto_ticket_detection()
    return get_live_stream_status()


def get_live_stream_status():
    with live_stream_lock:
        return dict(live_stream_state)
