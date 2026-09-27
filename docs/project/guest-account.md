# Khách hàng và tài khoản chờ cấp quyền (thay cho vai trò guest)

> **Cập nhật 2026-09-27 (US-077 / decision 0017):** vai trò `guest` đã bị bỏ. File giữ tên cũ để các link hiện có không bị gãy.

Trước đây `guest` gánh ba việc cùng lúc: tài khoản của khách, hàng đợi nhân viên chờ admin duyệt, và vai trò dự phòng khi thiếu hoặc sai role. Giờ nó được tách thành hai khái niệm (xem `CONTEXT.md` ở gốc repo):

- **Khách hàng (Customer)**: người ngoài công ty, **không có tài khoản**, gửi phản hồi và tra cứu trạng thái trên **Customer web**.
- **Tài khoản chờ cấp quyền (Pending account)**: role `pending`. Tài khoản đăng nhập được vào Staff web nhưng **không có quyền gì** cho tới khi admin cấp `admin`, `manager` hoặc `staff`.

---

## 1. Phân quyền tổng quan

| Tính năng | Admin | Manager | Staff | Pending | Khách hàng (không tài khoản) |
|-----------|:-----:|:-------:|:-----:|:-------:|:-----:|
| Gửi phản hồi trên Customer web | — | — | — | — | ✅ |
| Tra cứu trạng thái bằng mã tra cứu | — | — | — | — | ✅ |
| Dashboard / cockpit | ✅ | ✅ | ✅ | ❌ | ❌ |
| Gửi feedback trong Staff web (`POST /api/feedback/submit`) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Xem danh sách feedback, sửa nhãn AI (HITL) | ✅ | ✅ | ✅ | ❌ | ❌ |
| AI Chat nội bộ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Quản lý người dùng, tạo tài khoản | ✅ | ❌ | ❌ | ❌ | ❌ |

Quyền theo phòng ban của manager/staff xem ở [rbac-departments.md](rbac-departments.md).

---

## 2. Khách hàng và Customer web

Customer web là một ứng dụng riêng ở `customer-web/` (Vite + React, SPA tĩnh), deploy thành service riêng, tách hẳn khỏi Staff web (`app/`). Nó không có Supabase client, không đăng nhập, không chứa code nội bộ. Chỉ có tiếng Việt, thiết kế ưu tiên điện thoại vì khách thường quét mã QR.

Hai trang:

- `/`: form gửi phản hồi (nội dung, kênh, khu vực) và một ô "Tra cứu mã".
- `/status/:code`: trạng thái của một phản hồi.

Trình duyệt gọi thẳng backend qua `VITE_BACKEND_API_URL`, không qua proxy, vì rate limit tính theo IP của client:

- `POST /api/public/feedback`: không cần token. Trả về mã tra cứu (`public_ref`).
- `GET /api/public/feedback/{public_ref}`: trả đúng ba trường `public_ref`, `status`, `created_at`.

Khách hàng chỉ thấy:

- Sau khi gửi: **mã tra cứu** (có nút sao chép) và link tới trang trạng thái. Không hiện nhãn AI (topic, sentiment, severity).
- Trang trạng thái: **trạng thái** và **ngày gửi**. Ba nhãn trạng thái: `received` → "Đã tiếp nhận", `under_review` → "Đang xem xét", `reviewed` → "Đã xem xét". "Đã xem xét" nghĩa là nhân viên đã kiểm tra phân loại của AI, không có nghĩa sự việc đã được xử lý xong.
- Mã không tồn tại, đã hết hạn lưu trữ hoặc đã bị xoá nội dung đều hiện cùng một thông báo "không tìm thấy".

Chống lạm dụng:

- Rate limit theo hash IP: mặc định 5 lần gửi và 60 lần tra cứu mỗi giờ (`RATE_LIMIT_PUBLIC_INTAKE`, `RATE_LIMIT_PUBLIC_STATUS`).
- Honeypot: form có một ô ẩn tên `website`. Người thật để trống. Nếu ô này có nội dung, backend trả 400, không lưu gì, và lần gửi đó vẫn bị tính vào rate limit.
- Chưa có captcha/Turnstile (backlog).

Quyền riêng tư: số điện thoại, email, biển số được che tự động trước khi lưu (`clean_text`). Mỗi phản hồi ẩn danh có `retention_until = ngày gửi + 180 ngày`. Mỗi ngày lúc 03:00 (giờ Việt Nam), `backend-worker` thay nội dung các phản hồi quá hạn bằng "[Đã xoá theo hạn lưu trữ]", xoá `submitter_hash`, và ghi `redacted_at`. Nhãn, khu vực, kênh, ngày và điểm rủi ro được giữ lại, nên dashboard và xu hướng không đổi.

Phía Staff web, phản hồi từ Customer web có `source = 'public'`, `user_id = NULL`, và hiện badge **"Khách hàng"** trong danh sách feedback.

---

## 3. Tài khoản chờ cấp quyền (`pending`)

Một tài khoản ở trạng thái `pending` khi:

- là tài khoản `guest` cũ: migration của US-077 đổi toàn bộ `guest` thành `pending`, không xoá tài khoản hay feedback nào;
- được tạo ngoài form "Tạo tài khoản" của admin, ví dụ qua Supabase Dashboard. Trigger `handle_new_user` gán `pending`, trừ profile đầu tiên của hệ thống thành `admin`;
- có role bị thiếu hoặc không hợp lệ: mọi chỗ fail-closed (`auth_guard.py`, route guard, MCP) đều rơi về `pending`.

Tài khoản `pending` được gì:

- **Staff web**: sau khi đăng nhập chỉ thấy màn "Tài khoản đang chờ admin cấp quyền" với nút đăng xuất. Không có thanh điều hướng, không tải dữ liệu.
- **Backend**: 403 ở mọi endpoint, trừ `GET /api/me`, `POST /api/me/password` và `/health`.
- **Chat**: `POST /api/agent/chat` trả 403. Tầng chat công khai giờ chỉ còn cho ops staff khi gửi cờ `public_only` (widget trang chủ).
- **MCP**: qua HTTP, `SupabaseTokenVerifier` từ chối identity `pending` hoặc role lạ (cả JWT lẫn bearer `mcp_tokens`) bằng 401: không có phiên, không có danh sách tool. Bản stdio với `MCP_ROLE` rỗng hoặc `pending` không có tool nào.
- **Database (RLS)**: `is_ops_staff()` loại `pending`. Chỉ ops staff mới `INSERT` được vào `feedback`, và phải đúng `user_id` của mình. Không ai tự `INSERT`/`DELETE` được dòng `profiles`. Knowledge base nội bộ (`graph_nodes`, `graph_edges`) chỉ ops staff đọc được.

Admin cấp quyền ở trang Quản lý người dùng: tab "Chờ cấp quyền" liệt kê tài khoản `pending` với nút "Cấp quyền Nhân viên" / "Cấp quyền Quản lý" (`PATCH /api/users/{id}/role`); backend còn có `POST /api/users/bulk-approve` để duyệt hàng loạt thành staff/manager.

> ⚠️ Nút "Từ chối và xoá tài khoản" gọi xoá tài khoản (`auth.admin.delete_user`). Mọi FK tới `auth.users` là `ON DELETE CASCADE`, nên feedback, alert, lịch sử chat và MCP token của người đó bị xoá theo. Đã ghi vào backlog, chưa sửa.

---

## 4. Tạo tài khoản

Chỉ admin tạo tài khoản. Staff web không còn form đăng ký, cũng không còn nút đăng nhập Google/Facebook.

### Cách 1: Form "Tạo tài khoản" trong trang Admin (cách chính)

1. Admin nhập email, họ tên, role (`admin` / `manager` / `staff`), phòng ban (tuỳ chọn) và mật khẩu tạm.
2. Mật khẩu tạm phải đạt 5 tiêu chí: ít nhất 8 ký tự, có chữ hoa, chữ thường, chữ số và ký tự đặc biệt.
3. Frontend gọi `POST /api/admin/users` (chỉ admin). Backend tạo tài khoản bằng service role (`auth.admin.create_user`, email xác nhận sẵn, `app_metadata.must_change_password = true`), gán role và phòng ban, ghi `audit_logs`, trả 201. Email trùng thì trả 409; dữ liệu sai trả 400 và chỉ nêu tên field. Mật khẩu không bao giờ được ghi log hay trả về.
4. Admin tự gửi email và mật khẩu tạm cho người đó (hệ thống không gửi mail mời).
5. Lần đăng nhập đầu tiên, Staff web chỉ hiện màn đổi mật khẩu (nhập hai lần, cùng 5 tiêu chí). Màn này gọi `POST /api/me/password`: backend kiểm lại 5 tiêu chí rồi gọi `auth.admin.update_user_by_id` để đặt mật khẩu mới và `app_metadata.must_change_password = false`. Staff web gọi `supabase.auth.refreshSession()` để lấy JWT mới không còn cờ, rồi mới vào màn thường.

Cờ nằm trong `app_metadata`, không phải `user_metadata`: chỉ service role ghi được `app_metadata`, nên người dùng không tự xoá cờ bằng `supabase.auth.updateUser` được. Chừng nào cờ còn bật, server tự chặn, không phụ thuộc Staff web:

- `require_ops_staff`, `require_admin`, `require_manager` trả 403 "Bạn cần đổi mật khẩu tạm trước khi tiếp tục". Chỉ `GET /api/me` (có trả `must_change_password`) và `POST /api/me/password` không cần role.
- MCP HTTP từ chối JWT còn cờ bằng 401.
- RLS: `password_is_current()` đọc `auth.jwt() -> app_metadata`; `is_ops_staff()` và `is_admin()` đòi hàm này đúng, nên PostgREST và realtime cũng đóng với tài khoản còn cờ.

### Cách 2: Supabase Dashboard

**Authentication → Users → Add user**. Tài khoản tạo kiểu này vào hệ thống với role `pending` (trừ khi đây là profile đầu tiên, sẽ thành `admin`). Admin cấp quyền như ở mục 3. Không có bước bắt đổi mật khẩu.

### Tắt đăng ký trên Supabase (thao tác tay)

Code đã bỏ form đăng ký, nhưng Supabase Auth vẫn nhận đăng ký trực tiếp qua API cho tới khi chủ dự án tắt trong Dashboard. Xem [setup-supabase.md](setup-supabase.md) mục 8.1. Trước khi tắt, tài khoản tự đăng ký vẫn chỉ vào hệ thống với role `pending`, không có quyền.

---

## 5. Kiểm thử nhanh (chỉ trên stack local)

Chạy với backend local trỏ vào Supabase local (`supabase start`). **Không** dùng file `.env` ở gốc repo, vì file đó trỏ vào production.

```bash
# Khách hàng: gửi không cần token → 200 kèm public_ref
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"text":"Tài xế chạy quá nhanh","channel":"web","area":"HN-Cau-Giay"}' \
  http://127.0.0.1:8000/api/public/feedback

# Honeypot có nội dung → 400, không lưu gì
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"text":"spam","website":"http://spam.example"}' \
  http://127.0.0.1:8000/api/public/feedback

# Tra cứu → chỉ public_ref, status, created_at
curl -s http://127.0.0.1:8000/api/public/feedback/<public_ref>

# Tài khoản pending: /api/me → 200 (role "pending"), mọi thứ khác (trừ POST /api/me/password) → 403
curl -s -H "Authorization: Bearer $TOKEN_PENDING" http://127.0.0.1:8000/api/me
curl -s -X POST -H "Authorization: Bearer $TOKEN_PENDING" \
  -H "Content-Type: application/json" -d '{"text":"test"}' \
  http://127.0.0.1:8000/api/feedback/submit
# → 403 Forbidden
```

Danh sách kiểm thử đầy đủ: `docs/harness/stories/epics/E04-public-intake/US-077-separate-customer-web/validation.md`.
