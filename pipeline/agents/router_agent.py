"""Router agent: định tuyến ticket về phòng ban theo routing_table.json.

Khác bản origin:
- Sửa bug NameError (origin dùng `severity_level` chưa định nghĩa, đúng phải là `severity`).
- Taxonomy đọc từ <repo>/data/taxonomy/ (layout phẳng) thay vì data_real/.
"""

import json
from pathlib import Path
from typing import Any, Dict
import time

from agents.common import log_agent_run
from agents.schemas import RouterOutput

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
    start_time = time.time()
    routing_config = load_routing_table()

    # 1. Severity override trước (Safety-first)
    str_sev = str(severity).upper()
    for override in routing_config.get("severity_overrides", []):
        ov_sev = str(override.get("severity", "")).upper()
        if ov_sev == str_sev or (str_sev in {"5", "P5"} and ov_sev == "P5"):
            output = RouterOutput(
                team=override.get("team", "Safety"),
                sla_hours=override.get("sla_hours", 1),
                routed_by=f"router_agent ({ov_sev} Override)",
                is_override=True,
            )
            log_agent_run(
                run_id=f"router_{int(time.time())}",
                agent_name="router_agent",
                status="success",
                latency_ms=int((time.time() - start_time) * 1000),
                output_summary=f"Routed to {output.team} (Override)",
                input_hash=f"{topic}_{severity}"
            )
            return output.model_dump()

    # 2. Routing theo topic
    for route in routing_config.get("routes", []):
        if route.get("topic") == topic:
            output = RouterOutput(
                team=route.get("team"),
                sla_hours=route.get("sla_hours", 24),
                routed_by="router_agent (Topic Match)",
                is_override=False,
            )
            log_agent_run(
                run_id=f"router_{int(time.time())}",
                agent_name="router_agent",
                status="success",
                latency_ms=int((time.time() - start_time) * 1000),
                output_summary=f"Routed to {output.team} (Topic Match)",
                input_hash=f"{topic}_{severity}"
            )
            return output.model_dump()

    # 3. Default
    output = RouterOutput(
        team=routing_config.get("default_team", "CSKH"),
        sla_hours=24,
        routed_by="router_agent (Default)",
        is_override=False,
    )
    log_agent_run(
        run_id=f"router_{int(time.time())}",
        agent_name="router_agent",
        status="success",
        latency_ms=int((time.time() - start_time) * 1000),
        output_summary=f"Routed to {output.team} (Default)",
        input_hash=f"{topic}_{severity}"
    )
    return output.model_dump()


if __name__ == "__main__":
    print(route_ticket("App Issue", 3))
    print(route_ticket("General Inquiry", 5))  # -> Safety override
