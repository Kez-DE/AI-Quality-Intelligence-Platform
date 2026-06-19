"""Canonical department names used by RBAC, routing and ticket workflows."""

from typing import Optional


DEPARTMENTS = ("IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing")

_DEPARTMENT_ALIASES = {
    "it": "IT",
    "safety": "Safety",
    "cskh": "CSKH",
    "vận hành": "Vận hành",
    "vận hành & đào tạo": "Vận hành",
    "van hanh": "Vận hành",
    "driver mgmt": "Vận hành",
    "pricing": "Pricing",
    "marketing": "Marketing",
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
