// `/status/:code`: the Feedback status for whoever holds the Lookup code.
//
// Shows only the status and the submitted date (SPEC item 6). The backend
// answers an unknown, expired or redacted code with the same 404, so this page
// cannot tell them apart either, and says so kindly.
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  STATUS_NOTE,
  errorText,
  getFeedbackStatus,
  statusLabel,
  type FeedbackStatus,
} from "../api";
import { Link } from "../router";
import { CodeText, Icon, LookupForm, Spinner } from "../ui";

type State =
  | { kind: "loading" }
  | { kind: "found"; data: FeedbackStatus }
  | { kind: "not-found" }
  | { kind: "error"; message: string };

// Customers are in Vietnam; a fixed zone keeps the date the same on any device.
const TZ = "Asia/Ho_Chi_Minh";
const DAY = new Intl.DateTimeFormat("vi-VN", { day: "numeric", month: "long", year: "numeric", timeZone: TZ });
const TIME = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: TZ });

/** "27 tháng 9, 2026 lúc 12:20". dateStyle+timeStyle puts the time first in vi-VN. */
export function formatSubmitted(iso: string | null): string {
  const date = iso ? new Date(iso) : null;
  if (!date || Number.isNaN(date.getTime())) return "Không rõ";
  return `${DAY.format(date)} lúc ${TIME.format(date)}`;
}

export default function StatusPage({ code }: { code: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (isCurrent: () => boolean = () => true) => {
      try {
        const data = await getFeedbackStatus(code);
        if (isCurrent()) setState({ kind: "found", data });
      } catch (err) {
        if (!isCurrent()) return;
        setState(
          err instanceof ApiError && err.status === 404
            ? { kind: "not-found" }
            : { kind: "error", message: errorText(err) },
        );
      }
    },
    [code],
  );

  useEffect(() => {
    document.title = "Tra cứu phản hồi — AI-Quality";
    if (!code) return;
    let current = true;
    setState({ kind: "loading" });
    void load(() => current);
    return () => {
      current = false;
    };
  }, [code, load]);

  async function refresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  return (
    <>
      <Link href="/" className="back-link">
        <Icon name="arrowLeft" className="size-4" />
        Gửi phản hồi mới
      </Link>
      <h1 className="page-title mt-4">Tra cứu phản hồi</h1>

      {code ? (
        <div className="aurora-card surface mt-7 p-5 md:p-8" aria-live="polite" aria-busy={state.kind === "loading"}>
          {state.kind === "loading" && <LoadingRows />}
          {state.kind === "found" && (
            <Found data={state.data} refreshing={refreshing} onRefresh={() => void refresh()} />
          )}
          {state.kind === "not-found" && <NotFound />}
          {state.kind === "error" && (
            <div className="reveal">
              <h2 className="section-title">Chưa tra cứu được</h2>
              <p className="mt-2 text-muted-foreground">{state.message}</p>
              <button type="button" className="btn btn-secondary mt-5" onClick={() => void refresh()} disabled={refreshing}>
                {refreshing ? <Spinner /> : <Icon name="refresh" />}
                Thử lại
              </button>
            </div>
          )}
        </div>
      ) : (
        <p className="mt-3 text-muted-foreground">Nhập mã bạn nhận được sau khi gửi phản hồi.</p>
      )}

      <section aria-labelledby="lookup-again" className="mt-12 border-t border-border pt-8">
        <h2 id="lookup-again" className="section-title">
          {code ? "Tra cứu mã khác" : "Tra cứu mã"}
        </h2>
        {/* A not-found code is pre-filled so a typo can be fixed in place. */}
        <LookupForm
          key={`${code}:${state.kind === "not-found"}`}
          initial={state.kind === "not-found" ? code : ""}
        />
      </section>
    </>
  );
}

function Found({
  data,
  refreshing,
  onRefresh,
}: {
  data: FeedbackStatus;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="reveal">
      <dl className="summary-list">
        <div>
          <dt>Mã tra cứu</dt>
          <dd>
            <CodeText code={data.public_ref} className="text-lg" />
          </dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>
            <span className="tag" data-status={data.status}>
              {statusLabel(data.status)}
            </span>
          </dd>
        </div>
        <div>
          <dt>Ngày gửi</dt>
          <dd>{formatSubmitted(data.created_at)}</dd>
        </div>
      </dl>
      {STATUS_NOTE[data.status] && <p className="mt-5 leading-relaxed">{STATUS_NOTE[data.status]}</p>}
      <button type="button" className="btn btn-secondary mt-6" onClick={onRefresh} disabled={refreshing}>
        {refreshing ? <Spinner /> : <Icon name="refresh" />}
        Làm mới
      </button>
    </div>
  );
}

function NotFound() {
  return (
    <div className="reveal">
      <h2 className="section-title">Không tìm thấy phản hồi với mã này</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 leading-relaxed text-muted-foreground marker:text-primary-strong">
        <li>Kiểm tra lại từng ký tự: mã phân biệt chữ hoa và chữ thường.</li>
        <li>Phản hồi gửi quá 180 ngày không còn tra cứu được.</li>
      </ul>
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-5" aria-label="Đang tra cứu">
      {[40, 28, 52].map((w) => (
        <div key={w} className="space-y-2">
          <div className="h-3.5 w-24 animate-pulse rounded-full bg-muted" />
          <div className="h-5 animate-pulse rounded-full bg-muted" style={{ width: `${w}%` }} />
        </div>
      ))}
    </div>
  );
}
