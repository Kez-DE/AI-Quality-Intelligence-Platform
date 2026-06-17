"""Task Agent — Gom cụm các alert thành Task và sinh báo cáo tự động."""

import time
import hashlib
from typing import Any, Dict, List
from datetime import datetime, timedelta

from agents.common import get_db, log_agent_run
from agents.common import call_llm

def cluster_alerts_into_tasks() -> Dict[str, Any]:
    """
    Thuật toán gom cụm Heuristic-First (Zero-LLM cho việc gom):
    1. Lấy tất cả alerts đang open và chưa có task_id.
    2. Gom theo (team, area) (hoặc có thể thêm topic nếu có).
    3. Tìm xem đã có Task nào đang open với cùng (team, area) chưa.
    4. Nếu có, tự động gán task_id mới vào alert.
    5. Nếu chưa có, tạo Task mới và gọi LLM 1 lần duy nhất để tạo title/summary từ các alerts mẫu.
    """
    start_time = time.time()
    db = get_db()
    
    # 1. Fetch unassigned alerts (no task_id)
    try:
        res = db.table("alerts").select("*").is_("task_id", "null").eq("status", "open").execute()
        unassigned_alerts = res.data or []
    except Exception as e:
        return {"status": "error", "error": f"Failed to fetch alerts: {str(e)}"}

    if not unassigned_alerts:
        return {"status": "success", "message": "No unassigned alerts found."}

    # Group alerts by (team, area)
    # Trong alerts schema hiện tại: area có sẵn. assigned_team nằm trong description (từ format **Assigned Team:**) hoặc cần trích xuất.
    # Vì schema alerts không có cột assigned_team, ta parse từ description
    clusters = {}
    for alert in unassigned_alerts:
        area = alert.get("area", "Unknown")
        desc = alert.get("description", "")
        team = "Unknown"
        # Parse team from description: "**Assigned Team:** Safety"
        if "**Assigned Team:**" in desc:
            parts = desc.split("**Assigned Team:**")
            if len(parts) > 1:
                team = parts[1].strip().split("\n")[0]
        
        # We can also extract topic from title if we strictly want to cluster by topic. For now, cluster by area & team.
        key = (team, area)
        if key not in clusters:
            clusters[key] = []
        clusters[key].append(alert)

    tasks_created = 0
    alerts_assigned = 0

    for (team, area), alerts in clusters.items():
        if not alerts:
            continue
            
        # Check if there is an open task for this team & area
        try:
            task_res = db.table("tasks").select("id").eq("assigned_team", team).eq("area", area).eq("status", "open").limit(1).execute()
            open_task = task_res.data[0] if task_res.data else None
        except Exception:
            open_task = None

        task_id = None
        if open_task:
            task_id = open_task["id"]
        else:
            # Create a new Task using LLM for title and summary
            sample_texts = "\n".join([f"- {a['title']}: {a.get('description', '')[:100]}..." for a in alerts[:5]])
            prompt = f"""Bạn là một Quản lý Vận hành (Operations Manager).
Dưới đây là một số sự cố (alerts) liên quan đến phòng ban {team} tại khu vực {area}:
{sample_texts}

Hãy tóm tắt và đặt tên cho một Nhiệm vụ (Task) chung để giao cho phòng {team} giải quyết dứt điểm các sự cố này.
Trả về định dạng JSON:
{{
  "title": "Tên Task ngắn gọn (dưới 10 chữ)",
  "summary": "Tóm tắt tình hình và hành động cần làm (2-3 câu)"
}}"""
            try:
                llm_res = call_llm("You are a helpful assistant.", prompt, "json_object")
                import json
                try:
                    task_data = json.loads(llm_res)
                except:
                    task_data = {
                        "title": f"Xử lý cụm sự cố tại {area}",
                        "summary": "Nhiều sự cố được báo cáo tại khu vực này. Cần kiểm tra và xử lý."
                    }
                
                # Insert new task
                # Find a user_id for owner_id to satisfy RLS if needed, or leave null
                new_task = {
                    "title": task_data.get("title", f"Vấn đề {team} tại {area}"),
                    "summary": task_data.get("summary", ""),
                    "assigned_team": team,
                    "area": area,
                    "topic": "General", # Can be extracted from LLM if needed
                    "priority": "P2", # Default, can calculate max severity from alerts
                    "status": "open"
                }
                insert_res = db.table("tasks").insert(new_task).execute()
                if insert_res.data:
                    task_id = insert_res.data[0]["id"]
                    tasks_created += 1
            except Exception as e:
                print(f"[TaskAgent] Lỗi tạo task mới: {e}")
                continue

        # Assign task_id to all alerts in this cluster
        if task_id:
            alert_ids = [a["id"] for a in alerts]
            try:
                db.table("alerts").update({"task_id": task_id}).in_("id", alert_ids).execute()
                alerts_assigned += len(alert_ids)
            except Exception as e:
                print(f"[TaskAgent] Lỗi cập nhật alerts: {e}")

    log_agent_run(
        run_id=f"task_cluster_{int(time.time())}",
        agent_name="task_agent",
        status="success",
        latency_ms=int((time.time() - start_time) * 1000),
        output_summary=f"Created {tasks_created} tasks, assigned {alerts_assigned} alerts."
    )

    return {
        "status": "success",
        "tasks_created": tasks_created,
        "alerts_assigned": alerts_assigned
    }

def generate_daily_report(team: str) -> Dict[str, Any]:
    """Sinh báo cáo định kỳ cho phòng ban, tối ưu LLM token."""
    start_time = time.time()
    db = get_db()
    
    # Lấy metrics từ DB
    try:
        # Get tasks
        tasks_res = db.table("tasks").select("*").eq("assigned_team", team).execute()
        tasks = tasks_res.data or []
        open_tasks = [t for t in tasks if t["status"] in ["open", "in_progress"]]
        
        if not open_tasks:
            return {"status": "skipped", "message": f"No open tasks for {team}"}
            
        task_summary = "\n".join([f"- {t['title']} (Khu vực: {t.get('area', 'Chung')}, Ưu tiên: {t['priority']})" for t in open_tasks])
        
        prompt = f"""Bạn là một AI Analyst. Hãy viết một báo cáo ngắn gọn (định dạng Markdown) gửi Trưởng phòng {team} tổng hợp tình hình vận hành ngày hôm nay.
Dưới đây là các Task đang mở của phòng {team}:
{task_summary}

Yêu cầu Báo cáo (Khoảng 150-200 chữ, phải có 4 mục sau):
### 1. Nguyên nhân gốc rễ (Root Cause)
[Phân tích nguyên nhân đằng sau các Task]
### 2. Mức độ rủi ro hiện tại (Risk Level)
[Đánh giá: LOW / WARNING / CRITICAL]
### 3. Dự báo 24-48h tới (Forecast)
[Dự báo tình hình]
### 4. Đề xuất hành động (Action Plan)
[3 hành động cụ thể kèm deadline]
"""
        content = call_llm("You are an AI Analyst.", prompt, "text")
        
        report_data = {
            "team": team,
            "report_date": datetime.utcnow().date().isoformat(),
            "content": content
        }
        db.table("department_reports").insert(report_data).execute()
        
        log_agent_run(
            run_id=f"report_{team}_{int(time.time())}",
            agent_name="task_agent",
            status="success",
            latency_ms=int((time.time() - start_time) * 1000),
            output_summary=f"Generated report for {team}"
        )
        return {"status": "success", "team": team}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    res = cluster_alerts_into_tasks()
    print("Cluster Result:", res)
