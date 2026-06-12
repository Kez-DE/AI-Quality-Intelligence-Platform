"""Region mapping thống nhất: code <-> label đẹp.

Nguồn chuẩn: data/reference/area_catalog.json. Backend dùng để:
- chuẩn hoá area do người dùng/dataset nhập về code chuẩn (lưu DB),
- trả label đẹp cho mọi nơi cần hiển thị.

Quy ước: DB luôn lưu CODE (vd 'HN-Cau-Giay'). UI luôn hiển thị LABEL
(vd 'Cầu Giấy, Hà Nội'). Frontend có bản mirror trong app/src/lib/regions.ts.
"""

from __future__ import annotations

# code -> label. Giữ khớp 1-1 với app/src/lib/regions.ts.
REGIONS: dict[str, str] = {
    "HN-Cau-Giay": "Cầu Giấy, Hà Nội",
    "HN-Ha-Dong": "Hà Đông, Hà Nội",
    "HN-Dong-Da": "Đống Đa, Hà Nội",
    "HN-Hoan-Kiem": "Hoàn Kiếm, Hà Nội",
    "HN-Tay-Ho": "Tây Hồ, Hà Nội",
    "HN-Long-Bien": "Long Biên, Hà Nội",
    "HCM-Quan-1": "Quận 1, Hồ Chí Minh",
    "HCM-Binh-Thanh": "Bình Thạnh, Hồ Chí Minh",
    "HCM-Thu-Duc": "Thủ Đức, Hồ Chí Minh",
    "HCM-Quan-7": "Quận 7, Hồ Chí Minh",
    "HCM-Tan-Binh": "Tân Bình, Hồ Chí Minh",
    "HCM-Go-Vap": "Gò Vấp, Hồ Chí Minh",
    "DN-Hai-Chau": "Hải Châu, Đà Nẵng",
    "DN-Son-Tra": "Sơn Trà, Đà Nẵng",
    "DN-Ngu-Hanh-Son": "Ngũ Hành Sơn, Đà Nẵng",
    "DN-Thanh-Khe": "Thanh Khê, Đà Nẵng",
}

# label -> code (đảo ngược) để chuẩn hoá dữ liệu cũ lưu bằng label.
_LABEL_TO_CODE = {label.lower(): code for code, label in REGIONS.items()}


def region_label(code_or_label: str | None) -> str:
    """Trả label đẹp từ code (hoặc chính label nếu đã là label)."""
    if not code_or_label:
        return "Không rõ"
    if code_or_label in REGIONS:
        return REGIONS[code_or_label]
    # đã là label hợp lệ
    if code_or_label.lower() in _LABEL_TO_CODE:
        return code_or_label
    return code_or_label


def region_code(code_or_label: str | None) -> str | None:
    """Chuẩn hoá về CODE để lưu DB. Nhận cả code lẫn label."""
    if not code_or_label:
        return None
    if code_or_label in REGIONS:
        return code_or_label
    return _LABEL_TO_CODE.get(code_or_label.lower(), code_or_label)
