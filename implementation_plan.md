# Kế hoạch Tối ưu Backend & Tích hợp RAG

Kế hoạch này vạch ra lộ trình nâng cấp toàn diện Backend FastAPI và các AI Agent của dự án XanhSM, sử dụng triệt để bộ 5 Kỹ năng (Skills) tiêu chuẩn cao.

## Lộ trình Triển khai

### Giai đoạn 1: Chuẩn hóa Kiến trúc API & Xử lý Lỗi
Sử dụng: `@skills/api-and-interface-design` & `@skills/debugging-and-error-recovery`

* **Mục tiêu:** Đảm bảo Backend hoạt động ổn định, dễ mở rộng và không bao giờ nuốt lỗi.
* **Hành động:**
  - Rà soát toàn bộ `pipeline/main.py` để áp dụng nguyên tắc **Validate at Boundaries**: Mọi request đầu vào phải được định nghĩa bằng Pydantic Models.
  - Chuẩn hóa định dạng HTTP Error. Thay vì trả về string lộn xộn, mọi Exception (đặc biệt khi gọi Supabase hoặc LLM) sẽ trả về chung một cấu trúc JSON: `{ "error": { "code": "...", "message": "..." } }`.
  - Phân trang (Pagination) triệt để cho các API trả về list (như `/api/reports`).

### Giai đoạn 2: Tăng cường Bảo mật (Đặc biệt cho AI)
Sử dụng: `@skills/security-and-hardening`

* **Mục tiêu:** Bảo vệ dữ liệu người dùng và ngăn chặn tấn công vào các LLM Agent.
* **Hành động:**
  - **OWASP LLM:** Cài đặt bộ lọc (Validation) cho đầu ra và đầu vào của Agent. Không bao giờ đưa thẳng dữ liệu PII vào Prompt.
  - Xử lý Rate Limiting cho `/api/agent/chat` (để tránh bị abuse API key OpenAI/Llama).
  - Áp dụng các Best-practice quản lý biến môi trường trong `.env`.

### Giai đoạn 3: Tối ưu Giám sát Hệ thống (Observability)
Sử dụng: `@skills/observability-and-instrumentation`

* **Mục tiêu:** Theo dõi độ trễ, lỗi và hiệu năng của AI theo thời gian thực.
* **Hành động:**
  - Tích hợp **Structured Logging (JSON format)** cho ứng dụng FastAPI (kèm `request_id` cho mỗi API call) thay cho `print` thông thường.
  - Ghi nhận chỉ số RED (Rate, Errors, Duration) khi Agent xử lý công việc: Đếm thời gian trễ của LLM, tỷ lệ gọi tools thất bại.
  - Cải tiến tính năng Webhook hiện tại: Đính kèm Log context chính xác thay vì chỉ gửi cảnh báo chung chung.

### Giai đoạn 4: Thiết kế Unified RAG với Context Engineering
Sử dụng: `@skills/context-engineering`

* **Mục tiêu:** Hoàn thiện tính năng RAG kết hợp (Semantic Search + Knowledge Base) đã chốt trước đó, với chất lượng cao nhất.
* **Hành động:**
  - Áp dụng các nguyên tắc cấu trúc Context: Không nhồi quá nhiều tài liệu rác vào Agent. Chỉ truy xuất top 3 chunks (Đoạn tài liệu) liên quan nhất từ Supabase `pgvector`.
  - Áp dụng "The Inline Planning Pattern" cho ReAct Agent: Buộc Agent phải xuất ra một kế hoạch ngắn gọn trước khi gọi Database Tools để tránh Hallucination.
  - Xây dựng file `rag_engine.py` chuẩn chỉnh, có khả năng bóc tách, nhúng (embed) và truy vấn Vector.

---

## User Review Required

> [!IMPORTANT]
> **Yêu cầu đánh giá**
> Kế hoạch này sẽ tái cấu trúc một số phần trong Backend `pipeline/main.py` để đạt chuẩn chất lượng cao. Bạn có muốn chia nhỏ Kế hoạch này ra thi công dần (bắt đầu từ **Giai đoạn 1**), hay bạn muốn nhảy thẳng vào **Giai đoạn 4 (Unified RAG)** trước?
