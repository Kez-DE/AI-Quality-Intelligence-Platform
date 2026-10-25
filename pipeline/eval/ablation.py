"""Đo lại bảng bóc tách trên MỘT đáp án cố định.

Đáp án = route_ticket(gold_topic, gold_sev, gold_sent) — đầy đủ cả hai quy tắc.
Bốn cấu hình dự đoán được chấm trên đúng đáp án đó, nên chúng so sánh được với nhau.
"""
import sys; sys.path.insert(0, ".")
from collections import Counter
from eval.splits import golden_split
from agents.router_agent import route_ticket
from classifier import predict_feedback

_, holdout = golden_split()
N = len(holdout)

def dept(topic, sev, sent):
    return route_ticket(topic, sev, sent, log_run=False)["team"]

rows = []
for x in holdout:
    gt, gs, gse = x.get("topic"), x.get("severity"), x.get("sentiment")
    p = predict_feedback(x.get("text_full") or "")
    rows.append((dept(gt, gs, gse), p["topic"], p["severity"], p["sentiment"], gt))

NEU = "neutral"          # cảm xúc trung tính => quy tắc ghi đè cảm xúc không kích hoạt
P3  = 3                  # mức thường => quy tắc ghi đè P5 không kích hoạt

configs = {
    "chỉ bảng chủ đề (bỏ cả hai)": lambda t, s, se: dept(t, P3,  NEU),
    "+ ghi đè P5":                 lambda t, s, se: dept(t, s,   NEU),
    "+ ghi đè cảm xúc":            lambda t, s, se: dept(t, P3,  se),
    "đầy đủ cả hai":               lambda t, s, se: dept(t, s,   se),
}
print(f"n = {N}   đáp án cố định = route_ticket(nhãn vàng đầy đủ)\n")
acc = {}
for name, f in configs.items():
    ok = sum(1 for gd, pt, ps, pse, _ in rows if f(pt, ps, pse) == gd)
    acc[name] = ok
    print(f"  {name:32} {ok/N*100:5.1f}%   ({ok}/{N})")

full = acc["đầy đủ cả hai"]; base = acc["chỉ bảng chủ đề (bỏ cả hai)"]
print(f"\n  Giá tầng ghi đè (đầy đủ - chỉ bảng) = {(full-base)/N*100:+.1f} điểm")

# bỏ-từng-cái + đếm b/c cho McNemar
print("\n  Bỏ-từng-cái so với cấu hình đầy đủ:")
for name in ("+ ghi đè P5", "+ ghi đè cảm xúc"):
    f = configs[name]
    b = c = 0
    for gd, pt, ps, pse, _ in rows:
        a_ok = f(pt, ps, pse) == gd
        f_ok = configs["đầy đủ cả hai"](pt, ps, pse) == gd
        if f_ok and not a_ok: b += 1
        if a_ok and not f_ok: c += 1
    print(f"    {name:20} {acc[name]/N*100:5.1f}%  | đầy đủ sửa đúng thêm b={b}, làm sai c={c}")

# quy tắc P5 có kích hoạt lần nào không
p5_pred = sum(1 for _,_,ps,_,_ in rows if str(ps).upper().lstrip("P") == "5")
p5_gold = sum(1 for x in holdout if str(x.get("severity")).upper().lstrip("P") == "5")
print(f"\n  Bản ghi đạt mức 5:  nhãn vàng = {p5_gold}   dự đoán = {p5_pred}")
