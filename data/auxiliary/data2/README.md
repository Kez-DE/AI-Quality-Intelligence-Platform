# Data_2 Auxiliary Dataset

Folder này giữ Data_2 như một dataset phụ trợ. Nó không thay thế dataset runtime
chính `data/processed/seed_real_clean.json`.

## Quyết định sử dụng

Data_2 chỉ dùng cho:

- kiểm thử synthetic Safety spike;
- thí nghiệm balanced-label model;
- tham khảo taxonomy/safety keywords riêng của Data_2.

Không copy các file trong folder này đè lên `data/processed/`, `data/train/` hoặc
`data/taxonomy/` nếu chưa có migration và đánh giá riêng.

## Nội dung

| File | Số dòng | Ghi chú |
| :--- | ---: | :--- |
| `train_balanced/seed_train_labeled.canonical.json` | 4.948 | Tập balanced đã chuẩn hóa schema |
| `train_balanced/train_split.canonical.json` | 3.958 | Train split cho thí nghiệm Data_2 |
| `train_balanced/test_split.canonical.json` | 990 | Test split cho thí nghiệm Data_2 |
| `synthetic/safety_spike_cases.canonical.json` | 30 | Case Safety synthetic, toàn bộ severity 5 |
| `taxonomy/safety_keywords.json` | n/a | Keyword Safety riêng của Data_2 |
| `taxonomy/taxonomy.json` | n/a | Taxonomy phụ trợ |
| `taxonomy/routing_table.json` | n/a | Routing phụ trợ |
| `taxonomy/severity_rules.json` | n/a | Severity rules phụ trợ |
| `summary.json` | 1 manifest | Tóm tắt provenance và phân phối nhãn |

## Provenance

`summary.json` ghi nguồn chuẩn bị cục bộ là `~/Downloads/Data_2/data` tại thời
điểm tạo file. Repo này chỉ lưu bản đã chuẩn hóa dưới `data/auxiliary/data2/`.

Data_2 có nhiều dòng mock/synthetic, đặc biệt ID bắt đầu bằng `FB-MOCK-*`:

- `seed_train_labeled.canonical.json`: 4.948 dòng, 2.706 dòng mock ID, 3.742 text
  unique.
- `synthetic/safety_spike_cases.canonical.json`: 30 dòng, 26 dòng mock ID.

Vì vậy, folder này phải được mô tả là **auxiliary/experimental**, không phải
public-review canonical dataset.

## Cách tái tạo

```bash
python3 scripts/prepare_data2_auxiliary.py
```

Script đọc Data_2 từ `~/Downloads/Data_2/data` theo mặc định và ghi lại toàn bộ
folder này, gồm `summary.json` và README.
