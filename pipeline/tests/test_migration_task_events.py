from pathlib import Path

MIG = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "20260628000000_task_events_and_status.sql"
)


def test_migration_file_exists():
    assert MIG.is_file(), f"Thiếu migration: {MIG}"


def test_migration_has_task_events_table_and_status_check():
    sql = MIG.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.task_events" in sql
    assert "tasks_status_check" in sql
    assert "'pending_review'" in sql
    assert "'assigned'" in sql
    assert "completion_report_id" in sql
