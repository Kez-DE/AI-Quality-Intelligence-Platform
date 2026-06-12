C2-App-116/
│
├── scripts/                              # Cohort AI logging — KHÔNG ĐỘNG
│   ├── _pyrun.sh
│   ├── _pyrun.cmd
│   ├── setup_hooks.sh
│   ├── setup_hooks.ps1
│   ├── log_hook.py
│   ├── log_antigravity.py
│   ├── log_manual.py
│   └── submit_log.py
│
├── .claude/                              # Cohort hook config — giữ nguyên
├── .codex/
├── .cursor/
├── .gemini/
├── .github/
│   └── hooks/
├── .agents/
│
├── JOURNAL.md                            # Nhật ký học tập/team
├── WORKLOG.md                            # Quyết định kỹ thuật
├── .env.example                          # Template env chung
├── .gitignore
├── README.md
│
├── app/                                  # Frontend xanh_iu — TypeScript/React
│   │
│   ├── package.json
│   ├── bun.lock
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── components.json
│   ├── bunfig.toml
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── router.tsx
│   │   ├── routeTree.gen.ts
│   │   ├── styles.css
│   │   │
│   │   ├── components/
│   │   │   ├── AppShell.tsx
│   │   │   ├── QualityCockpit.tsx
│   │   │   ├── MomoChat.tsx
│   │   │   ├── RagApp.tsx
│   │   │   │
│   │   │   ├── charts/
│   │   │   │   ├── KpiCards.tsx
│   │   │   │   ├── TrendChart.tsx
│   │   │   │   ├── AreaHeatmap.tsx
│   │   │   │   ├── TopicDistribution.tsx
│   │   │   │   ├── SeverityDonut.tsx
│   │   │   │   └── SlaStatusBar.tsx
│   │   │   │
│   │   │   ├── feedback/
│   │   │   │   ├── FeedbackTable.tsx
│   │   │   │   ├── FeedbackDetailDrawer.tsx
│   │   │   │   └── EvidenceList.tsx
│   │   │   │
│   │   │   ├── alerts/
│   │   │   │   ├── AlertList.tsx
│   │   │   │   ├── AlertDetail.tsx
│   │   │   │   └── AlertSeverityBadge.tsx
│   │   │   │
│   │   │   ├── tickets/
│   │   │   │   ├── TicketQueue.tsx
│   │   │   │   ├── TicketCard.tsx
│   │   │   │   ├── TicketDetail.tsx
│   │   │   │   ├── TeamFilter.tsx
│   │   │   │   └── SlaBadge.tsx
│   │   │   │
│   │   │   ├── review/
│   │   │   │   ├── ReviewQueue.tsx
│   │   │   │   ├── ReviewItem.tsx
│   │   │   │   ├── LabelCorrectionForm.tsx
│   │   │   │   └── CorrectionHistory.tsx
│   │   │   │
│   │   │   ├── driver/
│   │   │   │   ├── DriverInbox.tsx
│   │   │   │   ├── DriverNotificationCard.tsx
│   │   │   │   └── DriverRiskPanel.tsx
│   │   │   │
│   │   │   └── ui/
│   │   │       └── ...shadcn components
│   │   │
│   │   ├── routes/
│   │   │   ├── __root.tsx
│   │   │   ├── auth.tsx
│   │   │   ├── index.tsx
│   │   │   │
│   │   │   └── _authenticated/
│   │   │       ├── route.tsx                  # Auth guard
│   │   │       ├── dashboard.tsx              # KPI, trend, heatmap
│   │   │       ├── feedback.tsx               # Feedback raw/processed
│   │   │       ├── alerts.tsx                 # Alert spike + evidence
│   │   │       ├── tickets.tsx                # Ticket queue theo phòng ban
│   │   │       ├── review.tsx                 # Human-in-the-loop queue
│   │   │       ├── corrections.tsx            # Correction logs
│   │   │       ├── driver-inbox.tsx           # Mock inbox tài xế
│   │   │       └── chat.tsx                   # Chatbot/RAG insight
│   │   │
│   │   ├── integrations/
│   │   │   └── supabase/
│   │   │       ├── client.ts
│   │   │       ├── client.server.ts
│   │   │       ├── auth-middleware.ts
│   │   │       └── types.ts
│   │   │
│   │   ├── lib/
│   │   │   ├── ai.functions.ts                # Chatbot server function
│   │   │   ├── queries.ts                     # Supabase read queries
│   │   │   ├── dashboard.queries.ts
│   │   │   ├── tickets.queries.ts
│   │   │   ├── review.queries.ts
│   │   │   ├── config.server.ts
│   │   │   └── utils.ts
│   │   │
│   │   └── hooks/
│   │       ├── use-mobile.tsx
│   │       ├── useDashboardData.ts
│   │       ├── useTickets.ts
│   │       └── useReviewQueue.ts
│   │
│   └── README.md
│
├── pipeline/                              # Python pipeline — backend xử lý batch
│   │
│   ├── requirements.txt
│   ├── README.md
│   ├── .env                               # Gitignore
│   ├── run_batch.py                       # Orchestrator chính cho demo
│   ├── run_scrape.py                      # Cào review store
│   ├── run_train.py                       # Train/retrain classifier
│   ├── run_agent_on_alerts.py             # Chạy agent riêng trên alert đã có
│   │
│   ├── config/
│   │   ├── settings.py                    # Load env/config
│   │   ├── constants.py                   # Threshold, SLA, teams
│   │   └── logging_config.py              # Python logging setup
│   │
│   ├── ingest/
│   │   ├── scrape_google_play.py          # Cào Google Play
│   │   ├── scrape_app_store.py            # Cào Apple App Store
│   │   ├── scrape_reviews.py              # Wrapper gọi cả 2 nguồn
│   │   ├── generate_synthetic.py          # Sinh synthetic feedback
│   │   ├── mix_seed_data.py               # Trộn real + synthetic
│   │   ├── load_batch.py                  # Load seed_demo → feedback_raw
│   │   └── normalizers.py                 # Chuẩn hóa field 2 store
│   │
│   ├── clean/
│   │   ├── preprocess.py                  # Clean text
│   │   ├── pii_masking.py                 # Mask email/sđt/tên nhạy cảm
│   │   ├── deduplicate.py                 # Hash/similarity dedup
│   │   └── validators.py                  # Validate feedback input
│   │
│   ├── ml/
│   │   ├── label_with_llm.py              # LLM bootstrap label train data
│   │   ├── train.py                       # Train TF-IDF + LinearSVC
│   │   ├── classify.py                    # Inference classifier
│   │   ├── severity_rules.py              # Rule Safety override
│   │   ├── confidence.py                  # Confidence score heuristic
│   │   ├── taxonomy.py                    # Topic taxonomy
│   │   ├── evaluate.py                    # F1, safety recall
│   │   ├── model.joblib                   # Commit để demo reproducible
│   │   └── metrics.json                   # Commit nếu nhỏ, ghi kết quả train
│   │
│   ├── analytics/
│   │   ├── spike.py                       # Spike detection 1h vs 7d
│   │   ├── aggregates.py                  # Aggregate KPI/trend/topic
│   │   ├── evidence.py                    # Chọn evidence_ids tiêu biểu
│   │   └── dashboard_views.py             # Populate/query views nếu cần
│   │
│   ├── agent/                            # LLM AGENT — có log đầy đủ
│   │   │
│   │   ├── __init__.py
│   │   │
│   │   ├── llm_agent.py                  # Agent chính: alert → action/ticket JSON
│   │   ├── router.py                     # Rule routing table topic→team/SLA
│   │   ├── tools.py                      # Tool cho agent: query evidence/summary
│   │   ├── guardrails.py                 # Safety override, confidence gate
│   │   ├── prompts.py                    # System/user prompt templates
│   │   ├── schemas.py                    # Pydantic schema cho agent output
│   │   ├── parser.py                     # Parse/repair JSON output
│   │   ├── retries.py                    # Retry khi JSON lỗi/API lỗi
│   │   │
│   │   ├── agent_logger.py               # Log riêng cho agent run
│   │   ├── trace.py                      # Tạo trace_id/run_id cho mỗi lần agent chạy
│   │   ├── audit.py                      # Ghi audit log vào Supabase
│   │   ├── decisions.py                  # Chuẩn hóa quyết định agent
│   │   └── README.md                     # Giải thích agent design
│   │
│   ├── driver/
│   │   ├── notify.py                     # Driver notification logic
│   │   ├── message_templates.py          # Template phản hồi tài xế
│   │   ├── risk_score.py                 # Optional risk score
│   │   └── guardrails.py                 # Không auto gửi Safety nghiêm trọng
│   │
│   ├── db/
│   │   ├── supabase_client.py            # Service role client
│   │   ├── readers.py                    # Query raw/processed/alerts
│   │   ├── writers.py                    # Insert processed/alerts/tickets/logs
│   │   ├── migrations_check.py           # Optional: kiểm tra schema
│   │   └── types.py                      # Dataclass/type hints
│   │
│   ├── correction/
│   │   ├── fetch_corrections.py          # Pull correction_logs từ DB
│   │   ├── build_retrain_dataset.py      # Merge seed_train + corrections
│   │   └── retrain_from_corrections.py   # Train model v2 từ log sửa nhãn
│   │
│   ├── tests/
│   │   ├── test_preprocess.py
│   │   ├── test_severity_rules.py
│   │   ├── test_router.py
│   │   ├── test_agent_schema.py
│   │   ├── test_guardrails.py
│   │   └── test_spike.py
│   │
│   └── logs/                             # Runtime local logs — Gitignore
│       └── .gitkeep
│
├── supabase/
│   ├── config.toml
│   └── migrations/
│       ├── 0001_profiles.sql
│       ├── 0002_feedback_raw.sql
│       ├── 0003_feedback_processed.sql
│       ├── 0004_alerts.sql
│       ├── 0005_tickets.sql
│       ├── 0006_correction_logs.sql
│       ├── 0007_driver_notifications.sql
│       ├── 0008_agent_run_logs.sql       # Log agent ở DB
│       ├── 0009_views_dashboard.sql
│       └── 0010_rls_policies.sql
│
├── data/
│   ├── seed_real.json                    # Review thật snapshot
│   ├── seed_synthetic.json               # Synthetic data
│   ├── seed_demo.json                    # 150 feedback cho demo
│   ├── seed_train.json                   # Train data
│   ├── taxonomy.json                     # 10 topic + keyword + routing
│   ├── sample_agent_inputs.json          # Input mẫu cho agent test
│   ├── sample_agent_outputs.json         # Output mẫu đã validate
│   └── output/
│       └── .gitkeep                      # Runtime output — ignore nội dung
│
├── docs/
│   ├── architecture.md                   # Kiến trúc demo vs production
│   ├── repo-structure.md                 # Giải thích cấu trúc repo
│   ├── data-provenance.md                # Nguồn dữ liệu: real/synthetic
│   ├── pipeline-flow.md                  # Luồng ingest→clean→ML→agent
│   ├── agent-design.md                   # Agent, tool, prompt, guardrail
│   ├── agent-logging.md                  # Agent logging/audit trail
│   ├── hitl-and-learning.md              # HITL + correction_logs
│   ├── ticket-routing.md                 # Ticket/phòng ban/SLA
│   ├── driver-notification.md            # Phản hồi tài xế
│   └── demo-script.md                    # Kịch bản demo 5 phút
│
└── notebooks/                            # Optional, chỉ để EDA
    ├── data_exploration.ipynb
    ├── model_evaluation.ipynb
    └── README.md