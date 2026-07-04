"""Sinh review tổng hợp tiếng Việt cho 6 phòng ban (đặt đồ ăn, thanh toán, app đặt xe).

Một phần review được chèn BIỂN SỐ XE + SỐ ĐIỆN THOẠI ngay trong text để test PII-masking
(`clean.mask_pii`) và `risk_vehicle`. Xuất JSON đúng schema `ingest.py`:
    [{"text", "topic", "sentiment", "area", "source"}]

Dùng `chat_completion` trực tiếp (temperature cao, không cache) để review đa dạng — KHÔNG
qua `call_llm` (ghim temp 0.1 + LRU cache → trùng lặp). PII được chèn XÁC ĐỊNH ở tầng Python,
không phụ thuộc LLM có tuân thủ hay không.

Chạy:  python scripts/generate_synthetic_reviews.py            # 5000 dòng -> data/processed/
       python scripts/generate_synthetic_reviews.py --smoke   # 20 dòng, kiểm tra nhanh
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from agent.model_router import chat_completion  # noqa: E402
from clean import PHONE_PATTERN, LICENSE_PLATE_PATTERN  # noqa: E402  (dùng chính regex của mask_pii)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_OUT = os.path.join(REPO, "data", "processed", "synthetic_reviews_5000.json")

AREAS = [
    "HN-Cau-Giay", "HN-Dong-Da", "HN-Ha-Dong", "HN-Hoan-Kiem", "HN-Long-Bien", "HN-Tay-Ho",
    "HCM-Quan-1", "HCM-Quan-7", "HCM-Binh-Thanh", "HCM-Go-Vap", "HCM-Tan-Binh", "HCM-Thu-Duc",
    "DN-Hai-Chau", "DN-Ngu-Hanh-Son", "DN-Son-Tra", "DN-Thanh-Khe",
]

# (topic, sentiment, chủ đề gợi ý cho LLM, số lượng, xác suất chèn PII). Tổng n = 5000.
# topic khớp routing_table.json → phòng ban; sentiment 'negative' tạo volume spike.
PLAN = [
    ("App Issue",       "negative", "app đặt xe/đặt đồ ăn bị lỗi, crash, không đặt được, đăng nhập fail", 900, 0.10),  # IT
    ("Payment",         "negative", "trừ tiền sai, hoàn tiền chậm, thanh toán đồ ăn thất bại, ví lỗi",     850, 0.10),  # Tài chính & Thanh toán
    ("Pricing",         "negative", "giá cước bất thường, phụ phí ẩn, nghi gian lận giá, tính tiền sai",   850, 0.15),  # Quản lý Rủi ro & Gian lận
    ("Safety",          "negative", "tài xế chạy ẩu, phóng nhanh vượt ẩu, mất an toàn cho khách",          550, 0.60),  # Vận hành
    ("Driver Behavior", "negative", "thái độ tài xế thô lỗ, gọi điện làm phiền, đòi thêm tiền",            550, 0.60),  # Vận hành
    ("Delay",           "negative", "giao đồ ăn trễ, chờ xe quá lâu, tài xế hủy chuyến",                   450, 0.25),  # Vận hành
    ("Other",           "negative", "tổng đài/CSKH hỗ trợ kém, chờ lâu, không giải quyết",                 450, 0.25),  # CSKH
    ("Other",           "positive", "khen tính năng app, trải nghiệm tốt, góp ý cải thiện UX",             400, 0.05),  # Sản phẩm (positive override)
]

BATCH = 25          # review/lần gọi LLM
WORKERS = 8


def has_pii(text: str) -> bool:
    return bool(LICENSE_PLATE_PATTERN.search(text) or PHONE_PATTERN.search(text))


def random_plate() -> str:
    prov = random.randint(11, 99)
    letters = random.choice("ABCDEFGHKLMNPSTVXYZ")
    if random.random() < 0.4:
        letters += random.choice("ABCDEFGHKLMNPSTVXYZ")
    return f"{prov}{letters}-{random.randint(100, 999)}.{random.randint(10, 99)}"


def random_phone() -> str:
    prefix = random.choice(["09", "08", "07", "03", "05"])
    rest = "".join(str(random.randint(0, 9)) for _ in range(8))
    return f"{prefix}{rest[:2]} {rest[2:5]} {rest[5:]}"


def inject_pii(text: str) -> str:
    """Chèn biển số và/hoặc SĐT tự nhiên vào cuối review (xác định, không nhờ LLM)."""
    bits = []
    r = random.random()
    if r < 0.5 or r < 0.8:  # đa số có biển số
        bits.append(f"Biển số xe: {random_plate()}")
    if r >= 0.5:            # phần lớn kèm SĐT
        bits.append(f"SĐT tài xế: {random_phone()}")
    if not bits:
        bits.append(f"Biển số xe: {random_plate()}")
    return f"{text} ({', '.join(bits)})"


def _gen_batch(topic: str, sentiment: str, theme: str, area: str, n: int, seed: int) -> list[str]:
    sys_prompt = (
        "Bạn là người dùng Việt Nam viết đánh giá app gọi xe/giao đồ ăn (GreenSM/Xanh SM). "
        "Viết tiếng Việt tự nhiên, đa dạng độ dài và giọng điệu, như review thật trên App Store."
    )
    user = (
        f"Sinh {n} review KHÁC NHAU (seed {seed}) về: {theme}. "
        f"Sắc thái: {sentiment}. Khu vực: {area}. "
        "Không đánh số, không tiêu đề. Trả về JSON: {{\"reviews\": [\"...\", \"...\"]}} "
        f"đúng {n} phần tử, mỗi phần tử là 1 review 1-4 câu."
    )
    try:
        res = chat_completion(
            [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            response_json=True, temperature=0.9,
        )
        if res.get("provider") == "mock":
            return []
        data = json.loads(res.get("content") or "{}")
        reviews = data.get("reviews") if isinstance(data, dict) else data
        return [str(x).strip() for x in (reviews or []) if str(x).strip()]
    except Exception as exc:  # bền: 1 batch lỗi không làm vỡ cả run
        print(f"[gen] batch lỗi ({topic}/{area}): {str(exc)[:120]}")
        return []


def generate(count: int, out_path: str) -> dict:
    # Chia mỗi nhóm PLAN theo tỉ lệ để tổng = count (mặc định 5000).
    scale = count / sum(p[3] for p in PLAN)
    jobs = []  # (topic, sentiment, theme, area, n_batch, pii_prob, seed)
    seed = 0
    for topic, sentiment, theme, n, pii in PLAN:
        n = round(n * scale)
        remaining = n
        while remaining > 0:
            b = min(BATCH, remaining)
            area = AREAS[seed % len(AREAS)]
            jobs.append((topic, sentiment, theme, area, b, pii, seed))
            remaining -= b
            seed += 1

    rows: list[dict] = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {
            ex.submit(_gen_batch, t, s, th, ar, b, sd): (t, s, ar, b, pii)
            for (t, s, th, ar, b, pii, sd) in jobs
        }
        for fut in concurrent.futures.as_completed(futs):
            topic, sentiment, area, b, pii = futs[fut]
            texts = fut.result()[:b]
            for txt in texts:
                if random.random() < pii and not has_pii(txt):
                    txt = inject_pii(txt)
                rows.append({
                    "text": txt, "topic": topic, "sentiment": sentiment,
                    "area": area, "source": "synthetic",
                })
            done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"[gen] batch {done}/{len(jobs)} — rows so far: {len(rows)}")

    random.shuffle(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    pii_n = sum(1 for r in rows if has_pii(r["text"]))
    summary = {"total": len(rows), "with_pii": pii_n, "out": out_path}
    print(f"[gen] DONE {summary}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5000)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--smoke", action="store_true", help="chạy nhanh 20 dòng để kiểm tra")
    args = ap.parse_args()
    generate(20 if args.smoke else args.count, args.out)
