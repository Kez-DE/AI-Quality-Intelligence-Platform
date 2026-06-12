"""Retrain sentiment model — vá lỗ hổng câu ngắn.

Train trên train_split + augment_short_sentences, đo per-class recall trên
test_split GỐC (không lẫn augment) để so sánh công bằng với model cũ.

Chạy: pipeline/.venv/bin/python ml/train_sentiment.py
Model mới ghi ra ml/sentiment_model.NEW.joblib (KHÔNG ghi đè bản đang chạy).
Quyết định giữ/bỏ dựa trên output, rồi mới swap thủ công.
"""
import json
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report

PIPELINE_DIR = Path(__file__).resolve().parent.parent
DATA = PIPELINE_DIR.parent / "data" / "train"
ML = PIPELINE_DIR / "ml"


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["samples"] if isinstance(d, dict) and "samples" in d else d


def text_of(r):
    return r.get("text_full") or r.get("text") or ""


train = load(DATA / "train_split.json")
test = load(DATA / "test_split.json")
aug = load(DATA / "augment_short_sentences.json")

Xtr = [text_of(r) for r in train] + [text_of(r) for r in aug]
ytr = [r["sentiment"] for r in train] + [r["sentiment"] for r in aug]
Xte = [text_of(r) for r in test]
yte = [r["sentiment"] for r in test]

print(f"train={len(train)} + aug={len(aug)} = {len(Xtr)} | test={len(Xte)}")

# Cấu hình khớp model cũ, NHƯNG min_df=1 để câu ngắn (token hiếm) không bị loại.
pipe = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000,
                              sublinear_tf=True, lowercase=True)),
    ("clf", LinearSVC(C=1.0, class_weight="balanced", max_iter=5000)),
])
pipe.fit(Xtr, ytr)

print("\n=== MODEL MỚI — per-class trên test_split gốc ===")
pred = pipe.predict(Xte)
print(classification_report(yte, pred, digits=3))

# So sánh model cũ
old = joblib.load(ML / "sentiment_model.joblib")
print("=== MODEL CŨ — per-class trên cùng test ===")
print(classification_report(yte, old.predict(Xte), digits=3))

# Test đúng các câu ngắn gây lỗi
probes = [
    "tài xế thân thiện, nhiệt tình",
    "Tài xế thân thiện nhiệt tình",
    "thân thiện nhiệt tình",
    "App không thân thiện, rối mắt",
    "Tài xế chạy ẩu gây tai nạn",
    "Giá quá đắt",
    "Chuyến đi bình thường",
]
print("=== PROBE câu ngắn (mới vs cũ) ===")
for p in probes:
    print(f"  NEW={pipe.predict([p])[0]:>8} | OLD={old.predict([p])[0]:>8} | {p}")

joblib.dump(pipe, ML / "sentiment_model.NEW.joblib")
print(f"\nĐã ghi {ML / 'sentiment_model.NEW.joblib'} (chưa swap)")
