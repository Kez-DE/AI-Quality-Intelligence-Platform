from unittest.mock import MagicMock, patch

from ingest import _process_and_insert_batch


def test_deferred_batch_skips_llm_and_inserts_for_ml_worker():
    db = MagicMock()
    payload = [{
        "text": "Phản hồi tiêu cực",
        "sentiment": "negative",
        "severity": "P3",
    }]

    with patch("agents.scoring_agent.score_feedback_batch") as score_batch:
        _process_and_insert_batch(db, payload, defer_llm_scoring=True)

    score_batch.assert_not_called()
    db.table.assert_called_once_with("feedback")
    db.table.return_value.insert.assert_called_once_with(payload)


def test_scored_batch_inserts_overall_risk():
    """#7: overall_risk column exists (migration 20260617); popping it forced
    ml-worker to re-score every negative via LLM a second time (double cost)."""
    import ingest as ingest_mod
    ingest_mod._llm_cache.clear()
    db = MagicMock()
    payload = [{
        "text": "Tài xế chạy ẩu suýt gây tai nạn",
        "sentiment": "negative",
        "severity": "P3",
        "needs_review": False,
        "review_reason": None,
    }]

    def fake_score(rows):
        for r in rows:
            r.update({"risk_safety": 8, "risk_fraud": 0, "risk_attitude": 0,
                      "risk_vehicle": 0, "risk_compliance": 0, "overall_risk": 5})
        return rows

    with patch("agents.scoring_agent.score_feedback_batch", side_effect=fake_score):
        _process_and_insert_batch(db, payload, defer_llm_scoring=False)

    inserted = db.table.return_value.insert.call_args.args[0]
    assert inserted[0]["overall_risk"] == 5
    assert inserted[0]["severity"] == "P5"


def test_failed_scoring_not_cached_as_fake_risk():
    """#8b: cache must not memoize fabricated overall_risk=3 for rows whose
    scoring failed — future duplicates would get fake 'scored' data."""
    import ingest as ingest_mod
    ingest_mod._llm_cache.clear()
    db = MagicMock()
    payload = [{
        "text": "Văn bản lỗi scoring",
        "sentiment": "negative",
        "severity": "P3",
        "needs_review": False,
        "review_reason": None,
    }]

    def fake_score_fail(rows):
        for r in rows:  # scoring_agent fallback: no overall_risk
            r.update({"risk_safety": 0, "risk_fraud": 0, "risk_attitude": 0,
                      "risk_vehicle": 0, "risk_compliance": 0,
                      "needs_review": True, "review_reason": "Lỗi API"})
        return rows

    with patch("agents.scoring_agent.score_feedback_batch", side_effect=fake_score_fail):
        _process_and_insert_batch(db, payload, defer_llm_scoring=False)

    assert all("overall_risk" not in v or v["overall_risk"] is None
               for v in ingest_mod._llm_cache.values()) or not ingest_mod._llm_cache


def test_batch_insert_failure_counts_all_rows_and_clears_batch():
    """#8: one poison batch must not cascade — failed_count reflects real rows
    lost and the batch is cleared so later records insert normally."""
    import json, tempfile, os
    from unittest.mock import MagicMock
    import ingest as ingest_mod

    records = [{"text": f"feedback {i}", "sentiment": "positive"} for i in range(4)]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(records, f)
        path = f.name

    db = MagicMock()
    (db.table.return_value.select.return_value.eq.return_value.order.return_value
       .limit.return_value.execute.return_value.data) = [{"id": "u1"}]
    calls = {"n": 0}

    def insert_side_effect(batch):
        calls["n"] += 1
        m = MagicMock()
        if calls["n"] == 1:
            m.execute.side_effect = Exception("constraint violation")
        return m

    db.table.return_value.insert.side_effect = insert_side_effect

    with patch.object(ingest_mod, "get_supabase", return_value=db), \
         patch.object(ingest_mod, "has_supabase_admin_key", return_value=True), \
         patch("classifier.predict_feedback", return_value={
             "topic": "Other", "sentiment": "positive", "severity": "P1",
             "confidence": 0.9, "needs_review": False, "review_reason": None}):
        result = ingest_mod.ingest_dataset(path, batch_size=2)

    os.unlink(path)
    assert result["failed"] == 2          # first batch of 2 lost, counted fully
    assert result["inserted"] == 2        # second batch unaffected by poison
    assert calls["n"] == 2                # batch cleared → no cascading retries


def _ingest_one_row(profiles):
    """Run ingest_dataset on one record against FakeDB; return (result, db)."""
    import json, tempfile, os
    import ingest as ingest_mod
    from tests._fakedb import FakeDB

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump([{"text": "app ổn", "sentiment": "positive"}], f)
        path = f.name
    db = FakeDB(profiles=profiles, feedback=[])
    try:
        with patch.object(ingest_mod, "get_supabase", return_value=db), \
             patch.object(ingest_mod, "has_supabase_admin_key", return_value=True), \
             patch("classifier.predict_feedback", return_value={
                 "topic": "Other", "sentiment": "positive", "severity": "P1",
                 "confidence": 0.9, "needs_review": False, "review_reason": None}):
            result = ingest_mod.ingest_dataset(path)
    finally:
        os.unlink(path)
    return result, db


def test_dataset_owner_is_the_oldest_admin_never_a_customer():
    """US-078: owner used to be `profiles limit(1)` (heap order), which can be a
    Customer account. It would then see every rider's text in its history, and
    deleting it would cascade-delete the dataset."""
    result, db = _ingest_one_row([
        {"id": "cust", "role": "guest", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": "admin-new", "role": "admin", "created_at": "2026-06-01T00:00:00+00:00"},
        {"id": "admin-old", "role": "admin", "created_at": "2026-02-01T00:00:00+00:00"},
    ])
    assert result["inserted"] == 1
    assert [r["user_id"] for r in db.tables["feedback"]] == ["admin-old"]


def test_dataset_ingest_refuses_without_an_admin():
    result, db = _ingest_one_row([{"id": "cust", "role": "guest", "created_at": "2026-01-01T00:00:00+00:00"}])
    assert result == {"success": False, "error": "No user found"}
    assert db.tables["feedback"] == []
