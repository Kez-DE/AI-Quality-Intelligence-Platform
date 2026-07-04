"""KB phủ đủ 6 phòng ban chuẩn: 3 phòng mới thêm phải có tài liệu, đúng department."""
from agent.knowledge_base import search_knowledge

NEW_DEPTS = ["Tài chính & Thanh toán", "Sản phẩm", "Quản lý Rủi ro & Gian lận"]


def test_each_new_department_has_kb_docs():
    for dept in NEW_DEPTS:
        results = search_knowledge("quy trình xử lý", department=dept, top_k=3)
        assert results, f"KB rỗng cho phòng {dept}"
        assert any((r.get("department") or "") == dept for r in results), \
            f"Không có chunk gắn đúng department={dept}"


def test_safety_sops_searchable_under_van_hanh():
    # SOP an toàn/tai nạn thuộc phòng Vận hành (topic Safety route về Vận hành).
    # Trước đây bị gắn nhầm department="Safety" (không phải 1 trong 6 phòng) nên ops
    # không tra cứu được — nay đã sửa.
    results = search_knowledge("tai nạn giao thông", department="Vận hành", top_k=5)
    assert any(r["doc_id"] == "sop_tai_nan_giao_thong.md" for r in results)
