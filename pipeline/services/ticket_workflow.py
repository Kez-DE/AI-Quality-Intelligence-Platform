import os
from datetime import datetime, timezone

from env_config import get_settings
from ingest import get_supabase

_s = get_settings()

ticket_workflow_state = {
    # Mặc định TẮT: alert chuyển trạng thái bằng workflow THẬT (nút ops), không auto theo tuổi.
    "enabled": _s.auto_ticket_workflow_enabled,
    "in_progress_after_seconds": _s.auto_ticket_in_progress_after_seconds,
    "resolved_after_seconds": _s.auto_ticket_resolved_after_seconds,
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
