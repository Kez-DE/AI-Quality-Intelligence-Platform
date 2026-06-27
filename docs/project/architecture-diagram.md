# Architecture Diagram — AI Quality Intelligence Platform

> **Cập nhật 2026-06-27:** Cập nhật nhãn multi-agent trong component diagram (8 agent nghiệp vụ + Orchestrator, thay tên rút gọn cũ).

Sơ đồ components + data flow cho Gate G2. GitHub render trực tiếp các khối Mermaid bên dưới.
Bản mô tả chữ chi tiết: [`docs/project/architecture.md`](architecture.md).

## 1. Component diagram (tổng quan hệ thống)

```mermaid
flowchart TB
    subgraph Client["Người dùng"]
        U["Admin / Manager / Staff / Guest"]
    end

    subgraph FE["Frontend — app/ (React 19 + TanStack Start + Vite)"]
        UI["Dashboard · Feedback · Alerts · Insights · Chat · Admin"]
    end

    subgraph BE["Backend — pipeline/ (FastAPI)"]
        API["main.py — REST API + auth_guard (RBAC)"]
        PIPE["Pipeline: clean -> classifier -> rules -> ingest -> spike_detector"]
        AG["agents/: orchestrator + 8 agent nghiệp vụ<br/>(alert · analyst · ingestion · insight · router · scoring · task · ticket)"]
        ROUTER["agent/model_router.py — LLM failover"]
    end

    subgraph DATA["Dữ liệu & LLM"]
        DB[("Supabase — PostgreSQL + Auth + Realtime")]
        LLM["LLM providers: OpenRouter / OpenAI / Gemini / Groq"]
        ML["ML models .joblib (TF-IDF + LinearSVC)"]
    end

    U --> UI
    UI -- REST --> API
    UI -- Realtime subscribe --> DB
    API --> PIPE
    API --> AG
    PIPE --> ML
    PIPE -- ghi feedback/alerts --> DB
    AG --> ROUTER
    ROUTER --> LLM
    AG -- ghi insights/alerts --> DB
    API -- verify JWT + role --> DB
```

## 2. Data flow — user flow chính (review → phân loại → spike → alert)

```mermaid
flowchart LR
    R["Review thô<br/>(form / streaming 50/s / dataset)"]
    C1["clean.py<br/>mask PII + chuẩn hoá"]
    C2["classifier.py<br/>TF-IDF + LinearSVC"]
    C3["rules.py<br/>rule keyword + Safety override + confidence band"]
    I["ingest.py<br/>ghi Supabase feedback"]
    S["spike_detector.py<br/>group theo khu vực, đếm P4/P5"]
    L["llm_agent.py<br/>LLM phân tích root cause + định tuyến phòng ban"]
    A["alerts<br/>ghi Supabase -> FE realtime"]

    R --> C1 --> C2 --> C3 --> I --> S --> L --> A
```

## 3. Human-in-the-Loop (vòng học khép kín)

```mermaid
flowchart LR
    Q["Review Queue<br/>(P5 / safety / confidence thấp)"]
    H{"Nhân viên<br/>duyệt?"}
    OK["Duyệt: reviewed=true"]
    FIX["Sửa nhãn -> correction_logs<br/>(audit + data retrain)"]
    DB[("Supabase")]

    Q --> H
    H -- nhãn AI đúng --> OK --> DB
    H -- nhãn AI sai --> FIX --> DB
```

## 4. LLM provider failover

```mermaid
flowchart LR
    REQ["Yêu cầu LLM<br/>(chat / spike / agent)"]
    OR["OpenRouter"]
    OA["OpenAI"]
    GM["Gemini"]
    GR["Groq"]
    MK["Mock (demo luồng)"]

    REQ --> OR -- lỗi/hết key --> OA -- lỗi/hết key --> GM -- lỗi/hết key --> GR -- hết key --> MK
```

## 5. HI-Loop Approval (báo cáo → task khép kín)

```mermaid
flowchart LR
    AA["analyst_agent<br/>action_items + root_cause"]
    DR[("department_reports<br/>suggested_tasks (JSONB)")]
    MGR{"Manager<br/>biên tập Draft Task"}
    DRAFT["PUT /draft-tasks<br/>lưu nháp (409 nếu đã duyệt)"]
    DISP["POST /approve-and-dispatch<br/>RPC atomic"]
    TK[("tasks<br/>source=report, report_id")]
    BOARD["Task Board<br/>badge 'Từ báo cáo' + link gốc"]

    AA --> DR --> MGR
    MGR --> DRAFT --> DR
    MGR --> DISP --> TK --> BOARD
```

