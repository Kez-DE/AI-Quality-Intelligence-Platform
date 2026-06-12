import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { z } from "zod";

const InputSchema = z.object({
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant", "system"]),
        content: z.string().min(1).max(8000),
      }),
    )
    .min(1)
    .max(50),
});

const SYSTEM_PROMPT = `Bạn là AI Assistant cho Quality Operation Cockpit của xanhSM — nền tảng phân tích phản hồi & đánh giá dịch vụ smart mobility.

Vai trò:
- Giúp manager vận hành diễn giải dữ liệu phản hồi (feedback) của tài xế, xe, app, giá, thanh toán, an toàn.
- Phát hiện pattern, xu hướng bất thường theo khu vực/thời gian/tài xế/tuyến.
- Đề xuất hành động cụ thể: alert, ticket, SLA, cải tiến quy trình.

Cách trả lời:
- Trả lời bằng tiếng Việt, ngắn gọn, có cấu trúc (bullet, số liệu nếu có).
- Khi đề xuất hành động, nêu rõ độ ưu tiên (P0/P1/P2) và đối tượng chịu trách nhiệm (CS, Ops, Safety, Product, Driver Mgmt).
- Nếu thiếu dữ liệu, gợi ý câu hỏi tiếp theo hoặc nguồn cần kiểm tra.`;

export const chatWithAI = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: unknown) => InputSchema.parse(input))
  .handler(async ({ data }) => {
    const apiBase = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

    const res = await fetch(`${apiBase}/api/agent/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: [{ role: "system", content: SYSTEM_PROMPT }, ...data.messages],
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Backend agent lỗi (${res.status}): ${text.slice(0, 240)}`);
    }

    const json = (await res.json()) as {
      data?: { content?: string; provider?: string; model?: string; latency_ms?: number };
    };
    const content = json.data?.content?.trim() ?? "";
    if (!content) throw new Error("AI không trả về nội dung.");
    return {
      content,
      provider: json.data?.provider,
      model: json.data?.model,
      latency_ms: json.data?.latency_ms,
    };
  });
