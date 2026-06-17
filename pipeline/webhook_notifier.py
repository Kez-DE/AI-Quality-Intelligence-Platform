import httpx
from env_config import get_settings

def send_alert_webhook(title: str, message: str, severity: str = "medium", area: str = "general") -> bool:
    """Gửi cảnh báo đến Webhook (Discord/Slack/Teams) khi có bất thường."""
    webhook_url = get_settings().webhook_url
    
    payload = {
        "text": f"🚨 *CẢNH BÁO KHẨN CẤP ({severity.upper()})* 🚨\n"
                f"**Khu vực:** {area}\n"
                f"**Tiêu đề:** {title}\n"
                f"**Chi tiết:** {message}\n"
                f"Yêu cầu các quản lý khu vực kiểm tra và xử lý ngay lập tức!"
    }

    if not webhook_url:
        print("[Webhook Notifier] Không tìm thấy cấu hình WEBHOOK_URL. In ra log thay vì gửi:")
        print(payload["text"])
        return True

    try:
        response = httpx.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[Webhook Notifier] Đã gửi cảnh báo {severity.upper()} cho {area} thành công.")
        return True
    except Exception as e:
        print(f"[Webhook Notifier] Lỗi khi gửi webhook: {e}")
        return False
