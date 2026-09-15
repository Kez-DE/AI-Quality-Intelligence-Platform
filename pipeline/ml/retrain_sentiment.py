"""Retrain sentiment on the golden TRAIN split only (never the holdout).

Mirrors retrain_topic.py. The shipped sentiment_model.joblib was imported from
an earlier project with no training manifest, so dept accuracy — which depends
on predicted sentiment — could not be shown to be free of leakage.
Promote to sentiment_model.joblib only if it holds up on the holdout.
"""
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report

from eval.splits import golden_split

OUT = Path(__file__).resolve().parent / "sentiment_model.candidate.joblib"


def main():
    train, holdout = golden_split()
    X = [d["text_full"] for d in train]
    y = [d["sentiment"] for d in train]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=30000,
                        sublinear_tf=True),
        LinearSVC(class_weight="balanced"),
    )
    model.fit(X, y)
    joblib.dump(model, OUT)
    print(f"Saved candidate -> {OUT}  (trained on {len(train)} samples)")

    Xh = [d["text_full"] for d in holdout]
    yh = [d["sentiment"] for d in holdout]
    old = joblib.load(OUT.parent / "sentiment_model.joblib")
    print(f"\n--- holdout n={len(holdout)} ---")
    print(f"train-fit accuracy (candidate) = {model.score(X, y):.4f}")
    print(f"holdout   accuracy (candidate) = {model.score(Xh, yh):.4f}")
    print(f"holdout   accuracy (shipped)   = {old.score(Xh, yh):.4f}")
    print("\n=== CANDIDATE per-class on holdout ===")
    print(classification_report(yh, model.predict(Xh), digits=3, zero_division=0))
    print("=== SHIPPED per-class on holdout ===")
    print(classification_report(yh, old.predict(Xh), digits=3, zero_division=0))


if __name__ == "__main__":
    main()
