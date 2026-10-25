# Khách hàng, tài khoản khách hàng và tài khoản chờ cấp quyền

> **Cập nhật 2026-09-27 (US-077 / decision 0017):** vai trò `guest` đã bị bỏ. File giữ tên cũ để các link hiện có không bị gãy.
>
> **Cập nhật 2026-09-28 (US-078 / decision 0018):** `guest` quay lại với đúng một nghĩa: **tài khoản khách hàng** (Customer account), chỉ dùng trên Customer web. Tự đăng ký giờ vào với role `guest`, không còn vào `pending`. `pending` giữ nguyên nghĩa.

Trước US-077, `guest` gánh ba việc cùng lúc: tài khoản của khách, hàng đợi nhân viên chờ admin duyệt, và vai trò dự phòng khi thiếu hoặc sai role. Giờ mỗi việc có một khái niệm riêng (xem `CONTEXT.md` ở gốc repo):

- **Khách hàng (Customer)**: người ngoài công ty, gửi phản hồi và tra cứu trạng thái trên **Customer web**. Tài khoản là **tuỳ chọn**: không có tài khoản thì tra cứu bằng mã tra cứu.
- **Tài khoản khách hàng (Customer account)**: role `guest`. Khách hàng tự đăng ký trên Customer web để xem lịch sử phản hồi của mình và dùng trợ lý chat. **Không vào được Staff web** và không có quyền nội bộ nào.
- **Tài khoản chờ cấp quyền (Pending account)**: role `pending`. Tài khoản đăng nhập được vào Staff web nhưng **không có quyền gì** cho tới khi admin cấp `admin`, `manager` hoặc `staff`.

---

## 1. Phân quyền tổng quan

| Tính năng | Admin | Manager | Staff | Pending | Tài khoản khách hàng (`guest`) | Khách hàng (không tài khoản) |
|-----------|:-----:|:-------:|:-----:|:-------:|:-----:|:-----:|
| Gửi phản hồi trên Customer web | — | — | — | — | ✅ | ✅ |
| Tra cứu trạng thái bằng mã tra cứu | — | — | — | — | ✅ | ✅ |
| Xem lịch sử phản hồi của mình (`/cua-toi`) | — | — | — | — | ✅ | ❌ |
| Trợ lý chat cho khách hàng | — | — | — | — | ✅ | ❌ |
| Dashboard / cockpit | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Gửi feedback trong Staff web (`POST /api/feedback/submit`) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Xem danh sách feedback, sửa nhãn AI (HITL) | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| AI Chat nội bộ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Quản lý người dùng, tạo tài khoản | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

Quyền theo phòng ban của manager/staff xem ở [rbac-departments.md](rbac-departments.md).

---

## 2. Khách hàng và Customer web

Customer web là một ứng dụng riêng ở `customer-web/` (Vite + React, SPA tĩnh), deploy thành service riêng, tách hẳn khỏi Staff web (`app/`). Nó không chứa code nội bộ. Từ US-078 nó có Supabase client (publishable key) để khách hàng đăng nhập nếu muốn; không đăng nhập thì mọi thứ chạy như trước. Chỉ có tiếng Việt, thiết kế ưu tiên điện thoại vì khách thường quét mã QR.

Hai trang không cần đăng nhập:

- `/`: form gửi phản hồi (nội dung, kênh, khu vực) và một ô "Tra cứu mã".
- `/status/:code`: trạng thái của một phản hồi.

Các trang tài khoản (US-078) xem ở mục 3.

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

Phía Staff web, phản hồi từ Customer web có `source = 'public'` (không tài khoản, `user_id = NULL`) hoặc `source = 'customer'` (tài khoản khách hàng). Cả hai hiện badge **"Khách hàng"** trong danh sách feedback.

---

## 3. Tài khoản khách hàng (`guest`)

Khách hàng tự tạo tài khoản trên Customer web; admin không tạo loại tài khoản này.

Các trang:

- `/dang-ky`: email, mật khẩu (cùng 5 tiêu chí như Staff web), họ tên.
- `/dang-nhap`: email + mật khẩu, hoặc Google, Facebook (OAuth, quay về `${origin}/`).
- `/quen-mat-khau`: gửi email đặt lại mật khẩu, link dẫn về `/dat-lai-mat-khau`.
- `/dat-lai-mat-khau`: đặt mật khẩu mới sau khi mở link.
- `/cua-toi`: lịch sử phản hồi của chính mình, mới nhất trước; mỗi dòng có trạng thái, ngày gửi, nội dung và link tới `/status/:code`. Không bao giờ hiện nhãn AI.
- Nút chat nổi: chỉ hiện khi đã đăng nhập; chưa đăng nhập thì nhắc đăng nhập.

Trigger `handle_new_user` gán `guest` cho mọi tài khoản mới, trừ profile đầu tiên của hệ thống thành `admin`. Tài khoản do admin tạo (`POST /api/admin/users`) được backend gán role Staff ngay sau trigger, nên không bị ảnh hưởng.

Backend: router riêng `/api/customer` (`pipeline/customer_api.py`), chỉ nhận role `guest`; role khác nhận 403.

- `POST /api/customer/feedback`: cùng đường xử lý với phản hồi ẩn danh (làm sạch và che PII, phân loại, rule, severity, honeypot, giới hạn độ dài), nhưng `user_id` là tài khoản khách hàng và `source = 'customer'`. Vẫn có mã tra cứu. Rate limit theo user id. Màn thành công vẫn chỉ hiện mã tra cứu.
- `GET /api/customer/feedback`: phản hồi của chính mình, chỉ gồm `public_ref`, `status`, `created_at`, `text`. Không có topic, sentiment, severity. Đây là đường đọc lịch sử duy nhất.
- `POST /api/customer/chat`: trợ lý chat cho khách, chỉ dùng knowledge base công khai, rate limit theo user id. Khi trợ lý ghi nhận phản hồi, phản hồi đi qua đúng bộ phân loại như `POST /api/customer/feedback` (không còn tự gán nhãn hay P3 cố định như tầng guest cũ).

Phản hồi của tài khoản khách hàng không có `retention_until` (decision 0018 §9): job 180 ngày không xoá nội dung, mã tra cứu không hết hạn. Nội dung còn cho tới khi tài khoản bị xoá (xoá theo cascade).

Tài khoản khách hàng **không** được gì ở phía nội bộ:

- **Staff web**: đăng nhập xong chỉ thấy màn "Đây là tài khoản khách hàng", có link sang Customer web và nút đăng xuất. Không có thanh điều hướng, không tải dữ liệu.
- **Backend**: 403 ở mọi route Staff (`require_ops_staff`, `require_admin`, `require_manager`). `GET /api/me` vẫn trả role `guest`.
- **Database (RLS)**: `is_ops_staff()` không gồm `guest`. Không đọc trực tiếp được dòng `feedback` / `alerts` nào, kể cả dòng của mình (SELECT chỉ cho ops staff từ migration `20260928000000` mục 3); lịch sử chỉ qua `GET /api/customer/feedback`. Không `INSERT` trực tiếp vào `feedback`; không đọc `graph_nodes` / `graph_edges`.

Ngược lại, tài khoản Staff hoặc `pending` đăng nhập trên Customer web chỉ thấy thông báo "Tài khoản nhân viên dùng Staff web" và Customer web không gọi API khách hàng nào.

---

## 4. Tài khoản chờ cấp quyền (`pending`)

Một tài khoản ở trạng thái `pending` khi:

- là tài khoản `guest` cũ trước US-077: migration của US-077 đổi toàn bộ `guest` thành `pending`, không xoá tài khoản hay feedback nào. US-078 không đổi lại, hai tài khoản này vẫn là `pending`;
- bị admin hạ quyền xuống `pending`;
- có role bị thiếu hoặc không hợp lệ: mọi chỗ fail-closed (`auth_guard.py`, route guard, MCP) đều rơi về `pending`. DEFAULT của cột `profiles.role` vẫn là `pending`.

Tự đăng ký (trên Customer web hay thẳng qua Supabase Auth) và tạo user trong Supabase Dashboard không còn ra `pending`: trigger gán `guest`.

Tài khoản `pending` được gì:

- **Staff web**: sau khi đăng nhập chỉ thấy màn "Tài khoản đang chờ admin cấp quyền" với nút đăng xuất. Không có thanh điều hướng, không tải dữ liệu.
- **Backend**: 403 ở mọi endpoint, trừ `GET /api/me`, `POST /api/me/password` và `/health`.
- **Chat**: `POST /api/agent/chat` trả 403. Tầng chat công khai dùng cho ops staff (cờ `public_only`, widget trang chủ) và cho tài khoản khách hàng qua `POST /api/customer/chat`; `pending` không vào được cả hai.
- **MCP**: qua HTTP, `SupabaseTokenVerifier` từ chối identity `pending` hoặc role lạ (cả JWT lẫn bearer `mcp_tokens`) bằng 401: không có phiên, không có danh sách tool. Bản stdio với `MCP_ROLE` rỗng hoặc `pending` không có tool nào.
- **Database (RLS)**: `is_ops_staff()` loại `pending`. Không đọc được dòng `feedback` / `alerts` nào, kể cả dòng của mình (migration `20260928000000` mục 3). Chỉ ops staff mới `INSERT` được vào `feedback`, và phải đúng `user_id` của mình. Không ai tự `INSERT`/`DELETE` được dòng `profiles`. Knowledge base nội bộ (`graph_nodes`, `graph_edges`) chỉ ops staff đọc được.

Admin cấp quyền ở trang Quản lý người dùng: tab "Chờ cấp quyền" liệt kê tài khoản `pending` (không gồm tài khoản khách hàng) với nút "Cấp quyền Nhân viên" / "Cấp quyền Quản lý" (`PATCH /api/users/{id}/role`); backend còn có `POST /api/users/bulk-approve` để duyệt hàng loạt thành staff/manager.

Tài khoản khách hàng không nằm ở tab nào; nó chỉ hiện khi tìm kiếm, ở dạng **chỉ đọc**: nhãn "Khách hàng", không đổi được role hay phòng ban, chỉ xoá được. Bảng "Nhân viên đang hoạt động" ở dashboard chỉ liệt kê admin, manager và staff.

> ⚠️ Nút "Từ chối và xoá tài khoản" gọi xoá tài khoản (`auth.admin.delete_user`). Mọi FK tới `auth.users` là `ON DELETE CASCADE`, nên feedback, alert, lịch sử chat và MCP token của người đó bị xoá theo. Đã ghi vào backlog, chưa sửa.

---

## 5. Tạo tài khoản Staff

Chỉ admin tạo tài khoản Staff. Staff web không có form đăng ký, cũng không có nút đăng nhập Google/Facebook. Đăng ký tự do chỉ có trên Customer web và chỉ ra tài khoản khách hàng (mục 3).

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

**Authentication → Users → Add user**. Tài khoản tạo kiểu này đi qua trigger nên vào hệ thống với role `guest` (trừ khi đây là profile đầu tiên, sẽ thành `admin`). Chỉ dùng cách này để chủ dự án tạo admin khi chưa vào được Staff web (setup-supabase mục 8.4): tạo tài khoản mới cho đúng người đó rồi sửa `role` trong **Table Editor → profiles**. Không có bước bắt đổi mật khẩu.

**Không nâng tài khoản khách hàng tự đăng ký lên Staff**, kể cả qua Table Editor: danh tính do người đăng ký tự khai. Người cần quyền Staff được admin tạo tài khoản mới bằng Cách 1.

### Đăng ký trên Supabase

Từ US-078, đăng ký và các provider Email, Google, Facebook **giữ bật** vì Customer web cần. Xem [setup-supabase.md](setup-supabase.md) mục 8.1 và 8.3 (redirect URL của Customer web).

---

## 6. Kiểm thử nhanh (chỉ trên stack local)

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

# Tài khoản khách hàng: lịch sử của mình → 200; route Staff → 403
curl -s -H "Authorization: Bearer $TOKEN_GUEST" http://127.0.0.1:8000/api/customer/feedback
curl -s -H "Authorization: Bearer $TOKEN_GUEST" http://127.0.0.1:8000/api/feedback/recent
# → 403 Forbidden
```

Danh sách kiểm thử đầy đủ: `docs/harness/stories/epics/E04-public-intake/US-077-separate-customer-web/validation.md` và `docs/harness/stories/epics/E04-public-intake/US-078-customer-accounts/validation.md`.
