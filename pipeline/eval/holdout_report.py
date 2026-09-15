"""Per-class metrics + confusion matrix + Wilson CI on the holdout split.

Overall accuracy hides which class fails. This reports precision/recall/F1
per topic and per department on the SAME holdout `route_eval` gates on.

Run: cd pipeline && .venv/bin/python -m eval.holdout_report [--json]
"""
from __future__ import annotations

import json
import math
import sys

from sklearn.metrics import classification_report, confusion_matrix

from classifier import predict_feedback
from agents.router_agent import route_ticket
from eval.splits import golden_split


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval — correct for small n, unlike normal approx."""
    if n == 0:
        return (0.0, 0.0)
    p = correct / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _dept(topic, severity, sentiment) -> str:
    return route_ticket(topic, severity, sentiment, log_run=False)["team"]


def run() -> dict:
    _, holdout = golden_split()
    gold_topic, pred_topic, gold_dept, pred_dept = [], [], [], []

    for x in holdout:
        p = predict_feedback(x.get("text_full") or "")
        gold_topic.append(x.get("topic"))
        pred_topic.append(p["topic"])
        gold_dept.append(_dept(x.get("topic"), x.get("severity"), x.get("sentiment")))
        pred_dept.append(_dept(p["topic"], p["severity"], p["sentiment"]))

    n = len(holdout)
    t_ok = sum(a == b for a, b in zip(gold_topic, pred_topic))
    d_ok = sum(a == b for a, b in zip(gold_dept, pred_dept))

    return {
        "n": n,
        "topic": {
            "accuracy": t_ok / n,
            "ci95": wilson(t_ok, n),
            "report": classification_report(
                gold_topic, pred_topic, output_dict=True, zero_division=0),
            "labels": sorted(set(gold_topic) | set(pred_topic)),
            "confusion": confusion_matrix(
                gold_topic, pred_topic,
                labels=sorted(set(gold_topic) | set(pred_topic))).tolist(),
        },
        "dept": {
            "accuracy": d_ok / n,
            "ci95": wilson(d_ok, n),
            "report": classification_report(
                gold_dept, pred_dept, output_dict=True, zero_division=0),
            "labels": sorted(set(gold_dept) | set(pred_dept)),
            "confusion": confusion_matrix(
                gold_dept, pred_dept,
                labels=sorted(set(gold_dept) | set(pred_dept))).tolist(),
        },
    }


def _print(r: dict) -> None:
    for axis, title in (("topic", "TOPIC"), ("dept", "DEPARTMENT")):
        a = r[axis]
        lo, hi = a["ci95"]
        print(f"\n=== {title} — n={r['n']} ===")
        print(f"accuracy {a['accuracy']*100:.1f}%  (95% CI {lo*100:.1f}–{hi*100:.1f}%)")
        print(f"{'label':<18}{'prec':>7}{'rec':>7}{'f1':>7}{'n':>7}")
        rep = a["report"]
        for k in a["labels"]:
            m = rep.get(k)
            if not m:
                continue
            print(f"{k:<18}{m['precision']:>7.3f}{m['recall']:>7.3f}"
                  f"{m['f1-score']:>7.3f}{int(m['support']):>7}")
        for k in ("macro avg", "weighted avg"):
            m = rep[k]
            print(f"{k:<18}{m['precision']:>7.3f}{m['recall']:>7.3f}"
                  f"{m['f1-score']:>7.3f}{int(m['support']):>7}")
        print("confusion (rows=gold, cols=pred): " + ", ".join(a["labels"]))
        for lab, row in zip(a["labels"], a["confusion"]):
            print(f"  {lab:<18}{row}")


if __name__ == "__main__":
    res = run()
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        _print(res)
