# Spec: Bổ sung KB từ chính sách thật (cào greensm + tham khảo Be/Grab)

**Date:** 2026-07-03
**Lane:** Normal (data/KB cho RAG; không đụng auth/schema/quyền/runtime code)

## Bối cảnh & mục tiêu

KB nội bộ hiện là mock tự soạn (`architecture.md`). Làm chính xác hơn bằng cách neo SOP 6
phòng vào **chính sách công khai thật của xanhSM (greensm.com)**, làm mới public FAQ khách,
và re-index vector. Be/Grab chỉ tham khảo mẫu quy trình ngành.

Hạ tầng đã sẵn: Firecrawl chạy `:3002` (verify: cào greensm terms-policies OK, 5865 ký tự);
scripts `scrape_public_policy.py` + `build_public_kb.py` + `seed_graph_kb.py` đã có.

## Nguồn & guardrail (BẮT BUỘC)

| Nguồn | Vai trò | Vào repo? |
|---|---|---|
| greensm.com/vn-vi (xanhSM) | Nguồn sự thật duy nhất: mọi FACT + toàn bộ SĐT/email hỗ trợ | Có (qua public_kb + trích trong SOP) |
| be.com.vn, grab.com/vn | CHỈ tham khảo mẫu quy trình khi soạn SOP | **KHÔNG** — output ở `/tmp`, không commit |

- **Liên hệ (SĐT/email/hotline) trong `data/` chỉ được lấy từ greensm.com.** Be/Grab không
  bao giờ đóng góp số liệu hay liên hệ.
- Nội dung Be/Grab **không vào repo**: cào vào `/tmp/competitor_scrape/` (gitignored), chỉ
  dùng làm tài liệu đọc khi soạn SOP. Nhờ vậy guardrail "không có liên hệ Be/Grab trong
  data/" thỏa hiển nhiên (không có content Be/Grab nào trong repo).
- Câu/pattern mượn từ ngành → ghi rõ trong SOP: "tham khảo thông lệ ngành, không phải chính
  sách xanhSM chính thức".

## Thay đổi

### 1. Cào greensm (mở rộng nguồn)
- `pipeline/scripts/scrape_public_policy.py`: mở rộng `SEED_URLS` (thêm trang chính sách tài
  xế/cước/hủy chuyến/an toàn nếu tồn tại) + nới regex `discover_help_links` để bắt thêm path
  `/terms-policies/*`. Output `/tmp/public_scrape/`.

### 2. Cào Be/Grab (tham khảo, tách biệt)
- Script cào nhẹ (có thể tham số hóa `scrape_public_policy.py` hoặc script phụ) → be.com.vn +
  grab.com/vn trang help/terms → `/tmp/competitor_scrape/`. Không commit. Chỉ để đọc.

### 3. Dựng KB
- **Public KB (khách):** chạy `build_public_kb.py` → làm mới `data/public_kb/*.md` (chỉ
  greensm). Nếu cấu trúc trang đổi làm parser lệch → chỉnh parser tối thiểu.
- **Internal SOP 6 phòng:** với mỗi phòng, làm giàu/soạn lại file trong
  `data/knowledge_base/sop/` (+ `sla/`, `tech/`) neo fact greensm + pattern ngành (đánh dấu),
  frontmatter `department:` đúng tên chuẩn + `source:` URL greensm khi có. Phủ đủ: Vận hành,
  CSKH, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận, IT. Phần thuần nội bộ
  không có nguồn công khai → giữ + ghi chú "nội bộ, chưa có nguồn công khai".
- **Liên hệ hỗ trợ:** trích hotline/email xanhSM từ greensm → dùng thống nhất trong KB.

### 4. Re-index
- `seed_graph_kb.py` (Supabase + Cohere) → RAG + `search_knowledge_base` phủ nội dung mới.

## Validation
- Mỗi URL greensm cào ra `.md` non-empty; manifest ghi đủ.
- `data/public_kb` dựng lại có câu trả lời thật (không rỗng hàng loạt).
- Mỗi phòng trong 6 phòng có ≥1 SOP `department:` đúng + `source:` khi áp dụng.
- **grep guardrail:** không có SĐT/email/tên miền của Be/Grab trong `data/` (regex số VN +
  `be.com.vn`/`grab.com`); liên hệ trong KB khớp greensm.
- `pipeline/tests/test_kb_six_departments.py` vẫn pass; thêm assert liên hệ (nếu cần).
- `seed_graph_kb.py` chạy OK; hybrid `search_knowledge_base(query, scope_team=<phòng>)` ra
  nội dung mới.

## Không đổi
- Runtime: chat, MCP, rag_engine, schema, quyền. Chỉ thêm/sửa file data + mở rộng script cào.
