// The Customer assistant (US-078): a floating button on every page. Only a
// Customer account talks to it (POST /api/customer/chat, public knowledge only);
// logged out, the panel asks the Customer to log in. Replies render as plain
// text, never as HTML.
import { useEffect, useRef, useState } from "react";
import { customerChat, errorText, type ChatMessage } from "./api";
import { STAFF_MESSAGE, settling, useAuth } from "./auth";
import { Link } from "./router";
import { supabase } from "./supabase";
import { Icon, Spinner } from "./ui";

// `local`: UI copy (greeting, error, empty-reply fallback), shown but never sent
// to the model as its own words.
type Bubble = ChatMessage & { local?: true };

const GREETING: Bubble = {
  role: "assistant",
  content: "Xin chào! Mình có thể giải đáp chính sách, cách gửi phản hồi, hoặc ghi nhận phản hồi giúp bạn.",
  local: true,
};
// Same window the Staff web widget sends.
const HISTORY = 8;

export default function ChatWidget() {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Bubble[]>([GREETING]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const token = auth.kind === "customer" ? auth.token : null;
  const userId = auth.kind === "customer" ? auth.userId : null;

  // A new login starts a new conversation; a token refresh does not.
  useEffect(() => setMsgs([GREETING]), [userId]);
  useEffect(() => {
    if (open) (inputRef.current ?? titleRef.current)?.focus();
  }, [open]);
  // Block body on purpose: Chrome's scrollIntoView returns a Promise, which an
  // arrow expression would hand to React as the effect's cleanup.
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [msgs, busy]);

  if (!supabase) return null;

  // The panel unmounts with focus inside it; hand focus back to the button.
  function close() {
    setOpen(false);
    fabRef.current?.focus();
  }

  async function send(e?: { preventDefault(): void }) {
    e?.preventDefault();
    const q = input.trim();
    if (!q || busy || !token) return;
    const history: Bubble[] = [...msgs, { role: "user", content: q }];
    setMsgs(history);
    setInput("");
    setBusy(true);
    let reply: Bubble;
    try {
      const sent = history.filter((m) => !m.local).slice(-HISTORY);
      const content = await customerChat(token, sent);
      reply = content
        ? { role: "assistant", content }
        : { role: "assistant", content: "Xin lỗi, mình chưa có câu trả lời.", local: true };
    } catch (err) {
      reply = { role: "assistant", content: errorText(err), local: true };
    }
    setMsgs((m) => [...m, reply]);
    setBusy(false);
  }

  return (
    <>
      {open && (
        <section
          id="chat-panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="chat-title"
          className="chat-panel surface"
          onKeyDown={(e) => e.key === "Escape" && close()}
        >
          <header className="band flex items-center justify-between gap-3 px-4 py-3">
            <h2 id="chat-title" ref={titleRef} tabIndex={-1} className="font-semibold outline-none">
              Trợ lý khách hàng
            </h2>
            <button
              type="button"
              className="btn btn-on-band min-h-10 px-2.5"
              aria-label="Đóng trợ lý"
              onClick={close}
            >
              <Icon name="close" />
            </button>
          </header>

          {token ? (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
                {msgs.map((m, i) => (
                  <p key={i} className="chat-bubble" data-role={m.role}>
                    <span className="sr-only">{m.role === "user" ? "Bạn: " : "Trợ lý: "}</span>
                    {m.content}
                  </p>
                ))}
                {busy && (
                  <p className="chat-bubble flex items-center gap-2" data-role="assistant">
                    <Spinner /> Đang trả lời…
                  </p>
                )}
                <div ref={endRef} />
              </div>
              <form onSubmit={send} className="flex items-end gap-2 border-t border-border p-3">
                <label htmlFor="chat-input" className="sr-only">
                  Tin nhắn
                </label>
                <textarea
                  id="chat-input"
                  ref={inputRef}
                  rows={1}
                  value={input}
                  maxLength={2000}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) void send(e);
                  }}
                  placeholder="Nhập câu hỏi…"
                  className="field-input chat-input min-h-12 flex-1 py-3"
                />
                <button type="submit" className="btn btn-primary min-h-12 px-3.5" disabled={busy || !input.trim()}>
                  <Icon name="send" />
                  <span className="sr-only">Gửi</span>
                </button>
              </form>
            </>
          ) : (
            <div className="p-5">
              {auth.kind === "staff" ? (
                <p>{STAFF_MESSAGE}.</p>
              ) : auth.kind === "error" ? (
                <p>
                  Không kiểm tra được tài khoản.{" "}
                  <button type="button" className="back-link" onClick={auth.retry}>
                    Thử lại
                  </button>
                </p>
              ) : settling(auth) ? (
                <p role="status" className="flex items-center gap-2 text-muted-foreground">
                  <Spinner /> Đang kiểm tra tài khoản…
                </p>
              ) : (
                <p>
                  Trợ lý dành cho tài khoản khách hàng.{" "}
                  <Link href="/dang-nhap" className="back-link" onClick={() => setOpen(false)}>
                    Đăng nhập
                  </Link>{" "}
                  để trò chuyện. Gửi phản hồi vẫn không cần tài khoản.
                </p>
              )}
            </div>
          )}
        </section>
      )}

      <button
        ref={fabRef}
        type="button"
        className="chat-fab"
        aria-expanded={open}
        aria-controls="chat-panel"
        aria-label={open ? "Đóng trợ lý" : "Mở trợ lý khách hàng"}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name={open ? "close" : "chat"} className="size-6" />
      </button>
    </>
  );
}
