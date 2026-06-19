# Knowledge Base Nội Bộ — RAG Cho Ops Chat

Folder này chứa tài liệu nội bộ **mock** dùng cho demo RAG của admin/manager/staff.
Đây không phải SOP/SLA chính thức của Green SM. Nội dung được tự soạn để mô phỏng
các quy trình xử lý sự cố thường gặp và để agent có nguồn trích dẫn ổn định khi
trả lời câu hỏi nghiệp vụ.

## Cách runtime đọc KB

Runtime hiện tại không dùng pgvector, migration `knowledge_chunks`, hay script
`agent.ingest_knowledge`. Retriever thật nằm ở
`pipeline/agent/knowledge_base.py` và hoạt động như sau:

1. Load mọi file `.md` dưới `data/knowledge_base/`, trừ `README.md`.
2. Parse YAML frontmatter bằng parser đơn giản trong code.
3. Chunk nội dung theo heading cấp 2 (`##`).
4. Tìm kiếm bằng keyword/BM25-lite, có bỏ dấu tiếng Việt và boost theo title/tags.
5. Nếu có `department`, chỉ trả tài liệu đúng phòng ban để khớp RBAC.

Pricing và Marketing chưa có tài liệu nội bộ trong folder này; khi lọc đúng hai
phòng đó, retriever trả rỗng là hành vi mong muốn để tránh leak tài liệu phòng
khác.

## Cấu trúc

```text
data/knowledge_base/
├── README.md
├── sla/
│   └── sla_boi_thuong_chuan.md
├── sop/
│   ├── sop_gian_lan_cuoc.md
│   ├── sop_mat_do_tren_xe.md
│   ├── sop_tai_nan_giao_thong.md
│   ├── sop_tai_xe_quay_roi.md
│   └── sop_thai_do_tai_xe.md
├── tech/
│   ├── tech_loi_khong_nhan_cuoc.md
│   └── tech_loi_thanh_toan.md
└── tickets/
    └── ticket_case_studies_p5.md
```

## Manifest tài liệu

| File | Department | Category | Severity scope | Vai trò |
| :--- | :--- | :--- | :--- | :--- |
| `sla/sla_boi_thuong_chuan.md` | CSKH | `sla` | P1-P5 | SLA đóng ticket và bồi thường demo |
| `sop/sop_tai_nan_giao_thong.md` | Safety | `safety` | P5 | Quy trình tai nạn giao thông |
| `sop/sop_tai_xe_quay_roi.md` | Safety | `safety` | P5 | Quy trình quấy rối/đe dọa an toàn |
| `sop/sop_gian_lan_cuoc.md` | Safety | `fraud` | P4-P5 | Quy trình gian lận cước/vòi vĩnh |
| `sop/sop_mat_do_tren_xe.md` | CSKH | `lost_item` | P2-P3 | Quy trình mất đồ/bỏ quên đồ |
| `sop/sop_thai_do_tai_xe.md` | Vận hành | `attitude` | P3-P4 | Quy trình thái độ tài xế |
| `tech/tech_loi_thanh_toan.md` | IT | `app` | P2-P3 | Hướng dẫn lỗi thanh toán |
| `tech/tech_loi_khong_nhan_cuoc.md` | IT | `app` | P2-P3 | Hướng dẫn lỗi không nhận cuốc/định vị |
| `tickets/ticket_case_studies_p5.md` | Safety | `case_study` | P4-P5 | Case study few-shot cho P5 |

## Frontmatter bắt buộc

Mỗi file KB cần có block metadata ở đầu file:

```yaml
---
document_title: Quy trình xử lý Tai nạn Giao thông (SOP-SAFETY-01)
category: safety
department: Safety
severity_scope: [P5]
source: mock
tags: [tai-nan, khan-cap, cong-an, cap-cuu, bao-hiem]
---
```

Các key đang được code dùng trực tiếp: `document_title`, `category`,
`department`, `tags`. `severity_scope` giúp người đọc hiểu phạm vi áp dụng nhưng
chưa được dùng để filter trong retriever hiện tại.

## Kiểm tra nhanh

```bash
cd pipeline
python -m agent.knowledge_base
```

Lệnh trên in đường dẫn KB, số chunk đã load và một vài kết quả truy vấn mẫu. Nếu
muốn kiểm tra chatbot guest, dùng `python -m agent.public_kb`.
