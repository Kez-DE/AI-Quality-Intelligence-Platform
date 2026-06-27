"""RBAC tiering bộ tool của chat agent theo vai trò (role).

Tầng quyền (kết hợp với scope_team đã ép phòng ban ở execute_tool):
- staff   : search_knowledge_base (SOP/cách làm) + get_team_priority_tasks (task phòng mình).
- manager : thêm get_feedback_summary/get_hot_areas/get_sla_tickets (báo cáo) — vẫn scope phòng.
- admin   : toàn bộ tool, toàn hệ thống (khác biệt với manager là scope_team=None).
"""
from agent.chat_tools import tools_for_role, TOOLS_DEFINITIONS


def _names(tools):
    return {t["function"]["name"] for t in tools}


def test_admin_gets_all_tools():
    assert _names(tools_for_role("admin")) == _names(TOOLS_DEFINITIONS)


def test_staff_only_howto_and_own_tasks():
    assert _names(tools_for_role("staff")) == {"search_knowledge_base", "get_team_priority_tasks"}


def test_staff_has_no_aggregate_analytics():
    s = _names(tools_for_role("staff"))
    assert s.isdisjoint({"get_feedback_summary", "get_hot_areas", "get_sla_tickets"})


def test_manager_can_access_reports():
    m = _names(tools_for_role("manager"))
    assert {"get_feedback_summary", "get_hot_areas", "get_sla_tickets"}.issubset(m)
    assert {"search_knowledge_base", "get_team_priority_tasks"}.issubset(m)


def test_tier_is_monotonic():
    s = _names(tools_for_role("staff"))
    m = _names(tools_for_role("manager"))
    a = _names(tools_for_role("admin"))
    assert s < m, "staff phải ít tool hơn manager"
    assert m <= a, "manager là tập con của admin (khác biệt còn lại là scope_team phòng ban)"


def test_unknown_role_defaults_to_full_then_scope_guards():
    # Vai trò lạ -> mặc định full tool; scope_team ở execute_tool vẫn là lớp chặn dữ liệu.
    assert _names(tools_for_role(None)) == _names(TOOLS_DEFINITIONS)
