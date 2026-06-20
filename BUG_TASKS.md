# BACKLOG TASK TỪ KẾT QUẢ TEST — cần dev xử lý

> Sinh từ các lỗi tester đã log. Mỗi task có: vấn đề, vị trí code, việc cần làm, **tiêu chí nghiệm thu (Acceptance)** để tester verify lại sau khi fix.
> Nguồn lỗi chi tiết: `tester_result.md` (PII/RBAC/Chat), `tester_task_routing.md` (định tuyến/báo cáo).
>
> **Lưu ý:** Đây là snapshot lỗi tại thời điểm test, được giữ để đối chiếu lịch sử. Nhiều mục đã được xử lý trên `main`; trạng thái triển khai hiện tại được ghi trong `WORKLOG.md` và được xác nhận bằng test tự động.

**Trạng thái:** 🔴 chưa làm · 🟡 đang làm · ✅ xong & đã verify

---

## NHÓM A — ĐỊNH TUYẾN TICKET (gốc của "toàn đổ CSKH") · Ưu tiên P1

> ✅ **ĐÃ XÁC NHẬN TRÊN LIVE (20/6):** Chạy pipeline → 9/9 ticket đều `Assigned Team = CSKH`,
> kể cả ticket có topic = **Driver Behavior** (Routing Note hiện rõ) lẽ ra phải về **Vận hành**.
> ⇒ Bằng chứng: topic nhận đúng nhưng team vẫn sai → **routing_table bị bỏ qua hoàn toàn.**

### TASK-00 · (GỐC) spike_detector để LLM tự bịa phòng ban, KHÔNG dùng routing_table 🔴🔴
- **Vấn đề (đã xác nhận):** Luồng tạo ticket P5 (`spike_detector.py`) lấy team từ **`alert_data['assigned_team']` do LLM tự sinh** ([spike_detector.py:92](pipeline/spike_detector.py#L92)), **không gọi `route_ticket`, không đọc routing_table**. LLM (`analyze_spike`) được cho ví dụ phòng ban SAI ("Cửa hàng, Giao hàng" — không tồn tại) và không biết 6 phòng chuẩn ([llm_agent.py:27](pipeline/llm_agent.py#L27)); lỗi LLM → fallback cứng "CSKH" ([llm_agent.py:63](pipeline/llm_agent.py#L63)).
- **Hệ quả:** Mọi ticket P5 → CSKH (hoặc phòng LLM bịa), routing_table chuẩn vô tác dụng.
- **Việc cần làm:** Sau khi có topic, **BẮT BUỘC ép team qua `route_ticket(topic, severity)`** thay vì tin chuỗi LLM. Bỏ field `assigned_team` khỏi LLM (hoặc chỉ dùng tham khảo), không cho LLM quyết định phòng.
- **Acceptance:**
  - [ ] Ticket topic Driver Behavior → team **Vận hành**; App Issue → **IT**; Safety → **Safety**.
  - [ ] Không còn ticket nào gán phòng ngoài 6 phòng chuẩn.
  - [ ] Chạy lại pipeline: ticket phân bổ đúng nhiều phòng, không dồn 100% CSKH.

### TASK-00b · Hợp nhất 2 luồng tạo ticket (spike_detector vs orchestrator) 🔴
- **Vấn đề:** `run_full_cycle` chạy CẢ `orchestrator.run_agent_pipeline` (dùng route_ticket) LẪN `spike_detector.detect_spikes` (dùng LLM free-text) → 2 logic định tuyến mâu thuẫn, có thể tạo ticket trùng/khác team cho cùng spike.
- **Việc cần làm:** Chọn 1 luồng chuẩn (khuyến nghị orchestrator + route_ticket), bỏ hoặc đồng bộ luồng còn lại.
- **Acceptance:** [ ] Chỉ 1 logic định tuyến áp dụng; không 2 ticket khác team cho cùng (area, topic).

> 3 task dưới đây vẫn cần làm để topic non-P5 đến đúng phòng:

### TASK-01 · Tạo ticket theo (Khu vực × Chủ đề), không gom chung theo khu vực 🔴
- **Vấn đề:** Mỗi khu vực chỉ tạo 1 ticket, định tuyến bằng topic của 1 feedback mới nhất → topic khác bị bỏ, không về đúng phòng.
- **Vị trí:** `pipeline/agents/orchestrator.py` dòng 88-114 (`top_topic = fbs[0].get("topic")`).
- **Việc cần làm:** Gom feedback theo cặp **(area, topic)** rồi tạo/route ticket cho từng cụm topic, thay vì lấy 1 topic đại diện cho cả khu vực.
- **Acceptance:**
  - [ ] 1 khu vực có nhiều topic → sinh ticket riêng cho từng topic, route về đúng phòng (App Issue→IT, Driver Behavior→Vận hành...).
  - [ ] Không còn cảnh 1 ticket "gánh" nhiều loại vấn đề khác phòng.

### TASK-02 · Cho phép topic không-P5 vẫn tạo ticket khi bùng nổ 🔴
- **Vấn đề:** Luồng ticket chỉ nhận feedback **P4/P5** (`orchestrator.py` dòng 72), nhưng `rules.py` cap App Issue/Driver Behavior/Pricing/Delay ở **P3** → các topic này **không bao giờ tạo ticket** → IT/Vận hành/Pricing nhận ~0 ticket. (VD: 279 App Issue không đổ về IT.)
- **Vị trí:** `pipeline/agents/orchestrator.py` dòng 72; logic ngưỡng ở `rules.py` dòng 183-245.
- **Việc cần làm:** Thêm điều kiện tạo ticket theo **số lượng/spike** (vd ≥ N feedback cùng (area, topic) trong cửa sổ thời gian thì tạo ticket dù chỉ P3), không chỉ dựa P4/P5. (Hoặc xem lại rule severity cho App/Driver.)
- **Acceptance:**
  - [ ] Khu vực có nhiều phản hồi App Issue (P3) → tạo được ticket cho **IT**.
  - [ ] Nhiều phản hồi tài xế (P3) → tạo ticket cho **Vận hành**.
  - [ ] Không tạo ticket rác cho vài feedback lẻ tẻ (ngưỡng hợp lý).

### TASK-03 · Truyền đúng P-severity vào router để override "P5 → Safety" hoạt động 🔴
- **Vấn đề:** `orchestrator.py` dòng 98 truyền severity dạng alert (`"CRITICAL"`) vào `route_ticket`, nhưng router so với `"P5"` → nhánh ép P5 về Safety **không bao giờ chạy** qua pipeline chính.
- **Vị trí:** `pipeline/agents/orchestrator.py` dòng 98; `pipeline/agents/router_agent.py` dòng 40-61.
- **Việc cần làm:** Truyền **severity gốc P1–P5** (hoặc map đúng) vào `route_ticket`, tách khỏi mức alert CRITICAL/WARNING/WATCH.
- **Acceptance:**
  - [ ] Feedback P5 (bất kể topic) → ticket route về **Safety** (đúng spec Safety-first).
  - [ ] `routed_by` ghi nhận "(P5 Override)" khi áp dụng.

---

## NHÓM B — CHE GIẤU PII · Ưu tiên P1

### TASK-04 · Mask PII nhất quán: số điện thoại bàn + biển số 2 chữ cái 🔴
- **Vấn đề (đã verify trên live):** Feedback `Gọi tôi số bàn 024 3974 3091...` và `Xe biển 30AB-12345...` hiển thị **nguyên văn, không che**. Hệ thống che biển 1 chữ cái nhưng lọt biển 2 chữ + số bàn → che nửa vời.
- **Vị trí:** `pipeline/clean.py` hàm `mask_pii` (regex SĐT dòng 29, biển số dòng 42).
- **Việc cần làm:**
  - Regex SĐT: nhận cả số bàn (10–11 số, có mã vùng) và nhiều cách viết nhóm.
  - Regex biển số: cho phép **1–2 chữ cái** (`30AB-12345`, sê-ri LD/NG/NN...).
  - Giữ allowlist email công khai (`support.vn@greensm.com`, `dpooffice@greensm.com`).
- **Acceptance:**
  - [ ] Gửi `024 3974 3091`, `091 234 5678`, `30AB-12345` → list hiện `[SĐT_ĐÃ_ẨN]` / `[BIỂN_SỐ_ĐÃ_ẨN]`.
  - [ ] Các ca cũ vẫn mask đúng (`0912345678`, `29A-12345`, email cá nhân).
  - [ ] 2 email công khai trong allowlist **không** bị che.
  - [ ] Không che nhầm dãy số hợp lệ thông thường (kiểm regression).
- **Lưu ý:** Cần **deploy lại backend** (mask chạy server-side lúc submit). Nếu team chốt "không mask biển số cho ops" thì phải bỏ mask biển **đồng loạt** (không để nửa vời).

---

## NHÓM C — QUYẾT ĐỊNH SẢN PHẨM / TÀI LIỆU · Ưu tiên P2–P3

### TASK-05 · Chốt chính sách scope feedback theo phòng ban 🔴
- **Vấn đề:** Alerts/Insights/Chat **có** lọc theo phòng, nhưng trang **Phản hồi (`/api/feedback/recent`) KHÔNG** lọc → manager/staff thấy feedback **mọi phòng** (`main.py` dòng 164-172). Mâu thuẫn nội bộ.
- **Việc cần làm:** Team quyết định: feedback có scope theo phòng không? Nếu có → thêm lọc `department` cho ops không phải admin.
- **Acceptance:** [ ] Hành vi feedback nhất quán với Alerts/Insights theo quyết định đã chốt.

### TASK-06 · Sửa README cho khớp quyền Staff thực tế 🔴
- **Vấn đề:** README ghi Staff ❌ "Ticket Triage" & "Phân tích phòng ban", nhưng cả menu lẫn backend (`require_ops_staff`) **đều cho staff vào**. Lệch tài liệu.
- **Việc cần làm:** Hoặc sửa README (staff ✅), hoặc siết quyền nếu thực sự muốn cấm staff. Chốt 1 hướng.
- **Acceptance:** [ ] README và hành vi thực tế khớp nhau.

### TASK-07 (tùy chọn, hardening) · Thêm route guard theo role cho trang admin-only 🔴
- **Vấn đề:** Route guard FE chỉ chặn `guest` (`route.tsx` dòng 39). Staff/manager mở URL admin-only thì component tự chặn (đã PASS), nhưng thiếu lớp guard ở router.
- **Mức độ:** Thấp (dữ liệu đã an toàn nhờ component + backend 403). Chỉ là defense-in-depth.
- **Acceptance:** [ ] Staff/manager dán URL admin-only → redirect `/dashboard` ngay từ router.

---

### TASK-08 · Báo cáo AI: nội dung bị đổ đồng + 2 bộ sinh báo cáo đè nhau 🔴
- **Vấn đề:** Báo cáo/phân tích root-cause gom theo **khu vực** nên **trộn nhiều phòng vào 1 báo cáo** rồi đổ về CSKH (xác nhận qua data live: 1 ticket vừa nói lỗi app vừa nói tài xế). Ngoài ra có **2 bộ sinh báo cáo** cùng ghi `(team, report_date)`: orchestrator (analyst/insight-based) và `task_agent.generate_daily_report` (task-based) → đè lên nhau.
- **Phụ thuộc:** Phần lớn tự khỏi sau khi sửa định tuyến (TASK-00→03) vì feedback sẽ tách đúng phòng.
- **Việc cần làm:** (1) Sau khi sửa routing, phân tích theo **(phòng/topic)** thay vì gom cả khu vực. (2) Chốt 1 nguồn sinh báo cáo chuẩn, bỏ/đồng bộ nguồn kia.
- **Acceptance:**
  - [ ] Báo cáo mỗi phòng chỉ nói vấn đề của phòng đó, không trộn IT + Vận hành.
  - [ ] Phòng IT/Vận hành có báo cáo (không trống) sau khi định tuyến đúng.
  - [ ] Chỉ 1 bộ sinh báo cáo ghi vào `department_reports`.

---

## ĐÃ TEST — KHÔNG CẦN LÀM (PASS, để tham khảo)
- ✅ Phân quyền trang admin-only (staff/manager bị chặn, 3 lớp).
- ✅ Chat guest không rò rỉ dữ liệu nội bộ + chống prompt injection.
- ✅ Chat admin/ops trả đúng dữ liệu nội bộ.
- ✅ Báo cáo AI — **chỉ phần cơ chế**: dedup đúng (1 báo cáo/phòng/ngày), cấu trúc 4 mục, có fallback.
  ⚠️ Phần **nội dung** thì CHƯA ổn — xem TASK-08 (bị đổ đồng do lỗi định tuyến).

---

