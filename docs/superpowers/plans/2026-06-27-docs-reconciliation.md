# Đối soát & hoàn thiện docs/project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đối soát toàn bộ `docs/project` với code đã hoàn thành, chạy e2e thật lấy bằng chứng, sửa stale tại chỗ kèm ghi chú "Cập nhật 2026-06-27".

**Architecture:** Flow-first (phương án A): trước hết thiết lập "ground truth" từ code + một lượt chạy e2e thật (Task 1), rồi đối soát từng nhóm doc theo luồng/area dựa trên ground truth đó. Mỗi task = một nhóm doc + chu trình "tìm stale (grep) → sửa theo canonical fact → xác minh lại (grep sạch / khớp code) → commit".

**Tech Stack:** Markdown (docs), Python/FastAPI + pytest + apscheduler (backend pipeline), scikit-learn, Cohere embeddings + BM25 + RRF (RAG), Supabase/Postgres, Vite/Bun + React 19 (frontend), Railway (deploy).

## Global Constraints

Các giá trị dưới đây là **canonical facts** đã xác minh từ code (2026-06-27). Mọi task phải làm cho doc khớp các giá trị này; nếu trong khi làm phát hiện code khác giá trị này, **ưu tiên đọc lại code và cập nhật cả constant này lẫn doc**.

- **6 phòng ban** (`pipeline/departments.py` → `DEPARTMENTS`): `IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`. KHÔNG còn `Marketing`.
- **Agent roster** (`pipeline/agents/`): **8 agent nghiệp vụ** = các file `*_agent.py`: `alert`, `analyst`, `ingestion`, `insight`, `router`, `scoring`, `task`, `ticket`; **+ `orchestrator.py`** (điều phối) **+ `report_builder.py`** (helper dựng báo cáo, KHÔNG phải agent). ⇒ Cách diễn đạt đúng: "8 agent nghiệp vụ + Orchestrator" (README hiện đã đúng; chỉ cần đảm bảo các doc khác không nói "10 agent" hay "6 agent").
- **RAG**: hybrid — Cohere `embed-multilingual-v3.0` + pgvector + BM25-lite keyword, hợp nhất bằng Reciprocal Rank Fusion (RRF, hằng số k=60) tại `pipeline/agent/rag_engine.py`. KHÔNG mô tả "chỉ keyword".
- **Worker topology**: 4 worker chuyên trách `worker_ticket.py`, `worker_ingest.py`, `worker_ml.py`, `worker_agent.py` (+ `worker.py` base/dispatcher); API `main.py` chỉ giữ scheduler on-demand, job định kỳ chạy trong worker.
- **RBAC**: 4 vai trò `admin`, `manager` (quản lý), `staff` (nhân viên), `guest` (khách).
- **Ghi chú thay đổi**: mỗi file doc được sửa phải có dòng/khối: `> **Cập nhật 2026-06-27:** <tóm tắt cái đã sửa>` đặt ngay dưới tiêu đề H1.
- **Văn phong (humanizer)** — áp cho mọi prose viết/sửa trong các task này:
  - KHÔNG dùng gạch ngang dài `—` hay `–`. Thay bằng dấu chấm, phẩy, hai chấm, hoặc ngoặc đơn. Trước khi commit, quét file để chắc không còn `—`/`–`.
  - KHÔNG ngôn ngữ quảng cáo/thổi phồng ("vibrant", "testament", "pivotal", "groundbreaking", "đóng vai trò then chốt", "minh chứng cho"). Giữ giọng trung tính, chính xác.
  - KHÔNG câu "-ing"/"việc... nhằm..." độn để giả chiều sâu; KHÔNG ép rule-of-three; KHÔNG header phân mảnh (heading rồi 1 câu lặp lại heading).
  - Dùng "là/có/dùng" trực tiếp thay vì "đóng vai trò là/sở hữu/cung cấp".
  - KHÔNG bôi đậm máy móc từng cụm; chỉ in đậm khi thật cần.
  - Đây là tài liệu tham chiếu kỹ thuật: KHÔNG chèn ngôi thứ nhất, cảm xúc, hay quan điểm cá nhân. Trung tính, plain là đúng.
  - Tránh diff-anchored ("trước đây dùng X, nay đổi"). Mô tả hệ thống ở trạng thái hiện tại. Ngoại lệ duy nhất: dòng "Cập nhật 2026-06-27" (ghi chú version-scoped, được phép).
- **Phạm vi**: chỉ sửa tài liệu; KHÔNG sửa code nguồn, schema, migration, contract. KHÔNG đụng `docs/harness/*` và `docs/superpowers/*` (trừ plan/spec này).
- **Nhánh**: tất cả commit trên nhánh `docs/reconcile-project-docs` (đã tạo).

---

### Task 1: Ground truth — chạy e2e thật & ghi bằng chứng

**Files:**
- Modify: `docs/project/eval-evidence.md` (thêm khối "Bằng chứng e2e 2026-06-27")

**Interfaces:**
- Consumes: code pipeline + `.env` (đã có key thật), `pipeline/eval/gold_dataset.json`.
- Produces: khối bằng chứng e2e thật + bản ghi ground-truth (roster agent, 6 phòng ban, RAG hybrid, worker topology) mà các task sau trích dẫn.

- [ ] **Step 1: Chạy unit/integration suite (rẻ nhất, không tốn token)**

Run: `cd pipeline && python -m pytest -q 2>&1 | tail -30`
Expected: ghi lại số test pass/fail/skip thật. Nếu fail do thiếu network/DB, ghi rõ test nào & lý do.

- [ ] **Step 2: Chạy eval router + model trên gold dataset**

Run: `cd pipeline && python -m eval.route_eval 2>&1 | tail -20 ; python -m eval.evaluate_model 2>&1 | tail -20`
Expected: ghi lại accuracy/F1 thật xuất ra. Nếu script cần tham số khác, đọc đầu file `pipeline/eval/route_eval.py` & `evaluate_model.py` để gọi đúng, rồi ghi lệnh đã dùng.

- [ ] **Step 3: Khởi động API & kiểm tra health (read-only)**

Run (nền): `cd pipeline && (uvicorn main:app --port 8000 &) ; sleep 6 ; curl -s localhost:8000/health ; echo`
Expected: phản hồi health JSON. Ghi lại. Sau đó tắt: `pkill -f "uvicorn main:app" || true`.

- [ ] **Step 4: Một lượt pipeline thật trên mẫu nhỏ (quan sát multi-agent)**

Đọc `pipeline/ingest.py` để biết cách nạp batch nhỏ; chạy ingest→clean→classify trên ≤20 bản ghi seed (dùng `data/`), rồi gọi orchestrator một lượt nếu khả thi.
Run (ví dụ, điều chỉnh theo chữ ký thật): `cd pipeline && python -c "import ingest, clean, classifier; print('modules import OK')"`
Expected: import OK + (nếu chạy được) log các agent chạy. Ghi lại agent nào thực thi; KHÔNG nguỵ tạo nếu không chạy được — ghi lý do.

- [ ] **Step 5: Smoke build frontend**

Run: `cd app && bun install --frozen-lockfile 2>&1 | tail -5 ; bun run build 2>&1 | tail -15`
Expected: build thành công (hoặc ghi lỗi thật). Nếu không có `bun`, thử `npm run build` và ghi lại.

- [ ] **Step 6: Ghi ground truth + bằng chứng vào eval-evidence.md**

Thêm dưới tiêu đề H1 của `docs/project/eval-evidence.md`:

```markdown
> **Cập nhật 2026-06-27:** Bổ sung bằng chứng e2e thật (pytest, eval router/model, health, pipeline smoke, frontend build).

## Bằng chứng e2e — 2026-06-27

**Ground truth đã xác minh từ code:**
- 6 phòng ban: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
- Agent: 8 nghiệp vụ (*_agent.py) + Orchestrator + report_builder (helper).
- RAG hybrid: Cohere embed-multilingual-v3.0 + BM25-lite + RRF (k=60).
- 4 worker: ticket/ingest/ml/agent; API scheduler on-demand.

**Kết quả chạy:**
- pytest: <dán số liệu thật>
- route_eval / evaluate_model: <dán accuracy/F1 thật>
- /health: <dán phản hồi>
- pipeline smoke: <dán log/agent thực thi hoặc lý do skip>
- frontend build: <pass/lỗi thật>
```

Thay `<...>` bằng output thật từ các step trên.

- [ ] **Step 7: Commit**

```bash
git add docs/project/eval-evidence.md
git commit -m "docs(evidence): bằng chứng e2e thật + ground truth 2026-06-27"
```

---

### Task 2: Doc kiến trúc & luồng (architecture + e2e-flow + routing)

**Files:**
- Modify: `docs/project/architecture.md`
- Modify: `docs/project/architecture-diagram.md`
- Modify: `docs/project/architecture/e2e-flow.md`
- Modify: `docs/project/architecture/routing-taxonomy.md`

**Interfaces:**
- Consumes: ground truth Task 1; danh sách 12 luồng trong spec Mục 2.
- Produces: `architecture/e2e-flow.md` là doc luồng quyền uy, khớp 12 luồng.

- [ ] **Step 1: Tìm stale trong nhóm kiến trúc**

Run: `grep -rniE "marketing|chỉ keyword|keyword[- ]only|4 phòng|bốn phòng|ingest/|analytics/|10 agent|6 agent" docs/project/architecture.md docs/project/architecture-diagram.md docs/project/architecture/`
Expected: liệt kê các dòng stale (phòng ban cũ, RAG keyword-only, cấu trúc thư mục sai, số agent sai). Đây là "failing test".

- [ ] **Step 2: Đối chiếu sơ đồ luồng với code**

Đọc `pipeline/main.py`, `pipeline/agents/orchestrator.py`, `pipeline/worker_*.py`. Xác nhận sơ đồ trong `architecture-diagram.md` & `e2e-flow.md` khớp: ingest→clean→classify→rules→spike→orchestrator(8 agent)→report/ticket/task; 4 worker; chat+hybrid RAG.

- [ ] **Step 3: Sửa các doc theo ground truth**

Sửa từng dòng stale tìm được: phòng ban → 6 phòng (Global Constraints); RAG → hybrid Cohere+BM25+RRF; cấu trúc pipeline → file phẳng + `agent/` + `agents/`; số agent → "8 nghiệp vụ + Orchestrator". Đảm bảo `e2e-flow.md` liệt kê đủ 12 luồng theo spec Mục 2.

- [ ] **Step 4: Thêm ghi chú "Cập nhật 2026-06-27" vào mỗi file đã sửa**

Đặt ngay dưới H1 mỗi file: `> **Cập nhật 2026-06-27:** đồng bộ 6 phòng ban, RAG hybrid, roster agent, cấu trúc pipeline với code.`

- [ ] **Step 5: Xác minh grep sạch**

Run: `grep -rniE "marketing|chỉ keyword|4 phòng|bốn phòng|analytics/|10 agent|6 agent" docs/project/architecture.md docs/project/architecture-diagram.md docs/project/architecture/`
Expected: KHÔNG còn dòng stale (trừ khi cố ý nhắc lịch sử trong ngữ cảnh "trước đây"). 

- [ ] **Step 6: Commit**

```bash
git add docs/project/architecture.md docs/project/architecture-diagram.md docs/project/architecture/
git commit -m "docs(arch): đồng bộ kiến trúc & luồng e2e với code (6 phòng, RAG hybrid, 8 agent)"
```

---

### Task 3: Doc cơ chế & giải thích (co_che + giai_thich)

**Files:**
- Modify: `docs/project/co_che.md` (41KB)
- Modify: `docs/project/giai_thich.md` (24KB)

**Interfaces:**
- Consumes: ground truth Task 1; sơ đồ luồng đã chuẩn ở Task 2.
- Produces: hai doc narrative khớp 12 luồng & canonical facts.

- [ ] **Step 1: Tìm stale**

Run: `grep -niE "marketing|chỉ dùng keyword|keyword[- ]only|4 phòng|bốn phòng|10 agent|6 agent|ingest/|analytics/" docs/project/co_che.md docs/project/giai_thich.md`
Expected: liệt kê dòng stale.

- [ ] **Step 2: Đối chiếu mô tả luồng với code**

Với mỗi luồng được hai doc mô tả (đặc biệt: scoring 5 chiều, spike→ticket, multi-agent, báo cáo phòng ban 3 khối, chat tiered RAG, task loop), mở file code tương ứng (spec Mục 2) và xác nhận mô tả đúng. Sửa chỗ lệch.

- [ ] **Step 3: Sửa theo ground truth + thêm ghi chú**

Sửa các dòng stale; thêm dưới H1 mỗi file: `> **Cập nhật 2026-06-27:** đồng bộ 6 phòng ban, RAG hybrid, roster agent với code hoàn thiện.`

- [ ] **Step 4: Xác minh grep sạch**

Run: `grep -niE "marketing|keyword[- ]only|4 phòng|bốn phòng|10 agent|6 agent|analytics/" docs/project/co_che.md docs/project/giai_thich.md`
Expected: không còn stale ngoài ngữ cảnh lịch sử.

- [ ] **Step 5: Commit**

```bash
git add docs/project/co_che.md docs/project/giai_thich.md
git commit -m "docs(cơ chế): đồng bộ co_che & giai_thich với code"
```

---

### Task 4: Doc agent & hệ AI (agents-guide + ai-systems)

**Files:**
- Modify: `docs/project/agents-guide.md`
- Modify: `docs/project/ai-systems.md`

**Interfaces:**
- Consumes: roster agent (Global Constraints), RAG hybrid, model router.
- Produces: doc agent/AI khớp `pipeline/agents/` và `pipeline/agent/`.

- [ ] **Step 1: Liệt kê roster thật từ code**

Run: `ls pipeline/agents/*_agent.py | xargs -n1 basename ; echo '---' ; ls pipeline/agent/*.py | xargs -n1 basename`
Expected: 8 `*_agent.py` + (orchestrator, report_builder); và `chat_agent, chat_tools, knowledge_base, model_router, public_kb, rag_engine`.

- [ ] **Step 2: Tìm stale**

Run: `grep -niE "10 agent|6 agent|9 agent|marketing|chỉ keyword|keyword[- ]only" docs/project/agents-guide.md docs/project/ai-systems.md`
Expected: liệt kê dòng cần sửa.

- [ ] **Step 3: Sửa theo ground truth + ghi chú**

Đảm bảo: liệt kê đúng 8 agent nghiệp vụ + Orchestrator + report_builder; mô tả RAG hybrid (Cohere+BM25+RRF); model router phân tầng. Thêm dưới H1: `> **Cập nhật 2026-06-27:** đồng bộ roster agent & RAG hybrid với code.`

- [ ] **Step 4: Xác minh**

Run: `grep -niE "10 agent|6 agent|9 agent|marketing|keyword[- ]only" docs/project/agents-guide.md docs/project/ai-systems.md`
Expected: không còn stale.

- [ ] **Step 5: Commit**

```bash
git add docs/project/agents-guide.md docs/project/ai-systems.md
git commit -m "docs(ai): đồng bộ roster agent & RAG hybrid"
```

---

### Task 5: Data model vs migrations

**Files:**
- Modify: `docs/project/data-model.md` (22KB)

**Interfaces:**
- Consumes: schema thật trong `supabase/` migrations.
- Produces: data-model khớp bảng/cột/RLS thật.

- [ ] **Step 1: Liệt kê migrations & bảng thật**

Run: `find supabase -name "*.sql" | sort ; echo '---tables---' ; grep -rhiE "create table|alter table .* add column" supabase --include=*.sql | head -60`
Expected: danh sách bảng/cột thật (gồm các bảng task/report/correction mới).

- [ ] **Step 2: Tìm bảng/cột nêu trong doc nhưng không có trong migration (và ngược lại)**

Đọc `docs/project/data-model.md`, đối chiếu từng bảng với output Step 1. Ghi ra danh sách lệch (bảng thiếu/thừa, cột đổi tên, phòng ban enum).

- [ ] **Step 3: Sửa data-model theo schema thật + ghi chú**

Cập nhật bảng/cột/enum (đặc biệt enum phòng ban 6 giá trị, bảng task-completion-loop & report-approval & correction-log). Thêm dưới H1: `> **Cập nhật 2026-06-27:** đồng bộ với migrations Supabase (6 phòng, task/report/correction).`

- [ ] **Step 4: Xác minh enum phòng ban & bảng mới**

Run: `grep -niE "marketing|4 phòng" docs/project/data-model.md ; grep -rniE "task_events|report.*approval|correction" supabase --include=*.sql | head`
Expected: doc không còn 4-phòng/Marketing; bảng task/report/correction có trong cả doc lẫn migration.

- [ ] **Step 5: Commit**

```bash
git add docs/project/data-model.md
git commit -m "docs(data-model): đồng bộ schema với migrations Supabase"
```

---

### Task 6: RBAC, phòng ban & guest

**Files:**
- Modify: `docs/project/rbac-departments.md`
- Modify: `docs/project/guest-account.md`

**Interfaces:**
- Consumes: `pipeline/auth_guard.py`, `pipeline/departments.py`, RLS migrations, chat tiering (`pipeline/agent/chat_tools.py`).
- Produces: doc RBAC khớp 4 vai trò + 6 phòng + phân tầng chat guest/staff.

- [ ] **Step 1: Tìm stale**

Run: `grep -niE "marketing|4 phòng|bốn phòng" docs/project/rbac-departments.md docs/project/guest-account.md`
Expected: liệt kê dòng stale phòng ban.

- [ ] **Step 2: Đối chiếu vai trò & scope với code**

Đọc `pipeline/auth_guard.py` (4 vai trò, scope phòng ban) và `pipeline/agent/chat_tools.py` (Guest: Public FAQ / Staff: Internal Ops Tools). Xác nhận doc khớp.

- [ ] **Step 3: Sửa + ghi chú**

Cập nhật danh sách 6 phòng ban & phân tầng chat. Thêm dưới H1 mỗi file: `> **Cập nhật 2026-06-27:** đồng bộ 6 phòng ban & phân tầng quyền chat.`

- [ ] **Step 4: Xác minh**

Run: `grep -niE "marketing|4 phòng|bốn phòng" docs/project/rbac-departments.md docs/project/guest-account.md`
Expected: không còn stale.

- [ ] **Step 5: Commit**

```bash
git add docs/project/rbac-departments.md docs/project/guest-account.md
git commit -m "docs(rbac): đồng bộ 6 phòng ban & phân tầng chat guest/staff"
```

---

### Task 7: Setup & deploy (macos/windows/supabase/railway)

**Files:**
- Modify: `docs/project/setup-macos.md`
- Modify: `docs/project/setup-windows.md`
- Modify: `docs/project/setup-supabase.md`
- Modify: `docs/project/deploy-railway.md`

**Interfaces:**
- Consumes: `.env.example`, `docker-compose.yml`, `railway.json`, `pipeline/requirements.txt`, `app/package.json`.
- Produces: hướng dẫn setup/deploy chạy được, env-var khớp `.env.example`.

- [ ] **Step 1: Liệt kê env-var thật & dịch vụ Railway**

Run: `grep -vE '^\s*#|^\s*$' .env.example | sed -E 's/=.*//' | sort ; echo '---' ; cat railway.json`
Expected: danh sách key thật (gồm COHERE_API_KEY, OPENROUTER_*, LIVE_STREAM_*, AUTO_TICKET_*).

- [ ] **Step 2: Đối chiếu doc với env thật & lệnh build**

Đọc 4 file. Tìm env-var nêu trong doc nhưng không có trong `.env.example` (hoặc ngược lại); kiểm tra lệnh cài (bun/npm, pip) khớp `app/package.json` & `pipeline/requirements.txt`. Memory: 6 service Railway nối GitHub auto-deploy — đảm bảo deploy-railway.md phản ánh đúng (không cần `railway up` thủ công cho luồng chính).

- [ ] **Step 3: Sửa + ghi chú**

Cập nhật env-var/lệnh; thêm key thiếu (đặc biệt COHERE_API_KEY cho RAG). Thêm dưới H1 mỗi file: `> **Cập nhật 2026-06-27:** đồng bộ env-var (.env.example) & luồng deploy.`

- [ ] **Step 4: Xác minh không thiếu key RAG/Cohere**

Run: `grep -li cohere docs/project/setup-*.md docs/project/deploy-railway.md`
Expected: ít nhất setup chính/deploy nhắc COHERE_API_KEY.

- [ ] **Step 5: Commit**

```bash
git add docs/project/setup-macos.md docs/project/setup-windows.md docs/project/setup-supabase.md docs/project/deploy-railway.md
git commit -m "docs(setup): đồng bộ env-var & luồng deploy Railway"
```

---

### Task 8: Product, demo, roadmap

**Files:**
- Modify: `docs/project/product/README.md`
- Modify: `docs/project/demo-script.md`
- Modify: `docs/project/roadmap.md`

**Interfaces:**
- Consumes: danh sách tính năng thật (README gốc + code), 12 luồng.
- Produces: product/demo/roadmap phản ánh trạng thái "đã hoàn thành".

- [ ] **Step 1: Tìm stale & việc "đã xong nhưng vẫn ghi TODO"**

Run: `grep -niE "marketing|4 phòng|TODO|chưa làm|sắp tới|dự kiến" docs/project/product/README.md docs/project/demo-script.md docs/project/roadmap.md`
Expected: liệt kê mục cần cập nhật (tính năng đã hoàn thành: task loop, HI-loop, hybrid RAG, 6 phòng).

- [ ] **Step 2: Đối chiếu tính năng với README gốc (đã cập nhật)**

So với bảng "Tính năng" trong `README.md` (11 tính năng). Chuyển các mục roadmap đã hoàn thành sang "Đã xong"; demo-script phản ánh luồng demo thật.

- [ ] **Step 3: Sửa + ghi chú**

Thêm dưới H1 mỗi file: `> **Cập nhật 2026-06-27:** phản ánh trạng thái hoàn thành (task loop, HI-loop, hybrid RAG, 6 phòng).`

- [ ] **Step 4: Xác minh**

Run: `grep -niE "marketing|4 phòng" docs/project/product/README.md docs/project/demo-script.md docs/project/roadmap.md`
Expected: không còn stale.

- [ ] **Step 5: Commit**

```bash
git add docs/project/product/README.md docs/project/demo-script.md docs/project/roadmap.md
git commit -m "docs(product): phản ánh trạng thái hoàn thành"
```

---

### Task 9: Chỉ mục docs/project + README gốc + app/flow.md (optional)

**Files:**
- Create/Modify: `docs/project/README.md` (chỉ mục điều hướng — tạo nếu chưa có)
- Modify: `README.md` (gốc — chỉ sửa drift đã flag, nếu có)
- Modify: `app/flow.md` (optional — cấu trúc thư mục sai)

**Interfaces:**
- Consumes: toàn bộ doc đã đối soát Task 2–8.
- Produces: một điểm vào điều hướng đúng cho `docs/project`.

- [ ] **Step 1: Kiểm tra README gốc có drift còn lại không**

Run: `grep -niE "10 agent|9 agent|6 agent|marketing|4 phòng|chỉ keyword" README.md`
Expected: nếu có dòng nào → sửa cho khớp Global Constraints; nếu sạch → bỏ qua phần README gốc (đã đúng).

- [ ] **Step 2: Sửa app/flow.md (optional)**

Đọc `app/flow.md`. Thay khối cấu trúc `pipeline/ingest|clean|ml|analytics|agent/` (sai) bằng cấu trúc thật: file phẳng (`ingest.py`, `clean.py`, `classifier.py`, `rules.py`, `spike_detector.py`, `llm_agent.py`, `main.py`, `worker_*.py`) + thư mục `agent/` (chat+RAG) + `agents/` (orchestrator + 8 agent + report_builder). Thêm ghi chú `> **Cập nhật 2026-06-27:** sửa cấu trúc pipeline cho khớp code.` Nếu quyết định bỏ qua, ghi 1 dòng lý do trong commit message thay vì sửa.

- [ ] **Step 3: Tạo/cập nhật chỉ mục docs/project/README.md**

Viết/cập nhật chỉ mục liệt kê & mô tả 1 dòng cho mỗi doc trong `docs/project`, nhóm theo: Kiến trúc & Luồng / Cơ chế & AI / Dữ liệu & RBAC / Setup & Deploy / Product. Thêm dưới H1: `> **Cập nhật 2026-06-27:** chỉ mục điều hướng sau đối soát toàn bộ docs/project.`

- [ ] **Step 4: Xác minh toàn cục — không còn stale chéo**

Run: `grep -rniE "marketing|chỉ keyword|keyword[- ]only|bốn phòng|10 agent" docs/project | grep -viE "trước đây|lịch sử|cập nhật"`
Expected: rỗng (mọi nhắc tới chỉ trong ngữ cảnh lịch sử). Nếu còn → quay lại task tương ứng sửa nốt.

- [ ] **Step 5: Commit**

```bash
git add docs/project/README.md README.md app/flow.md
git commit -m "docs(index): chỉ mục docs/project + sửa app/flow.md cấu trúc pipeline"
```

---

## Self-Review (đã chạy khi viết plan)

- **Spec coverage:** Mục 1 spec→Task 1; Mục 2 (12 luồng)→Task 2 (e2e-flow là nguồn quyền uy) + tham chiếu xuyên Task 3–6; Mục 3 (4 drift)→agent roster (Task 4/9), 6 phòng (Task 2–8), RAG hybrid (Task 2–4,7), app/flow.md (Task 9); Mục 4 (e2e thật)→Task 1; Mục 5 (sửa tại chỗ + ghi chú + README index)→mọi task có bước ghi chú + Task 9 index; Mục 6 acceptance→bước "Xác minh grep sạch" mỗi task + Step 4 Task 9 toàn cục; Mục 7 non-goals→Global Constraints.
- **Placeholder scan:** Các `<...>` trong Task 1 Step 6 là chỗ dán **output thật** (có hướng dẫn rõ), không phải placeholder mơ hồ. Không có "TODO/implement later" trong hành động.
- **Type/identifier consistency:** Tên file code (`*_agent.py`, `rag_engine.py`, `departments.py`, `worker_*.py`), danh sách 6 phòng ban, và cụm "8 agent nghiệp vụ + Orchestrator + report_builder" dùng nhất quán giữa Global Constraints và mọi task.
