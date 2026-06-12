// Nhãn hiển thị tiếng Việt cho toàn app.
// Giá trị canonical (EN) vẫn lưu DB + dùng cho logic (spike, agents, rules);
// đây CHỈ là lớp hiển thị — không đổi dữ liệu, không phá so sánh nội bộ.

// Cảm xúc
const SENTIMENT_VI: Record<string, string> = {
  negative: "Tiêu cực",
  neutral: "Trung tính",
  positive: "Tích cực",
};

// Chủ đề (khớp 7 lớp classifier)
const TOPIC_VI: Record<string, string> = {
  Safety: "An toàn",
  "Driver Behavior": "Tài xế",
  "App Issue": "Ứng dụng",
  Payment: "Thanh toán",
  Pricing: "Giá cước",
  Delay: "Chậm trễ",
  Other: "Khác",
};

// Kênh tiếp nhận
const CHANNEL_VI: Record<string, string> = {
  app: "Ứng dụng",
  rating: "Đánh giá",
  hotline: "Tổng đài",
  cs: "CSKH",
  survey: "Khảo sát",
};

export function sentimentLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return SENTIMENT_VI[value] ?? value;
}

export function topicLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return TOPIC_VI[value] ?? value;
}

export function channelLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return CHANNEL_VI[value] ?? value;
}

// Severity giữ mã P1..P5 (chuẩn quốc tế, ngắn gọn) + mô tả tiếng Việt khi cần.
const SEVERITY_VI: Record<string, string> = {
  P1: "P1 · Nhẹ",
  P2: "P2 · Thấp",
  P3: "P3 · Trung bình",
  P4: "P4 · Cao",
  P5: "P5 · Nghiêm trọng",
};

export function severityLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return SEVERITY_VI[value] ?? value;
}
