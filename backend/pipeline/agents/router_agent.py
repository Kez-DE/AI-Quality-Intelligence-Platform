import json
from pathlib import Path
from typing import Dict, Any

TAXONOMY_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data_real" / "taxonomy"
ROUTING_TABLE_PATH = TAXONOMY_DIR / "routing_table.json"

def load_routing_table() -> Dict[str, Any]:
    if not ROUTING_TABLE_PATH.exists():
        # Fallback if not found
        return {
            "routes": [],
            "default_team": "CSKH",
            "severity_overrides": []
        }
    with open(ROUTING_TABLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def route_ticket(topic: str, severity: Any) -> Dict[str, Any]:
    """
    Định tuyến ticket về đúng phòng ban dựa trên routing_table.json
    Luật P5 (hoặc P0/P1 khẩn cấp) luôn ép về phòng Safety.
    """
    routing_config = load_routing_table()
    
    # 1. Check P5 / Severity Override First (Safety First principle)
    severity_overrides = routing_config.get("severity_overrides", [])
    for override in severity_overrides:
        # Check by P5 string or numeric 5
        str_sev = str(severity_level).upper()
        if override.get("severity") == str_sev or (str_sev == "5" and override.get("severity") == "P5"):
            return {
                "team": override.get("team", "Safety"),
                "sla_hours": override.get("sla_hours", 1),
                "routed_by": f"router_agent ({override.get('severity')} Override)",
                "is_override": True
            }
        
    # 2. Normal Routing by Topic
    routes = routing_config.get("routes", [])
    for route in routes:
        if route.get("topic") == topic:
            return {
                "team": route.get("team"),
                "sla_hours": route.get("sla_hours", 24),
                "routed_by": "router_agent (Topic Match)",
                "is_override": False
            }
        
    # 3. Default Routing
    return {
        "team": routing_config.get("default_team", "CSKH"),
        "sla_hours": 24,
        "routed_by": "router_agent (Default)",
        "is_override": False
    }

if __name__ == "__main__":
    # Test driven
    print(route_ticket("App Issue", 3))
    print(route_ticket("General Inquiry", 5)) # Should override to Safety
