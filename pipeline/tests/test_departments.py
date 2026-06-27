from departments import DEPARTMENTS, alert_department, normalize_department


def test_departments_are_distinct_and_canonical():
    assert DEPARTMENTS == (
        "IT",
        "CSKH",
        "Vận hành",
        "Tài chính & Thanh toán",
        "Sản phẩm",
        "Quản lý Rủi ro & Gian lận",
    )
    assert len(set(DEPARTMENTS)) == 6


def test_normalize_legacy_department_aliases():
    assert normalize_department("Vận Hành") == "Vận hành"
    assert normalize_department("Vận hành & Đào tạo") == "Vận hành"
    assert normalize_department("Driver Mgmt") == "Vận hành"


def test_normalize_new_department_aliases():
    assert normalize_department("finance") == "Tài chính & Thanh toán"
    assert normalize_department("Thanh toán") == "Tài chính & Thanh toán"
    assert normalize_department("product") == "Sản phẩm"
    assert normalize_department("fraud") == "Quản lý Rủi ro & Gian lận"
    assert normalize_department("Rủi ro") == "Quản lý Rủi ro & Gian lận"


def test_marketing_no_longer_resolves():
    assert normalize_department("Marketing") is None


def test_alert_department_prefers_structured_field_and_supports_legacy():
    assert alert_department({
        "assigned_team": "Sản phẩm",
        "description": "**Assigned Team:** CSKH",
    }) == "Sản phẩm"
    assert alert_department({"description": "x\n**Assigned Team:** CSKH\n"}) == "CSKH"
