import { describe, it, expect } from "vitest";
import { linkifyCitations, srcTitle, srcContent } from "@/components/SourceCitation";

describe("SourceCitation helpers", () => {
  it("linkify [Nguồn N] -> markdown link #src-N", () => {
    expect(linkifyCitations("theo [Nguồn 1] và [Nguồn 12]")).toBe(
      "theo [Nguồn 1](#src-1) và [Nguồn 12](#src-12)",
    );
  });

  it("linkify chịu khoảng trắng và hoa/thường, không đụng text khác", () => {
    expect(linkifyCitations("[ Nguồn 3 ] xong")).toBe("[Nguồn 3](#src-3) xong");
    expect(linkifyCitations("không có trích dẫn")).toBe("không có trích dẫn");
  });

  it("srcTitle ưu tiên title, fallback document_title rồi mặc định", () => {
    expect(srcTitle({ title: "A" })).toBe("A");
    expect(srcTitle({ document_title: "B" })).toBe("B");
    expect(srcTitle({})).toBe("Tài liệu nội bộ");
  });

  it("srcContent trả content hoặc chuỗi rỗng", () => {
    expect(srcContent({ content: "x" })).toBe("x");
    expect(srcContent({})).toBe("");
  });
});
