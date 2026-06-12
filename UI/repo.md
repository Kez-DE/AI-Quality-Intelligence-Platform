C2-App-116/
│
├═══════════════════════════════════════════════════════════════════
│  🔒 KHUNG COHORT — KHÔNG ĐỘNG (tài sản chấm điểm)
├═══════════════════════════════════════════════════════════════════
│
├── scripts/                          # logging AI usage — giữ nguyên 100%
│   ├── _pyrun.sh  _pyrun.cmd          # launcher Python đa nền tảng
│   ├── setup_hooks.sh  setup_hooks.ps1
│   ├── log_hook.py  log_antigravity.py  log_manual.py
│   └── submit_log.py                 # gửi log khi git push
│
├── .claude/  .codex/  .cursor/  .gemini/  .github/hooks/  .agents/
│                                      # hook config per-tool — giữ nguyên
│
├── .env.example                      # 🟡 MỞ RỘNG (thêm key dự án, xem §dưới)
├── JOURNAL.md                        # cập nhật cuối mỗi tuần (bắt buộc trước PR)
├── WORKLOG.md                        # cập nhật mỗi quyết định kỹ thuật
│
├═══════════════════════════════════════════════════════════════════
│  📱 app/  — FRONTEND (TypeScript, xanh_iu chuyển vào)
├═══════════════════════════════════════════════════════════════════
│
├── app/
│   ├── src/
│   │   ├── components/
│   │   │   ├── QualityCockpit.tsx     # dashboard chính (sửa: đọc DB thật)
│   │   │   ├── AppShell.tsx           # layout + sidebar nav
│   │   │   ├── charts/                # 🆕 component biểu đồ tách riêng
│   │   │   │   ├── TrendChart.tsx     #    xu hướng feedback theo ngày
│   │   │   │   ├── AreaHeatmap.tsx    #    heatmap khu vực
│   │   │   │   └── SeverityDonut.tsx  #    phân bố mức nghiêm trọng
│   │   │   └── ui/                    # shadcn components (giữ nguyên)
│   │   │
│   │   ├── routes/_authenticated/
│   │   │   ├── route.tsx              # guard auth (giữ)
│   │   │   ├── dashboard.tsx          # 📊 KPI + trend + heatmap (DB thật)
│   │   │   ├── feedback.tsx           # 📝 danh sách phản hồi đã phân loại
│   │   │   ├── alerts.tsx             # 🚨 cảnh báo spike + evidence
│   │   │   ├── tickets.tsx            # 🎫 queue theo phòng ban + SLA
│   │   │   ├── review.tsx             # 🟡 HITL — duyệt/sửa nhãn AI
│   │   │   ├── corrections.tsx        # 📜 nhật ký correction_log
│   │   │   ├── driver-inbox.tsx       # 📲 mô phỏng notify tài xế
│   │   │   └── chat.tsx               # 💬 chatbot RAG
│   │   │
│   │   ├── integrations/supabase/
│   │   │   ├── client.ts              # client (publishable key — đọc)
│   │   │   ├── auth-middleware.ts     # verify Bearer token (giữ)
│   │   │   └── types.ts               # 🟡 REGEN sau khi đổi schema
│   │   │
│   │   ├── lib/
│   │   │   ├── ai.functions.ts        # 🟡 chatbot RAG (sửa: query DB trước LLM)
│   │   │   ├── queries.ts             # 🆕 các hàm đọc Supabase (KPI, spike...)
│   │   │   └── config.server.ts       # config server-only
│   │   │
│   │   ├── router.tsx  routeTree.gen.ts  styles.css
│   │   │
│   │   ├── package.json  bun.lock     # 🟢 COMMIT (pin version)
│   │   ├── vite.config.ts  tsconfig.json
│   │   └── components.json
│   │
├═══════════════════════════════════════════════════════════════════
│  🐍 pipeline/  — BACKEND xử lý (Python)
├═══════════════════════════════════════════════════════════════════
│
├── pipeline/
│   ├── ingest/
│   │   ├── scrape_reviews.py          # cào App Store + Play → seed_real.json
│   │   ├── generate_synthetic.py      # sinh synthetic (taxonomy 10 nhóm)
│   │   └── load_batch.py              # đọc seed → ghi feedback_raw
│   │
│   ├── clean/
│   │   └── preprocess.py              # dedup, PII mask (regex), chuẩn hóa
│   │
│   ├── ml/
│   │   ├── label_with_llm.py          # LLM gán nhãn train data (chạy 1 lần)
│   │   ├── train.py                   # train TF-IDF + LinearSVC → model.joblib
│   │   ├── classify.py                # inference + severity rule + confidence
│   │   ├── taxonomy.py                # 10 nhóm + keyword Safety (hardcode)
│   │   └── model.joblib              # 🟢 COMMIT (demo reproducible, vài MB)
│   │
│   ├── analytics/
│   │   └── spike.py                   # SQL aggregate 1h-vs-7d → sinh alert
│   │
│   ├── agent/
│   │   ├── router.py                  # routing table (rule cứng topic→team)
│   │   ├── llm_agent.py               # LLM quyết ca khó → ticket JSON (tầng-2)
│   │   ├── guardrails.py              # Safety override, confidence gate, HITL
│   │   └── schemas.py                 # Pydantic schema validate output LLM
│   │
│   ├── driver/
│   │   └── notify.py                  # phân tầng 4 mức → driver_notifications
│   │
│   ├── db/
│   │   ├── supabase_client.py         # kết nối (service_role — ghi DB)
│   │   └── writers.py                 # hàm ghi raw/processed/alerts/tickets
│   │
│   ├── run_batch.py                   # ★ ORCHESTRATOR — nút bấm demo
│   ├── requirements.txt               # 🟢 COMMIT
│   ├── .env                           # 🔴 GITIGNORE (secret)
│   └── README.md                      # cách chạy pipeline
│
├═══════════════════════════════════════════════════════════════════
│  🗄️ supabase/  — Schema (SQL migrations)
├═══════════════════════════════════════════════════════════════════
│
├── supabase/
│   ├── config.toml
│   └── migrations/                    # 🟢 COMMIT
│       ├── 0001_core_schema.sql           # profiles, feedback_raw
│       ├── 0002_processed.sql             # feedback_processed
│       ├── 0003_alerts_tickets.sql        # alerts, tickets
│       ├── 0004_correction_logs.sql       # correction_logs (HITL)
│       ├── 0005_driver_notifications.sql  # driver_notifications + risk_scores
│       └── 0006_views.sql                 # view tổng hợp cho dashboard
│
├═══════════════════════════════════════════════════════════════════
│  📦 data/  — Dữ liệu (input pipeline)
├═══════════════════════════════════════════════════════════════════
│
├── data/
│   ├── seed_real.json                 # 🟢 review thật cào từ store (snapshot)
│   ├── seed_synthetic.json            # 🟢 synthetic (nhóm Safety + metadata)
│   ├── seed_demo.json                 # 🟢 150 đánh giá demo (trộn + cắm spike)
│   ├── seed_train.json                # 🟢 ~1000 mẫu train classifier
│   ├── taxonomy.json                  # 🟢 10 nhóm + keyword + routing table
│   └── output/.gitkeep                # 🔴 output runtime ignore, giữ thư mục
│
├═══════════════════════════════════════════════════════════════════
│  📄 docs/  — Tài liệu
├═══════════════════════════════════════════════════════════════════
│
├── docs/
│   ├── architecture.md                # sơ đồ luồng demo + production, 3 kênh
│   ├── hitl-and-learning.md           # luồng HITL + correction loop
│   ├── data-provenance.md             # nguồn dữ liệu (chống overclaim)
│   ├── agent-design.md                # routing table + guardrail + schema
│   └── demo-script.md                 # kịch bản 5 phút
│
├── .gitignore                         # (bản đầy đủ §dưới)
└── README.md                          # 🟡 MỞ RỘNG: chạy app + pipeline