import os
import json
import hashlib
from time import perf_counter
import concurrent.futures
from supabase import create_client, Client
from clean import clean_text
from env_config import get_supabase_config, has_supabase_admin_key

SUPABASE_URL, SUPABASE_KEY = get_supabase_config()

# Caching In-memory cho LLM: text_hash -> dict_of_risks (Tầng 3)
_llm_cache = {}

def get_hash(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Thiếu cấu hình SUPABASE_URL và SUPABASE key trong .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def build_feedback_payload(row: dict, user_id: str) -> dict | None:
    raw_text = row.get("text") or row.get("text_full") or ""
    if not raw_text:
        return None

    cleaned_text = clean_text(raw_text)
    
    # Lọc ML (Tầng 1)
    from classifier import predict_feedback
    prediction = predict_feedback(cleaned_text)

    # Khởi tạo Payload mặc định (Rủi ro 0, an toàn)
    payload = {
        "user_id": user_id,
        "text": cleaned_text,
        "topic": row.get("topic") or prediction["topic"],
        "sentiment": row.get("sentiment") or prediction["sentiment"],
        "severity": prediction["severity"], # Tạm lấy từ ML/Rule, sẽ bị ghi đè nếu là negative
        "confidence": prediction.get("confidence", 0.95),
        "area": row.get("area") or row.get("area_label") or row.get("city_label") or "Unknown",
        "source": row.get("source", "app_store"),
        "channel": "app",
        # Default Deep Risk Matrix = 0
        "risk_safety": 0,
        "risk_fraud": 0,
        "risk_attitude": 0,
        "risk_vehicle": 0,
        "risk_compliance": 0,
        "needs_review": prediction.get("needs_review", False),
        "review_reason": prediction.get("review_reason", None)
    }
    return payload

def _process_and_insert_batch(
    db: Client,
    payload_batch: list[dict],
    *,
    defer_llm_scoring: bool = False,
):
    if not payload_batch:
        return
        
    # 1. Lọc ra các feedback Negative cần gọi LLM
    negative_payloads = [] if defer_llm_scoring else [
        p for p in payload_batch if p["sentiment"] == "negative"
    ]
    
    # 2. Xử lý Caching (Tầng 3)
    to_score_llm = []
    for p in negative_payloads:
        h = get_hash(p["text"])
        if h in _llm_cache:
            p.update(_llm_cache[h])
            # Ghi đè severity bằng overall_risk từ Cache
            if "overall_risk" in p:
                p["severity"] = f"P{p['overall_risk']}"
        else:
            to_score_llm.append(p)
            
    # 3. Chạy LLM Batching bằng Multi-threading (Tầng 2)
    if to_score_llm:
        from agents.scoring_agent import score_feedback_batch
        
        # Chia nhỏ thành các lô 20 records để tránh quá tải Context Window của LLM
        chunk_size = 20
        chunks = [to_score_llm[i:i + chunk_size] for i in range(0, len(to_score_llm), chunk_size)]
        
        print(f"Gom {len(to_score_llm)} feedbacks vào {len(chunks)} LLM API Call(s)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # score_feedback_batch sẽ sửa trực tiếp vào các dict trong chunks
            list(executor.map(score_feedback_batch, chunks))
            
        # Cập nhật lại Cache sau khi LLM xử lý xong. Item scoring FAIL (không có
        # overall_risk — fallback needs_review) KHÔNG được cache: memoize điểm
        # bịa overall_risk=3 sẽ gắn dữ liệu giả cho mọi text trùng về sau.
        for p in to_score_llm:
            if "overall_risk" not in p:
                continue
            h = get_hash(p["text"])
            p["severity"] = f"P{p['overall_risk']}"
            _llm_cache[h] = {
                "risk_safety": p.get("risk_safety", 0),
                "risk_fraud": p.get("risk_fraud", 0),
                "risk_attitude": p.get("risk_attitude", 0),
                "risk_vehicle": p.get("risk_vehicle", 0),
                "risk_compliance": p.get("risk_compliance", 0),
                "overall_risk": p["overall_risk"],
                "severity": p["severity"],
                "needs_review": p.get("needs_review", False),
                "review_reason": p.get("review_reason", None),
            }

    # overall_risk có cột thật từ migration 20260617. Trước đây pop ra khiến
    # DB luôn NULL → ml-worker chấm LLM lần 2 cho mọi negative (phí gấp đôi).

    # 4. Lưu toàn bộ lô (cả positive, neutral, negative) vào DB
    db.table("feedback").insert(payload_batch).execute()


def ingest_dataset(
    json_path: str,
    limit: int | None = None,
    batch_size: int = 150,
    offset: int = 0,
    *,
    defer_llm_scoring: bool = False,
):
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

    def _flush_batch(batch: list[dict]) -> None:
        """Insert one batch; a failed batch counts every row and is dropped so
        one poison batch cannot cascade into every later insert attempt."""
        nonlocal inserted_count, failed_count, batch_count
        if not batch:
            return
        try:
            _process_and_insert_batch(db, batch, defer_llm_scoring=defer_llm_scoring)
            inserted_count += len(batch)
            batch_count += 1
        except Exception as e:
            print(f"Error inserting batch of {len(batch)}: {e}")
            failed_count += len(batch)

    for row in records_to_process:
        try:
            payload = build_feedback_payload(row, mock_user_id)
        except Exception as e:
            print(f"Error building payload: {e}")
            failed_count += 1
            continue
        if not payload:
            continue
        payload_batch.append(payload)
        if len(payload_batch) >= batch_size:
            _flush_batch(payload_batch)
            payload_batch = []

    _flush_batch(payload_batch)

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
        "llm_scoring_deferred": defer_llm_scoring,
    }

if __name__ == "__main__":
    dataset_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "processed",
        "seed_real_clean.json",
    )
    ingest_dataset(dataset_file)
