import os
import requests

def send_webhook_alert(title: str, severity: str, area: str, description: str):
    """
    Gửi thông báo tới kênh chat nội bộ (Slack/Zalo/Discord) qua Webhook.
    Chỉ gửi cho các Ticket có severity P5/Critical.
    """
    webhook_url = os.getenv("WEBHOOK_URL")
    
    payload = {
        "text": f"🚨 *CẢNH BÁO KHẨN CẤP (P5)* 🚨\n"
                f"**Khu vực:** {area}\n"
                f"**Tiêu đề:** {title}\n"
                f"**Chi tiết:** {description}\n"
                f"Yêu cầu các quản lý khu vực kiểm tra và xử lý ngay lập tức!"
    }

    if not webhook_url:
        print("[Webhook Notifier] Không tìm thấy cấu hình WEBHOOK_URL. In ra log thay vì gửi:")
        print(payload["text"])
        return True

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[Webhook Notifier] Đã gửi cảnh báo P5 cho {area} thành công.")
        return True
    except Exception as e:
        print(f"[Webhook Notifier] Lỗi khi gửi webhook: {e}")
        return False
