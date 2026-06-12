import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from backend.pipeline.agents.common import get_db

TAXONOMY_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data_real" / "taxonomy"
SEVERITY_RULES_PATH = TAXONOMY_DIR / "severity_rules.json"

def load_severity_rules() -> Dict[str, Any]:
    if not SEVERITY_RULES_PATH.exists():
        return {
            "alert_escalation": {
                "WATCH": {"min_negative": 3},
                "WARNING": {"min_negative": 5},
                "CRITICAL": {"min_negative": 10}
            },
            "alert_cooldown_minutes": 60
        }
    with open(SEVERITY_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def is_duplicate_alert(db, area: str, cooldown_minutes: int) -> bool:
    """Kiểm tra xem khu vực này có alert nào đang mở trong vòng N phút qua không."""
    try:
        since = (datetime.utcnow() - timedelta(minutes=cooldown_minutes)).isoformat()
        response = db.table("alerts") \
            .select("id") \
            .eq("area", area) \
            .eq("status", "open") \
            .gte("created_at", since) \
            .limit(1) \
            .execute()
        
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking duplicate alerts: {e}")
        return False

def classify_alert_severity(case_count: int, has_p5: bool = False) -> str:
    rules = load_severity_rules()
    
    if has_p5:
        return "CRITICAL"
        
    thresholds = rules.get("alert_escalation", {})
    # Sắp xếp từ lớn đến bé để tìm cấp cao nhất
    sorted_levels = sorted(thresholds.items(), key=lambda x: x[1].get("min_negative", 0), reverse=True)
    
    for level_name, config in sorted_levels:
        if case_count >= config.get("min_negative", 0):
            return level_name
            
    return "INFO" # Không đạt mức cảnh báo

def process_area_alerts(area: str, recent_feedbacks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Phân tích một tập hợp feedback của khu vực và quyết định có nên tạo cảnh báo không.
    Trả về Dict thông tin cảnh báo nếu cần tạo, ngược lại trả về None.
    """
    rules = load_severity_rules()
    cooldown = rules.get("alert_cooldown_minutes", 60)
    db = get_db()
    
    case_count = len(recent_feedbacks)
    has_p5 = any(str(f.get("severity", "")).upper() in ["P5", "P0"] for f in recent_feedbacks)
    has_p5 = has_p5 or any(isinstance(f.get("severity"), int) and f.get("severity") >= 5 for f in recent_feedbacks)
    
    severity_level = classify_alert_severity(case_count, has_p5)
    
    if severity_level == "INFO":
        return {"action": "skip", "reason": "Not enough cases for alert"}
        
    # Check deduplication
    if is_duplicate_alert(db, area, cooldown):
        return {"action": "skip", "reason": f"Duplicate alert within {cooldown} mins"}
        
    return {
        "action": "create",
        "area": area,
        "severity": severity_level,
        "case_count": case_count,
        "has_p5": has_p5
    }

if __name__ == "__main__":
    # Test
    print(classify_alert_severity(4)) # WATCH
    print(classify_alert_severity(6)) # WARNING
    print(classify_alert_severity(2, True)) # CRITICAL
