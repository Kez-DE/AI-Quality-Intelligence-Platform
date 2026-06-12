"""Router agent: định tuyến ticket về phòng ban theo routing_table.json.

Khác bản origin:
- Sửa bug NameError (origin dùng `severity_level` chưa định nghĩa, đúng phải là `severity`).
- Taxonomy đọc từ <repo>/data/taxonomy/ (layout phẳng) thay vì data_real/.
"""

import json
from pathlib import Path
from typing import Any, Dict

# pipeline/agents/router_agent.py -> repo root = parent x3
TAXONOMY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "taxonomy"
ROUTING_TABLE_PATH = TAXONOMY_DIR / "routing_table.json"


def load_routing_table() -> Dict[str, Any]:
    if not ROUTING_TABLE_PATH.exists():
        return {"routes": [], "default_team": "CSKH", "severity_overrides": []}
    with open(ROUTING_TABLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def route_ticket(topic: str, severity: Any) -> Dict[str, Any]:
    """Định tuyến ticket về đúng phòng ban. P5/P0 ép về Safety (Safety-first)."""
    routing_config = load_routing_table()

    # 1. Severity override trước (Safety-first)
    str_sev = str(severity).upper()
    for override in routing_config.get("severity_overrides", []):
        ov_sev = str(override.get("severity", "")).upper()
        if ov_sev == str_sev or (str_sev in {"5", "P5"} and ov_sev == "P5"):
            return {
                "team": override.get("team", "Safety"),
                "sla_hours": override.get("sla_hours", 1),
                "routed_by": f"router_agent ({ov_sev} Override)",
                "is_override": True,
            }

    # 2. Routing theo topic
    for route in routing_config.get("routes", []):
        if route.get("topic") == topic:
            return {
                "team": route.get("team"),
                "sla_hours": route.get("sla_hours", 24),
                "routed_by": "router_agent (Topic Match)",
                "is_override": False,
            }

    # 3. Default
    return {
        "team": routing_config.get("default_team", "CSKH"),
        "sla_hours": 24,
        "routed_by": "router_agent (Default)",
        "is_override": False,
    }


if __name__ == "__main__":
    print(route_ticket("App Issue", 3))
    print(route_ticket("General Inquiry", 5))  # -> Safety override
