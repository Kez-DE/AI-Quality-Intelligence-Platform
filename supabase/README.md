# Hướng dẫn thiết lập Supabase Local & Đồng bộ DB (Dành cho Team)

Dự án sử dụng Supabase local. Bạn cần cài đặt **Docker Desktop** (và bật WSL nếu dùng Windows).

**Khởi động Supabase:**
1. Cài đặt Supabase CLI: `npm install -g supabase`
2. Chạy lệnh: `supabase start`
   - *Lưu ý (Lỗi 403 jsr.io ở Việt Nam):* Nếu quá trình tải bị lỗi `403 Forbidden` do `jsr.io` chặn IP, hãy yên tâm vì file `supabase/config.toml` hiện đã được cấu hình tắt `edge_runtime` (`enabled = false`) để tránh lỗi này. (Nếu bắt buộc dùng Edge Functions sau này, hãy bật VPN như 1.1.1.1 và bật lại thành `true`).

**Đẩy (Push) dữ liệu lên Remote Project (nếu cần thiết):**
1. Đăng nhập tài khoản: `supabase login`
2. Liên kết thư mục: `supabase link --project-ref <mã-project-id>` (Cần nhập mật khẩu DB của project).
3. Đẩy thiết kế bảng lên: `supabase db push`

Sau khi chạy xong `supabase start`, hãy copy các link API, `anon key` và `service_role key` in ra màn hình để điền vào file `.env` ở thư mục gốc (tham khảo `.env.example`).
