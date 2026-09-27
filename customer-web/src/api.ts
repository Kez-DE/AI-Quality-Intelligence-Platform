// Anonymous client for the two public backend routes (US-076, US-077).
//
// Copied from `publicFetch` in app/src/lib/api.ts, then narrowed for the
// Customer web:
// - A Customer has no account, so nothing here ever attaches Authorization.
// - The browser calls the backend directly. The public rate limit keys on the
//   client IP, so a proxy in front would put every Customer in one bucket.
// - Errors are mapped from the HTTP status to Vietnamese copy. The backend's
//   own messages are partly English (the 429 and the honeypot 400).

export const API_BASE = (import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

export const MAX_TEXT = 4000;

export type StatusValue = "received" | "under_review" | "reviewed";

export type FeedbackStatus = {
  public_ref: string;
  status: StatusValue;
  created_at: string | null;
};

export type SubmitInput = {
  text: string;
  channel: string;
  area: string;
  /** Honeypot. Humans leave it empty; the backend rejects anything else. */
  website: string;
};

export const STATUS_LABEL: Record<StatusValue, string> = {
  received: "Đã tiếp nhận",
  under_review: "Đang xem xét",
  reviewed: "Đã xem xét",
};

// "Reviewed" means staff checked the classification, not that the problem is
// fixed (CONTEXT.md, Feedback status). The copy must not promise more.
export const STATUS_NOTE: Record<StatusValue, string> = {
  received: "Hệ thống đã nhận phản hồi và chuyển tới đội phụ trách.",
  under_review: "Phản hồi đang chờ nhân viên xem xét.",
  reviewed: "Nhân viên đã xem xét phản hồi của bạn.",
};

export function statusLabel(value: string): string {
  return STATUS_LABEL[value as StatusValue] ?? "Đang cập nhật";
}

export const NETWORK_MESSAGE = "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.";
export const TIMEOUT_MESSAGE = "Máy chủ phản hồi quá lâu. Vui lòng thử lại.";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Vietnamese copy for an HTTP error status. `retryAfter` is the header, in seconds. */
export function messageFor(status: number, retryAfter?: string | null): string {
  if (status === 400 || status === 422) {
    return "Phản hồi chưa hợp lệ. Vui lòng kiểm tra nội dung rồi gửi lại.";
  }
  if (status === 404) return "Không tìm thấy phản hồi với mã này.";
  if (status === 429) {
    const seconds = Number(retryAfter);
    const wait = seconds > 0 ? `sau khoảng ${Math.ceil(seconds / 60)} phút` : "sau ít phút";
    return `Bạn đã thao tác quá nhiều lần. Vui lòng thử lại ${wait}.`;
  }
  return "Hệ thống đang bận. Vui lòng thử lại sau ít phút.";
}

export async function publicFetch<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 15_000,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers,
        credentials: "omit",
        signal: controller.signal,
      });
    } catch {
      throw new ApiError(0, controller.signal.aborted ? TIMEOUT_MESSAGE : NETWORK_MESSAGE);
    }
    if (!res.ok) throw new ApiError(res.status, messageFor(res.status, res.headers.get("Retry-After")));
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export async function submitFeedback(input: SubmitInput): Promise<{ public_ref: string }> {
  const json = await publicFetch<{ data: { public_ref: string } }>("/api/public/feedback", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return json.data;
}

export async function getFeedbackStatus(code: string): Promise<FeedbackStatus> {
  const json = await publicFetch<{ data: FeedbackStatus }>(
    `/api/public/feedback/${encodeURIComponent(code)}`,
  );
  return json.data;
}

/** Any thrown value as copy a Customer can act on. */
export function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : messageFor(500);
}
