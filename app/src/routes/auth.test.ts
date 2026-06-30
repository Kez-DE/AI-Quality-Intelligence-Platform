import { describe, it, expect } from "vitest";
import { validatePassword } from "./auth";

describe("validatePassword", () => {
  it("fails all on empty string", () => {
    expect(validatePassword("")).toEqual({ len: false, upper: false, lower: false, digit: false, special: false });
  });

  it("passes len only for 8 lowercase chars", () => {
    const r = validatePassword("abcdefgh");
    expect(r.len).toBe(true);
    expect(r.upper).toBe(false);
    expect(r.digit).toBe(false);
    expect(r.special).toBe(false);
  });

  it("passes all for Abc123!x", () => {
    expect(validatePassword("Abc123!x")).toEqual({ len: true, upper: true, lower: true, digit: true, special: true });
  });

  it("detects special chars", () => {
    expect(validatePassword("a@").special).toBe(true);
  });

  it("score 0 when empty", () => {
    const checks = validatePassword("");
    expect(Object.values(checks).filter(Boolean).length).toBe(0);
  });
});
