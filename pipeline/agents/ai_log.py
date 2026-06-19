"""AI-log: ghi lại vận hành của 6 agent ra file JSONL cục bộ (ngoài Supabase).

Mục đích: debug nhanh không cần mở DB — mỗi lần agent chạy ghi 1 dòng JSON vào
`pipeline/agents/ai-log/YYYY-MM-DD.jsonl`. Được gọi tự động từ
`agents.common.log_agent_run`, nên cả 6 agent (ingestion, router, ticket, task,
insight, analyst, alert) đều log mà không phải sửa từng agent.

Lưu ý vận hành: filesystem trên Railway là EPHEMERAL — file log mất sau mỗi
redeploy/restart. Dùng cho debug local + trong phiên chạy. Nguồn log bền vững
vẫn là bảng Supabase `agent_run_logs`. Tắt file-log qua AI_LOG_ENABLED=false.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

# pipeline/agents/ai_log.py -> pipeline/agents/ai-log/
_DEFAULT_DIR = Path(__file__).resolve().parent / "ai-log"
_LOG_DIR = Path(os.getenv("AI_LOG_DIR", str(_DEFAULT_DIR)))
_ENABLED = os.getenv("AI_LOG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
_LOCK = Lock()  # tuần tự hóa ghi giữa các APScheduler job / request


def _today_file() -> Path:
    return _LOG_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"


def log_agent_event(
    agent_name: str,
    status: str,
    *,
    run_id: str = "",
    latency_ms: int = 0,
    output_summary: str = "",
    error_message: str = "",
    provider: str = "",
    model: str = "",
    **extra,
) -> None:
    """Ghi 1 sự kiện vận hành agent ra file JSONL theo ngày.

    Best-effort: mọi lỗi I/O đều nuốt để KHÔNG bao giờ làm vỡ pipeline agent.
    """
    if not _ENABLED:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "status": status,
        "run_id": run_id,
        "latency_ms": latency_ms,
        "summary": output_summary,
        "error": error_message,
        "provider": provider,
        "model": model,
    }
    if extra:
        record.update(extra)
    try:
        with _LOCK:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with _today_file().open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 - logging không được làm vỡ agent
        print(f"[ai_log] write failed: {exc}", flush=True)


def read_recent(limit: int = 100, agent_name: str = "") -> list[dict]:
    """Đọc N dòng log gần nhất của hôm nay (lọc theo agent nếu truyền)."""
    path = _today_file()
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if agent_name and rec.get("agent") != agent_name:
                continue
            out.append(rec)
            if len(out) >= limit:
                break
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_log] read failed: {exc}", flush=True)
    return out


__all__ = ["log_agent_event", "read_recent"]
