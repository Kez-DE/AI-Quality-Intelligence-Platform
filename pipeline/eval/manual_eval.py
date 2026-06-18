"""Manual eval harness — chạy các test case thật qua model + rule engine.

Mục đích: sinh bằng chứng eval (Gate G2) bằng OUTPUT THỰC TẾ, không mock.
Mỗi case đi qua đúng pipeline phân loại của hệ thống:
    clean.mask_pii  -> clean.clean_text -> classifier.predict_feedback (model + rules)

Chạy:
    cd pipeline
    PYTHONIOENCODING=utf-8 python eval/manual_eval.py            # in bảng
    PYTHONIOENCODING=utf-8 python eval/manual_eval.py --json     # in JSON

Kết quả đã chốt được lưu tại docs/eval-evidence.md.
"""

from __future__ import annotations

import json
import os
import sys

# Cho phép chạy từ thư mục pipeline/ (import classifier, clean, rules trực tiếp).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clean import clean_text, mask_pii  # noqa: E402
from classifier import predict_feedback  # noqa: E402

# (id, input thô, kỳ vọng/mô tả flow đang kiểm tra)
CASES = [
    (
        "TC-01",
        "Tài xế say xỉn gây tai nạn, xe tông vào người đi đường rồi bỏ chạy",
        "Safety override: phải ép Safety / negative / P5 / needs_review=true",
    ),
    (
        "TC-02",
        "App bị lỗi không đặt được xe, bấm mãi không được",
        "Lỗi ứng dụng: phải nhận topic App Issue, sentiment negative",
    ),
    (
        "TC-03",
        "Tài xế thu tiền gấp đôi, thu phí sai so với báo giá trên app",
        "Gian lận thanh toán: phải nhận topic Payment, sentiment negative",
    ),
    (
        "TC-04",
        "Tài xế thân thiện, lái xe an toàn, rất hài lòng",
        "Phản hồi tích cực: phải nhận positive / P1, không cần duyệt",
    ),
    (
        "TC-05",
        "Gọi xe mãi không có tài xế nhận chuyến ở khu vực này",
        "Thiếu cung/khó gọi xe: phải nhận sentiment negative",
    ),
    (
        "TC-06",
        "Số điện thoại của tôi là 0912345678, email abc@gmail.com, xe biển 30A-12345",
        "PII masking: phải ẩn SĐT, email và biển số trước khi phân loại",
    ),
]


def run():
    results = []
    for cid, text, expectation in CASES:
        masked = mask_pii(text)
        output = predict_feedback(clean_text(text))
        results.append(
            {
                "id": cid,
                "input": text,
                "expectation": expectation,
                "masked": masked,
                "output": output,
            }
        )
    return results


def main():
    results = run()
    if "--json" in sys.argv:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    for r in results:
        print(f"=== {r['id']} ===")
        print(f"  Kỳ vọng : {r['expectation']}")
        print(f"  Input   : {r['input']}")
        print(f"  Masked  : {r['masked']}")
        print(f"  Output  : {json.dumps(r['output'], ensure_ascii=False)}")
        print()


if __name__ == "__main__":
    main()
