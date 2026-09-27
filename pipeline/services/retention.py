"""Retention for public Feedback (US-077 / decision 0017).

The Customer web promises "Nội dung tự xoá sau 180 ngày". A public row carries
`retention_until` from intake; once it passes, the words a Customer typed are
wiped and the classification is kept. The dashboards, trends, alerts and
routing that already counted the row stay exactly as they were.

Runs once a day from the backend-worker (worker_ticket.py).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ingest import get_supabase

REDACTED_TEXT = "[Đã xoá theo hạn lưu trữ]"

# Ids per UPDATE. PATCH filters travel in the URL, and 100 UUIDs keep it far
# under PostgREST's request-line limit.
_CHUNK = 100


def redact_expired_public_feedback(now: datetime | None = None) -> int:
    """Wipe the text of public rows past `retention_until`. Returns rows redacted.

    Idempotent: a redacted row carries `redacted_at` and is never picked again.
    Kept: topic, sentiment, severity, area, channel, created_at, overall_risk,
    public_ref (the status endpoint answers 404 for a redacted row anyway).
    Never logs row content.
    """
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    db = get_supabase()

    # ponytail: one PostgREST page (default max 1000 rows) per run; a larger
    # backlog drains over the following nights. Loop here if volume ever needs it.
    due = (
        db.table("feedback")
        .select("id")
        .eq("source", "public")
        .lt("retention_until", stamp)
        .is_("redacted_at", "null")
        .execute()
        .data
        or []
    )
    ids = [row["id"] for row in due]

    redacted = 0
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start : start + _CHUNK]
        # Copies first, then the row. If the run dies between the two, the row is
        # still unredacted, so the next run finds it and finishes both.
        # correction_logs.note is the only copy linked by id; see decision 0017
        # for the copies that are not (alert text, LLM logs, webhooks).
        db.table("correction_logs").update({"note": None}).in_("feedback_id", chunk).execute()
        done = (
            db.table("feedback")
            .update({"text": REDACTED_TEXT, "submitter_hash": None, "redacted_at": stamp})
            .in_("id", chunk)
            .is_("redacted_at", "null")
            .execute()
            .data
            or []
        )
        redacted += len(done)
    return redacted
