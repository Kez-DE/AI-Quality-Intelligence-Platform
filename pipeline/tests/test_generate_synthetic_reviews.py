"""Kiểm tra phần xác định của generator (không gọi LLM): định dạng PII + phân bổ PLAN."""
import importlib.util
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_synthetic_reviews.py")
_spec = importlib.util.spec_from_file_location("gen_reviews", _PATH)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

VALID_TOPICS = {"App Issue", "Payment", "Pricing", "Safety", "Driver Behavior", "Delay", "Other"}


def test_generated_pii_is_detectable_by_real_mask_pii():
    # Biển số/SĐT sinh ra PHẢI bị mask_pii ẩn đi (dùng chính regex của clean.py).
    from clean import mask_pii
    for _ in range(50):
        assert "[BIỂN_SỐ_ĐÃ_ẨN]" in mask_pii(f"xe {gen.random_plate()} chạy ẩu"), "biển số ko bị mask"
        assert "[SĐT_ĐÃ_ẨN]" in mask_pii(f"gọi {gen.random_phone()} nhé"), "SĐT ko bị mask"


def test_inject_pii_always_adds_detectable_pii():
    for _ in range(50):
        out = gen.inject_pii("Tài xế chạy ẩu, thái độ kém.")
        assert gen.has_pii(out)


def test_plan_topics_valid_and_scales_to_5000():
    assert all(t in VALID_TOPICS for (t, *_rest) in gen.PLAN)
    scale = 5000 / sum(p[3] for p in gen.PLAN)
    total = sum(round(n * scale) for (_t, _s, _th, n, _pii) in gen.PLAN)
    assert abs(total - 5000) <= 2  # sai số làm tròn nhỏ
    # đủ 6 phòng: cả positive-Other (Sản phẩm) lẫn các topic negative đều có mặt
    assert ("Other", "positive") in [(t, s) for (t, s, *_r) in gen.PLAN]
