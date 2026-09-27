// The API client is the whole trust boundary of the Customer web: it must never
// send credentials, must carry the honeypot, and must turn every failure into
// Vietnamese a Customer can act on.
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  NETWORK_MESSAGE,
  STATUS_LABEL,
  TIMEOUT_MESSAGE,
  getFeedbackStatus,
  statusLabel,
  submitFeedback,
} from "./api";

function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: async () => body,
  }));
  vi.stubGlobal("fetch", spy);
  return spy;
}

const input = { text: "xe bẩn", channel: "app", area: "", website: "" };

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("submitFeedback", () => {
  it("sends no Authorization header and no cookies", async () => {
    const spy = mockFetch(200, { data: { public_ref: "8kQ2rT7xLm4A" } });

    await submitFeedback(input);

    const init = spy.mock.calls[0][1];
    const headers = new Headers(init?.headers);
    expect(headers.has("Authorization")).toBe(false);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(init?.credentials).toBe("omit");
  });

  it("posts the honeypot field in the body", async () => {
    const spy = mockFetch(200, { data: { public_ref: "8kQ2rT7xLm4A" } });

    await submitFeedback({ ...input, website: "" });

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/public\/feedback$/);
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({ text: "xe bẩn", channel: "app", area: "", website: "" });
    expect(Object.hasOwn(body, "website")).toBe(true);
  });

  it("returns only the Lookup code it needs", async () => {
    mockFetch(200, { data: { public_ref: "8kQ2rT7xLm4A", status: "received" } });
    await expect(submitFeedback(input)).resolves.toMatchObject({ public_ref: "8kQ2rT7xLm4A" });
  });
});

describe("error mapping", () => {
  it("maps 400 (honeypot or empty text) to Vietnamese", async () => {
    mockFetch(400, { error: { code: "HTTP_ERROR", message: "Invalid submission" } });
    await expect(submitFeedback(input)).rejects.toThrow(
      "Phản hồi chưa hợp lệ. Vui lòng kiểm tra nội dung rồi gửi lại.",
    );
  });

  it("maps 404 to the not-found message and keeps the status", async () => {
    mockFetch(404, { error: { message: "Không tìm thấy phản hồi với mã này" } });
    const err = await getFeedbackStatus("nope").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(404);
    expect((err as ApiError).message).toBe("Không tìm thấy phản hồi với mã này.");
  });

  it("maps 429 to Vietnamese with the Retry-After wait in minutes", async () => {
    mockFetch(429, { error: { message: "Rate limit exceeded. Try again in 120s." } }, {
      "Retry-After": "120",
    });
    await expect(submitFeedback(input)).rejects.toThrow(
      "Bạn đã thao tác quá nhiều lần. Vui lòng thử lại sau khoảng 2 phút.",
    );
  });

  it("maps 429 without Retry-After to a vague wait", async () => {
    mockFetch(429, {});
    await expect(submitFeedback(input)).rejects.toThrow("Vui lòng thử lại sau ít phút.");
  });

  it("maps a network failure to Vietnamese", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const err = await submitFeedback(input).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(0);
    expect((err as ApiError).message).toBe(NETWORK_MESSAGE);
  });

  it("maps a timeout to Vietnamese", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_input: RequestInfo | URL, init?: RequestInit) =>
          new Promise((_resolve, reject) =>
            init?.signal?.addEventListener("abort", () => reject(new DOMException("", "AbortError"))),
          ),
      ),
    );
    const pending = submitFeedback(input).catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(15_000);
    expect(((await pending) as ApiError).message).toBe(TIMEOUT_MESSAGE);
  });

  it("maps a 5xx to a generic busy message", async () => {
    mockFetch(503, { error: { message: "Không lưu được phản hồi" } });
    await expect(submitFeedback(input)).rejects.toThrow("Hệ thống đang bận");
  });
});

describe("status labels", () => {
  it("maps every Feedback status value to its Vietnamese label", () => {
    expect(STATUS_LABEL).toEqual({
      received: "Đã tiếp nhận",
      under_review: "Đang xem xét",
      reviewed: "Đã xem xét",
    });
    expect(statusLabel("received")).toBe("Đã tiếp nhận");
    expect(statusLabel("under_review")).toBe("Đang xem xét");
    expect(statusLabel("reviewed")).toBe("Đã xem xét");
  });

  it("never shows a raw or retired value such as 'resolved'", () => {
    expect(statusLabel("resolved")).toBe("Đang cập nhật");
    expect(statusLabel("")).toBe("Đang cập nhật");
  });
});
