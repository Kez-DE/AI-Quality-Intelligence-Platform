import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import App, { STATUS_ROUTE } from "./App";
import { navigate } from "./router";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("STATUS_ROUTE", () => {
  it("matches only /status with an optional code segment", () => {
    expect(STATUS_ROUTE.exec("/status")?.[1]).toBeUndefined();
    expect(STATUS_ROUTE.exec("/status/")?.[1]).toBe("");
    expect(STATUS_ROUTE.exec("/status/ABC123")?.[1]).toBe("ABC123");
    expect(STATUS_ROUTE.exec("/status/ABC123/")?.[1]).toBe("ABC123");
    for (const path of ["/statuss", "/status-faq", "/statusABC", "/status/a/b"]) {
      expect(STATUS_ROUTE.exec(path)).toBeNull();
    }
  });
});

describe("App routing", () => {
  it("moves focus to the new page heading on a route change", async () => {
    // jsdom implements neither; the Toaster's theme="system" reads matchMedia.
    vi.stubGlobal("scrollTo", vi.fn());
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    }));
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {}))); // status lookup stays loading
    render(<App />);
    expect(document.activeElement).toBe(document.body);

    act(() => navigate("/status/ABC123"));

    const heading = await screen.findByRole("heading", { level: 1, name: "Tra cứu phản hồi" });
    expect(document.activeElement).toBe(heading);
  });
});
