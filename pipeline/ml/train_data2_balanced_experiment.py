"""Evaluate Data_2 balanced training as an experiment, without swapping models.

This trains temporary TF-IDF + LinearSVC classifiers from
`data/auxiliary/data2/train_balanced/` and compares them against the current
canonical test split. It writes metrics only; production `.joblib` files are not
overwritten.

Run from repo root:
    pipeline/.venv/bin/python pipeline/ml/train_data2_balanced_experiment.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
AUX = REPO_ROOT / "data" / "auxiliary" / "data2" / "train_balanced"
CANONICAL_TRAIN = REPO_ROOT / "data" / "train"
OUT = PIPELINE_DIR / "ml" / "experiments" / "data2_balanced_metrics.json"


def load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    rows = data["samples"] if isinstance(data, dict) and "samples" in data else data
    return cast(list[dict[str, Any]], rows)


def text_of(row: dict[str, Any]) -> str:
    return row.get("text_full") or row.get("text") or ""


def train_classifier(rows: list[dict[str, Any]], label: str) -> Pipeline:
    pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=30000,
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            ("clf", LinearSVC(C=1.0, class_weight="balanced", max_iter=5000)),
        ]
    )
    pipe.fit([text_of(row) for row in rows], [row[label] for row in rows])
    return pipe


def report(model, rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    y_true = [row[label] for row in rows]
    y_pred = model.predict([text_of(row) for row in rows])
    return cast(
        dict[str, Any],
        classification_report(y_true, y_pred, digits=3, output_dict=True, zero_division=0),  # type: ignore[arg-type]
    )


def main() -> None:
    aux_train = load(AUX / "train_split.canonical.json")
    aux_test = load(AUX / "test_split.canonical.json")
    canonical_test = load(CANONICAL_TRAIN / "test_split.json")

    topic_model = train_classifier(aux_train, "topic")
    sentiment_model = train_classifier(aux_train, "sentiment")

    current_topic_model = joblib.load(PIPELINE_DIR / "ml" / "topic_model.joblib")
    current_sentiment_model = joblib.load(PIPELINE_DIR / "ml" / "sentiment_model.joblib")

    metrics = {
        "purpose": "Data_2 balanced-label experiment only; production models are not overwritten.",
        "train_rows": len(aux_train),
        "aux_test_rows": len(aux_test),
        "canonical_test_rows": len(canonical_test),
        "data2_trained_model": {
            "topic_on_data2_test": report(topic_model, aux_test, "topic"),
            "sentiment_on_data2_test": report(sentiment_model, aux_test, "sentiment"),
            "topic_on_canonical_test": report(topic_model, canonical_test, "topic"),
            "sentiment_on_canonical_test": report(sentiment_model, canonical_test, "sentiment"),
        },
        "current_production_model": {
            "topic_on_canonical_test": report(current_topic_model, canonical_test, "topic"),
            "sentiment_on_canonical_test": report(current_sentiment_model, canonical_test, "sentiment"),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {OUT}")
    print("Key metrics:")
    print(
        "  Data_2-trained topic macro-F1 on canonical test:",
        round(metrics["data2_trained_model"]["topic_on_canonical_test"]["macro avg"]["f1-score"], 3),
    )
    print(
        "  Current topic macro-F1 on canonical test:",
        round(metrics["current_production_model"]["topic_on_canonical_test"]["macro avg"]["f1-score"], 3),
    )
    print(
        "  Data_2-trained sentiment macro-F1 on canonical test:",
        round(metrics["data2_trained_model"]["sentiment_on_canonical_test"]["macro avg"]["f1-score"], 3),
    )
    print(
        "  Current sentiment macro-F1 on canonical test:",
        round(metrics["current_production_model"]["sentiment_on_canonical_test"]["macro avg"]["f1-score"], 3),
    )


if __name__ == "__main__":
    main()
