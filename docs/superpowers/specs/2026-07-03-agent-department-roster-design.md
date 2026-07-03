# Spec: Agent biết roster phòng ban (fix "chưa có thông tin số phòng ban")

**Date:** 2026-07-03
**Lane:** Normal (sửa ngữ cảnh agent; không schema/auth/quyền)

## Bối cảnh & nguyên nhân

Admin chat hỏi "hiện tại có bao nhiêu phòng ban" → agent trả "chưa có thông tin". **Không phải
thiếu data:** danh sách 6 phòng là hằng số cứng `departments.py → DEPARTMENTS` (IT, CSKH, Vận
hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận). Nguyên nhân thật:

- `AGENT_SYSTEM_PROMPT` và `DATA_CONTEXT` (`services/agent_context.py`) **không liệt kê phòng ban**.
- Không tool nào trả roster.
- Prompt ra lệnh: "chỉ nêu số liệu khi có trong DATA_CONTEXT; thiếu thì nói chưa đủ" → agent nói
  "chưa có thông tin".

Thêm KB data KHÔNG fix chắc chắn (search_knowledge_base bị scope + phụ thuộc câu hỏi).

## Fix

Bơm roster (từ chính `DEPARTMENTS` — một nguồn sự thật) vào `build_agent_data_context()`:

- **Mọi ops/admin:** thêm dòng `- Phòng ban hệ thống (6): IT, CSKH, Vận hành, Tài chính & Thanh
  toán, Sản phẩm, Quản lý Rủi ro & Gian lận.` (đọc từ `DEPARTMENTS`, không hardcode lại).
- **Admin (scope_team None):** thêm **đếm feedback theo từng phòng** từ feedback đã tải sẵn
  (route qua `route_ticket` — đã import), ví dụ `- Feedback theo phòng: CSKH: 42, Vận hành: 30,
  ...` → agent trả lời được "phòng nào nóng nhất / so sánh phòng ban".
- **staff/manager:** chỉ roster tên (sự thật cấu trúc, đã hiển thị trong UI), KHÔNG đếm
  per-phòng (giữ scope dữ liệu như cũ — chỉ thấy phòng mình).

## Ràng buộc guest (bắt buộc)

Khách KHÔNG được thấy roster/đếm phòng — chỉ public data. Đảm bảo **cấu trúc sẵn có**: guest và
`public_only` đi nhánh `GUEST_SYSTEM_PROMPT` + public KB (`main.py:1172`), KHÔNG gọi
`build_agent_data_context`. Fix chỉ đụng hàm này nên khách không bị ảnh hưởng. Thêm test khẳng
định guest path không chứa roster.

## Files
- Modify: `pipeline/services/agent_context.py` (chỉ `build_agent_data_context`, + import `DEPARTMENTS`)
- Test: `pipeline/tests/test_agent_department_roster.py`

## Validation
- `build_agent_data_context(admin)` chứa đủ 6 tên phòng + dòng "Feedback theo phòng".
- `build_agent_data_context(staff có phòng)` chứa 6 tên phòng, KHÔNG có đếm per-phòng của phòng khác.
- `build_agent_data_context(staff chưa gán phòng)` giữ nguyên thông báo "chưa có phạm vi".
- Roster đọc từ `DEPARTMENTS` (đổi hằng → context đổi theo; không hardcode chuỗi phòng).
- Guest: `GUEST_SYSTEM_PROMPT` không chứa roster (khách chỉ public).
- E2E thật: hỏi "có bao nhiêu phòng ban" bằng JWT admin → trả đúng 6 phòng + liệt kê.

## Không đổi
- Guest/public path, tools, schema, quyền, KB data.
