import { describe, expect, it } from "vitest";
import { splitAssistantBlocks } from "./assistantBlocks";

describe("splitAssistantBlocks", () => {
  it("strips inline emphasis from card titles, which render as plain text", () => {
    // Real staff-chat answer shape (2026-09-28): the model bolds its headings.
    const blocks = splitAssistantBlocks(
      "Đề xuất:\n\n### **1. Quản lý Rủi ro & Gian lận**\n\n*   **Nhận định:** P5.\n\n**Phòng Vận hành (Operations):**\n*   **Ưu tiên P0:** Rà soát.",
    );
    const titles = blocks.map((b) => b.title).filter(Boolean);
    expect(titles).toEqual(["1. Quản lý Rủi ro & Gian lận", "Phòng Vận hành (Operations):"]);
    expect(titles.join(" ")).not.toContain("*");
    // Bodies keep their markdown; MarkdownContent renders them.
    expect(blocks.some((b) => b.body.includes("**Nhận định:**"))).toBe(true);
  });
});
