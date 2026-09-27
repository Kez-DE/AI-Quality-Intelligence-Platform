import { describe, expect, it } from "vitest";
import { formatSubmitted } from "./StatusPage";

describe("formatSubmitted", () => {
  it("reads date first, in Vietnam time", () => {
    expect(formatSubmitted("2026-09-27T05:20:00+00:00")).toBe("27 tháng 9, 2026 lúc 12:20");
  });

  it("falls back when the date is missing or invalid", () => {
    expect(formatSubmitted(null)).toBe("Không rõ");
    expect(formatSubmitted("not-a-date")).toBe("Không rõ");
  });
});
