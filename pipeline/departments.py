"""Canonical department names used by RBAC, routing and ticket workflows."""

from typing import Optional


DEPARTMENTS = (
    "IT",
    "CSKH",
    "Vận hành",
    "Tài chính & Thanh toán",
    "Sản phẩm",
    "Quản lý Rủi ro & Gian lận",
)

_DEPARTMENT_ALIASES = {
    "it": "IT",
    "cskh": "CSKH",
    "vận hành": "Vận hành",
    "vận hành & đào tạo": "Vận hành",
    "van hanh": "Vận hành",
    "driver mgmt": "Vận hành",
    "tài chính": "Tài chính & Thanh toán",
    "thanh toán": "Tài chính & Thanh toán",
    "finance": "Tài chính & Thanh toán",
    "sản phẩm": "Sản phẩm",
    "product": "Sản phẩm",
    "rủi ro": "Quản lý Rủi ro & Gian lận",
    "gian lận": "Quản lý Rủi ro & Gian lận",
    "risk": "Quản lý Rủi ro & Gian lận",
    "fraud": "Quản lý Rủi ro & Gian lận",
}


def normalize_department(value: object, default: Optional[str] = None) -> Optional[str]:
    """Map legacy/free-text team names to one of the six RBAC departments."""
    raw = str(value or "").strip()
    if not raw:
        return default
    lowered = raw.casefold()
    if lowered in _DEPARTMENT_ALIASES:
        return _DEPARTMENT_ALIASES[lowered]
    for alias, department in _DEPARTMENT_ALIASES.items():
        if alias in lowered:
            return department
    return default


def alert_department(alert: dict, default: Optional[str] = None) -> Optional[str]:
    """Read structured assigned_team first, then parse legacy Markdown metadata."""
    structured = normalize_department(alert.get("assigned_team"))
    if structured:
        return structured
    description = str(alert.get("description") or "")
    marker = "**Assigned Team:**"
    if marker in description:
        legacy = description.split(marker, 1)[1].strip().split("\n", 1)[0]
        return normalize_department(legacy, default)
    return default


__all__ = ["DEPARTMENTS", "alert_department", "normalize_department"]
