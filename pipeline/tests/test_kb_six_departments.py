"""KB phủ đủ 6 phòng ban chuẩn: 3 phòng mới thêm phải có tài liệu, đúng department."""
from agent.knowledge_base import search_knowledge

NEW_DEPTS = ["Tài chính & Thanh toán", "Sản phẩm", "Quản lý Rủi ro & Gian lận"]


def test_each_new_department_has_kb_docs():
    for dept in NEW_DEPTS:
        results = search_knowledge("quy trình xử lý", department=dept, top_k=3)
        assert results, f"KB rỗng cho phòng {dept}"
        assert any((r.get("department") or "") == dept for r in results), \
            f"Không có chunk gắn đúng department={dept}"


def test_legacy_kb_still_searchable():
    # phòng legacy vẫn ra kết quả — không làm hỏng KB cũ
    results = search_knowledge("tai nạn giao thông", department="Safety", top_k=3)
    assert results
