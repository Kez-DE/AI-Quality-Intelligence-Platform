# JOURNAL — C2-App-116

Nhật ký học tập & hành trình sản phẩm của team 116.

## Tuần 1 (12/06/2026)

### Đã làm
- Chốt đề tài **AI Quality Intelligence Platform** (Quality Operation Cockpit):
  phân tích phản hồi khách hàng smart mobility, phát hiện spike sự cố theo khu
  vực, agent LLM định tuyến ticket cho phòng ban.
- Di trú dự án nguồn `xanh_iu` (build sẵn ~90% qua Lovable) vào repo team theo
  layout chuẩn: `app/` (frontend) + `pipeline/` (Python) + `supabase/` + `data/`
  + `docs/`.
- Nối classifier với model ML thật (TF-IDF + LinearSVC), sửa 3 bug (mock
  classifier, đảo ngược severity, sai đường dẫn sau khi làm phẳng pipeline).
- Thêm dữ liệu canonical kèm tài liệu provenance, đặt backend về chế độ batch.

### Khó nhất
Hiểu đúng trạng thái thực tế của repo. Ban đầu tưởng repo team trống, nhưng hóa
ra backend+UI đã được commit lên `main` ở layout cũ (`UI/` + `backend/pipeline/`).
Phải đọc kỹ git history + so từng nguồn (xanh_iu, dataset crawl, blueprint) trước
khi quyết, tránh build trùng hoặc build mù. Bug khó phát hiện nhất là **đảo ngược
severity**: code lọc P0/P1 trong khi thang dự án P5 mới là nặng nhất — spike
detector đang âm thầm bỏ sót đúng các ca Safety nghiêm trọng.

### AI tool đã dùng
| Tool | Dùng để làm gì |
| :--- | :--- |
| Fu (Hermes) | Khảo sát codebase, restructure, sửa bug pipeline, verify chạy thật, viết docs |

### Học được
- "Một repo một nguồn sự thật": gom frontend + pipeline + schema + data + docs vào
  một cấu trúc phẳng giúp truy vết và bàn giao dễ hơn nhiều.
- `git mv` giữ được lịch sử file (tracked thành rename) — không mất blame khi tái
  cấu trúc lớn.
- LinearSVC không có `predict_proba`; phải ước lượng confidence từ
  `decision_function` margin.
- Pin version thư viện ML khớp lúc train (`scikit-learn==1.6.1`) để tránh
  InconsistentVersionWarning và rủi ro kết quả sai.

### Làm lại sẽ khác
Kiểm tra trạng thái cả `main` và các branch ngay từ đầu (không chỉ branch đang
đứng) trước khi giả định repo trống — sẽ tiết kiệm một vòng khảo sát.

### Kế hoạch tuần sau
- Áp migration schema lên Supabase Cloud, chạy ingest end-to-end với user thật.
- Kiểm frontend build được + kết nối Supabase, chạy thử luồng demo "bấm nút 150
  review → dashboard đỏ → agent sinh ticket".
- Thêm auth/role (Admin/Manager/Staff/Guest) + deploy frontend (Vercel) và
  backend (Railway/Render) theo yêu cầu BTC.
