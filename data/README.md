# Data — AI Quality Intelligence Platform

Toàn bộ dữ liệu trong dự án này phục vụ **demo học thuật** (AI20K-223). Đây
không phải dữ liệu vận hành thật của xanhSM/GreenSM.

## Phân tầng dữ liệu (provenance)

| Thư mục | File | Nguồn | Vai trò |
| :--- | :--- | :--- | :--- |
| `raw/` | `ai223_public_reviews_5000_enriched_locations.csv` | Review công khai Google Play + Apple App Store, đã làm giàu metadata | Lớp ngôn ngữ thật (5000 review) |
| `processed/` | `seed_real_clean.json` | Dẫn xuất từ raw + nhãn do LLM sinh (distillation) | Nguồn ingest chính (đã có nhãn) |
| `train/` | `seed_train_labeled.json`, `train_split.json`, `test_split.json` | Tập huấn luyện/đánh giá classifier | Train TF-IDF + LinearSVC |
| `demo/` | `seed_demo_150.json` | 150 review công khai + cắm spike Safety tổng hợp | "Nút bấm" demo trên sân khấu (chưa có nhãn ML) |
| `reference/` | `area_catalog.json`, `enrichment_summary.json` | Bảng tra khu vực + tóm tắt enrichment | Tham chiếu khu vực HN/HCM/ĐN |
| `auxiliary/data2/` | Data_2 đã chuẩn hoá schema | Bộ phụ trợ có mock/synthetic | Kiểm thử Safety spike + thử nghiệm train cân bằng nhãn |

## Quyết định về Data_2

Dataset chính của hệ thống vẫn là bộ public reviews đã enrich hiện tại trong repo:

- `raw/ai223_public_reviews_5000_enriched_locations.csv`
- `processed/seed_real_clean.json`

`Data_2` **không thay thế** dataset chính. Các phần được chuẩn hoá vào
`auxiliary/data2/` chỉ dùng như auxiliary dataset để:

1. bổ sung synthetic Safety spike cases cho kiểm thử/demo;
2. thử nghiệm balanced-label training riêng;
3. tham khảo taxonomy/safety keywords.

Không mô tả các file trong `auxiliary/data2/` là dữ liệu public-review chính vì
Data_2 có nhiều row mock/synthetic (`FB-MOCK-*`).

## Trường THẬT vs TỔNG HỢP

Phân biệt rõ ràng theo yêu cầu provenance:

**Trường THẬT (từ review công khai):**
`text` / `text_full`, `title`, `rating`, `timestamp`, `app`, `source`,
`source_platform`, `app_id`, `source_url`, `version`.

**Trường TỔNG HỢP (synthetic demo metadata):**
`area`, `area_label`, `city`, `city_label`, `driver_id`, `trip_id`,
`event_time`, `is_demo_spike`, `issue_hint`.

**Nhãn ML (`topic`, `sentiment`, `severity`, `confidence`):** sinh bằng LLM
(distillation) cho tập train, hoặc do classifier dự đoán lúc runtime. Không
phải nhãn do con người gán thủ công ở quy mô lớn.

## Khu vực tổng hợp

Bao phủ Hà Nội, Hồ Chí Minh, Đà Nẵng. Code-style ID ổn định
(`HN-Cau-Giay`) + nhãn hiển thị (`Cầu Giấy, Hà Nội`). Xem `reference/area_catalog.json`.

## Demo vs Production

- **Demo (dự án này):** batch thủ công 100–150 review/lô, hàng đợi/inbox giả lập.
- **Production (ngoài phạm vi):** ingest real-time/micro-batch, thông báo, tích hợp app tài xế thật.
