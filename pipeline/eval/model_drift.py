import os
import sys
from datetime import datetime, timedelta, timezone

# Thêm đường dẫn thư mục gốc vào sys.path để import từ pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest import get_supabase

# Ngưỡng tỷ lệ sửa lỗi (Correction Rate) cho phép. Nếu vượt quá, kích hoạt cảnh báo Model Drift.
DRIFT_THRESHOLD = 0.05  # 5%

def check_model_drift(days: int = 7):
    """
    Đo lường tỷ lệ Correction (Model Drift) trong N ngày gần nhất.
    Tỷ lệ = Số feedback bị nhân viên sửa nhãn / Tổng số feedback nhận được.
    """
    print(f"Checking model drift for the last {days} days...")
    db = get_supabase()
    
    # Tính mốc thời gian
    time_limit = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Lấy tổng số feedback
    fb_resp = db.table("feedback").select("id", count="exact").gte("created_at", time_limit).execute()
    total_feedback = fb_resp.count or 0
    
    if total_feedback == 0:
        print("No feedback found in the specified timeframe.")
        return
        
    # Lấy số lượng feedback đã bị sửa (có trong correction_logs)
    logs_resp = db.table("correction_logs").select("feedback_id").gte("created_at", time_limit).execute()
    logs = logs_resp.data or []
    
    # Lọc ra các feedback_id duy nhất
    unique_corrected = set(log["feedback_id"] for log in logs)
    total_corrected = len(unique_corrected)
    
    drift_rate = total_corrected / total_feedback
    
    print("="*30)
    print("MODEL DRIFT REPORT")
    print("="*30)
    print(f"Timeframe: Last {days} days")
    print(f"Total Feedbacks: {total_feedback}")
    print(f"Total Corrected: {total_corrected}")
    print(f"Correction Rate: {drift_rate * 100:.2f}% (Threshold: {DRIFT_THRESHOLD * 100:.2f}%)")
    
    if drift_rate > DRIFT_THRESHOLD:
        print("\n[WARNING] MODEL DRIFT DETECTED!")
        print("The AI model's accuracy may have degraded. Consider retraining the model using the latest data from correction_logs.")
        
        # Ghi log cảnh báo vào bảng alerts để OPS team thấy trên Dashboard
        alert_row = {
            "title": "Cảnh báo Model Drift (Độ lệch mô hình AI)",
            "description": f"Tỷ lệ nhân viên phải sửa nhãn thủ công đã vượt ngưỡng (Correction Rate: {drift_rate * 100:.2f}% > {DRIFT_THRESHOLD * 100:.2f}% trong {days} ngày qua). Cần thu thập dữ liệu và huấn luyện lại mô hình.",
            "severity": "P2",
            "area": "System",
            "status": "open"
        }
        try:
            db.table("alerts").insert(alert_row).execute()
            print("Successfully created an alert in the system.")
        except Exception as e:
            print(f"Failed to create alert: {e}")
    else:
        print("\n[OK] Model performance is stable.")

if __name__ == "__main__":
    check_model_drift(days=7)
