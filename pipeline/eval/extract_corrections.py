import os
import sys
import json

# Thêm đường dẫn thư mục gốc vào sys.path để import từ pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest import get_supabase

def extract_correction_logs(output_file: str = "corrected_dataset.json"):
    print("Connecting to Supabase...")
    db = get_supabase()
    
    # Lấy dữ liệu từ bảng correction_logs
    print("Fetching correction logs...")
    response = db.table("correction_logs").select("*").execute()
    logs = response.data or []
    
    if not logs:
        print("No correction logs found in the database.")
        return
        
    print(f"Found {len(logs)} correction logs.")
    
    # Gộp các chỉnh sửa theo feedback_id
    corrections_by_feedback = {}
    for log in logs:
        fid = log["feedback_id"]
        if fid not in corrections_by_feedback:
            corrections_by_feedback[fid] = {}
        # Lưu lại new_value của field được sửa
        corrections_by_feedback[fid][log["field"]] = log["new_value"]
        
    print(f"Unique feedbacks corrected: {len(corrections_by_feedback)}")
    
    # Fetch nội dung gốc của các feedback này
    feedback_ids = list(corrections_by_feedback.keys())
    
    if not feedback_ids:
        return
        
    feedbacks_resp = db.table("feedback").select("id, text, topic, sentiment, severity").in_("id", feedback_ids).execute()
    feedbacks = feedbacks_resp.data or []
    
    dataset = []
    for fb in feedbacks:
        fid = fb["id"]
        corrections = corrections_by_feedback.get(fid, {})
        
        # Kết hợp nhãn hiện tại (đã được sửa trên db) hoặc nhãn sau khi sửa
        expected = {
            "topic": corrections.get("topic", fb.get("topic")),
            "sentiment": corrections.get("sentiment", fb.get("sentiment")),
            "severity": corrections.get("severity", fb.get("severity")),
        }
        
        dataset.append({
            "feedback_id": fid,
            "text": fb["text"],
            "expected": expected
        })
        
    # Lưu ra file
    out_path = os.path.join(os.path.dirname(__file__), output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully extracted {len(dataset)} examples to {out_path}.")
    print("You can now run this dataset through evaluate_model.py for continuous evaluation.")

if __name__ == "__main__":
    extract_correction_logs()
