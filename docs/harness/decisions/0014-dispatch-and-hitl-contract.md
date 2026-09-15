# 0014 — Hợp đồng phân phối việc và Human-in-the-Loop

- **Date:** 2026-08-27
- **Status:** accepted

## Context

Audit ngày 2026-08-27 (đo trên Supabase `ai-quality-intelligence` đang chạy, không phải
suy đoán) cho thấy đường "dữ liệu → alert → task → phòng ban" và vòng "báo cáo → task"
sai ở nhiều chỗ cùng lúc:

- **19/19** task do agent sinh có `topic='General'`, `due_at NULL`, `owner_id NULL`.
  `find_or_create_cluster_task` hardcode topic và không đặt SLA.
- Cụm task định danh bằng `(phòng, khu vực)`, bỏ chủ đề — 13/19 task rơi vào
  `Vận hành` vì luật override P5, mỗi khu vực gộp thành một task duy nhất. Một alert
  Safety P5 nhập thẳng vào task `Delay` P2 đang mở cùng khu vực.
- Task chỉ hút alert khi `status='open'`. Ngay khi manager giao việc (`assigned`),
  chu kỳ sau đẻ ra task trùng cho cùng cụm.
- `AUTO_TICKET_MAX_SPIKES` có **ba** mặc định khác nhau (1 ở worker, 6 ở live_stream,
  3 ở API). Đường production thật dùng **1**: tối đa một ticket mỗi lượt quét cho toàn
  hệ, phần còn lại bị cắt im lặng, không log, không hàng đợi.
- Alert thiếu `topic` (row legacy) bị coi là trùng với **mọi** chủ đề của cùng
  `(khu vực, phòng)`, chặn cả spike Safety mới suốt cửa sổ cooldown 60 phút.
- `approve_report_and_dispatch` chỉ nhận `require_ops_staff`: **staff thường duyệt được
  báo cáo và tạo hàng loạt task**, trong khi giao việc và duyệt báo cáo hoàn thành đều
  yêu cầu manager. `PATCH /approve` (duyệt trơn) khoá vĩnh viễn đường dispatch.
- `suggested_tasks` là `list[dict]` không schema: priority tự do, deadline lạ âm thầm
  thành +48h, danh sách rỗng vẫn khoá được báo cáo.
- Duyệt một báo cáo hoàn thành mức `blocked` nhắm `resolved`; transition không hợp lệ
  nên **bị bỏ qua im lặng** — manager thấy "đã duyệt", task kẹt `in_progress` vĩnh viễn.
- `authenticated` có `UPDATE`/`DELETE` trực tiếp trên `tasks`, `feedback`,
  `task_events`, `task_completion_reports`; `anon` có full CRUD trên `alerts`,
  `feedback`, `tasks`. Mọi cổng RBAC ở tầng API có thể bị vượt qua từ DevTools.
- Realtime notification không lọc phòng ban (RLS chỉ gate theo role), nên nhân viên
  một phòng nhận toast tiêu đề mọi ticket của các phòng khác.

## Decision

**1. Cụm task định danh bằng `(phòng ban, khu vực, chủ đề)`.** Bỏ chủ đề khỏi khoá là
   nguyên nhân trực tiếp khiến sự cố nặng bị chôn trong task nhẹ.

**2. Task hút alert khi ở `open`/`assigned`/`in_progress`.** `pending_review` và
   `resolved` ngừng hút. Chỉ khớp `open` sẽ sinh task trùng ngay sau khi giao việc.

**3. Ưu tiên chỉ đi lên.** Alert nặng hơn nhập vào task đang mở thì nâng `priority` và
   siết `due_at` theo SLA mới. Không bao giờ hạ.

**4. Không alert nào bị rơi.** LLM chỉ đặt tên cụm; hỏng hoặc tắt thì dùng tiêu đề suy
   diễn từ dữ liệu đếm được. Cụm lỗi được **đếm và trả về** (`clusters_failed`,
   `status='partial_success'`), `agent_run_logs` ghi `fallback` — không còn báo
   `success` trơn khi có cụm hỏng.

**5. Cắt do trần phải hiện ra.** `detect_spikes` trả `dropped_groups`, `dropped_teams`,
   `dedup_degraded` và in ra nhóm bị cắt. `DEFAULT_MAX_SPIKES = len(DEPARTMENTS)` là
   nguồn mặc định **duy nhất** cho live_stream, worker và API.

**6. Trùng alert phải trùng chủ đề.** Alert thiếu `topic` không còn chặn chủ đề khác.
   Cửa sổ dedup chỉ xét alert `open`/`in_progress`.

**7. Duyệt báo cáo là quyền manager.** `approve_report`, `update_draft_tasks`,
   `approve_and_dispatch` đều chuyển sang `require_manager`. `PATCH /approve` từ chối
   (409) khi báo cáo còn Draft Task, để không khoá mất đường dispatch.

**8. Draft task có schema thật** (`DraftTaskItem`): `action` bắt buộc 1–300 ký tự,
   `priority` khớp `^P[1-5]$`, `deadline` khớp token `parse_deadline` hiểu được,
   danh sách 1–20 phần tử. Deadline lạ bị từ chối (422) thay vì âm thầm +48h.

**9. Duyệt báo cáo hoàn thành phân biệt mức hoàn thành.**
   `approved + completed` → task `resolved` (và đóng alert liên kết).
   `approved + partial/blocked` → ghi nhận vướng mắc, task **ở nguyên**.
   `rejected` → task về `in_progress`.
   Transition không hợp lệ trả **409** và **không ghi gì**, thay vì bỏ qua im lặng.
   Một báo cáo chỉ được duyệt một lần; một task chỉ có một báo cáo chờ duyệt.

**10. Nhân viên chỉ báo cáo task của mình** (`owner_id == user.id`), cùng luật với
   `accept_task`.

**11. `support-resolve` chỉ áp dụng cho `source='ticket'`.** Task nội bộ phải đi hết
   vòng giao việc → nhận → báo cáo → manager duyệt.

**12. Đường GHI của vòng duyệt nhãn chịu scope phòng ban** như đường ĐỌC
   (`correct_feedback_label`, `review_feedback` gọi `can_view_team(_feedback_team(...))`).

**13. `GET /api/insights/departments` là read-only.** Trước đây nó gọi
   `run_agent_pipeline()` với `run_alert=True, run_report=True` — một request GET tạo
   alert, ticket, task và chèn báo cáo. Chạy pipeline dùng `POST /api/agent/run`.

**14. Ghi trực tiếp từ trình duyệt bị khoá** (migration `20260827000000`).
   `authenticated` mất `INSERT/UPDATE/DELETE` trên `tasks`, `alerts`, `task_events`,
   `task_completion_reports` và `UPDATE/DELETE` trên `feedback`; `anon` bị thu hồi toàn
   bộ. Giữ `SELECT` để realtime hoạt động. Backend chạy service_role nên không đổi.

**15. Realtime notification lọc phòng ban ở client** (`canSeeTeam`, bản sao của
   `can_view_team`), đọc `assigned_team` thay vì `record.team` vốn không tồn tại.

## Alternatives Considered

1. **Thêm status `blocked` cho task.** Cần migration đổi CHECK, sửa bảng transition và
   toàn bộ badge frontend. Bị loại: vấn đề thật là *duyệt im lặng không làm gì*, giải
   bằng ngữ nghĩa duyệt (#9) là đủ, diff nhỏ hơn nhiều. Trần đã biết: task `blocked` vẫn
   hiển thị `in_progress` trên bảng công việc; nếu vận hành cần phân biệt trực quan thì
   mới thêm status.
2. **Unique index từng phần `(assigned_team, area, topic)` cho task chưa đóng** để chặn
   TOCTOU ở tầng DB. Bị loại lần này: dữ liệu hiện có 19 task `topic='General'` sẽ vi
   phạm ràng buộc, cần backfill trước. Ghi nhận là việc kế tiếp.
3. **Giữ `require_ops_staff` cho duyệt báo cáo** để demo nhanh. Bị loại: mâu thuẫn với
   `docs/project/co_che.md` (manager là người duyệt) và với chính các endpoint khác.

## Consequences

Positive:

- Sự cố nặng không bị chôn trong task nhẹ; SLA có mặt trên mọi task agent sinh.
- Không còn alert mồ côi khi LLM hỏng; số cụm hỏng hiện ra trong `agent_run_logs`.
- Số spike bị cắt và trạng thái dedup suy giảm đều quan sát được.
- Vòng HITL không còn đường tắt: staff không tự duyệt báo cáo, không đóng task nội bộ.
- Lỗ hổng ghi thẳng DB từ trình duyệt bị đóng (G1/G2 trong `co_che.md` Phần B).

Tradeoffs:

- **Breaking:** staff mất quyền duyệt báo cáo (403). Cần đảm bảo mỗi phòng có manager.
- **Breaking:** `PATCH /api/reports/{id}/approve` trả 409 nếu báo cáo còn Draft Task.
- **Breaking:** `support-resolve` trả 409 với task không phải `source='ticket'`.
- Deadline không đúng token bị từ chối 422 — báo cáo cũ có `action_items` với deadline
  văn xuôi sẽ phải sửa tay khi manager duyệt.
- `AUTO_TICKET_MAX_SPIKES` mặc định 1 → 6 làm tăng số ticket và số lời gọi LLM mỗi lượt.

## Follow-Up

- Backfill `tasks.topic` cho 19 row `'General'`, rồi thêm unique index từng phần cho cụm.
- Nhắc hạn duyệt báo cáo CRITICAL và escalate task quá hạn (G10/P2-3) vẫn chưa có.
- `correction_logs` vẫn là bảng chỉ-ghi: chưa có endpoint đọc, chưa khép vòng retrain.
- Bảng công việc và bảng báo cáo hoàn thành chưa có realtime/poll, còn stale sau thao tác.

## Proof

- `pipeline/tests/test_cluster_task_helper.py` (18 test: khoá cụm, hút task, leo thang,
  fallback không LLM, cụm hỏng phải hiện ra).
- `pipeline/tests/test_hitl_hardening.py` (22 test: role gate, bẫy duyệt trơn, schema
  draft task, chủ sở hữu, ngữ nghĩa duyệt blocked, scope phòng ban khi sửa nhãn).
- `pipeline/tests/test_spike_detector.py` (nhóm bị cắt được trả về, topic rỗng không
  chặn chủ đề khác).
- `pipeline/tests/test_support_resolve.py` (từ chối task không phải ticket).
- Toàn bộ: `cd pipeline && .venv/bin/python -m pytest tests -q` → 245 passed.
- Frontend: `npx tsc --noEmit` sạch, `npx vitest run` 11 passed.
