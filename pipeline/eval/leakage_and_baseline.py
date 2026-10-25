import sys; sys.path.insert(0, ".")
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from eval.splits import golden_split
from agents.router_agent import route_ticket

train, hold = golden_split()
Xtr = [d["text_full"] for d in train]; Xho = [d["text_full"] for d in hold]

print("=== 1. Trùng lặp gần giữa tập huấn luyện và tập giữ lại ===")
v = TfidfVectorizer(ngram_range=(1,2), min_df=1).fit(Xtr + Xho)
A, B = v.transform(Xho), v.transform(Xtr)
sim = (A @ B.T).max(axis=1).toarray().ravel()
for t in (0.99, 0.95, 0.90):
    n = int((sim >= t).sum())
    print(f"  cosine >= {t}: {n}/{len(Xho)} = {n/len(Xho)*100:.1f}%")
print(f"  trung vị tương đồng lớn nhất = {np.median(sim):.3f}")

print("\n=== 2. Đường cơ sở: SVC học THẲNG nhãn phòng ban ===")
dept = lambda d: route_ticket(d.get("topic"), d.get("severity"), d.get("sentiment"), log_run=False)["team"]
ytr = [dept(d) for d in train]; yho = [dept(d) for d in hold]
m = make_pipeline(TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=50000),
                  LinearSVC(class_weight="balanced"))
m.fit(Xtr, ytr)
acc = float(np.mean(np.array(m.predict(Xho)) == np.array(yho)))
print(f"  SVC -> phòng ban trực tiếp : {acc*100:.1f}%  ({int(acc*len(yho))}/{len(yho)})")
print(f"  đường ống hiện tại          : 71.1%  (688/968)")
print(f"  chênh                       : {acc*100-71.1:+.1f} điểm")
