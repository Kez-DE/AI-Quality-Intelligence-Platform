# Giải thích hệ thống: từ một review đến lúc phòng ban xử lý xong

> **Cập nhật 2026-06-27:** đồng bộ 6 phòng ban, RAG hybrid, roster agent với code hoàn thiện.
>
> **Cập nhật 2026-09-27 (US-077 / decision 0017):** tách Customer web khỏi Staff web, bỏ role `guest` thay bằng `pending`, chỉ admin tạo tài khoản.
>
> **Cập nhật 2026-09-28 (US-078 / decision 0018):** `guest` quay lại làm tài khoản khách hàng (tuỳ chọn, chỉ dùng Customer web); tự đăng ký và tài khoản tạo trong Supabase Dashboard vào với `guest`.

Tài liệu này mô tả toàn bộ cách hệ thống vận hành: một phản hồi của khách đi vào, được phân loại, định tuyến về phòng ban, rồi xử lý ra sao. Phần sau giải thích các loại tài khoản, các bộ máy chạy nền, các lớp AI, và đi qua từng màn hình của ứng dụng kèm các nút bấm chính.

Hệ thống tên là AI Quality Intelligence Platform (Quality Operation Cockpit của xanhSM). Bài toán nó giải: mỗi ngày có hàng nghìn phản hồi khách hàng về dịch vụ gọi xe, con người không đọc xuể. Hệ thống đọc thay, gán nhãn, phát hiện cụm vấn đề bất thường, sinh cảnh báo và ticket theo SLA, rồi giao đúng phòng ban để xử lý trước khi sự cố lan rộng.

Mã nguồn chia ba tầng trong một repo: frontend gồm hai web riêng là `app/` (Staff web, cho nhân viên) và `customer-web/` (Customer web, khách gửi phản hồi không cần tài khoản), `pipeline/` (backend Python FastAPI + các worker), `supabase/` (PostgreSQL + RBAC). Supabase là trục nối: pipeline ghi kết quả vào đó, frontend đọc ra để hiển thị realtime.

---

## 1. Bức tranh lớn: một review đi từ đầu đến cuối

Lấy ví dụ một câu phản hồi: "Tài xế đi ẩu, suýt tông người, thái độ còn khó chịu". Đây là đường đi của nó.

```
Review vào (Customer web / form / CSV / dataset / streaming)
   │
   ▼
[1] clean.py        che PII (số điện thoại, email, biển số), chuẩn hóa text
   │
   ▼
[2] classifier.py   model TF-IDF + LinearSVC đoán topic + sentiment   (tầng MODEL)
   │
   ▼
[3] rules.py        rule keyword ghi đè khi tín hiệu rõ                 (tầng RULE)
   │                 lưới Safety ép Safety / negative / P5 / cần duyệt
   ▼
[4] ingest.py       ghi vào bảng feedback (topic, sentiment, severity P1..P5,
   │                 confidence, area, needs_review, review_reason)
   ▼
[5] spike_detector  gom theo (khu vực, chủ đề, phòng); áp ngưỡng risk/volume → spike
   │
   ▼
[6] router_agent    định tuyến spike về phòng ban + SLA + priority
   │   llm_agent     LLM viết title / nguyên nhân gốc / hành động đề xuất
   ▼
[7] alerts          ghi ticket vào Supabase → frontend hiển thị realtime
   │
   ▼
   task_agent gom ticket trùng thành Task → phòng ban nhận, xử lý, đóng
   │
   ▼
   insight_agent + analyst_agent tổng hợp số liệu + báo cáo theo phòng
```

Vài điểm cần hiểu rõ ở luồng này.

Phân loại đi qua hai tầng. Model học từ dữ liệu đoán nền topic và cảm xúc. Sau đó rule engine chạy theo, ghi đè khi gặp từ khóa rõ ràng. Lý do tách hai tầng: model yếu ở câu ngắn (người dùng gõ form thường viết ngắn, ít token, model hay ngả về lớp tiêu cực đa số), nên rule lấp đúng lỗ hổng đó.

Lưới Safety luôn thắng. Bất kỳ review nào chứa từ khóa nguy hiểm (tai nạn, xe tông, bỏ chạy, say xỉn, cướp, hành hung, sàm sỡ) đều bị ép thành Safety, negative, P5, cần duyệt. An toàn không nhường cho xác suất.

Định tuyến phòng ban theo bảng `data/taxonomy/routing_table.json`:

| Chủ đề | Phòng ban | SLA | Priority mặc định |
|--------|-----------|-----|-------------------|
| Safety | Vận hành | 1 giờ | P5 |
| Driver Behavior | Vận hành | 8 giờ | P3 |
| App Issue | IT | 12 giờ | P3 |
| Payment | Tài chính & Thanh toán | 12 giờ | P3 |
| Pricing | Quản lý Rủi ro & Gian lận | 12 giờ | P3 |
| Delay | Vận hành | 8 giờ | P3 |
| Other | CSKH | 24 giờ | P4 |

Hai luật ghi đè quan trọng. Mọi ticket P5 bị ép về Vận hành (đội phản ứng nhanh) bất kể chủ đề. Phản hồi tích cực chung hoặc góp ý tính năng (positive + Other/App Issue) chuyển về Sản phẩm để khai thác nâng cấp UX/UI; còn positive gắn chủ đề chuyên môn khác (thanh toán, tài xế, giá cước...) vẫn về đúng phòng theo topic.

Router quyết định phòng ban. LLM không được tự gán phòng, nó chỉ viết tiêu đề, mô tả nguyên nhân và hành động đề xuất.

---

## 2. Các tài khoản và vai trò

Hệ thống có hai trục phân quyền tách biệt: role (cấp độ quyền) và department (phòng ban, quyết định thấy dữ liệu của ai).

Bốn role:

| Role | Nhãn UI | Làm được gì |
|------|---------|-------------|
| `admin` | Quản trị viên | Toàn quyền: quản lý user, bật/tắt streaming, trigger pipeline, xem mọi phòng |
| `manager` | Quản lý | Giám sát phòng mình: alerts, tasks, insights, reports, chat |
| `staff` | Nhân viên | Việc hàng ngày của phòng mình: feedback, tasks, support, chat |
| `pending` | Chờ cấp quyền | Chưa làm được gì: chỉ thấy màn chờ admin cấp quyền |

Sáu phòng ban: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận. Một tài khoản vận hành (admin/manager/staff) có thể chưa được gán phòng. Khi đó họ chưa xem được dữ liệu phòng nào cho tới khi admin gán.

Cách hệ thống chặn xem chéo phòng: backend chạy bằng service role key của Supabase nên bỏ qua RLS của Postgres. Vì vậy mọi kiểm tra quyền nằm ở tầng API trong `pipeline/auth_guard.py`. Có hai helper:

- `scoped_team` dùng cho endpoint danh sách: admin thấy tất cả, ops bị ép lọc về đúng phòng mình, ops chưa gán phòng bị chặn 403.
- `can_view_team` dùng cho thao tác trên một record: chặn ghi/đọc chéo phòng.

Khách hàng (người ngoài công ty) không cần tài khoản. Họ gửi phản hồi trên Customer web và tra cứu bằng mã tra cứu (xem mục Customer web ở phần 5). Nếu muốn, họ tự đăng ký tài khoản khách hàng (role `guest`) để xem lịch sử phản hồi và dùng trợ lý chat; tài khoản này không vào được Staff web.

Tạo tài khoản: chỉ admin tạo, bằng form "Tạo tài khoản" trong trang Quản lý người dùng; Staff web không còn form tự đăng ký. Bootstrap: profile đầu tiên của hệ thống thành admin. Tài khoản tự đăng ký và tài khoản tạo ngoài form của admin (ví dụ trong Supabase Dashboard) vào với `guest` (tài khoản khách hàng), không được nâng lên Staff. Hai tài khoản `guest` cũ trước US-077 vẫn là `pending`, chờ admin duyệt lên staff hoặc manager.

Chat cũng phân quyền theo phòng và chỉ dành cho ops (tài khoản `pending` bị chặn 403). Khi widget trang chủ gửi cờ `public_only`, trợ lý chạy tầng công khai với prompt riêng, chỉ trả lời về cách dùng app, đặt xe, thanh toán, khuyến mãi, khiếu nại, và không bao giờ chạm dữ liệu nội bộ. Ops dùng prompt nội bộ kèm RAG, và mọi truy vấn bị ép lọc về phòng của họ (admin xem toàn hệ thống). Cả hai luồng đều che PII ở cả đầu vào lẫn đầu ra.

---

## 3. Các bộ máy chạy nền

Backend không phải một tiến trình. Nó là một web API cộng bốn worker, mỗi cái lo một việc theo nhịp riêng để không giẫm chân nhau.

| Service | Chạy gì | Nhịp | Tốn LLM |
|---------|---------|------|---------|
| `backend` (web API) | Nhận request, chat, scheduler theo lệnh | theo request | có (chat) |
| `ingest-worker` | Bơm dataset theo batch, tự phát hiện spike | 10 giây/batch | gián tiếp |
| `ml-worker` | Quét feedback tiêu cực chưa chấm rủi ro, chấm 5 chiều bằng LLM | 30 đến 60 giây | có |
| `agent-worker` | Chạy full multi-agent pipeline | 300 giây | có |
| `backend-worker` | Đẩy vòng đời ticket open → in_progress → resolved; 03:00 hằng ngày xoá nội dung phản hồi ẩn danh quá hạn lưu trữ | 5 giây + cron 03:00 | không (rule) |

Chỉ `agent-worker` và `ml-worker` tốn tiền gọi LLM, và cả hai đều có cờ tắt hoặc fallback mock.

Có hai chế độ đưa dữ liệu vào hệ thống.

Streaming là luồng chính, gần realtime. Admin bật stream, scheduler bơm dataset theo từng lô. Cứ vài lô lại tự chạy spike detection để sinh ticket. Frontend subscribe Supabase realtime nên dashboard tự cập nhật mà không cần refresh.

Batch thủ công là các nút bấm an toàn cho lúc demo. Admin bắn một lô review và sinh alert ngay, không phụ thuộc nhịp scheduler hay mạng.

Mọi lệnh gọi LLM đi qua một cổng duy nhất là `pipeline/agent/model_router.py`. Cổng này có failover: thử lần lượt các provider có key (OpenRouter, OpenAI, Gemini, Groq), provider nào lỗi thì nhảy sang cái kế, hết key thật thì dùng mock để demo không bao giờ vỡ. Đổi provider hay model chỉ cần sửa biến môi trường, không sửa code.

---

## 4. Các lớp AI và multi-agent

Hệ thống có bốn lớp AI chạy trên dataset feedback.

Lớp A là chat LLM thời gian thực, phục vụ giao diện chat. Lớp B là multi-agent pipeline chạy batch. Lớp C là model machine learning (TF-IDF + LinearSVC, train offline) lo phân loại topic và sentiment. Lớp D là các thành phần rule (lưới Safety, spike detector, vòng đời ticket).

Multi-agent pipeline gồm các agent nghiệp vụ, điều phối bởi `orchestrator.run_agent_pipeline()` chạy trong `agent-worker`. Vai trò từng agent:

| Agent | Loại | Việc |
|-------|------|------|
| `ingestion_agent` | ML + rule | Che PII, chuẩn hóa khu vực, phân loại, ghi bảng feedback |
| `scoring_agent` | LLM + rule | Chấm 5 chiều rủi ro (safety, fraud, attitude, vehicle, compliance) rồi gộp ra điểm 1 đến 5 |
| `alert_agent` | Rule | Phân cấp WATCH/WARNING/CRITICAL, chống tạo alert trùng |
| `router_agent` | Rule | Định tuyến ticket về phòng ban theo bảng routing, P5 ép về Vận hành |
| `ticket_agent` | DB | Tạo và cập nhật ticket, quét ticket quá hạn SLA |
| `task_agent` | Rule + LLM | Gom các alert cùng (phòng, khu vực) thành một task, LLM đặt tên |
| `insight_agent` | Rule | Tổng hợp số liệu và chủ đề theo phòng |
| `analyst_agent` | LLM | Phân tích nguyên nhân gốc và đề xuất hành động, có giọng riêng theo phòng |

Hai agent đầu chạy độc lập ngoài orchestrator: `ingestion_agent` ở luồng ingest, `scoring_agent` ở `ml-worker`.

Model machine learning đạt khoảng 77% chính xác trên topic và 94% trên sentiment (test 932 mẫu). Phần còn yếu là câu ngắn, và rule engine bù vào đó.

---

## 5. Đi qua từng màn hình

Phần này mô tả các màn hình theo góc nhìn người dùng: ai thấy gì, các nút chính làm gì, bấm vào thì gọi API nào.

Thanh điều hướng bên trái lọc theo role. Tài khoản `pending` không có thanh điều hướng, chỉ thấy màn "Tài khoản đang chờ admin cấp quyền" với nút đăng xuất. Staff và manager thấy thêm Ticket Triage, Task Manager, CSKH Support, Phân tích phòng ban, AI Chat, Giới thiệu. Manager và admin thấy thêm Báo cáo AI. Admin thấy thêm Live Stream và Quản lý người dùng. Góc trên phải có badge phòng ban, chuông thông báo realtime, nút đổi sáng/tối, và nút đăng xuất.

### Đăng nhập

Màn `/auth` chỉ còn đăng nhập bằng email và mật khẩu, có nút con mắt để hiện hoặc ẩn mật khẩu. Không còn form đăng ký, cũng không còn nút đăng nhập Google/Facebook. Báo lỗi được dịch sang tiếng Việt rõ ràng (sai mật khẩu, email chưa xác nhận).

Tài khoản do admin tạo có mật khẩu tạm. Lần đăng nhập đầu, Staff web chỉ hiện màn đổi mật khẩu: nhập mật khẩu mới hai lần, đạt 5 tiêu chí (ít nhất 8 ký tự, chữ hoa, chữ thường, chữ số, ký tự đặc biệt). Màn này gửi mật khẩu mới tới `POST /api/me/password`; backend đặt mật khẩu và xoá cờ `must_change_password` trong `app_metadata`. Đổi xong mới vào được các màn khác. Việc chặn không chỉ nằm ở giao diện: chừng nào cờ còn bật, backend trả 403, MCP trả 401 và RLS không cho quyền ops.

### Dashboard

Màn `/dashboard` là cockpit tổng quan, đọc realtime. Trên cùng là dải KPI. Bên dưới chia hai cột: luồng feedback trực tiếp, biểu đồ xu hướng, phân tích theo nhóm chủ đề bên trái; bảng alert, bản đồ nhiệt theo khu vực, bảng xếp hạng phòng ban, danh sách tài xế cần theo dõi bên phải. Dưới cùng là bảng ticket và phần phân tích nâng cao.

Bấm vào một nhóm chủ đề hoặc một khu vực trên bản đồ nhiệt sẽ mở drawer chi tiết, liệt kê các feedback thuộc nhóm hoặc khu vực đó.

Ops chưa gán phòng thấy thông báo nhắc liên hệ admin.

### Phản hồi (Feedback)

Màn `/feedback` là nơi gửi và duyệt phản hồi. Trên cùng là form gửi phản hồi mới: ô nội dung, chọn kênh, chọn khu vực (dropdown thay vì gõ tay để dữ liệu nhất quán). Bấm "Lưu phản hồi" gọi `POST /api/feedback/submit`, AI tự phân loại sau khi gửi.

Với tài khoản vận hành, bên dưới có bốn thẻ thống kê bấm được để lọc nhanh: Tổng phản hồi, Cần duyệt, P4/P5, Confidence thấp. Bấm vào thẻ nào thì danh sách lọc theo thẻ đó.

Phần chính chia hai cột. Cột trái là luồng phản hồi chung, có nút refresh. Cột phải là hàng đợi cần duyệt, lấy đúng các ca P5, safety, hoặc confidence thấp từ `GET /api/feedback/recent?needs_review=true&reviewed=false`, kèm badge giải thích lý do cần duyệt.

Mỗi dòng phản hồi hiện nhãn AI gán (chủ đề, cảm xúc, mức độ, phần trăm confidence, khu vực). Phản hồi khách hàng gửi từ Customer web (`source = 'public'`) có thêm badge "Khách hàng". Hai nút thao tác:

- "Sửa nhãn" mở ô chỉnh ba nhãn (chủ đề, cảm xúc, mức độ). Bấm "Lưu nhãn" gọi `PATCH /api/feedback/{id}/label`, ghi lại vào correction log (ai sửa, sửa field gì, từ cũ sang mới), đặt confidence về 1.0 và đánh dấu đã duyệt. Đây vừa là audit, vừa là dữ liệu để retrain sau này.
- "Duyệt" (chỉ ở hàng đợi cần duyệt) gọi `PATCH /api/feedback/{id}/review`, chuyển phản hồi ra khỏi hàng đợi.

### Nạp dữ liệu (Feedback Upload)

Màn `/feedback/upload` có hai tab. Tab nhập trực tiếp có ô text và phần xem trước sau khi che PII: số điện thoại, email, biển số xe bị thay bằng nhãn ẩn ngay trên trình duyệt trước khi gửi. Tab tải CSV cho phép kéo thả hoặc chọn file (tối đa 5MB, định dạng cột text, channel, area), xem trước bảng đã che PII, rồi bấm "Bắt đầu Nạp" để gửi từng dòng kèm thanh tiến độ vòng tròn. Có nút dừng giữa chừng.

### Ticket Triage (Alerts)

Màn `/alerts` hiển thị các cảnh báo AI sinh ra, cập nhật realtime qua Supabase và poll mỗi 2 giây. Trên cùng là ba ô đếm theo trạng thái: chờ xử lý, đang xử lý, đã xong. Dưới đó là dải trạng thái live stream và auto-ticket, cho biết stream có đang chạy không, đã chạy bao nhiêu batch, lần sinh ticket gần nhất.

Bộ lọc gồm tab phòng ban (admin chọn được mọi phòng, ops khác bị ghim vào phòng mình), dropdown lọc trạng thái, dropdown lọc độ ưu tiên.

Mỗi thẻ alert hiện badge mức độ, badge phòng ban kèm icon, priority, chủ đề, khu vực, thời gian. Hai khối giải thích: nguyên nhân gốc do AI phân tích, và hành động đề xuất. Có thêm khối lý do định tuyến khi cần. Nút thao tác đổi theo trạng thái:

- Alert đang "chờ xử lý": nút "Nhận xử lý" gọi `PATCH /api/alerts/{id}/status` chuyển sang in_progress.
- Alert "đang xử lý": nút "Đã giải quyết" chuyển sang resolved.
- Alert "đã xong": hiện nhãn hoàn thành, không còn nút.

### Task Manager (Tasks)

Màn `/tasks` gom các ticket trùng lặp thành task chung. Thanh lọc có trạng thái, phòng ban (admin chọn, ops bị ghim), độ ưu tiên, và nút bật lọc task quá hạn.

Mỗi task là một thẻ bấm để mở rộng. Khi mở rộng có:

- Hai nút đổi trạng thái: "Tiếp nhận" (in_progress) và "Hoàn thành" (resolved), gọi `PATCH /api/tasks/{id}/status`.
- Khối gán task: chọn người nhận từ danh sách, chọn hạn hoàn thành, bấm "Gán" gọi `PATCH /api/tasks/{id}/assign`.
- Danh sách ticket con thuộc task đó, tải qua `GET /api/tasks/{id}/alerts`.

Task quá hạn (qua due_at mà chưa resolved) có badge đỏ.

### CSKH Support

Màn `/support` là bàn làm việc cho nhân viên CSKH, bố cục hai cột. Cột trái là hàng đợi ticket đang mở, sắp xếp ưu tiên task quá hạn và priority cao lên đầu, có nút lọc theo mức độ. Cột phải là chi tiết ticket được chọn: thông tin ticket, danh sách ghi nhận liên quan, và ô soạn phản hồi khách hàng.

Ô phản hồi có các nút mẫu câu soạn sẵn (xin lỗi, cảm ơn, kiểm tra tài xế, hoàn tiền) để điền nhanh. Bấm "Phản hồi và Đóng Ticket" sẽ hỏi xác nhận, rồi gọi `PATCH /api/tasks/{id}/status` chuyển task sang resolved và bỏ khỏi hàng đợi.

### Phân tích phòng ban (Insights)

Màn `/insights` biến các agent thành tính năng thật. Khi mở, nó gọi nhanh số liệu từng phòng (không gọi LLM) qua Insight Agent. Trên cùng có ba thẻ tóm tắt: tổng phản hồi, số phòng có dữ liệu, số ca nghiêm trọng. Bấm thẻ ca nghiêm trọng mở modal liệt kê các ca P4/P5 gần đây.

Mỗi phòng ban là một thẻ hiện phân bố mức độ, chủ đề nổi bật, vài ví dụ phản hồi gần nhất. Nút "Phân tích sâu bằng AI" gọi Analyst Agent kèm LLM riêng cho phòng đó (`with_analysis=true`), trả về nguyên nhân gốc, mức rủi ro, và danh sách hành động đề xuất. Tách hai bước như vậy để tiết kiệm chi phí: gom số liệu thì nhanh và miễn phí, chỉ gọi LLM khi người dùng thật sự cần phân tích sâu.

### Báo cáo AI (Reports)

Màn `/reports` chỉ dành cho manager và admin. Admin chọn phòng ban qua dropdown, manager xem phòng mình. Nút "Tạo báo cáo mới" gọi `POST /api/agent/generate-report` để Analyst Agent sinh báo cáo vận hành cho phòng đó. Mỗi lần tạo là một bản insert mới, không ghi đè bản cũ (không còn ràng buộc unique theo ngày).

Mỗi báo cáo hiện dưới dạng thẻ, viền đổi màu theo mức độ (đỏ nếu có CRITICAL, vàng nếu có WARNING). Nội dung render từ Markdown. Nút copy để sao chép nội dung Markdown.

Bên dưới phần Markdown của báo cáo chưa duyệt có **trình biên tập Dự thảo kế hoạch hành động** (Draft Task Editor): danh sách hành động AI đề xuất (từ cột `suggested_tasks`), manager có thể sửa nội dung, mức ưu tiên, thời hạn, thêm hoặc xóa từng dòng. Hai nút:

- **Lưu nháp** (`PUT /api/reports/{id}/draft-tasks`) — lưu danh sách đã chỉnh, mở lại vẫn còn.
- **Duyệt và triển khai task** (`POST /api/reports/{id}/approve-and-dispatch`) — duyệt báo cáo đồng thời tạo từng hành động thành task chính thức trên Task Board (atomic qua RPC). Toast báo "Đã duyệt, tạo N task".

Sau khi duyệt, báo cáo bị khóa: editor ẩn đi, chỉ còn thông báo "Đã duyệt, các task đã được tạo trên Task Board". Các task này hiện badge "Từ báo cáo" + link "Xem báo cáo gốc" ở màn `/tasks`. Vẫn giữ đường duyệt cũ chỉ-duyệt-không-tạo-task (`PATCH /api/reports/{id}/approve`) để tương thích ngược.

### AI Chat

Màn `/chat` thay đổi theo role. Tiêu đề, gợi ý câu hỏi, và phạm vi dữ liệu khác nhau giữa staff, manager, admin. Ops thấy phạm vi là phòng của mình, admin thấy "Toàn hệ thống".

Khung chat có các thẻ gợi ý câu hỏi để bấm nhanh, ô soạn tin (Enter để gửi, Shift+Enter xuống dòng), nút gửi. Mỗi câu trả lời của AI hiện kèm provider, model, độ trễ, và có nút copy. Câu hỏi của người dùng có nút sửa để hỏi lại. Nút "Cuộc trò chuyện mới" xóa lịch sử chat.

Mọi tin nhắn gửi qua `POST /api/agent/chat`. Backend tự phân tầng: khi có cờ `public_only` (widget trang chủ) thì dùng RAG công khai, còn lại ops và admin dùng ReAct agent kèm RAG nội bộ lọc theo phòng. Với ops, nếu câu trả lời có trích dẫn tài liệu SOP/SLA thì hiện thêm cột nguồn tham khảo bên phải kèm độ tương đồng.

### Live Stream (chỉ admin)

Màn `/live-stream` điều khiển luồng ingest demo. Ô trạng thái cho biết đang chạy hay đã dừng, đã xong bao nhiêu batch, kết quả lô cuối. Phần cấu hình có các ô số: batch size, interval (giây), số ticket mỗi N batch, tối đa ticket mỗi lần; và các ô tick: lặp lại, tự tạo ticket, reset offset khi bật. Cấu hình lưu vào trình duyệt.

Nút lớn "Bật Live Stream" gọi `POST /api/live-stream/start` kèm tham số. Khi đang chạy thì đổi thành "Dừng Live Stream" gọi `POST /api/live-stream/stop`. Khi dataset chạy hết, lần bật sau sẽ tự reset offset về 0.

### Quản lý người dùng (chỉ admin)

Màn `/admin` chia tab theo nhóm: chờ cấp quyền, quản lý, nhân viên, quản trị viên. Trên cùng có bốn ô đếm số lượng từng nhóm.

Form "Tạo tài khoản" nhận email, họ tên, role (admin, manager hoặc staff), phòng ban và mật khẩu tạm, rồi gọi `POST /api/admin/users`. Email đã tồn tại thì báo lỗi. Admin tự gửi mật khẩu tạm cho người đó; người đó phải đổi mật khẩu ở lần đăng nhập đầu.

Tab "Chờ cấp quyền" hiển thị các tài khoản `pending` dưới dạng thẻ, với ba nút: "Cấp quyền Nhân viên" và "Cấp quyền Quản lý" (gọi `PATCH /api/users/{id}/role`), và "Từ chối và xoá tài khoản" (có hỏi xác nhận). Lưu ý: xoá tài khoản xoá luôn feedback, alert và lịch sử chat của người đó (FK `ON DELETE CASCADE`).

Các tab còn lại hiển thị bảng. Mỗi dòng có dropdown đổi role, dropdown gán phòng ban (`PATCH /api/users/{id}/department`), và nút xóa. Admin không tự đổi quyền hay tự xóa tài khoản đang đăng nhập của mình. Mọi thay đổi role và phòng ban đều ghi audit log.

### Giới thiệu (About)

Màn `/about` có ba tab giải thích bài toán và giải pháp, kiến trúc hệ thống, và giá trị mang lại. Đây là trang trình bày, không có thao tác nghiệp vụ.

### Customer web (khách hàng, không đăng nhập)

Customer web là một website riêng (`customer-web/`), không phải một màn của Staff web. Khách tới đó bằng mã QR hoặc nút "Gửi phản hồi" trên trang chủ Staff web. Giao diện ưu tiên điện thoại, chỉ có tiếng Việt, không có đăng nhập.

Trang `/` là form gửi phản hồi: ô nội dung (bắt buộc), chọn kênh, chọn khu vực. Dưới form có dòng "Không cần tài khoản. Số điện thoại, email, biển số được che tự động. Nội dung tự xoá sau 180 ngày." Bấm gửi gọi `POST /api/public/feedback`. Thành công thì chỉ hiện mã tra cứu (có nút sao chép) và link tới trang trạng thái, không hiện nhãn AI. Lỗi nhập liệu, lỗi gửi quá nhiều lần (429) hay lỗi mạng đều hiện thông báo rõ ràng. Trên trang còn có ô "Tra cứu mã" để mở trạng thái của một mã cũ.

Trang `/status/:code` gọi `GET /api/public/feedback/{code}` và chỉ hiện trạng thái cùng ngày gửi: "Đã tiếp nhận", "Đang xem xét" hoặc "Đã xem xét" (nhân viên đã kiểm tra phân loại của AI, không có nghĩa sự việc đã xử lý xong). Mã sai, hết hạn hoặc đã bị xoá nội dung đều hiện chung một thông báo không tìm thấy.

---

## 6. Human-in-the-loop và audit

AI gán nhãn không phải lúc nào cũng đúng, nên hệ thống luôn để con người sửa và lưu vết.

Khi nhân viên sửa nhãn ở màn Phản hồi, hệ thống ghi vào `correction_logs`: ai sửa, sửa trường nào, giá trị cũ và mới. Bản ghi này phục vụ hai mục đích: kiểm toán xem ai đã can thiệp, và làm dữ liệu cho lần retrain model sau (một vòng học khép kín).

Admin có thể phân loại lại dữ liệu cũ bằng rule mới qua `POST /api/feedback/reclassify`, nhưng các bản đã có người duyệt thì được giữ nguyên, không ghi đè.

Mọi thay đổi quyền và phòng ban của người dùng đều vào `audit_logs`.

---

## 7. Vòng đời ticket và SLA

Sau khi alert được tạo, `backend-worker` tự đẩy trạng thái theo thời gian: open chuyển sang in_progress, rồi sang resolved. Đây là mô phỏng để demo luồng, thời gian chờ giữa các bước cấu hình được.

Song song, mỗi chủ đề có một mốc SLA theo bảng routing (ví dụ Safety 1 giờ, App Issue 12 giờ). Ticket agent quét các ticket quá hạn. Ở màn Task Manager và CSKH Support, task quá due_at mà chưa resolved sẽ bị đánh dấu quá hạn để nhân viên ưu tiên xử lý.

---

## 8. Bản demo so với production thật

Hệ thống hiện tại chạy thật, nhưng vẫn là bản demo. Phần khác với một production đầy đủ:

| Khía cạnh | Bản đang chạy | Production đầy đủ |
|-----------|---------------|-------------------|
| Nguồn review | Streaming từ dataset đóng gói + nhập tay | Hút realtime trực tiếp từ store và app |
| Dữ liệu | Review công khai + metadata synthetic | Dữ liệu vận hành thật của hãng |
| Thông báo | Realtime trên dashboard | Push tới Slack, email, app tài xế |
| Hạ tầng | Supabase cloud + chạy local | Container hóa, CI/CD, monitoring đầy đủ |

Để hiểu sâu hơn, xem thêm `docs/project/ai-systems.md` (chi tiết các lớp AI), `docs/project/agents-guide.md` (thứ tự và I/O từng agent), `docs/project/rbac-departments.md` (phân quyền), và `docs/project/architecture.md` (kiến trúc tổng thể).
