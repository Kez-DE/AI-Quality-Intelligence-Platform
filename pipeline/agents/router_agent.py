"""Router agent: định tuyến ticket về phòng ban theo routing_table.json.

Khác bản origin:
- Sửa bug NameError (origin dùng `severity_level` chưa định nghĩa, đúng phải là `severity`).
- Taxonomy đọc từ <repo>/data/taxonomy/ (layout phẳng) thay vì data_real/.
"""

import json
from typing import Any, Dict
import time

from agents.common import log_agent_run
from agents.schemas import RouterOutput
from core.paths import TAXONOMY_DIR
from departments import normalize_department

ROUTING_TABLE_PATH = TAXONOMY_DIR / "routing_table.json"


# Cache theo mtime: giữ được tính config-driven (sửa JSON là ăn ngay, không cần restart)
# mà không phải đọc + parse file mỗi lần route. insight_agent gọi route_ticket một lần
# cho MỖI feedback của MỖI phòng — 6 phòng x 2000 bản ghi là 12.000 lượt đọc đĩa mỗi chu kỳ.
_routing_cache: tuple[float, Dict[str, Any]] | None = None


def load_routing_table() -> Dict[str, Any]:
    global _routing_cache
    if not ROUTING_TABLE_PATH.exists():
        raise FileNotFoundError(f"Routing taxonomy not found: {ROUTING_TABLE_PATH}")
    mtime = ROUTING_TABLE_PATH.stat().st_mtime
    if _routing_cache is not None and _routing_cache[0] == mtime:
        return _routing_cache[1]
    with open(ROUTING_TABLE_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    if not config.get("routes"):
        raise ValueError(f"Routing taxonomy has no routes: {ROUTING_TABLE_PATH}")
    _routing_cache = (mtime, config)
    return config


def route_ticket(
    topic: str,
    severity: Any,
    sentiment: str | None = None,
    *,
    log_run: bool = True,
) -> Dict[str, Any]:
    """Định tuyến ticket về đúng phòng ban.

    Thứ tự ưu tiên:
      1. Severity override — P5 ép về Vận hành (đội phản ứng nhanh), thắng tất cả.
      2. Sentiment override — feedback positive về Sản phẩm để nâng cấp UX, NHƯNG chỉ với
         các topic được liệt kê trong override["topics"] (vd "Other", "App Issue"). Positive
         gắn chủ đề chuyên môn khác không khớp danh sách này nên rơi xuống topic match
         (đúng phòng chuyên môn).
      3. Topic match — theo bảng routes.
      4. Default team.
    """
    start_time = time.time()
    routing_config = load_routing_table()

    # 1. Severity override trước (P5 -> Vận hành, phản ứng nhanh)
    str_sev = str(severity).strip().upper()
    formatted_sev = f"P{str_sev}" if str_sev.isdigit() else str_sev
    if formatted_sev not in {"P1", "P2", "P3", "P4", "P5"}:
        formatted_sev = None
    input_hash = f"{topic}_{severity}"

    for override in routing_config.get("severity_overrides", []):
        ov_sev = str(override.get("severity", "")).upper()
        if formatted_sev == ov_sev:
            output = RouterOutput(
                team=normalize_department(override.get("team"), "Vận hành"),
                sla_hours=override.get("sla_hours", 1),
                routed_by=f"router_agent ({ov_sev} Override)",
                is_override=True,
                priority=override.get("priority_default"),
                description=override.get("description"),
            )
            if log_run:
                log_agent_run(
                    run_id=f"route_{int(time.time())}",
                    agent_name="router_agent",
                    status="success",
                    latency_ms=int((time.time() - start_time) * 1000),
                    output_summary=f"{output.team} (Sev Override)",
                    input_hash=input_hash,
                )
            return output.model_dump()

    # 2. Sentiment override (positive -> Sản phẩm để nâng cấp UX), chỉ áp cho các topic trong override["topics"].
    #    BẮT BUỘC khai báo "topics" rõ ràng: override thiếu/rỗng "topics" bị bỏ qua,
    #    để tránh tái sinh bug cũ (positive ép MỌI topic về một phòng).
    if sentiment:
        str_sentiment = str(sentiment).strip().lower()
        for override in routing_config.get("sentiment_overrides", []):
            if str(override.get("sentiment", "")).strip().lower() != str_sentiment:
                continue
            allowed_topics = override.get("topics")
            if not allowed_topics or topic not in allowed_topics:
                continue
            output = RouterOutput(
                team=normalize_department(override.get("team"), "Sản phẩm"),
                sla_hours=override.get("sla_hours", 48),
                routed_by=f"router_agent ({str_sentiment} Sentiment)",
                is_override=True,
                priority=override.get("priority_default"),
                description=override.get("description"),
            )
            if log_run:
                log_agent_run(
                    run_id=f"router_{int(time.time())}",
                    agent_name="router_agent",
                    status="success",
                    latency_ms=int((time.time() - start_time) * 1000),
                    output_summary=f"Routed to {output.team} (Sentiment)",
                    input_hash=f"{topic}_{severity}_{str_sentiment}"
                )
            return output.model_dump()

    # 3. Routing theo topic
    for route in routing_config.get("routes", []):
        if route.get("topic") == topic:
            output = RouterOutput(
                team=normalize_department(route.get("team"), "CSKH"),
                sla_hours=route.get("sla_hours", 24),
                routed_by="router_agent (Topic Match)",
                is_override=False,
                priority=formatted_sev or route.get("priority_default"),
                description=route.get("description"),
            )
            if log_run:
                log_agent_run(
                    run_id=f"router_{int(time.time())}",
                    agent_name="router_agent",
                    status="success",
                    latency_ms=int((time.time() - start_time) * 1000),
                    output_summary=f"Routed to {output.team} (Topic Match)",
                    input_hash=f"{topic}_{severity}"
                )
            return output.model_dump()

    # 4. Default
    output = RouterOutput(
        team=normalize_department(routing_config.get("default_team"), "CSKH"),
        sla_hours=24,
        priority=formatted_sev or "P4",
        routed_by="router_agent (Default)",
        is_override=False,
    )
    if log_run:
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
    print(route_ticket("General Inquiry", 5))  # -> Vận hành override
    print(route_ticket("Other", 2, sentiment="positive"))  # -> Sản phẩm
