// A Supabase session is not a Customer account: the role from /api/me decides.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

type FakeSession = { access_token: string; user: { id: string; email: string } };
const session: FakeSession = { access_token: "tok-1", user: { id: "u1", email: "nv@congty.vn" } };

// What the fake Supabase client holds; each test starts logged in as `session`.
const sb = {
  session: session as FakeSession | null,
  listener: null as null | ((event: string, next: FakeSession | null) => void),
  callback: { recoveryToken: null as string | null, error: null as string | null },
  signOut: vi.fn(async (_options?: unknown) => {
    sb.session = null;
    sb.listener?.("SIGNED_OUT", null);
    return { error: null };
  }),
  signUp: vi.fn(),
};

vi.mock("./supabase", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./supabase")>()),
  supabase: {
    auth: {
      getSession: async () => ({ data: { session: sb.session } }),
      onAuthStateChange: (cb: typeof sb.listener) => {
        sb.listener = cb;
        return { data: { subscription: { unsubscribe() {} } } };
      },
      signOut: sb.signOut,
      signUp: sb.signUp,
    },
  },
  authCallback: sb.callback,
  redirectTo: (p = "/") => p,
}));

const { default: App } = await import("./App");
const { STAFF_MESSAGE } = await import("./auth");
const { parseCallback } = await import("./supabase");

/** /api/me answers with each role (or HTTP status) in turn, repeating the last. */
function stubBackend(...me: (string | number)[]) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    let status = 200;
    let body: unknown = { status: "success", data: [] };
    if (url.endsWith("/api/me")) {
      const next = me.length > 1 ? me.shift()! : me[0];
      if (typeof next === "number") status = next;
      else body = { status: "success", data: { id: "u1", email: session.user.email, role: next } };
    } else if (init?.method === "POST") {
      body = { status: "success", data: { public_ref: "8kQ2rT7xLm4A" } };
    }
    return { ok: status === 200, status, headers: new Headers(), json: async () => body };
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

async function submitForm(spy: ReturnType<typeof stubBackend>) {
  fireEvent.change(screen.getByLabelText("Chuyện gì đã xảy ra?"), { target: { value: "Xe bẩn" } });
  fireEvent.click(screen.getByRole("button", { name: "Gửi phản hồi" }));
  await screen.findByRole("heading", { name: "Đã nhận phản hồi" });
  const [url, init] = spy.mock.calls.filter(([, i]) => i?.method === "POST").at(-1)!;
  return { url: String(url), auth: new Headers(init?.headers).get("Authorization") };
}

const ACCOUNT_CHECK_FAILED = "Không kiểm tra được tài khoản.";
const SAVED_TO_ACCOUNT = "Phản hồi được lưu vào mục Phản hồi của tôi.";

beforeEach(() => {
  sb.session = session;
  sb.callback.recoveryToken = null;
  sb.callback.error = null;
  sb.signOut.mockClear();
  sb.signUp.mockReset();
  vi.stubGlobal("scrollTo", vi.fn());
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("AuthProvider role gate", () => {
  for (const role of ["staff", "pending", "manager", "admin"]) {
    it(`tells a ${role} login to use the Staff web and makes no customer API calls`, async () => {
      window.history.replaceState(null, "", "/cua-toi");
      const spy = stubBackend(role);
      render(<App />);

      expect(await screen.findByText(`${STAFF_MESSAGE}.`)).toBeTruthy();
      await act(async () => {});
      const urls = spy.mock.calls.map(([u]) => String(u));
      expect(urls.some((u) => u.endsWith("/api/me"))).toBe(true);
      expect(urls.filter((u) => u.includes("/api/customer/"))).toEqual([]);
      expect(new Headers(spy.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer tok-1");
    });
  }

  it("treats role guest as a Customer account and loads its history", async () => {
    window.history.replaceState(null, "", "/cua-toi");
    const spy = stubBackend("guest");
    render(<App />);

    expect(await screen.findByText(/Bạn chưa gửi phản hồi nào/)).toBeTruthy();
    expect(screen.queryByText(`${STAFF_MESSAGE}.`)).toBeNull();
    expect(screen.getByText("nv@congty.vn")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Đăng xuất/ })).toBeTruthy();
    expect(spy.mock.calls.some(([u]) => String(u).endsWith("/api/customer/feedback"))).toBe(true);
  });

  it("after a failed /api/me, says the form posts without the account, and retries", async () => {
    const spy = stubBackend(502, "guest");
    render(<App />);

    expect(await screen.findByText(ACCOUNT_CHECK_FAILED)).toBeTruthy();
    expect(await submitForm(spy)).toEqual({ url: expect.stringMatching(/\/api\/public\/feedback$/), auth: null });

    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    fireEvent.click(await screen.findByRole("button", { name: "Gửi phản hồi khác" }));
    expect(await screen.findByText(SAVED_TO_ACCOUNT)).toBeTruthy();
    expect(screen.queryByText(ACCOUNT_CHECK_FAILED)).toBeNull();
    expect(await submitForm(spy)).toEqual({
      url: expect.stringMatching(/\/api\/customer\/feedback$/),
      auth: "Bearer tok-1",
    });
  });

  it("drops the local session when /api/me answers 401", async () => {
    stubBackend(401);
    render(<App />);

    expect(await screen.findByRole("link", { name: "Đăng nhập" })).toBeTruthy();
    expect(sb.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(screen.queryByText("nv@congty.vn")).toBeNull();
    expect(screen.queryByText(ACCOUNT_CHECK_FAILED)).toBeNull();
  });

  it("sends the current session token, not the one React last saw", async () => {
    const spy = stubBackend("guest");
    render(<App />);
    await screen.findByText(SAVED_TO_ACCOUNT);

    // Refreshed in storage (tab resumed); TOKEN_REFRESHED has not reached React yet.
    sb.session = { ...session, access_token: "tok-2" };
    expect(await submitForm(spy)).toEqual({
      url: expect.stringMatching(/\/api\/customer\/feedback$/),
      auth: "Bearer tok-2",
    });
  });
});

describe("auth redirects", () => {
  it("parseCallback reads a recovery token and an error code from either part of the URL", () => {
    expect(parseCallback("", "#access_token=t1&type=recovery")).toEqual({ recoveryToken: "t1", error: null });
    expect(parseCallback("", "#access_token=t1&type=signup")).toEqual({ recoveryToken: null, error: null });
    expect(parseCallback("?error=access_denied&error_code=otp_expired", "")).toEqual({
      recoveryToken: null,
      error: "otp_expired",
    });
    expect(parseCallback("", "#error=server_error")).toEqual({ recoveryToken: null, error: "server_error" });
  });

  it("says why a link failed and cleans the URL", async () => {
    window.history.replaceState(null, "", "/?error=access_denied&error_code=otp_expired#error=access_denied");
    sb.callback.error = "otp_expired";
    sb.session = null;
    stubBackend("guest");
    render(<App />);

    expect(await screen.findByText(/Liên kết đã hết hạn hoặc đã được dùng/)).toBeTruthy();
    expect(window.location.search + window.location.hash).toBe("");
    expect(sb.callback.error).toBeNull();
  });
});

describe("ResetPasswordPage", () => {
  it("does not give the form to a login no recovery link opened", async () => {
    window.history.replaceState(null, "", "/dat-lai-mat-khau");
    stubBackend("guest");
    render(<App />);

    expect(await screen.findByText(/không hợp lệ hoặc đã hết hạn/)).toBeTruthy();
    await act(async () => {});
    expect(screen.queryByLabelText("Mật khẩu")).toBeNull();

    act(() => sb.listener?.("PASSWORD_RECOVERY", session));
    expect(await screen.findByLabelText("Mật khẩu")).toBeTruthy();
  });

  it("gives the form to the session opened from the recovery link's token", async () => {
    window.history.replaceState(null, "", "/dat-lai-mat-khau");
    sb.callback.recoveryToken = "tok-1";
    stubBackend("guest");
    render(<App />);

    expect(await screen.findByLabelText("Mật khẩu")).toBeTruthy();
  });
});

describe("SignupPage", () => {
  async function signUp() {
    window.history.replaceState(null, "", "/dang-ky");
    sb.session = null;
    stubBackend("guest");
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Họ và tên"), { target: { value: "An" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "an@b.vn" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "Abcdef1!" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Đăng ký" }));
    });
  }

  it("asks to confirm the email when sign-up returns no session", async () => {
    sb.signUp.mockResolvedValueOnce({ data: { session: null }, error: null });
    await signUp();
    expect(await screen.findByRole("heading", { name: "Kiểm tra email" })).toBeTruthy();
  });

  it("goes to the form when sign-up logs the Customer in", async () => {
    sb.signUp.mockImplementationOnce(async () => {
      sb.session = session;
      sb.listener?.("SIGNED_IN", session);
      return { data: { session }, error: null };
    });
    await signUp();
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(screen.queryByRole("heading", { name: "Kiểm tra email" })).toBeNull();
  });
});
