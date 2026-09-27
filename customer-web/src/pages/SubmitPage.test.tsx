import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import SubmitPage from "./SubmitPage";

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
});
