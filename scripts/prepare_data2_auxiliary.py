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
    readme = f"""# Data_2 auxiliary dataset

This folder intentionally keeps Data_2 separate from the canonical runtime dataset.

## Decision

- Canonical runtime dataset remains `data/processed/seed_real_clean.json`.
- Data_2 is used only as an auxiliary dataset for:
  - synthetic Safety spike testing;
  - balanced-label model experiments;
  - taxonomy / safety-keyword reference.

Do **not** replace `data/processed/seed_real_clean.json` with files from this folder without a separate migration and evaluation pass.

## Contents

```text
synthetic/safety_spike_cases.canonical.json
train_balanced/seed_train_labeled.canonical.json
train_balanced/train_split.canonical.json
train_balanced/test_split.canonical.json
taxonomy/safety_keywords.json
taxonomy/taxonomy.json
taxonomy/routing_table.json
taxonomy/severity_rules.json
summary.json
```

## Provenance rule

Rows in this folder come from `~/Downloads/Data_2`. Data_2 includes mock/synthetic rows, especially IDs starting with `FB-MOCK-*`. Therefore this folder must be described as **auxiliary**, not as the main public-review dataset.

## Generated summary

- Balanced labeled rows: {summary['train_balanced']['seed_train_labeled']['rows']}
- Balanced labeled mock rows: {summary['train_balanced']['seed_train_labeled']['mock_id_rows']}
- Balanced labeled unique texts: {summary['train_balanced']['seed_train_labeled']['unique_texts']}
- Safety spike rows: {summary['synthetic']['safety_spike_cases']['rows']}

Regenerate with:

```bash
python3 scripts/prepare_data2_auxiliary.py
```
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
