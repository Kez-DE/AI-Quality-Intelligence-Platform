"""Eval harness: đo độ chính xác định tuyến trên golden set có nhãn topic.

Chạy: cd pipeline && .venv/bin/python -m eval.route_eval [--json]
Dùng làm oracle cho mọi chỉnh sửa rules.py / routing_table.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from core.paths import DATA_DIR
from classifier import predict_feedback
from agents.router_agent import route_ticket

GOLDEN_PATH = DATA_DIR / "train" / "seed_train_labeled.json"


def load_golden(path: str | None = None) -> list[dict]:
    with open(path or GOLDEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _dept(topic, severity, sentiment) -> str:
    return route_ticket(topic, severity, sentiment, log_run=False)["team"]


def evaluate(samples: list[dict]) -> dict:
    n = len(samples)
    topic_ok = 0
    dept_ok = 0
    topic_confusion: Counter = Counter()
    dept_confusion: Counter = Counter()
    gold_dept_dist: Counter = Counter()
    pred_dept_dist: Counter = Counter()

    for x in samples:
        text = x.get("text_full") or ""
        gt = x.get("topic")
        gsev = x.get("severity")
        gsent = x.get("sentiment")

        pred = predict_feedback(text)
        pt = pred["topic"]
        psev = pred["severity"]
        psent = pred["sentiment"]

        if pt == gt:
            topic_ok += 1
        gd = _dept(gt, gsev, gsent)
        pd = _dept(pt, psev, psent)
        if pd == gd:
            dept_ok += 1

        topic_confusion[(gt, pt)] += 1
        dept_confusion[(gd, pd)] += 1
        gold_dept_dist[gd] += 1
        pred_dept_dist[pd] += 1

    return {
        "n": n,
        "topic_accuracy": topic_ok / n if n else 0.0,
        "dept_accuracy": dept_ok / n if n else 0.0,
        "topic_confusion": dict(topic_confusion),
        "dept_confusion": dict(dept_confusion),
        "gold_dept_dist": dict(gold_dept_dist),
        "pred_dept_dist": dict(pred_dept_dist),
    }


def _print_report(r: dict) -> None:
    print(f"N = {r['n']}")
    print(f"TOPIC accuracy:      {r['topic_accuracy'] * 100:.1f}%")
    print(f"DEPARTMENT accuracy: {r['dept_accuracy'] * 100:.1f}%")
    print("\nGold dept distribution (tải đúng):")
    for k, v in sorted(r["gold_dept_dist"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print("Predicted dept distribution (tải thực tế):")
    for k, v in sorted(r["pred_dept_dist"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print("\nTop topic misroutes (gold -> pred, >=20):")
    for (g, p), v in sorted(r["topic_confusion"].items(), key=lambda kv: -kv[1]):
        if g != p and v >= 20:
            print(f"  {v:5d}  {g:16s} -> {p}")
    print("\nTop department misroutes (gold -> pred, >=20):")
    for (g, p), v in sorted(r["dept_confusion"].items(), key=lambda kv: -kv[1]):
        if g != p and v >= 20:
            print(f"  {v:5d}  {g:10s} -> {p}")


if __name__ == "__main__":
    result = evaluate(load_golden())
    if "--json" in sys.argv:
        serializable = {
            k: (v if not isinstance(v, dict) or not v or not isinstance(next(iter(v)), tuple)
                else {f"{a}->{b}": c for (a, b), c in v.items()})
            for k, v in result.items()
        }
        print(json.dumps(serializable, ensure_ascii=False, indent=2))
    else:
        _print_report(result)
