import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clean import mask_pii, sanitize_pii_payload


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


def test_mask_pii_masks_common_phone_and_license_plate_formats():
    samples = [
        "Gọi 0912345678, xe 30A-12345",
        "Gọi +84 912 345 678, xe 51F-123.45",
        "Gọi 84-912-345-678, xe 59X1 123.45",
        "Gọi 028 3822 9999, xe 80NG-123.45",
    ]

    for sample in samples:
        masked = mask_pii(sample)
        assert "[SĐT_ĐÃ_ẨN]" in masked
        assert "[BIỂN_SỐ_ĐÃ_ẨN]" in masked
        assert "912" not in masked
        assert "123.45" not in masked


def test_sanitize_pii_payload_is_recursive_and_does_not_mutate_input():
    payload = {
        "content": "SĐT 0912345678",
        "tool_calls": [{"function": {"arguments": '{"plate":"30A-12345"}'}}],
    }

    sanitized = sanitize_pii_payload(payload)

    assert sanitized["content"] == "SĐT [SĐT_ĐÃ_ẨN]"
    assert "[BIỂN_SỐ_ĐÃ_ẨN]" in sanitized["tool_calls"][0]["function"]["arguments"]
    assert payload["content"] == "SĐT 0912345678"
