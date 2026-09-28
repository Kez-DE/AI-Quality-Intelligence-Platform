import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { AuthContext, STAFF_MESSAGE, type Auth } from "./auth";

vi.mock("./supabase", () => ({
  supabase: { auth: { getSession: async () => ({ data: { session: null } }) } },
}));

const { default: ChatWidget } = await import("./ChatWidget");

const customer = (token = "tok-1", userId = "u1"): Auth => ({ kind: "customer", email: "a@b.vn", token, userId });

function renderAs(auth: Auth) {
  const widget = (a: Auth) => (
    <AuthContext.Provider value={a}>
      <ChatWidget />
    </AuthContext.Provider>
  );
  const view = render(widget(auth));
  return { rerenderAs: (a: Auth) => view.rerender(widget(a)) };
}

/** Each call answers with the next reply: a string, or an HTTP status to fail with. */
function stubChat(...replies: (string | number)[]) {
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
    const next = replies.shift() ?? "";
    const status = typeof next === "number" ? next : 200;
    return {
      ok: status === 200,
      status,
      headers: new Headers(),
      json: async () => ({ data: { content: next } }),
    };
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

const openPanel = () => fireEvent.click(screen.getByRole("button", { name: "Mở trợ lý khách hàng" }));

async function ask(q: string) {
  fireEvent.change(screen.getByLabelText("Tin nhắn"), { target: { value: q } });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Gửi" }));
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("ChatWidget", () => {
  it("reads data.content and keeps the conversation across a token refresh", async () => {
    stubChat("Chính sách hoàn tiền là 7 ngày.");
    const { rerenderAs } = renderAs(customer("tok-1"));
    openPanel();
    await ask("Hoàn tiền thế nào?");
    expect(screen.getByText("Chính sách hoàn tiền là 7 ngày.")).toBeTruthy();

    rerenderAs(customer("tok-2")); // TOKEN_REFRESHED: same account, new token
    expect(screen.getByText("Hoàn tiền thế nào?")).toBeTruthy();
    expect(screen.getByText("Chính sách hoàn tiền là 7 ngày.")).toBeTruthy();

    rerenderAs(customer("tok-3", "u2")); // a different account
    expect(screen.queryByText("Hoàn tiền thế nào?")).toBeNull();
  });

  it("survives a scrollIntoView that returns a Promise (Chrome 153)", async () => {
    // A Promise returned from an effect is taken as its cleanup; React then
    // throws "destroy is not a function" on the next run and blanks the page.
    const proto = Element.prototype as unknown as { scrollIntoView?: () => Promise<void> };
    const original = proto.scrollIntoView;
    proto.scrollIntoView = () => Promise.resolve();
    try {
      stubChat("Trả lời một.", "Trả lời hai.");
      renderAs(customer());
      openPanel();
      await ask("Câu một");
      await ask("Câu hai");
      expect(screen.getByText("Trả lời hai.")).toBeTruthy();
    } finally {
      proto.scrollIntoView = original;
    }
  });

  it("shows an error as a bubble but never sends it, or the greeting, to the model", async () => {
    const spy = stubChat(502, "Có, bạn gửi được qua đây.");
    renderAs(customer());
    openPanel();
    await ask("Câu một");
    expect(screen.getByText("Hệ thống đang bận. Vui lòng thử lại sau ít phút.")).toBeTruthy();

    await ask("Câu hai");
    const sent = JSON.parse(String(spy.mock.calls[1][1]?.body)).messages;
    expect(sent).toEqual([
      { role: "user", content: "Câu một" },
      { role: "user", content: "Câu hai" },
    ]);
  });

  it("asks a logged-out visitor to log in, focuses the panel and returns focus on close", () => {
    renderAs({ kind: "anon" });
    const fab = screen.getByRole("button", { name: "Mở trợ lý khách hàng" });
    openPanel();
    expect(screen.getByRole("link", { name: "Đăng nhập" }).getAttribute("href")).toBe("/dang-nhap");
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Trợ lý khách hàng" }));

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(fab);

    openPanel();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Đóng trợ lý" }));
    expect(document.activeElement).toBe(fab);
  });

  it("focuses the message box for a Customer account", () => {
    renderAs(customer());
    openPanel();
    expect(document.activeElement).toBe(screen.getByLabelText("Tin nhắn"));
  });

  it("tells a staff login to use the Staff web", () => {
    renderAs({ kind: "staff", email: "nv@b.vn" });
    openPanel();
    expect(screen.getByText(`${STAFF_MESSAGE}.`)).toBeTruthy();
  });

  it("offers a retry, not a login prompt, when the account check failed", () => {
    const retry = vi.fn();
    renderAs({ kind: "error", email: "a@b.vn", retry });
    openPanel();
    expect(screen.queryByRole("link", { name: "Đăng nhập" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("waits while the account is being checked", () => {
    renderAs({ kind: "checking", email: "a@b.vn" });
    openPanel();
    expect(screen.getByRole("status").textContent).toMatch(/Đang kiểm tra tài khoản/);
    expect(screen.queryByRole("link", { name: "Đăng nhập" })).toBeNull();
  });
});
