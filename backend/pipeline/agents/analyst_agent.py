import json
from typing import Dict, Any, List
from backend.pipeline.agents.common import call_llm

def analyze_root_cause(team: str, insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sử dụng LLM để phân tích sâu nguyên nhân gốc rễ xuyên suốt nhiều ticket của một phòng ban.
    Đưa ra 3 đề xuất hành động.
    """
    samples = insights.get("recent_samples", [])
    if not samples:
        return {
            "status": "skipped",
            "reason": "No recent samples to analyze",
            "analysis": None
        }
        
    texts = [s["text"] for s in samples]
    combined_texts = "\n- ".join(texts)
    
    system_prompt = f"""
    You are an expert operations analyst for the {team} department.
    Your task is to analyze recent negative customer feedback and identify the ROOT CAUSE.
    Do not just summarize the feedback. Look for systemic issues.
    
    You must return a JSON object with this exact structure:
    {{
        "root_cause_summary": "A 1-2 sentence summary of the main systemic issue",
        "risk_level": "LOW", "MEDIUM", "HIGH", or "CRITICAL",
        "action_items": [
            {{"action": "Specific action 1", "deadline": "24h"}},
            {{"action": "Specific action 2", "deadline": "48h"}},
            {{"action": "Specific action 3", "deadline": "1w"}}
        ]
    }}
    """
    
    user_prompt = f"Analyze the following recent feedback for {team}:\n- {combined_texts}"
    
    response_text = call_llm(system_prompt, user_prompt, response_format="json_object")
    
    try:
        if response_text:
            analysis = json.loads(response_text)
            return {
                "status": "success",
                "analysis": analysis
            }
    except json.JSONDecodeError:
        print(f"Failed to parse LLM response as JSON: {response_text}")
        
    # Fallback heuristic if LLM fails or is missing API key
    return {
        "status": "fallback",
        "analysis": {
            "root_cause_summary": f"Multiple complaints detected regarding {insights.get('top_topics', [{'topic': 'general'}])[0]['topic']}",
            "risk_level": "MEDIUM",
            "action_items": [
                {"action": f"Review recent tickets for {team}", "deadline": "24h"},
                {"action": "Contact affected users", "deadline": "48h"},
                {"action": "Update internal guidelines", "deadline": "1w"}
            ]
        }
    }

if __name__ == "__main__":
    # Test
    mock_insight = {
        "recent_samples": [
            {"text": "The app crashed when I tried to pay"},
            {"text": "Payment screen frozen for 5 minutes"}
        ],
        "top_topics": [{"topic": "App Issue"}]
    }
    print(analyze_root_cause("IT", mock_insight))
