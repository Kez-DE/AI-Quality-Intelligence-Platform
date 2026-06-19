# Data Manifest — AI Quality Intelligence Platform

Thư mục này chứa dữ liệu phục vụ demo học thuật của **C2-App-116**. Đây không
phải dữ liệu vận hành nội bộ của xanhSM/Green SM. Các review gốc đến từ nguồn
công khai; metadata vận hành như khu vực, tài xế, chuyến đi và cờ spike là dữ
liệu tổng hợp để demo luồng AI.

## Nguồn dữ liệu chính

| Đường dẫn | Quy mô hiện tại | Nguồn gốc | Vai trò runtime |
| :--- | :--- | :--- | :--- |
| `raw/ai223_public_reviews_5000_enriched_locations.csv` | 5.000 dòng CSV | Review công khai Google Play/App Store, đã gắn thêm metadata demo | Lớp dữ liệu thô để truy vết provenance |
| `processed/seed_real_clean.json` | 4.837 bản ghi | Dẫn xuất từ `raw/`, giữ schema gọn và nhãn LLM distillation | Dataset mặc định cho ingest/backend |
| `train/seed_train_labeled.json` | 4.837 bản ghi | Tập nhãn topic/sentiment/severity từ quá trình distillation | Nguồn train/evaluate classifier |
| `train/train_split.json` | 3.743 bản ghi | Split từ `seed_train_labeled.json` | Train split cho ML |
| `train/test_split.json` | 932 bản ghi | Split từ `seed_train_labeled.json` | Test split cho ML |
| `train/augment_short_sentences.json` | 3 mẫu | Câu ngắn tổng hợp | Thử nghiệm rule/model câu ngắn |
| `demo/seed_demo_150.json` | 150 bản ghi | Review công khai đã gắn metadata demo và spike flag | Nút demo/ingest nhanh, chưa có nhãn ML trong file |
| `reference/area_catalog.json` | 16 khu vực | Bảng tra tổng hợp cho Hà Nội, Hồ Chí Minh, Đà Nẵng | Chuẩn hóa `area`/`area_label` |
| `reference/enrichment_summary.json` | 1 manifest | Tóm tắt quá trình enrich 5.000 dòng | Kiểm chứng số lượng/khu vực/spike |
| `taxonomy/routing_table.json` | 7 route topic | Config demo | Router Agent định tuyến team/SLA |
| `taxonomy/severity_rules.json` | 1 bộ ngưỡng | Config demo | Alert Agent phân cấp WATCH/WARNING/CRITICAL |
| `knowledge_base/` | 9 tài liệu nội bộ mock | SOP/SLA/Tech/Ticket tự soạn cho demo | RAG nội bộ theo phòng ban |
| `public_kb/` | 8 tài liệu khách hàng | Tài liệu công khai Green SM đã làm sạch/tóm lược | RAG chatbot guest |
| `auxiliary/data2/` | 4.948 dòng balanced + 30 safety spike | Data_2 phụ trợ có mock/synthetic | Thí nghiệm train và kiểm thử spike, không thay runtime |

## Quy tắc provenance

**Trường công khai từ review/app store:** `text`, `text_full`, `title`,
`rating`, `timestamp`, `app`, `source`, `source_platform`, `app_id`,
`source_url`, `version`, `raw_id`, `developer_reply`, `thumbs_up`,
`scraped_at`.

**Trường tổng hợp cho demo:** `city`, `city_label`, `area`, `area_label`,
`driver_id`, `trip_id`, `event_time`, `issue_hint`, `is_demo_spike`,
`data_type`, `metadata_provenance`.

**Nhãn ML:** `topic`, `sentiment`, `severity`, `confidence` là nhãn sinh bằng
LLM distillation cho tập train hoặc do model/rule dự đoán khi chạy backend. Đây
không phải nhãn được nhân sự vận hành gán thủ công ở quy mô lớn.

## Dataset runtime

Dataset runtime mặc định là `data/processed/seed_real_clean.json`. Backend tìm
file này qua `pipeline/core/paths.py` và `pipeline/ingest.py`. Không thay bằng
`raw/`, `demo/` hoặc `auxiliary/data2/` nếu chưa có migration, đánh giá model và
kiểm thử ingest riêng.

`processed/seed_real_clean.json` đang dùng schema gọn:

```text
feedback_id, app, text_full, topic, sentiment, severity,
rating, timestamp, area_label, city_label
```

## Knowledge Base

- `knowledge_base/` là KB nội bộ **mock** cho admin/manager/staff. Retriever
  hiện tại là keyword/BM25-lite trong `pipeline/agent/knowledge_base.py`, load
  trực tiếp các file Markdown và chunk theo heading `##`.
- `public_kb/` là KB công khai cho guest chatbot. Retriever ở
  `pipeline/agent/public_kb.py` chỉ nhận file có frontmatter `audience: public`.
- Hai KB này tách biệt. Guest không đọc SOP/SLA nội bộ.

Chi tiết: [`knowledge_base/README.md`](knowledge_base/README.md) và
[`public_kb/README.md`](public_kb/README.md).

## Data_2 phụ trợ

`auxiliary/data2/` không phải dataset chính. Folder này giữ các file đã chuẩn hóa
từ Data_2 để:

1. kiểm thử spike Safety bằng synthetic cases;
2. thử nghiệm balanced-label training;
3. tham khảo taxonomy/safety keywords riêng của Data_2.

Data_2 có nhiều dòng mock/synthetic, đặc biệt ID dạng `FB-MOCK-*`, nên không được
mô tả là public-review canonical dataset. Chi tiết:
[`auxiliary/data2/README.md`](auxiliary/data2/README.md).

## Những mô tả không được dùng

- Không nói `driver_id`, `trip_id`, `area`, `event_time` là dữ liệu vận hành thật.
- Không nói `auxiliary/data2/` thay thế `processed/seed_real_clean.json`.
- Không nói `knowledge_base/` là tài liệu chính thức của Green SM.
- Không nói `data/taxonomy/` có `safety_keywords.json`; file này chỉ nằm trong
  `data/auxiliary/data2/taxonomy/`.
