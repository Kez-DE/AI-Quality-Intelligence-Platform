# Kế hoạch Kiểm thử & Rà soát Toàn diện (Audit Plan)

Theo yêu cầu rà soát và kiểm thử lại toàn bộ các luồng Frontend và Backend, tôi đã tiến hành khảo sát và nhận thấy hiện tại dự án chưa được cấu hình các bộ test tự động (`npm test` ở frontend không tồn tại, và `pytest` ở backend chưa được cài đặt). Dựa vào bộ kỹ năng **Test-Driven Development (TDD)** và **Frontend UI Engineering**, tôi đề xuất kế hoạch sau:

## 1. Mục tiêu (Goals)
- Đảm bảo 100% các API cốt lõi của Backend hoạt động không có lỗi (đặc biệt là logic AI, xử lý phản hồi, tạo ticket).
- Đảm bảo Frontend render mượt mà, gọi API thành công và xử lý tốt các trường hợp lỗi mạng hoặc dữ liệu trống.
- Tạo nền tảng kiểm thử (Test framework) vững chắc để team có thể tái sử dụng lâu dài.

## 2. Kế hoạch triển khai (Proposed Changes)

### Giai đoạn 1: Backend Testing (TDD & API Boundaries)
- **Công cụ:** Cài đặt `pytest`, `pytest-asyncio`, và `httpx` (để test FastAPI). Thêm vào `pipeline/requirements-test.txt`.
- **Viết Integration Tests:** Tạo thư mục `pipeline/tests/` và viết các test script để gọi trực tiếp vào các endpoint quan trọng:
  - `GET /health` (System Health)
  - `POST /api/feedback/submit` (Luồng nhận phản hồi & phân tích AI)
  - `POST /api/agent/chat` (Luồng AI Assistant)
  - `GET /api/tasks` & `GET /api/alerts/recent`
- **Xử lý Mock:** Viết mock cho các lệnh gọi ra bên ngoài (như Supabase hoặc API LLM) trong môi trường test để đảm bảo test chạy nhanh và ổn định mà không tốn API credit, tuân thủ đúng nguyên tắc Test Pyramid.
- **Rà soát log:** Chạy test và rà soát lỗi (exception) trong console. Nếu phát hiện lỗi (ví dụ thiếu biến môi trường, crash do data, lỗi logic), sẽ tự động sửa lỗi theo chuẩn Backend.

### Giai đoạn 2: Frontend Testing & UI Audit
- **Công cụ:** Cài đặt `vitest`, `jsdom`, và `@testing-library/react` vào thư mục `app/`.
- **Viết Component Tests (Smoke Tests):**
  - Đảm bảo các component quan trọng (`QualityCockpit`, `AppShell`, `FeedbackPage`) render thành công mà không bị crash.
  - Test các logic xử lý trạng thái (loading state, empty state).
- **Manual UI Audit:** 
  - Khởi động server Frontend (chế độ dev) và duyệt qua các trang (Dashboard, Alerts, Tasks, Feedback, Chat).
  - Áp dụng skill `frontend-ui-engineering`: Rà soát xem có phần nào bị vỡ layout, thiếu padding/margin, hoặc không có hiệu ứng hover/active không. Sửa ngay tại chỗ.
  - Bắt các lỗi hiển thị (vd: text tràn viền, loading indicator bị treo, lỗi React keys).

## 3. Câu hỏi và Đánh giá (Open Questions)

> [!IMPORTANT]
> - Hiện tại dự án chưa có test framework. Việc cài đặt thêm `pytest` (cho backend) và `vitest` (cho frontend) sẽ thêm một số cấu hình vào thư mục của bạn. Việc thiết lập test suite chuyên nghiệp là cực kỳ quan trọng cho TDD. Bạn có đồng ý với việc này không?
> - Trong quá trình test Backend, đối với các API gọi tới Supabase, bạn muốn thiết lập một DB Supabase cục bộ (Local Supabase) dùng cho test, hay chỉ đơn giản là Mock (giả lập) các kết quả trả về từ database để tiết kiệm thời gian?

Xin vui lòng phê duyệt kế hoạch này để tôi bắt đầu cài đặt môi trường test và tiến hành rà soát sửa lỗi toàn bộ!
