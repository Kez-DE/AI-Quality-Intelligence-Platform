"""ML Scoring Worker — risk-score unscored negative feedback via LLM (Deep Risk Matrix).

Runs as the `ml-worker` Railway service. APScheduler scans for feedback rows
where overall_risk IS NULL and sentiment = 'negative', then calls
score_feedback_batch() every WORKER_ML_INTERVAL_SECONDS.
"""

import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from agents.scoring_agent import score_feedback_batch
from env_config import get_settings
from ingest import get_supabase

# Đọc qua env_config để chỉ có MỘT nguồn mặc định. Trước đây os.getenv ở đây
# khai 30s còn env_config khai 60s -> tiến trình tốn LLM nhất chạy gấp đôi tần suất
# so với tài liệu.
_settings = get_settings()
BATCH_SIZE = _settings.worker_ml_batch_size
INTERVAL   = _settings.worker_ml_interval_seconds


def score_pending():
    """Fetch unscored negative feedback, run LLM risk scoring, update DB rows."""
    try:
        db = get_supabase()
        rows = (
            db.table("feedback")
            # needs_review must ride along: scoring preserves the row's own
            # value, and omitting it here silently wiped the HITL flag set
            # at ingest (P5/safety) on every scoring pass.
            .select("id,text,sentiment,topic,severity,needs_review")
            .is_("overall_risk", "null")
            .eq("sentiment", "negative")
            .limit(BATCH_SIZE)
            .execute()
        ).data or []

        if not rows:
            return

        print(f"[ml-worker] Scoring {len(rows)} pending feedback rows...", flush=True)
        scored = score_feedback_batch(rows)

        for item in scored:
            db.table("feedback").update({
                "risk_safety":     item.get("risk_safety", 0),
                "risk_fraud":      item.get("risk_fraud", 0),
                "risk_attitude":   item.get("risk_attitude", 0),
                "risk_vehicle":    item.get("risk_vehicle", 0),
                "risk_compliance": item.get("risk_compliance", 0),
                # LLM-failure fallback carries no overall_risk; writing NULL
                # would re-queue the row every INTERVAL forever. Sentinel 0 =
                # "attempted, needs human" — consumers guard 1<=risk<=5.
                "overall_risk":    item.get("overall_risk") or 0,
                "needs_review":    item.get("needs_review", False),
            }).eq("id", item["id"]).execute()

        print(f"[ml-worker] Scored {len(scored)} rows.", flush=True)

    except Exception as exc:
        print(f"[ml-worker] score_pending error: {exc}", file=sys.stderr, flush=True)


def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        score_pending,
        "interval",
        seconds=INTERVAL,
        id="ml_scoring",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    should_stop = False

    def stop(_signum, _frame):
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(f"ml-worker started. Scoring every {INTERVAL}s, batch={BATCH_SIZE}.", flush=True)

    try:
        while not should_stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        print("ml-worker stopped.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ml-worker failed: {exc}", file=sys.stderr, flush=True)
        raise
