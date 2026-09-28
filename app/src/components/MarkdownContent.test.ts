import { describe, expect, it } from "vitest";
import { normalizeMarkdownForRendering } from "./MarkdownContent";

describe("normalizeMarkdownForRendering", () => {
  it("leaves list items alone when their pipes sit inside inline code", () => {
    // Real staff-chat answer shape (2026-09-28): tool rows quoted as inline code.
    const md =
      "*   `[P5] open | Hoàn Kiếm, Hà Nội | Tài xế gian lận`\n*   `[P5] open | Tây Hồ, Hà Nội | Tài xế gây tai nạn`";
    expect(normalizeMarkdownForRendering(md)).toBe(md);
  });

  it("still repairs a pipe table whose cells hold inline code", () => {
    expect(normalizeMarkdownForRendering("| `id` | tên |\n| `a1` | Hà Nội |")).toBe(
      "| `id` | tên |\n| --- | --- |\n| `a1` | Hà Nội |",
    );
  });
});
