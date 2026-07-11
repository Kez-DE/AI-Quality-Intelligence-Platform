"""worker_ml.score_pending — queue hygiene and HITL-flag preservation."""
from unittest.mock import MagicMock, patch

import worker_ml


def _db_returning(rows):
    """MagicMock supabase double: select chain returns rows, captures updates."""
    db = MagicMock()
    select_chain = db.table.return_value.select.return_value
    select_chain.is_.return_value.eq.return_value.limit.return_value.execute.return_value.data = rows
    return db


def _updates(db):
    return [c.args[0] for c in db.table.return_value.update.call_args_list]


def test_select_includes_needs_review_column():
    """#6: without needs_review in SELECT, scoring rewrites the flag to False,
    wiping the human-review mark set at ingest (P5/safety)."""
    db = _db_returning([])
    with patch.object(worker_ml, "get_supabase", return_value=db):
        worker_ml.score_pending()
    select_arg = db.table.return_value.select.call_args.args[0]
    assert "needs_review" in select_arg


def test_fallback_rows_leave_null_queue_with_sentinel():
    """#5: LLM-failure fallback lacks overall_risk; writing NULL keeps the row
    in the every-30s scan forever. Sentinel 0 exits the queue; consumers guard
    1<=risk<=5 so 0 is treated as unscored severity-wise."""
    row = {"id": "f1", "text": "x", "sentiment": "negative", "topic": "t",
           "severity": "P3", "needs_review": False}

    def fake_score(rows):
        for r in rows:  # mimic scoring_agent fallback mutation
            r.update({"risk_safety": 0, "risk_fraud": 0, "risk_attitude": 0,
                      "risk_vehicle": 0, "risk_compliance": 0,
                      "needs_review": True,
                      "review_reason": "Lỗi API LLM Scoring, cần con người kiểm duyệt"})
        return rows

    db = _db_returning([row])
    with patch.object(worker_ml, "get_supabase", return_value=db), \
         patch.object(worker_ml, "score_feedback_batch", side_effect=fake_score):
        worker_ml.score_pending()

    (update,) = _updates(db)
    assert update["overall_risk"] == 0
    assert update["needs_review"] is True


def test_scored_row_preserves_ingest_review_flag():
    """#6: successful scoring must not downgrade needs_review=True from ingest."""
    row = {"id": "f2", "text": "x", "sentiment": "negative", "topic": "t",
           "severity": "P5", "needs_review": True}

    def fake_score(rows):
        for r in rows:  # success path: scoring_agent keeps existing needs_review
            r.update({"risk_safety": 2, "risk_fraud": 0, "risk_attitude": 0,
                      "risk_vehicle": 0, "risk_compliance": 0, "overall_risk": 2})
        return rows

    db = _db_returning([row])
    with patch.object(worker_ml, "get_supabase", return_value=db), \
         patch.object(worker_ml, "score_feedback_batch", side_effect=fake_score):
        worker_ml.score_pending()

    (update,) = _updates(db)
    assert update["overall_risk"] == 2
    assert update["needs_review"] is True
