import os
import json
from time import perf_counter
from supabase import create_client, Client
from clean import clean_text
from env_config import get_supabase_config, has_supabase_admin_key

SUPABASE_URL, SUPABASE_KEY = get_supabase_config()

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Thiếu cấu hình SUPABASE_URL và SUPABASE key trong .env")
    # Supabase clients are not shared across scheduler/request threads.
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def build_feedback_payload(row: dict, user_id: str) -> dict | None:
    raw_text = row.get("text") or row.get("text_full") or ""
    if not raw_text:
        return None

    cleaned_text = clean_text(raw_text)
    has_labels = row.get("topic") and row.get("sentiment") and row.get("severity") is not None
    if has_labels:
        prediction = {
            "topic": row.get("topic"),
            "sentiment": row.get("sentiment"),
            "severity": row.get("severity"),
            "confidence": row.get("confidence", 0.95),
        }
    else:
        # Lazy import keeps startup and labeled dataset ingest fast.
        from classifier import predict_feedback

        prediction = predict_feedback(cleaned_text)

    severity = row.get("severity", prediction["severity"])
    if isinstance(severity, str) and severity.upper().startswith("P"):
        severity_value = severity.upper()
    else:
        severity_value = f"P{int(severity)}"

    return {
        "user_id": user_id,
        "text": cleaned_text,
        "topic": row.get("topic") or prediction["topic"],
        "sentiment": row.get("sentiment") or prediction["sentiment"],
        "severity": severity_value,
        "confidence": prediction["confidence"],
        "area": row.get("area") or row.get("area_label") or row.get("city_label") or "Unknown",
        "source": row.get("source", "app_store"),
        "channel": "app",
    }

def ingest_dataset(json_path: str, limit: int | None = None, batch_size: int = 150, offset: int = 0):
    if not has_supabase_admin_key():
        return {
            "success": False,
            "error": "Missing SUPABASE_SERVICE_ROLE_KEY in root .env. Dataset ingest needs an admin key because feedback.user_id references auth.users.",
        }

    db = get_supabase()

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return {"success": False, "error": "File not found"}
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Lấy 1 user_id bất kỳ trong bảng profiles để làm mock_user_id (vì bảng feedback yêu cầu user_id NOT NULL)
    profiles_res = db.table("profiles").select("id").limit(1).execute()
    mock_user_id = None
    if profiles_res.data:
        mock_user_id = profiles_res.data[0]["id"]
    else:
        print("Lỗi: Không tìm thấy bất kỳ tài khoản nào trong hệ thống. Hãy đăng ký 1 tài khoản trên Frontend trước!")
        return {"success": False, "error": "No user found"}

    if offset < 0:
        offset = 0

    end = offset + limit if limit else None
    records_to_process = data[offset:end]
    started_at = perf_counter()
    payload_batch = []
    inserted_count = 0
    failed_count = 0
    batch_count = 0

    for row in records_to_process:
        try:
            payload = build_feedback_payload(row, mock_user_id)
            if not payload:
                continue
            payload_batch.append(payload)
            if len(payload_batch) >= batch_size:
                db.table("feedback").insert(payload_batch).execute()
                inserted_count += len(payload_batch)
                batch_count += 1
                payload_batch = []
        except Exception as e:
            print(f"Error inserting row: {e}")
            failed_count += 1

    if payload_batch:
        db.table("feedback").insert(payload_batch).execute()
        inserted_count += len(payload_batch)
        batch_count += 1

    duration_seconds = perf_counter() - started_at
    print(f"Successfully processed and inserted {inserted_count} records into Supabase!")
    return {
        "success": True,
        "inserted": inserted_count,
        "failed": failed_count,
        "batches": batch_count,
        "batch_size": batch_size,
        "duration_seconds": round(duration_seconds, 3),
        "rows_per_second": round(inserted_count / duration_seconds, 2) if duration_seconds else inserted_count,
        "source_file": json_path,
        "limit": limit,
        "offset": offset,
        "processed": len(records_to_process),
        "next_offset": offset + len(records_to_process),
        "total_rows": len(data),
        "complete": offset + len(records_to_process) >= len(data),
    }

if __name__ == "__main__":
    dataset_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "data",
        "processed",
        "seed_real_clean (1).json",
    )
    ingest_dataset(dataset_file)
