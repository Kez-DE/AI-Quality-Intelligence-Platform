C2-App-116/
│
├── 🔒 [KHUNG COHORT — KHÔNG ĐỘNG]
│   ├── scripts/                    # logging AI usage — giữ nguyên
│   │   ├── _pyrun.sh / .cmd
│   │   ├── setup_hooks.sh / .ps1
│   │   ├── log_hook.py / log_antigravity.py / log_manual.py
│   │   └── submit_log.py
│   ├── .claude/ .codex/ .cursor/ .gemini/ .github/hooks/  # hook configs
│   ├── .agents/                    # Antigravity rules
│   ├── .env.example                # mở rộng thêm key dự án (xem dưới)
│   ├── JOURNAL.md                  # cập nhật cuối mỗi tuần
│   └── WORKLOG.md                  # cập nhật mỗi quyết định kỹ thuật
│
├── 📱 app/                         # FRONTEND — xanh_iu chuyển vào đây
│   ├── src/
│   │   ├── components/             # QualityCockpit, ui/...
│   │   ├── routes/_authenticated/  # dashboard, feedback, alerts,
│   │   │                           #   tickets, chat
│   │   ├── integrations/supabase/  # client, types
│   │   └── lib/                    # ai.functions.ts (chatbot RAG)
│   ├── package.json
│   └── vite.config.ts
│
├── 🐍 pipeline/                    # BACKEND xử lý — Python
│   ├── ingest/
│   │   └── load_batch.py           # đọc seed → feedback_raw
│   ├── clean/
│   │   └── preprocess.py           # dedup, PII mask, chuẩn hóa
│   ├── ml/
│   │   ├── label_with_llm.py       # LLM gán nhãn train data (1 lần)
│   │   ├── train.py                # train TF-IDF + LinearSVC
│   │   ├── classify.py             # inference + severity rule
│   │   └── model.joblib            # artifact đã train
│   ├── analytics/
│   │   └── spike.py                # SQL aggregate 1h-vs-7d → alert
│   ├── agent/
│   │   ├── router.py               # routing table (rule cứng)
│   │   ├── llm_agent.py            # LLM quyết ca khó → ticket JSON
│   │   └── guardrails.py           # Safety override, confidence gate
│   ├── db/
│   │   └── supabase_client.py      # ghi raw/processed/alerts/tickets
│   ├── run_batch.py                # ★ ORCHESTRATOR — nút bấm demo
│   ├── requirements.txt
│   └── .env                        # key pipeline (gitignore)
│
├── 🗄️ supabase/
│   └── migrations/                 # schema 6 bảng
│       ├── 0001_core_schema.sql
│       ├── 0002_processed_alerts_tickets.sql
│       └── 0003_correction_logs.sql
│
├── 📦 data/
│   ├── seed_demo.json              # 150 đánh giá demo (cắm spike Safety)
│   ├── seed_train.json             # ~1000 mẫu để train classifier
│   └── taxonomy.json               # 10 nhóm + keyword Safety
│
├── 📄 docs/
│   ├── architecture.md             # sơ đồ luồng demo + production
│   ├── data-provenance.md          # nguồn dữ liệu (synthetic/review)
│   └── demo-script.md              # kịch bản 5 phút
│
├── .gitignore                      # node_modules, .venv, *.joblib lớn, .env
└── README.md                       # mở rộng: cách chạy app + pipeline