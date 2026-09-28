import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import MyFeedbackPage from "./MyFeedbackPage";
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

const customer = (token = "tok"): Auth => ({ kind: "customer", email: "a@b.vn", token, userId: "u1" });

function renderAs(auth: Auth) {
  const page = (a: Auth) => (
    <AuthContext.Provider value={a}>
      <MyFeedbackPage />
    </AuthContext.Provider>
  );
  const view = render(page(auth));
  return { ...view, rerenderAs: (a: Auth) => view.rerender(page(a)) };
}

describe("MyFeedbackPage", () => {
  it("lists own Feedback with status and link, never AI labels", async () => {
    const spy = stubFetch({
      data: [
        {
          public_ref: "8kQ2rT7xLm4A",
          status: "under_review",
          created_at: "2026-09-27T05:20:00Z",
          text: "Tài xế vượt đèn đỏ",
          topic: "An toàn",
          sentiment: "negative",
          severity: "P1",
        },
      ],
    });
    renderAs(customer());

    // A short link name (code, status); the text is its description, not its name.
    const link = await screen.findByRole("link", { name: /^Mã 8kQ2rT7xLm4A, Đang xem xét,/ });
    expect(link.getAttribute("href")).toBe("/status/8kQ2rT7xLm4A");
    expect(screen.getByRole("link", { description: "Tài xế vượt đèn đỏ" })).toBe(link);
    expect(screen.queryByRole("link", { name: /Tài xế/ })).toBeNull();
    expect(screen.getByText("Đang xem xét")).toBeTruthy();
    for (const label of ["An toàn", "negative", "P1"]) expect(screen.queryByText(label, { exact: false })).toBeNull();
    expect(document.body.textContent).not.toMatch(/An toàn|negative|P1|Tiêu cực|Mức độ|Chủ đề/);

    expect(new Headers(spy.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer tok");
  });

  it("shows an empty state", async () => {
    stubFetch({ data: [] });
    renderAs(customer());
    expect(await screen.findByText(/Bạn chưa gửi phản hồi nào/)).toBeTruthy();
  });

  it("does not refetch when only the token is refreshed", async () => {
    const spy = stubFetch({ data: [] });
    const { rerenderAs } = renderAs(customer("tok-1"));
    await screen.findByText(/Bạn chưa gửi phản hồi nào/);

    rerenderAs(customer("tok-2"));
    expect(screen.getByText(/Bạn chưa gửi phản hồi nào/)).toBeTruthy();
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("asks a logged-out visitor to log in and calls nothing", () => {
    const spy = stubFetch({});
    renderAs({ kind: "anon" });
    expect(screen.getByRole("link", { name: "Đăng nhập" }).getAttribute("href")).toBe("/dang-nhap");
    expect(spy).not.toHaveBeenCalled();
  });
});
