from datetime import datetime
from backend.pipeline.agents.insight_agent import generate_department_insights
from backend.pipeline.agents.analyst_agent import analyze_root_cause

def run_agent_pipeline():
    """
    Kích hoạt toàn bộ hệ thống Multi-Agent Pipeline.
    Trong hệ thống thực tế, hàm này sẽ được gọi bằng APScheduler mỗi 10 phút.
    """
    print(f"[{datetime.utcnow().isoformat()}] Bắt đầu chạy Agent Pipeline...")
    
    # Ở phiên bản hiện tại, spike_detector đã xử lý việc tìm kiếm và tạo alert.
    # Nhiệm vụ của Orchestrator ở đây là có thể mở rộng chạy Analyst Agent 
    # cho các phòng ban có alert "open" hoặc "in_progress".
    
    # Bước 1: Quét tất cả các phòng ban để tạo Insight
    teams = ["IT", "Safety", "Customer Service", "Operations", "Finance", "Marketing"]
    results = {}
    
    for team in teams:
        print(f"Generating insights for {team}...")
        insights = generate_department_insights(team, hours=24)
        
        # Nếu phòng ban có issue (vd: top_topics > 0 hoặc có sample), chạy Analyst
        if insights.get("total_feedback", 0) > 0:
            print(f"Running root cause analysis for {team}...")
            analysis = analyze_root_cause(team, insights)
            insights["analysis"] = analysis
            
        results[team] = insights
        
    print("Pipeline hoàn tất.")
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "departments_processed": len(results),
        "data": results
    }

if __name__ == "__main__":
    # Test
    res = run_agent_pipeline()
    print("Processed", res["departments_processed"], "departments.")
