// `/cua-toi`: a Customer account's own Feedback, newest first (US-078).
//
// Each row shows the text, the Feedback status and the date, and links to its
// status page. Nothing the backend classified (topic, sentiment, severity) is
// ever read or shown; listMyFeedback drops any extra field.
import { useEffect, useState } from "react";
import { errorText, listMyFeedback, statusLabel, type MyFeedback } from "../api";
import { useAuth } from "../auth";
import { Link, statusPath } from "../router";
import { CodeText, Icon, Spinner } from "../ui";
import { formatSubmitted } from "./StatusPage";

type State = { kind: "loading" } | { kind: "done"; rows: MyFeedback[] } | { kind: "error"; message: string };

export default function MyFeedbackPage() {
  const auth = useAuth();
  const token = auth.kind === "customer" ? auth.token : null;
  const userId = auth.kind === "customer" ? auth.userId : null;
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    document.title = "Phản hồi của tôi — AI-Quality";
  }, []);

  useEffect(() => {
    if (!token) return;
    let current = true;
    setState({ kind: "loading" });
    listMyFeedback(token).then(
      (rows) => current && setState({ kind: "done", rows }),
      (err: unknown) => current && setState({ kind: "error", message: errorText(err) }),
    );
    return () => {
      current = false;
    };
  }, [userId]); // not `token`: a refresh is the same account

  return (
    <>
      <h1 className="page-title">Phản hồi của tôi</h1>
      <div className="mt-6">
        <Body auth={auth.kind} state={state} />
      </div>
    </>
  );
}

function Body({ auth, state }: { auth: ReturnType<typeof useAuth>["kind"]; state: State }) {
  if (auth === "anon")
    return (
      <p>
        <Link href="/dang-nhap" className="back-link">
          Đăng nhập
        </Link>{" "}
        để xem các phản hồi bạn đã gửi.
      </p>
    );
  // The Shell already shows STAFF_MESSAGE, or the failed account check with a retry.
  if (auth === "staff" || auth === "error") return null;
  if (auth !== "customer" || state.kind === "loading")
    return (
      <p role="status" className="flex items-center gap-2 text-muted-foreground">
        <Spinner /> Đang tải…
      </p>
    );
  if (state.kind === "error") return <p role="alert">{state.message}</p>;
  if (state.rows.length === 0)
    return (
      <p>
        Bạn chưa gửi phản hồi nào khi đăng nhập.{" "}
        <Link href="/" className="back-link">
          Gửi phản hồi
        </Link>
      </p>
    );
  return (
    <ul className="space-y-3">
      {state.rows.map((row) => (
        <li key={row.public_ref}>
          {/* A short link name; the full text is the description, not the name. */}
          <Link
            href={statusPath(row.public_ref)}
            className="surface history-row"
            aria-label={`Mã ${row.public_ref}, ${statusLabel(row.status)}, ${formatSubmitted(row.created_at)}`}
            aria-describedby={`fb-text-${row.public_ref}`}
          >
            <span className="flex flex-wrap items-center justify-between gap-2">
              <span className="tag text-sm" data-status={row.status}>
                {statusLabel(row.status)}
              </span>
              <span className="text-sm text-muted-foreground">{formatSubmitted(row.created_at)}</span>
            </span>
            <span id={`fb-text-${row.public_ref}`} className="mt-3 line-clamp-3 block leading-relaxed">
              {row.text}
            </span>
            <span className="mt-3 flex items-center justify-between gap-2 text-sm text-muted-foreground">
              <span>
                Mã <CodeText code={row.public_ref} />
              </span>
              <Icon name="arrowRight" className="size-4 text-primary-strong" />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
