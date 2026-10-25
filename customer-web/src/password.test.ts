import { describe, it, expect } from "vitest";
import { isStrongPassword, validatePassword } from "./password";

describe("validatePassword", () => {
  it("fails all on empty string", () => {
    expect(validatePassword("")).toEqual({
      len: false,
      upper: false,
      lower: false,
      digit: false,
      special: false,
    });
  });

  it("passes len only for 8 lowercase chars", () => {
    const r = validatePassword("abcdefgh");
    expect(r.len).toBe(true);
    expect(r.upper).toBe(false);
    expect(r.digit).toBe(false);
    expect(r.special).toBe(false);
  });

  it("passes all for Abc123!x", () => {
    expect(validatePassword("Abc123!x")).toEqual({
      len: true,
      upper: true,
      lower: true,
      digit: true,
      special: true,
    });
  });

  it("detects special chars", () => {
    expect(validatePassword("a@").special).toBe(true);
  });

  it("score 0 when empty", () => {
    const checks = validatePassword("");
    expect(Object.values(checks).filter(Boolean).length).toBe(0);
  });
});

describe("isStrongPassword", () => {
  it("accepts a password that meets all 5 criteria", () => {
    expect(isStrongPassword("Abc123!x")).toBe(true);
  });

  it("rejects when any single criterion is missing", () => {
    expect(isStrongPassword("Abc123!")).toBe(false); // 7 chars
    expect(isStrongPassword("abc123!x")).toBe(false); // no upper
    expect(isStrongPassword("ABC123!X")).toBe(false); // no lower
    expect(isStrongPassword("Abcdef!x")).toBe(false); // no digit
    expect(isStrongPassword("Abc123xy")).toBe(false); // no special
  });
});
