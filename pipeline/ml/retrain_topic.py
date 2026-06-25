"""Retrain topic model on the golden TRAIN split only (never the holdout).
Promote to topic_model.joblib only if it beats the current model on the holdout.
"""
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline

from eval.splits import golden_split

OUT = Path(__file__).resolve().parent / "topic_model.candidate.joblib"


def main():
    train, _ = golden_split()
    X = [d["text_full"] for d in train]
    y = [d["topic"] for d in train]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000),
        LinearSVC(class_weight="balanced"),
    )
    model.fit(X, y)
    joblib.dump(model, OUT)
    print(f"Saved candidate -> {OUT}  (trained on {len(train)} samples)")


if __name__ == "__main__":
    main()
