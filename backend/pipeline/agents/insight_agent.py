from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.pipeline.agents.common import get_db
from backend.pipeline.agents.router_agent import load_routing_table, route_ticket

def generate_department_insights(team: str, hours: int = 24) -> Dict[str, Any]:
    """
    Tổng hợp insight cho một phòng ban cụ thể trong N giờ qua.
    Gom dữ liệu từ Supabase, tính toán metric:
    - Tổng số feedback
    - Phân bố mức độ nghiêm trọng
    - Top topics
    """
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    
    # 1. Fetch recent feedback
    # TODO: In production with large data, this should be done via a Postgres SQL function (RPC)
    # to avoid pulling all rows into memory. For now, we pull and process.
    try:
        response = db.table("feedback") \
            .select("id, text, topic, severity, created_at, area") \
            .gte("created_at", since) \
            .execute()
        
        all_feedback = response.data or []
    except Exception as e:
        print(f"Error fetching feedback for insights: {e}")
        all_feedback = []
        
    # 2. Filter feedback belonging to this team
    team_feedback = []
    for f in all_feedback:
        route_info = route_ticket(f.get("topic", ""), f.get("severity", 3))
        if route_info["team"] == team:
            team_feedback.append(f)
            
    # 3. Calculate metrics
    total_feedback = len(team_feedback)
    if total_feedback == 0:
        return {
            "team": team,
            "period_hours": hours,
            "total_feedback": 0,
            "severity_distribution": {"P1/P5": 0, "P2/P4": 0, "P3": 0},
            "top_topics": [],
            "recent_samples": []
        }
        
    severity_dist = {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0}
    topic_counts = {}
    
    for f in team_feedback:
        sev = f.get("severity")
        # Normalize severity
        sev_int = 3
        if isinstance(sev, int):
            sev_int = sev
        elif isinstance(sev, str) and sev.upper() in ["P5", "P0", "P1"]:
            sev_int = 5
            
        if sev_int >= 5:
            severity_dist["CRITICAL"] += 1
        elif sev_int == 4:
            severity_dist["WARNING"] += 1
        elif sev_int == 3:
            severity_dist["WATCH"] += 1
        else:
            severity_dist["INFO"] += 1
            
        topic = f.get("topic", "Unknown")
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
    # Sort topics
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Extract 3 samples
    samples = [{"id": f["id"], "text": f["text"], "area": f.get("area")} for f in team_feedback[:3]]
    
    return {
        "team": team,
        "period_hours": hours,
        "total_feedback": total_feedback,
        "severity_distribution": severity_dist,
        "top_topics": [{"topic": t[0], "count": t[1]} for t in sorted_topics[:5]],
        "recent_samples": samples
    }

if __name__ == "__main__":
    # Test
    print(generate_department_insights("Safety", 24))
