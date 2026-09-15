> **Cập nhật 2026-06-27:** sửa cấu trúc pipeline cho khớp code.

AI-Quality-Intelligence-Platform/
│
├── 🔒 [KHUNG HẠ TẦNG — KHÔNG ĐỘNG]
│   ├── scripts/                    # logging AI usage (local) — giữ nguyên
│   │   ├── _pyrun.sh / .cmd
│   │   ├── log_hook.py / log_antigravity.py / log_manual.py
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
├── 🐍 pipeline/                    # BACKEND xử lý: module phẳng + 2 thư mục agent
│   ├── ingest.py                   # đọc batch phản hồi vào feedback_raw
│   ├── clean.py                    # dedup, PII mask, chuẩn hóa text
│   ├── classifier.py               # TF-IDF + LinearSVC: gán topic + severity
│   ├── rules.py                    # rule cứng severity override
│   ├── spike_detector.py           # SQL aggregate 1h-vs-7d, sinh alert
│   ├── llm_agent.py                # LLM xử lý ca khó, sinh ticket JSON
│   ├── main.py                     # pipeline orchestrator (batch)
│   ├── worker_ticket.py            # worker xử lý ticket queue
│   ├── worker_ingest.py            # worker nhận ingest stream
│   ├── worker_ml.py                # worker chạy ML classify
│   ├── worker_agent.py             # worker gọi multi-agent pipeline
│   ├── departments.py              # registry 6 phòng ban + routing map
│   ├── auth_guard.py               # RBAC guard cho pipeline endpoints
│   ├── agent/                      # Chat + RAG (AI chat endpoint)
│   │   ├── chat_agent.py           # xử lý turn chat
│   │   ├── chat_tools.py           # tool definitions cho chat
│   │   ├── rag_engine.py           # RAG hybrid: Cohere embed + BM25 + RRF k=60
│   │   ├── knowledge_base.py       # KB nội bộ (embed + retrieve)
│   │   ├── public_kb.py            # KB công khai (khách guest)
│   │   └── model_router.py         # chọn model theo context
│   ├── agents/                     # Multi-agent nghiệp vụ (8 agent + Orchestrator + helper)
│   │   ├── orchestrator.py         # Orchestrator: chia việc cho 8 agent nghiệp vụ
│   │   ├── router_agent.py         # Router: định tuyến phòng ban
│   │   ├── ingestion_agent.py      # Ingest: tiếp nhận, làm sạch phản hồi
│   │   ├── scoring_agent.py        # Scoring: tính 5-dim risk score
│   │   ├── analyst_agent.py        # Analyst: phân tích, đề xuất hành động
│   │   ├── insight_agent.py        # Insight: xu hướng tổng hợp
│   │   ├── alert_agent.py          # Alert: phát hiện spike, sinh cảnh báo
│   │   ├── task_agent.py           # Task: tạo và giao task phòng ban
│   │   ├── ticket_agent.py         # Ticket: sinh ticket chính thức
│   │   └── report_builder.py       # Helper: tổng hợp báo cáo
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
