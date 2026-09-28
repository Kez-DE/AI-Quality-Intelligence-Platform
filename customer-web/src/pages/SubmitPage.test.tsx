import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import SubmitPage from "./SubmitPage";
import { AuthContext, type Auth } from "../auth";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(body: unknown) {
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({
    ok: true,
    status: 200,
    headers: new Headers(),
    json: async () => body,
  }));
  vi.stubGlobal("fetch", spy);
  return spy;
}

const submitButton = () => screen.getByRole("button", { name: "Gửi phản hồi" });

describe("SubmitPage", () => {
  it("renders the form fields and the privacy copy", () => {
    render(<SubmitPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Gửi phản hồi về chuyến đi" })).toBeTruthy();
    expect(screen.getByLabelText("Chuyện gì đã xảy ra?")).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Ứng dụng" })).toHaveProperty("checked", true);
    expect(screen.getByRole("combobox", { name: /Khu vực/ })).toBeTruthy();
    expect(screen.getByText("Không cần tài khoản.")).toBeTruthy();
    expect(screen.getByText("Số điện thoại, email, biển số được che tự động.")).toBeTruthy();
    expect(screen.getByText("Nội dung tự xoá sau 180 ngày.")).toBeTruthy();
    expect(submitButton()).toBeTruthy();
  });

  it("keeps the honeypot out of the tab order and away from autofill", () => {
    const { container } = render(<SubmitPage />);
    const honeypot = container.querySelector<HTMLInputElement>('input[name="website"]');

    expect(honeypot).not.toBeNull();
    expect(honeypot?.tabIndex).toBe(-1);
    expect(honeypot?.getAttribute("autocomplete")).toBe("off");
    expect(honeypot?.closest("[aria-hidden='true']")).not.toBeNull();
  });

  it("blocks empty and whitespace-only text without calling the backend", () => {
    const spy = stubFetch({});
    render(<SubmitPage />);

    fireEvent.click(submitButton());
    expect(screen.getAllByText("Vui lòng mô tả chuyện đã xảy ra").length).toBeGreaterThan(0);
    expect(screen.getByRole("alert")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Chuyện gì đã xảy ra?"), { target: { value: "   " } });
    fireEvent.click(submitButton());
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Chuyện gì đã xảy ra?").getAttribute("aria-invalid")).toBe("true");
  });

  it("shows only the Lookup code after sending, never AI labels", async () => {
    const spy = stubFetch({
      data: { public_ref: "8kQ2rT7xLm4A", topic: "Tài xế", severity: "P1", sentiment: "negative" },
    });
    vi.stubGlobal("scrollTo", vi.fn()); // jsdom does not implement it
    render(<SubmitPage />);

    fireEvent.change(screen.getByLabelText("Chuyện gì đã xảy ra?"), {
      target: { value: "Tài xế vượt đèn đỏ" },
    });
    fireEvent.click(submitButton());

    expect(await screen.findByRole("heading", { name: "Đã nhận phản hồi" })).toBeTruthy();
    expect(screen.getByText("8kQ2rT7xLm4A")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Xem trạng thái/ }).getAttribute("href")).toBe(
      "/status/8kQ2rT7xLm4A",
    );
    expect(screen.queryByText("Tài xế")).toBeNull();
    expect(screen.queryByText("P1")).toBeNull();
    expect(screen.queryByText("negative")).toBeNull();

    const body = JSON.parse(String(spy.mock.calls[0][1]?.body));
    expect(body).toMatchObject({ text: "Tài xế vượt đèn đỏ", channel: "app", website: "" });
  });

  describe("auth-aware submit", () => {
    async function submitAs(auth: Auth) {
      const spy = stubFetch({ data: { public_ref: "8kQ2rT7xLm4A" } });
      vi.stubGlobal("scrollTo", vi.fn());
      render(
        <AuthContext.Provider value={auth}>
          <SubmitPage />
        </AuthContext.Provider>,
      );
      fireEvent.change(screen.getByLabelText("Chuyện gì đã xảy ra?"), { target: { value: "Xe bẩn" } });
      fireEvent.click(submitButton());
      await screen.findByRole("heading", { name: "Đã nhận phản hồi" });
      const [url, init] = spy.mock.calls[0];
      return { url: String(url), headers: new Headers(init?.headers) };
    }

    it("sends the token to the customer route when logged in as a Customer account", async () => {
      const { url, headers } = await submitAs({ kind: "customer", email: "a@b.vn", token: "tok-1", userId: "u1" });
      expect(url).toMatch(/\/api\/customer\/feedback$/);
      expect(headers.get("Authorization")).toBe("Bearer tok-1");
      expect(screen.getByRole("link", { name: "Phản hồi của tôi" })).toBeTruthy();
    });

    it("uses the public route with no token when logged out", async () => {
      const { url, headers } = await submitAs({ kind: "anon" });
      expect(url).toMatch(/\/api\/public\/feedback$/);
      expect(headers.has("Authorization")).toBe(false);
    });

    it("uses the public route with no token for a staff login", async () => {
      const { url, headers } = await submitAs({ kind: "staff", email: "nv@b.vn" });
      expect(url).toMatch(/\/api\/public\/feedback$/);
      expect(headers.has("Authorization")).toBe(false);
    });

    // The 180-day redaction job covers source='public' only (decision 0018).
    it("does not promise the 180-day deletion to a Customer account", () => {
      render(
        <AuthContext.Provider value={{ kind: "customer", email: "a@b.vn", token: "tok-1", userId: "u1" }}>
          <SubmitPage />
        </AuthContext.Provider>,
      );
      expect(screen.queryByText(/180 ngày/)).toBeNull();
      expect(screen.getByText("Nội dung được lưu đến khi tài khoản bị xoá.")).toBeTruthy();
    });

    it("waits while the account role is still being checked", () => {
      render(
        <AuthContext.Provider value={{ kind: "checking", email: "a@b.vn" }}>
          <SubmitPage />
        </AuthContext.Provider>,
      );
      expect(submitButton()).toHaveProperty("disabled", true);
    });
  });
});
