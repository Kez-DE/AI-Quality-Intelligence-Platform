"""US-077 / decision 0017: public Feedback text is wiped once retention_until passes.

The promise on the Customer web is "Nội dung tự xoá sau 180 ngày". These tests pin
what "xoá" means: the words go, the labels stay, so dashboards and trends do not
move when a row ages out.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services import retention
from tests._fakedb import FakeDB

NOW = datetime(2027, 3, 22, 3, 0, tzinfo=timezone.utc)
PAST = "2027-03-21T10:00:00+00:00"
FUTURE = "2027-09-01T00:00:00+00:00"

LABELS = {
    "topic": "Safety",
    "sentiment": "negative",
    "severity": "P5",
    "area": "HN",
    "channel": "web",
    "created_at": "2026-09-22T10:00:00+00:00",
    "overall_risk": 5,
}


def _public(fid, retention_until, **extra):
    return {
        "id": fid,
        "source": "public",
        "public_ref": f"ref-{fid}",
        "submitter_hash": "hash",
        "retention_until": retention_until,
        "text": f"Tài xế biển [BIỂN_SỐ_ĐÃ_ẨN] chửi tôi ({fid})",
        **LABELS,
        **extra,
    }


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB(
        feedback=[
            _public("expired", PAST),
            _public("fresh", FUTURE),
            _public("done", PAST, redacted_at="2027-03-01T03:00:00+00:00",
                    text=retention.REDACTED_TEXT, submitter_hash=None),
            # Not a public row: retention does not apply, even if a date is set.
            {"id": "staff", "source": "manual", "retention_until": PAST, "text": "nội bộ", **LABELS},
            _public("no-deadline", None),
        ],
        correction_logs=[
            {"id": "c1", "feedback_id": "expired", "field": "topic",
             "old_value": "Other", "new_value": "Safety", "note": "khách nói tài xế chửi"},
            {"id": "c2", "feedback_id": "fresh", "field": "topic",
             "old_value": "Other", "new_value": "Safety", "note": "giữ nguyên"},
        ],
    )
    monkeypatch.setattr(retention, "get_supabase", lambda: fake)
    return fake


def _row(db, fid):
    return next(r for r in db.tables["feedback"] if r["id"] == fid)


def test_redacts_only_expired_unredacted_public_rows(db):
    before = {r["id"]: dict(r) for r in db.tables["feedback"]}

    assert retention.redact_expired_public_feedback(now=NOW) == 1

    row = _row(db, "expired")
    assert row["text"] == retention.REDACTED_TEXT
    assert row["submitter_hash"] is None
    assert row["redacted_at"] == NOW.isoformat()
    for fid in ("fresh", "done", "staff", "no-deadline"):
        assert _row(db, fid) == before[fid], f"{fid} must not be touched"


def test_labels_survive_redaction(db):
    retention.redact_expired_public_feedback(now=NOW)
    row = _row(db, "expired")
    for key, value in LABELS.items():
        assert row[key] == value, f"{key} feeds dashboards and must be kept"
    assert row["public_ref"] == "ref-expired"


def test_linked_correction_note_is_cleared(db):
    """The only copy of the text reachable by id: an operator note on a label fix."""
    retention.redact_expired_public_feedback(now=NOW)
    logs = {c["id"]: c for c in db.tables["correction_logs"]}
    assert logs["c1"]["note"] is None
    assert logs["c1"]["new_value"] == "Safety"  # the label history stays
    assert logs["c2"]["note"] == "giữ nguyên"


def test_is_idempotent(db):
    assert retention.redact_expired_public_feedback(now=NOW) == 1
    snapshot = [dict(r) for r in db.tables["feedback"]]

    assert retention.redact_expired_public_feedback(now=NOW) == 0
    assert db.tables["feedback"] == snapshot


def test_defaults_to_the_current_time(monkeypatch):
    fake = FakeDB(
        feedback=[_public("long-gone", "2000-01-01T00:00:00+00:00"), _public("fresh", "2999-01-01T00:00:00+00:00")],
        correction_logs=[],
    )
    monkeypatch.setattr(retention, "get_supabase", lambda: fake)
    assert retention.redact_expired_public_feedback() == 1
    assert _row(fake, "long-gone")["redacted_at"] is not None


def test_nothing_due_returns_zero(monkeypatch):
    fake = FakeDB(feedback=[_public("fresh", FUTURE)], correction_logs=[])
    monkeypatch.setattr(retention, "get_supabase", lambda: fake)
    assert retention.redact_expired_public_feedback(now=NOW) == 0


def test_ticket_worker_schedules_redaction_daily_at_3am_vietnam():
    """backend-worker, not the API: one process, one daily run (decision 0017).

    Railway runs UTC, so the timezone must be explicit or the job fires at 10:00 VN.
    """
    import worker_ticket

    scheduler = MagicMock()
    with patch.object(worker_ticket, "BackgroundScheduler", return_value=scheduler):
        assert worker_ticket.build_scheduler() is scheduler

    jobs = {call.kwargs["id"]: call for call in scheduler.add_job.call_args_list}
    assert "auto_ticket_workflow" in jobs, "existing workflow job must stay"

    job = jobs["retention_redact"]
    assert job.args[1] == "cron"
    assert job.kwargs["hour"] == 3
    assert job.kwargs["minute"] == 0
    assert str(job.kwargs["timezone"]) == "Asia/Ho_Chi_Minh"


def test_worker_job_runs_the_redaction(monkeypatch):
    import worker_ticket

    calls = []
    monkeypatch.setattr(worker_ticket, "redact_expired_public_feedback", lambda: calls.append(1) or 3)
    worker_ticket.run_retention_redaction()
    assert calls == [1]


def test_worker_job_swallows_errors_so_the_scheduler_survives(monkeypatch):
    import worker_ticket

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(worker_ticket, "redact_expired_public_feedback", boom)
    worker_ticket.run_retention_redaction()  # must not raise


# ---------------------------------------------------------------------------
# Nothing downstream may re-derive labels from the placeholder text
# ---------------------------------------------------------------------------


def test_reclassify_leaves_redacted_rows_alone(monkeypatch):
    """Reclassify re-predicts from `text`; on a redacted row that is the placeholder,
    so it would overwrite the kept labels with a guess about "[Đã xoá ...]"."""
    import classifier
    import main
    from auth_guard import AuthUser

    fake = FakeDB(feedback=[
        _public("wiped", PAST, redacted_at=NOW.isoformat(), text=retention.REDACTED_TEXT, reviewed=False),
        _public("live", FUTURE, reviewed=False),
    ])
    monkeypatch.setattr(main, "get_supabase", lambda: fake)
    monkeypatch.setattr(classifier, "predict_feedback", lambda _t: {
        "topic": "Other", "sentiment": "neutral", "severity": "P1", "confidence": 0.2,
    })

    main.reclassify_feedback(limit=10, _=AuthUser(id="a", email=None, role="admin", department=None))

    assert _row(fake, "wiped")["topic"] == "Safety"
    assert _row(fake, "live")["topic"] == "Other"


def test_ml_worker_does_not_score_redacted_rows(monkeypatch):
    import worker_ml

    fake = FakeDB(feedback=[
        {"id": "wiped", "sentiment": "negative", "overall_risk": None,
         "text": retention.REDACTED_TEXT, "redacted_at": NOW.isoformat()},
        {"id": "live", "sentiment": "negative", "overall_risk": None, "text": "tài xế chửi"},
    ])
    seen = []
    monkeypatch.setattr(worker_ml, "get_supabase", lambda: fake)
    monkeypatch.setattr(worker_ml, "score_feedback_batch", lambda rows: seen.extend(r["id"] for r in rows) or [])

    worker_ml.score_pending()

    assert seen == ["live"]
