#!/usr/bin/env python3
"""Prepare Data_2 as an auxiliary dataset, without replacing canonical data.

This script intentionally writes Data_2 under data/auxiliary/data2/ so the main
runtime dataset remains data/processed/seed_real_clean.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

TOPIC_MAP = {
    "An toàn": "Safety",
    "Thái độ tài xế": "Driver Behavior",
    "Ứng dụng": "App Issue",
    "Thanh toán": "Payment",
    "Giá cước": "Pricing",
    "Trễ chuyến": "Delay",
    "Khác": "Other",
}

SENTIMENT_MAP = {
    "Tiêu cực": "negative",
    "Trung tính": "neutral",
    "Tích cực": "positive",
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def source_text(row: dict[str, Any]) -> str:
    return str(
        row.get("noi_dung_day_du")
        or row.get("noi_dung")
        or row.get("text_full")
        or row.get("text")
        or ""
    ).strip()


def normalize_row(row: dict[str, Any], *, data_type: str) -> dict[str, Any]:
    """Convert Data_2 Vietnamese-field rows to the app's canonical schema."""
    text = source_text(row)
    title = row.get("tieu_de") or row.get("title")
    topic_raw = row.get("chu_de") or row.get("topic")
    sentiment_raw = row.get("cam_xuc") or row.get("sentiment")
    topic_value = str(topic_raw) if topic_raw is not None else None
    sentiment_value = str(sentiment_raw) if sentiment_raw is not None else None
    severity = row.get("do_nghiem_trong") or row.get("severity")
    if severity is None and topic_value == "An toàn" and sentiment_value == "Tiêu cực":
        severity = 5

    normalized = {
        "feedback_id": row.get("ma_phan_hoi") or row.get("feedback_id"),
        "app": row.get("ung_dung") or row.get("app"),
        "text_full": text,
        "topic": TOPIC_MAP.get(topic_value, topic_value) if topic_value else None,
        "sentiment": SENTIMENT_MAP.get(sentiment_value, sentiment_value) if sentiment_value else None,
        "severity": int(severity) if severity is not None else None,
        "area_label": row.get("khu_vuc") or row.get("area_label"),
        "city_label": row.get("thanh_pho") or row.get("city_label"),
        "rating": row.get("danh_gia") or row.get("rating"),
        "timestamp": row.get("thoi_gian") or row.get("timestamp"),
        "driver_id": row.get("ma_tai_xe") or row.get("driver_id"),
        "trip_id": row.get("ma_chuyen_di") or row.get("trip_id"),
        "data_type": data_type,
        "provenance": "Data_2 auxiliary dataset; synthetic/mock rows must not be described as canonical public-review data.",
    }
    if title:
        normalized["title"] = title
    return {k: v for k, v in normalized.items() if v is not None and v != ""}


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [source_text(row) for row in rows]
    unique_texts = {normalize_text(text) for text in texts if text}
    ids = [str(row.get("feedback_id") or row.get("ma_phan_hoi") or "") for row in rows]
    return {
        "rows": len(rows),
        "unique_texts": len(unique_texts),
        "duplicate_texts": sum(1 for text in texts if text) - len(unique_texts),
        "mock_id_rows": sum(1 for row_id in ids if row_id.startswith("FB-MOCK")),
        "topic_distribution": dict(Counter(str(row.get("topic") or row.get("chu_de")) for row in rows if row.get("topic") or row.get("chu_de")).most_common()),
        "sentiment_distribution": dict(Counter(str(row.get("sentiment") or row.get("cam_xuc")) for row in rows if row.get("sentiment") or row.get("cam_xuc")).most_common()),
        "severity_distribution": dict(Counter(str(row.get("severity") or row.get("do_nghiem_trong")) for row in rows if row.get("severity") or row.get("do_nghiem_trong")).most_common()),
    }


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def build_readme(out_dir: Path, summary: dict[str, Any]) -> None:
    readme = f"""# Data_2 Auxiliary Dataset

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
| `train_balanced/seed_train_labeled.canonical.json` | {summary['train_balanced']['seed_train_labeled']['rows']} | Tập balanced đã chuẩn hóa schema |
| `train_balanced/train_split.canonical.json` | {summary['train_balanced']['train_split']['rows']} | Train split cho thí nghiệm Data_2 |
| `train_balanced/test_split.canonical.json` | {summary['train_balanced']['test_split']['rows']} | Test split cho thí nghiệm Data_2 |
| `synthetic/safety_spike_cases.canonical.json` | {summary['synthetic']['safety_spike_cases']['rows']} | Case Safety synthetic, toàn bộ severity 5 |
| `taxonomy/safety_keywords.json` | n/a | Keyword Safety riêng của Data_2 |
| `taxonomy/taxonomy.json` | n/a | Taxonomy phụ trợ |
| `taxonomy/routing_table.json` | n/a | Routing phụ trợ |
| `taxonomy/severity_rules.json` | n/a | Severity rules phụ trợ |
| `summary.json` | 1 manifest | Tóm tắt provenance và phân phối nhãn |

## Provenance

`summary.json` ghi nguồn chuẩn bị cục bộ là `~/Downloads/Data_2/data` tại thời
điểm tạo file. Repo này chỉ lưu bản đã chuẩn hóa dưới `data/auxiliary/data2/`.

Data_2 có nhiều dòng mock/synthetic, đặc biệt ID bắt đầu bằng `FB-MOCK-*`:

- `seed_train_labeled.canonical.json`: {summary['train_balanced']['seed_train_labeled']['rows']} dòng, {summary['train_balanced']['seed_train_labeled']['mock_id_rows']} dòng mock ID, {summary['train_balanced']['seed_train_labeled']['unique_texts']} text unique.
- `synthetic/safety_spike_cases.canonical.json`: {summary['synthetic']['safety_spike_cases']['rows']} dòng, {summary['synthetic']['safety_spike_cases']['mock_id_rows']} dòng mock ID.

Vì vậy, folder này phải được mô tả là **auxiliary/experimental**, không phải
public-review canonical dataset.

## Cách tái tạo

```bash
python3 scripts/prepare_data2_auxiliary.py
```

Script đọc Data_2 từ `~/Downloads/Data_2/data` theo mặc định và ghi lại toàn bộ
folder này, gồm `summary.json` và README.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path.home() / "Downloads" / "Data_2" / "data"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()

    src = Path(args.source).expanduser().resolve()
    repo_root = Path(args.repo_root).resolve()
    out = repo_root / "data" / "auxiliary" / "data2"

    if not src.exists():
        raise FileNotFoundError(f"Data_2 source not found: {src}")

    datasets = {
        "seed_train_labeled": src / "train" / "seed_train_labeled.json",
        "train_split": src / "train" / "train_split.json",
        "test_split": src / "train" / "test_split.json",
    }

    summary: dict[str, Any] = {
        "source": str(src),
        "purpose": "Auxiliary Data_2 material for Safety spike tests and balanced-label model experiments.",
        "canonical_runtime_dataset": "data/processed/seed_real_clean.json",
        "train_balanced": {},
        "synthetic": {},
    }

    for name, path in datasets.items():
        rows = load_json(path)
        normalized = [normalize_row(row, data_type="data2_balanced_train_experiment") for row in rows]
        write_json(out / "train_balanced" / f"{name}.canonical.json", normalized)
        summary["train_balanced"][name] = summarize_rows(normalized)

    safety_rows = load_json(src / "synthetic" / "safety_spike_cases.json")
    safety_normalized = [normalize_row(row, data_type="data2_synthetic_safety_spike") for row in safety_rows]
    write_json(out / "synthetic" / "safety_spike_cases.canonical.json", safety_normalized)
    summary["synthetic"]["safety_spike_cases"] = summarize_rows(safety_normalized)

    for name in ["safety_keywords.json", "taxonomy.json", "routing_table.json", "severity_rules.json"]:
        copy_if_exists(src / "taxonomy" / name, out / "taxonomy" / name)

    write_json(out / "summary.json", summary)
    build_readme(out, summary)
    print(f"Prepared Data_2 auxiliary dataset under {out}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
