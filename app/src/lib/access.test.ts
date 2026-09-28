import { describe, it, expect } from "vitest";
import { staffWebGate, toRole } from "./access";

const gate = (role: unknown, pathname: string, mustChangePassword = false) =>
  staffWebGate({ role, pathname, mustChangePassword });

describe("toRole", () => {
  it("keeps the three Staff roles", () => {
    expect(toRole("admin")).toBe("admin");
    expect(toRole("manager")).toBe("manager");
    expect(toRole("staff")).toBe("staff");
  });

  it("keeps guest (Customer account)", () => {
    expect(toRole("guest")).toBe("guest");
  });

  it("fails closed to pending for anything else", () => {
    for (const v of ["pending", "", "Admin", "Guest", null, undefined, 42]) {
      expect(toRole(v)).toBe("pending");
    }
  });
});

describe("staffWebGate", () => {
  it("forces the password change first, even for admin or pending", () => {
    expect(gate("admin", "/dashboard", true)).toBe("change-password");
    expect(gate("pending", "/dashboard", true)).toBe("change-password");
    expect(gate("guest", "/dashboard", true)).toBe("change-password");
    expect(gate("staff", "/admin", true)).toBe("change-password");
  });

  it("shows only the waiting screen to a Pending account, on every path", () => {
    for (const p of ["/dashboard", "/feedback", "/chat", "/admin"]) {
      expect(gate("pending", p)).toBe("pending");
    }
  });

  it("treats a missing role as pending", () => {
    expect(gate(null, "/dashboard")).toBe("pending");
  });

  it("sends a Customer account (guest) to the customer screen on every path", () => {
    for (const p of ["/dashboard", "/feedback", "/chat", "/admin", "/support"]) {
      expect(gate("guest", p)).toBe("customer");
    }
  });

  it("lets admin open every route", () => {
    for (const p of ["/dashboard", "/admin", "/insights", "/reports", "/completion-reports"]) {
      expect(gate("admin", p)).toBe("allow");
    }
  });

  it("blocks manager from /admin only", () => {
    expect(gate("manager", "/admin")).toBe("to-dashboard");
    expect(gate("manager", "/insights")).toBe("allow");
    expect(gate("manager", "/reports")).toBe("allow");
    expect(gate("manager", "/alerts")).toBe("allow");
  });

  it("blocks staff from admin and analytics routes, including sub-paths", () => {
    for (const p of ["/admin", "/insights", "/reports", "/completion-reports", "/reports/abc"]) {
      expect(gate("staff", p)).toBe("to-dashboard");
    }
    for (const p of [
      "/dashboard",
      "/feedback",
      "/feedback/upload",
      "/tasks",
      "/support",
      "/chat",
    ]) {
      expect(gate("staff", p)).toBe("allow");
    }
  });
});
