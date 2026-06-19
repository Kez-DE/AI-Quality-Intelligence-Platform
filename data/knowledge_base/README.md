# Knowledge Base (RAG) — AI Quality Intelligence Platform

Bộ tài liệu nội bộ (mock, phục vụ demo Giai đoạn 4) làm nguồn tri thức cho RAG.
Mục tiêu: AI Agent trích dẫn đúng SOP/SLA thay vì "bịa" câu trả lời.

> ⚠️ **Dữ liệu mock.** Đây KHÔNG phải tài liệu chính thức của XanhSM. Nội dung được
> xây dựng giả lập, bám sát taxonomy nghiệp vụ thật (`data/taxonomy/`) để demo luồng RAG.
> Không crawl từ nguồn ngoài — toàn bộ là tài liệu tĩnh tự soạn.

## Cấu trúc thư mục

```
data/knowledge_base/
├── README.md              # File này — quy ước & manifest
├── sop/                   # Cẩm nang Vận hành (Standard Operating Procedures)
│   ├── sop_tai_nan_giao_thong.md
│   ├── sop_tai_xe_quay_roi.md
│   ├── sop_mat_do_tren_xe.md
│   ├── sop_gian_lan_cuoc.md
│   └── sop_thai_do_tai_xe.md
├── sla/                   # SLA & Chính sách Bồi thường
│   └── sla_boi_thuong_chuan.md
├── tech/                  # Hướng dẫn Kỹ thuật (App & System)
│   ├── tech_loi_thanh_toan.md
│   └── tech_loi_khong_nhan_cuoc.md
└── tickets/               # Lịch sử Ticket mẫu (few-shot case study)
    └── ticket_case_studies_p5.md
```

## Quy ước cho script chunk (làm ở lượt sau)

Mỗi file `.md` có **YAML frontmatter** mô tả metadata cấp tài liệu:

```yaml
---
document_title: Quy trình xử lý tai nạn giao thông 2026
category: safety          # safety | fraud | attitude | lost_item | app | sla | case_study
department: Safety        # Safety | Vận hành | IT | CSKH | Pricing
severity_scope: [P4, P5]  # mức severity tài liệu này áp dụng
source: mock              # luôn là mock cho dataset demo
tags: [tai-nan, khan-cap, cong-an]
---
```

**Chiến lược chunk (Semantic Chunking):**
- Cắt theo từng heading cấp 2 (`##`) — mỗi section là một chunk độc lập, giữ nguyên ngữ cảnh.
- Mỗi chunk lý tưởng 300–800 token; section nào quá dài thì script tách tiếp theo heading cấp 3 (`###`).
- Metadata của mỗi chunk = frontmatter của file + tiêu đề section (`heading`) để Hybrid Search lọc đúng phòng ban/thể loại.

**Mapping sang bảng `knowledge_chunks` (Supabase pgvector):**

| Cột | Nguồn |
| :--- | :--- |
| `document_title` | `frontmatter.document_title` |
| `content` | text của section (gồm cả heading) |
| `metadata` | `{category, department, severity_scope, tags, heading, source, source_file}` |
| `embedding` | `vector(1024)` — sinh bằng **bge-m3** ở bước ingest |

## Config đã chốt

- **Generate (LLM):** DeepSeek `deepseek-v4-flash` (qua `pipeline/agent/model_router.py`).
- **Embedding:** `BAAI/bge-m3` chạy local → `vector(1024)` (DeepSeek không có embedding API).
- **Migration:** `supabase/migrations/20260617120000_knowledge_chunks_rag.sql` (bảng + hàm `match_knowledge_chunks`).

## Cách nạp dữ liệu (ingest)

```bash
# Áp migration lên Supabase trước (CLI hoặc dán SQL Editor), rồi:
cd pipeline
python -m agent.ingest_knowledge --dry-run   # xem trước chunk, không ghi DB
python -m agent.ingest_knowledge             # embed bge-m3 + upsert vào knowledge_chunks
python -m agent.ingest_knowledge --reset     # xóa sạch rồi nạp lại
```

Cần `SUPABASE_SERVICE_ROLE_KEY` trong `.env`. Lần chạy đầu sẽ tải model bge-m3 (~2GB).
```
