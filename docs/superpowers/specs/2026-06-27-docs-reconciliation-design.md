# Spec — Đối soát & hoàn thiện tài liệu dự án theo code đã hoàn thành

- **Ngày**: 2026-06-27
- **Loại intake**: Maintenance request (tài liệu) — đối soát docs với code đã hoàn thiện
- **Lane**: normal (chỉ tài liệu; không đụng auth/data/contract/hành vi → không hard-gate)
- **Phương án**: A — Flow-first, lấy code làm chân lý

## 1. Mục tiêu & bối cảnh

Dự án **C2-App-116 (xanhSM AI Quality Intelligence Platform)** đã hoàn thiện. Trong quá
trình phát triển, code đã tiến hoá nhiều (6 phòng ban, RAG hybrid, multi-agent, task loop,
HI-loop) trong khi `docs/project` bị **drift** so với code thực tế. Mục tiêu: đối soát toàn
bộ `docs/project` với code đã hoàn thành, **chạy e2e thật** để lấy bằng chứng, rồi **sửa
stale tại chỗ kèm ghi chú thay đổi**, để tài liệu trở thành nguồn tham chiếu đúng.

Quyết định người dùng đã chốt:
- Phạm vi: **đối soát & cập nhật toàn bộ `docs/project`**.
- "Test luồng": **chạy thật end-to-end** (đã xác nhận `.env` có đủ key thật: Anthropic,
  OpenAI, OpenRouter, Cohere, Supabase, Railway; có ~35 file test + bộ eval gold dataset).
- Doc stale: **sửa tại chỗ + ghi chú thay đổi** (giữ lịch sử qua git).

## 2. Danh mục luồng chuẩn (canonical flows)

Xương sống của việc đối soát. Mỗi luồng là một đơn vị độc lập có thể hiểu & xác minh riêng.

| # | Luồng | File code nguồn (ground truth) |
|---|-------|--------------------------------|
| 1 | Ingest & streaming realtime | `ingest.py`, `worker_ingest.py`, live-stream env |
| 2 | Clean + PII mask | `clean.py` |
| 3 | ML classify + severity rules | `classifier.py`, `worker_ml.py`, `rules.py` |
| 4 | Ma trận rủi ro 5 chiều (Scoring) | `agents/scoring_agent.py`, `llm_agent.py`, `rescore_overall_risk.py` |
| 5 | Spike → auto alert/ticket | `spike_detector.py`, `agents/alert_agent.py`, `agents/ticket_agent.py`, `worker_ticket.py` |
| 6 | Multi-agent orchestration | `agents/orchestrator.py` + `router/ingestion/scoring/analyst/insight/alert/ticket/task/report_builder` |
| 7 | Phân tích phòng ban + báo cáo AI theo lịch (6 phòng, 3 khối) | `departments.py`, `agents/report_builder.py`, `agents/analyst_agent.py`, `agents/insight_agent.py` |
| 8 | AI Chat + Tiered Hybrid RAG | `agent/chat_agent.py`, `chat_tools.py`, `rag_engine.py`, `knowledge_base.py`, `public_kb.py`, `model_router.py` |
| 9 | Human-in-the-Loop duyệt nhãn + correction log | `users_admin.py`, eval `extract_corrections.py`, endpoints trong `main.py` |
| 10 | Khép kín Báo cáo → Task (HI-Loop approval) | `agents/task_agent.py`, report-approval endpoints |
| 11 | RBAC 4 vai trò + scope phòng ban | `auth_guard.py`, `departments.py`, RLS migrations |
| 12 | Topology worker + API | `main.py`, `worker.py`, `worker_ticket/ingest/ml/agent.py`, Dockerfiles |

## 3. Bản đồ truy vết & drift đã biết

Mỗi luồng map tới: (a) code nguồn (Mục 2), (b) (các) doc mô tả, (c) test/eval xác minh.

Drift đã xác minh-một-phần cần sửa:
- **Số agent**: README ghi "8 agent nghiệp vụ + Orchestrator"; `agents/` thực có 9 file
  agent (router, ingestion, scoring, analyst, insight, alert, ticket, task, report_builder)
  + orchestrator. → Chốt định nghĩa "agent" và sửa cho nhất quán toàn bộ doc.
- **6 phòng ban** (đã xác nhận trong `departments.py`): IT; CSKH; Vận hành;
  Tài chính & Thanh toán; Sản phẩm; Quản lý Rủi ro & Gian lận. Không còn Marketing. → Quét &
  sửa mọi doc còn nhắc 4 phòng / Marketing.
- **RAG hybrid** (đã xác nhận trong `rag_engine.py`): Cohere embeddings + BM25-lite keyword
  + Reciprocal Rank Fusion (k=60). → Sửa mọi mô tả "chỉ keyword".
- **`app/flow.md`** mô tả cấu trúc `pipeline/ingest|clean|ml|analytics|agent/` (sai) trong
  khi code là file phẳng + `agent/` + `agents/`. → Sửa (đánh dấu optional vì ngoài `docs/project`).

## 4. Chạy e2e thật để lấy bằng chứng

Thứ tự rẻ → đắt; ghi lại kết quả thật vào phần bằng chứng:
1. `pytest pipeline/tests` — suite có sẵn (~35 file), không tốn token.
2. Eval router/model trên `pipeline/eval/gold_dataset.json` (`route_eval.py`, `evaluate_model.py`).
3. Khởi động FastAPI backend → hit `/health` + vài endpoint thật (đọc-only nếu được).
4. Một lượt ingest→clean→classify→agent thật trên mẫu nhỏ để quan sát multi-agent + báo cáo.
5. Smoke build frontend (Bun) để xác nhận app build.

Mọi số liệu/kết quả thật cập nhật vào `docs/project/eval-evidence.md` (và/hoặc khối bằng
chứng trong doc liên quan). Bước nào không chạy được sẽ ghi rõ lý do, không nguỵ tạo.

## 5. Đối soát & ghi chú thay đổi

- Sửa stale **tại chỗ** trong từng file `docs/project`.
- Mỗi file được sửa thêm khối ngắn: `> **Cập nhật 2026-06-27** — <những gì đã sửa>`.
- Làm mới `docs/project/README.md` thành chỉ mục điều hướng đúng.
- Đảm bảo `docs/project/architecture/e2e-flow.md` là doc luồng quyền uy nhất, khớp Mục 2.
- Không refactor code, không đổi hành vi, không đụng `docs/harness/` & `docs/superpowers/`
  (trừ chính spec/plan này).

## 6. Tiêu chí hoàn thành (acceptance)

- [ ] Mọi file trong `docs/project` đã được đối soát với code; phần stale đã sửa.
- [ ] Mỗi file sửa có ghi chú "Cập nhật 2026-06-27".
- [ ] 4 drift ở Mục 3 được giải quyết nhất quán xuyên suốt.
- [ ] Bằng chứng e2e thật (pytest + eval + health + 1 lượt pipeline) ghi vào `eval-evidence.md`;
      bước không chạy được nêu rõ lý do.
- [ ] `docs/project/README.md` là chỉ mục đúng; `architecture/e2e-flow.md` khớp 12 luồng.
- [ ] `app/flow.md` được sửa (optional) hoặc nêu rõ nếu bỏ qua.

## 7. Ngoài phạm vi (non-goals)

- Không sửa/cấu trúc lại code nguồn.
- Không đổi schema/migration/contract.
- Không viết lại `docs/harness/*` hay `docs/superpowers/*` (chỉ thêm spec/plan này).
