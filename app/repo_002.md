C2-App-116/
│
├════════════════════════════════════════════════════════════
│  0. COHORT FRAMEWORK — KHÔNG ĐỘNG
├════════════════════════════════════════════════════════════
│
├── scripts/
│   ├── _pyrun.sh
│   ├── _pyrun.cmd
│   ├── setup_hooks.sh
│   ├── setup_hooks.ps1
│   ├── log_hook.py
│   ├── log_antigravity.py
│   ├── log_manual.py
│   └── submit_log.py
│
├── .claude/
├── .codex/
├── .cursor/
├── .gemini/
├── .github/
│   └── hooks/
├── .agents/
│
├── JOURNAL.md
├── WORKLOG.md
│
├════════════════════════════════════════════════════════════
│  1. PRODUCT / BUSINESS CONTEXT
├════════════════════════════════════════════════════════════
│
├── specs/
│   ├── product-vision.md
│   ├── problem-statement.md
│   ├── stakeholders.md
│   ├── requirements.md
│   ├── user-flow.md
│   ├── feature-list.md
│   ├── taxonomy.md
│   ├── metrics.md
│   └── api-contracts.md
│
├════════════════════════════════════════════════════════════
│  2. ARCHITECTURE DECISION RECORDS
├════════════════════════════════════════════════════════════
│
├── adrs/
│   ├── 0001-use-supabase-as-system-of-record.md
│   ├── 0002-use-batch-pipeline-instead-of-realtime.md
│   ├── 0003-use-python-pipeline-plus-react-frontend.md
│   ├── 0004-use-tfidf-linearsvc-for-demo-ml.md
│   ├── 0005-use-llm-agent-for-ticket-routing.md
│   ├── 0006-use-human-in-the-loop-for-safety.md
│   ├── 0007-use-synthetic-plus-store-review-data.md
│   └── 0008-commit-small-model-artifact-for-demo.md
│
├════════════════════════════════════════════════════════════
│  3. PLANNING / TASK MANAGEMENT
├════════════════════════════════════════════════════════════
│
├── planning/
│   ├── roadmap.md
│   ├── release-plan.md
│   └── sprints/
│       ├── sprint-02-foundation.md
│       ├── sprint-03-ml-classification.md
│       ├── sprint-04-agent-alert-ticket.md
│       ├── sprint-05-dashboard-hitl.md
│       └── sprint-06-polish-demo.md
│
├── tasks/
│   ├── TASK-001-move-xanh-iu-into-app.md
│   ├── TASK-002-create-supabase-schema.md
│   ├── TASK-003-build-data-generator.md
│   ├── TASK-004-scrape-store-reviews.md
│   ├── TASK-005-train-ml-classifier.md
│   ├── TASK-006-run-batch-classification.md
│   ├── TASK-007-detect-spikes.md
│   ├── TASK-008-build-llm-ticket-agent.md
│   ├── TASK-009-build-dashboard-db-queries.md
│   ├── TASK-010-build-human-review-queue.md
│   └── TASK-011-write-demo-script.md
│
├════════════════════════════════════════════════════════════
│  4. FRONTEND APP — xanh_iu
├════════════════════════════════════════════════════════════
│
├── app/
│   ├── package.json
│   ├── bun.lock
│   ├── bunfig.toml
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── components.json
│   ├── README.md
│   │
│   └── src/
│       ├── router.tsx
│       ├── routeTree.gen.ts
│       ├── styles.css
│       │
│       ├── components/
│       │   ├── AppShell.tsx
│       │   ├── QualityCockpit.tsx
│       │   │
│       │   ├── charts/
│       │   │   ├── KpiCards.tsx
│       │   │   ├── TrendChart.tsx
│       │   │   ├── AreaHeatmap.tsx
│       │   │   ├── TopicDistribution.tsx
│       │   │   ├── SeverityDonut.tsx
│       │   │   └── SlaStatusBar.tsx
│       │   │
│       │   ├── feedback/
│       │   │   ├── FeedbackTable.tsx
│       │   │   ├── FeedbackDetailDrawer.tsx
│       │   │   └── EvidenceList.tsx
│       │   │
│       │   ├── alerts/
│       │   │   ├── AlertList.tsx
│       │   │   ├── AlertDetail.tsx
│       │   │   └── AlertSeverityBadge.tsx
│       │   │
│       │   ├── tickets/
│       │   │   ├── TicketQueue.tsx
│       │   │   ├── TicketCard.tsx
│       │   │   ├── TicketDetail.tsx
│       │   │   ├── TeamFilter.tsx
│       │   │   └── SlaBadge.tsx
│       │   │
│       │   ├── review/
│       │   │   ├── ReviewQueue.tsx
│       │   │   ├── ReviewItem.tsx
│       │   │   ├── LabelCorrectionForm.tsx
│       │   │   └── CorrectionHistory.tsx
│       │   │
│       │   ├── agent/
│       │   │   ├── AgentRunTable.tsx
│       │   │   └── AgentRunDetail.tsx
│       │   │
│       │   ├── driver/
│       │   │   ├── DriverInbox.tsx
│       │   │   ├── DriverNotificationCard.tsx
│       │   │   └── DriverRiskPanel.tsx
│       │   │
│       │   └── ui/
│       │       └── ...
│       │
│       ├── routes/
│       │   ├── __root.tsx
│       │   ├── auth.tsx
│       │   ├── index.tsx
│       │   │
│       │   └── _authenticated/
│       │       ├── route.tsx
│       │       ├── dashboard.tsx
│       │       ├── feedback.tsx
│       │       ├── alerts.tsx
│       │       ├── tickets.tsx
│       │       ├── review.tsx
│       │       ├── corrections.tsx
│       │       ├── agent-logs.tsx
│       │       ├── driver-inbox.tsx
│       │       └── chat.tsx
│       │
│       ├── integrations/
│       │   └── supabase/
│       │       ├── client.ts
│       │       ├── client.server.ts
│       │       ├── auth-middleware.ts
│       │       └── types.ts
│       │
│       ├── lib/
│       │   ├── ai.functions.ts
│       │   ├── queries.ts
│       │   ├── dashboard.queries.ts
│       │   ├── feedback.queries.ts
│       │   ├── alerts.queries.ts
│       │   ├── tickets.queries.ts
│       │   ├── review.queries.ts
│       │   ├── agent.queries.ts
│       │   ├── driver.queries.ts
│       │   ├── config.server.ts
│       │   └── utils.ts
│       │
│       └── hooks/
│           ├── useDashboardData.ts
│           ├── useTickets.ts
│           ├── useReviewQueue.ts
│           ├── useAgentLogs.ts
│           └── use-mobile.tsx
│
├════════════════════════════════════════════════════════════
│  5. PYTHON PIPELINE — ML + AGENT + BATCH PROCESSING
├════════════════════════════════════════════════════════════
│
├── pipeline/
│   ├── requirements.txt
│   ├── README.md
│   ├── .env
│   │
│   ├── run_batch.py
│   ├── run_scrape.py
│   ├── run_train.py
│   ├── run_agent_on_alerts.py
│   ├── run_retrain_from_corrections.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   ├── constants.py
│   │   └── logging_config.py
│   │
│   ├── ingest/
│   │   ├── scrape_google_play.py
│   │   ├── scrape_app_store.py
│   │   ├── scrape_reviews.py
│   │   ├── generate_synthetic.py
│   │   ├── mix_seed_data.py
│   │   ├── load_batch.py
│   │   └── normalizers.py
│   │
│   ├── clean/
│   │   ├── preprocess.py
│   │   ├── pii_masking.py
│   │   ├── deduplicate.py
│   │   └── validators.py
│   │
│   ├── ml/
│   │   ├── label_with_llm.py
│   │   ├── train.py
│   │   ├── classify.py
│   │   ├── severity_rules.py
│   │   ├── confidence.py
│   │   ├── taxonomy.py
│   │   ├── evaluate.py
│   │   ├── model.joblib
│   │   └── metrics.json
│   │
│   ├── analytics/
│   │   ├── spike.py
│   │   ├── aggregates.py
│   │   ├── evidence.py
│   │   └── dashboard_views.py
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── llm_agent.py
│   │   ├── router.py
│   │   ├── tools.py
│   │   ├── guardrails.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   ├── parser.py
│   │   ├── retries.py
│   │   ├── decisions.py
│   │   ├── trace.py
│   │   ├── agent_logger.py
│   │   ├── audit.py
│   │   └── README.md
│   │
│   ├── driver/
│   │   ├── notify.py
│   │   ├── message_templates.py
│   │   ├── risk_score.py
│   │   └── guardrails.py
│   │
│   ├── correction/
│   │   ├── fetch_corrections.py
│   │   ├── build_retrain_dataset.py
│   │   └── retrain_from_corrections.py
│   │
│   ├── db/
│   │   ├── supabase_client.py
│   │   ├── readers.py
│   │   ├── writers.py
│   │   ├── migrations_check.py
│   │   └── types.py
│   │
│   ├── tests/
│   │   ├── test_preprocess.py
│   │   ├── test_pii_masking.py
│   │   ├── test_severity_rules.py
│   │   ├── test_confidence.py
│   │   ├── test_spike.py
│   │   ├── test_router.py
│   │   ├── test_agent_schema.py
│   │   └── test_guardrails.py
│   │
│   └── logs/
│       └── .gitkeep
│
├════════════════════════════════════════════════════════════
│  6. SUPABASE — DATABASE SCHEMA
├════════════════════════════════════════════════════════════
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
│       ├── 0008_agent_run_logs.sql
│       ├── 0009_dashboard_views.sql
│       └── 0010_rls_policies.sql
│
├════════════════════════════════════════════════════════════
│  7. DATA — REAL / SYNTHETIC / DEMO / OUTPUT
├════════════════════════════════════════════════════════════
│
├── data/
│   ├── raw/
│   │   ├── store_reviews_google_play.json
│   │   ├── store_reviews_app_store.json
│   │   └── README.md
│   │
│   ├── synthetic/
│   │   ├── seed_synthetic.json
│   │   ├── synthetic_generation_config.json
│   │   └── README.md
│   │
│   ├── demo/
│   │   ├── seed_demo_150.json
│   │   ├── demo_spike_config.json
│   │   └── README.md
│   │
│   ├── train/
│   │   ├── seed_train.json
│   │   ├── labeled_train.json
│   │   └── README.md
│   │
│   ├── taxonomy/
│   │   ├── taxonomy.json
│   │   ├── safety_keywords.json
│   │   └── routing_table.json
│   │
│   ├── agent/
│   │   ├── sample_agent_inputs.json
│   │   ├── sample_agent_outputs.json
│   │   └── README.md
│   │
│   └── output/
│       └── .gitkeep
│
├════════════════════════════════════════════════════════════
│  8. PROMPTS — QUẢN LÝ PROMPT RIÊNG
├════════════════════════════════════════════════════════════
│
├── prompts/
│   ├── README.md
│   ├── labeler/
│   │   ├── system.md
│   │   ├── user_template.md
│   │   └── output_schema.json
│   │
│   ├── ticket_agent/
│   │   ├── system.md
│   │   ├── user_template.md
│   │   └── output_schema.json
│   │
│   ├── driver_notification/
│   │   ├── system.md
│   │   ├── user_template.md
│   │   └── output_schema.json
│   │
│   └── chatbot/
│       ├── system.md
│       ├── user_template.md
│       └── output_schema.json
│
├════════════════════════════════════════════════════════════
│  9. ROOT TESTS — INTEGRATION / E2E
├════════════════════════════════════════════════════════════
│
├── tests/
│   ├── integration/
│   │   ├── test_run_batch_end_to_end.py
│   │   ├── test_supabase_writes.py
│   │   └── test_agent_ticket_flow.py
│   │
│   └── e2e/
│       ├── README.md
│       └── demo_checklist.md
│
├════════════════════════════════════════════════════════════
│  10. DOCUMENTATION
├════════════════════════════════════════════════════════════
│
├── docs/
│   ├── architecture.md
│   ├── repo-structure.md
│   ├── data-provenance.md
│   ├── pipeline-flow.md
│   ├── agent-design.md
│   ├── agent-logging.md
│   ├── hitl-and-learning.md
│   ├── ticket-routing.md
│   ├── driver-notification.md
│   ├── setup.md
│   ├── troubleshooting.md
│   └── demo-script.md
│
├── notebooks/
│   ├── data_exploration.ipynb
│   ├── model_evaluation.ipynb
│   └── README.md
│
├── AGENTS.md
├── .env.example
├── .gitignore
└── README.md


#tối ưu
C2-App-116/
├── specs/          # product/business context
├── adrs/           # architecture decisions
├── planning/       # roadmap + sprint plan
├── tasks/          # user stories/tasks
├── app/            # frontend xanh_iu
├── pipeline/       # Python ML + agent pipeline
├── supabase/       # DB migrations
├── data/           # raw/processed/demo/train data
├── prompts/        # prompt system/templates/versioning
├── tests/          # integration/e2e/system tests
├── docs/           # technical docs/runbook/demo
├── scripts/        # cohort logging, giữ nguyên
├── AGENTS.md       # rules/context cho AI agent
├── README.md
├── JOURNAL.md
├── WORKLOG.md
└── .gitignore