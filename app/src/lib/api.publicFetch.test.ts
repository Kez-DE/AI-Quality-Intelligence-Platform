// US-076: `publicFetch` là ranh giới giữa trang công khai và backend.
//
// Hai điều khiến nó tồn tại, và đây là chỗ chúng được giữ: nó KHÔNG gắn token
// (kể cả khi người mở đang đăng nhập), và nó đọc đúng phong bì lỗi của backend
// (`{ error: { message } }`, không phải `{ detail }` mặc định của FastAPI).
import { beforeEach, describe, expect, it, vi } from "vitest";
import { publicFetch } from "./api";

function mockFetch(status: number, body: unknown) {
  // Tham số được khai báo tường minh để `spy.mock.calls[0][1]` có kiểu RequestInit.
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    statusText: "Mocked",
    json: async () => body,
  }));
  globalThis.fetch = spy as unknown as typeof fetch;
  return spy;
}

describe("publicFetch", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("never sends an Authorization header", async () => {
    const spy = mockFetch(200, { data: { public_ref: "abc123" } });

    await publicFetch("/api/public/feedback", {
      method: "POST",
      body: JSON.stringify({ text: "xe bẩn" }),
    });

    const headers = new Headers(spy.mock.calls[0][1]?.headers);
    expect(headers.has("Authorization")).toBe(false);
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("surfaces the backend error envelope, not the status text", async () => {
    mockFetch(429, {
      error: { code: "HTTP_ERROR", message: "Rate limit exceeded. Try again in 42s." },
    });

    await expect(publicFetch("/api/public/feedback")).rejects.toThrow(
      "Rate limit exceeded. Try again in 42s.",
    );
  });

  it("falls back to FastAPI's default `detail` shape", async () => {
    mockFetch(404, { detail: "Không tìm thấy phản hồi với mã này" });

    await expect(publicFetch("/api/public/feedback/nope")).rejects.toThrow(
      "Không tìm thấy phản hồi với mã này",
    );
  });

  it("falls back to status text when the body is not JSON", async () => {
    const spy = vi.fn(async () => ({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => {
        throw new Error("not json");
      },
    }));
    globalThis.fetch = spy as unknown as typeof fetch;

    await expect(publicFetch("/api/public/feedback")).rejects.toThrow("502 Bad Gateway");
  });

  it("returns the parsed body on success", async () => {
    mockFetch(200, { data: { public_ref: "8kQ2rT7xLm4A", status: "received" } });

    const json = await publicFetch<{ data: { public_ref: string } }>("/api/public/feedback");
    expect(json.data.public_ref).toBe("8kQ2rT7xLm4A");
  });
});
