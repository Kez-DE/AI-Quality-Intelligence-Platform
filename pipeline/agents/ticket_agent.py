"""Ticket Agent — quản lý logic tạo/cập nhật ticket (alert) trên DB."""

import time
import hashlib
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

from agents.common import get_db, log_agent_run
from agents.schemas import TicketOutput
from departments import normalize_department

def create_or_update_ticket(
    area: str,
    title: str,
    description: str,
    severity: str,
    team: str,
    sla_hours: int,
    user_id: Optional[str] = None,
    topic: Optional[str] = None,
    priority: Optional[str] = None,
    ticket_type: str = "incident",
    routing_source: str = "router_agent",
) -> Dict[str, Any]:
    """Tạo mới hoặc cập nhật ticket."""
    start_time = time.time()
    db = get_db()
    
    if not user_id:
        # Lấy một user_id mặc định để thỏa mãn RLS / Foreign Key
        try:
            res = db.table("profiles").select("id").limit(1).execute()
            if res.data:
                user_id = res.data[0]["id"]
            else:
                output = TicketOutput(action="skipped", error="No valid user_id found in profiles")
                log_agent_run(
                    run_id=f"ticket_{int(time.time())}",
                    agent_name="ticket_agent",
                    status="failed",
                    latency_ms=int((time.time() - start_time) * 1000),
                    output_summary="Failed to find user_id",
                    error_message=output.error
                )
                return output.model_dump()
        except Exception as e:
            output = TicketOutput(action="skipped", error=str(e))
            log_agent_run(
                run_id=f"ticket_{int(time.time())}",
                agent_name="ticket_agent",
                status="failed",
                latency_ms=int((time.time() - start_time) * 1000),
                output_summary="Failed to fetch user profile",
                error_message=output.error
            )
            return output.model_dump()

    canonical_team = normalize_department(team, "CSKH")
    legacy_payload = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "severity": severity,
        "area": area,
        "status": "open"
    }
    payload = {
        **legacy_payload,
        "assigned_team": canonical_team,
        "topic": topic,
        "priority": priority,
        "ticket_type": ticket_type,
        "routing_source": routing_source,
        "sla_due_at": (datetime.now(timezone.utc) + timedelta(hours=sla_hours)).isoformat(),
    }
    
    try:
        try:
            res = db.table("alerts").insert(payload).execute()
        except Exception as schema_exc:
            # Cho phép backend mới chạy trong khoảng migration Supabase chưa được apply.
            if not any(field in str(schema_exc) for field in payload.keys() - legacy_payload.keys()):
                raise
            res = db.table("alerts").insert(legacy_payload).execute()
        ticket_id = res.data[0]["id"] if res.data else None
        
        output = TicketOutput(
            ticket_id=ticket_id,
            action="created",
            assigned_team=canonical_team,
            status="open"
        )
        log_agent_run(
            run_id=f"ticket_{int(time.time())}",
            agent_name="ticket_agent",
            status="success",
            latency_ms=int((time.time() - start_time) * 1000),
            output_summary=f"Created ticket {ticket_id} for {canonical_team}",
            input_hash=hashlib.md5(f"{area}_{title}".encode()).hexdigest()
        )
        return output.model_dump()
    except Exception as e:
        output = TicketOutput(action="skipped", error=str(e))
        log_agent_run(
            run_id=f"ticket_{int(time.time())}",
            agent_name="ticket_agent",
            status="failed",
            latency_ms=int((time.time() - start_time) * 1000),
            output_summary="Failed to insert alert",
            error_message=output.error,
            input_hash=hashlib.md5(f"{area}_{title}".encode()).hexdigest()
        )
        return output.model_dump()

def get_overdue_tickets(sla_hours: int = 24) -> list:
    """Lấy danh sách tickets đã quá SLA (mặc định 24h) và chưa resolved."""
    from datetime import datetime, timedelta, timezone

    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=sla_hours)).isoformat()

    try:
        res = db.table("alerts") \
            .select("id,title,severity,area,status,created_at") \
            .in_("status", ["open", "in_progress"]) \
            .lte("created_at", cutoff) \
            .order("created_at", desc=False) \
            .limit(100) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"[TicketAgent] Lỗi lấy overdue tickets: {e}")
        return []


__all__ = ["create_or_update_ticket", "get_overdue_tickets"]
