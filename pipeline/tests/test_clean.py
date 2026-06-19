import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clean import mask_pii


def test_mask_pii_preserves_public_greensm_support_email():
    text = "Liên hệ support.vn@greensm.com hoặc DPOoffice@greensm.com khi cần hỗ trợ."

    masked = mask_pii(text)

    assert "support.vn@greensm.com" in masked
    assert "DPOoffice@greensm.com" in masked


def test_mask_pii_still_masks_customer_email():
    text = "Email của tôi là khachhang@gmail.com, hãy phản hồi giúp tôi."

    masked = mask_pii(text)

    assert "khachhang@gmail.com" not in masked
    assert "[EMAIL_ĐÃ_ẨN]" in masked
