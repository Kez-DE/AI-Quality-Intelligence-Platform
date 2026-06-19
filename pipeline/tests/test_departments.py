from departments import DEPARTMENTS, alert_department, normalize_department


def test_departments_are_distinct_and_canonical():
    assert DEPARTMENTS == ("IT", "Safety", "CSKH", "Vận hành", "Pricing", "Marketing")
    assert len(set(DEPARTMENTS)) == 6


def test_normalize_legacy_department_aliases():
    assert normalize_department("Vận Hành") == "Vận hành"
    assert normalize_department("Vận hành & Đào tạo") == "Vận hành"
    assert normalize_department("Driver Mgmt") == "Vận hành"


def test_alert_department_prefers_structured_field_and_supports_legacy():
    assert alert_department({
        "assigned_team": "Marketing",
        "description": "**Assigned Team:** CSKH",
    }) == "Marketing"
    assert alert_department({"description": "x\n**Assigned Team:** Pricing\n"}) == "Pricing"
