// `/`: a Customer reports Feedback with no account (US-076, US-077), or from a
// logged-in Customer account, which saves it to "Phản hồi của tôi" (US-078).
//
// The success state shows the Lookup code and nothing the backend classified:
// no topic, sentiment or severity ever reaches this page (SPEC item 5).
import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { MAX_TEXT, errorText, submitFeedback } from "../api";
import { settling, useAuth } from "../auth";
import { AREA_GROUPS } from "../regions";
import { Link, statusPath } from "../router";
import { CodeText, Icon, LookupForm, Spinner, WarningMark } from "../ui";

// Stored codes, like the rest of the feedback table ("app" from ingest and the
// Staff web). The old /f form sent the Vietnamese labels themselves.
const CHANNELS = [
  { value: "app", label: "Ứng dụng" },
  { value: "hotline", label: "Hotline" },
  { value: "web", label: "Website" },
  { value: "social", label: "Mạng xã hội" },
];
const TEXT_ERROR = "Vui lòng mô tả chuyện đã xảy ra";

export default function SubmitPage() {
  const auth = useAuth();
  // Only a Customer account sends its token. A staff or pending login posts
  // through the public route like anyone logged out.
  const token = auth.kind === "customer" ? auth.token : undefined;
  const [text, setText] = useState("");
  const [channel, setChannel] = useState(CHANNELS[0].value);
  const [area, setArea] = useState("");
  // Failed attempts with empty text; 0 means no error. Each attempt remounts the
  // summary so focus moves to it again.
  const [textError, setTextError] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [code, setCode] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Gửi phản hồi — AI-Quality";
  }, []);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body = text.trim();
    if (!body) {
      setTextError((n) => n + 1);
      return;
    }
    const website = String(new FormData(e.currentTarget).get("website") ?? "");
    setSubmitting(true);
    try {
      const data = await submitFeedback({ text: body, channel, area, website }, token);
      setCode(data.public_ref);
      setText("");
    } catch (err) {
      toast.error(errorText(err), { duration: 8000 });
    } finally {
      setSubmitting(false);
    }
  }

  if (code) return <Confirmation code={code} saved={!!token} onAnother={() => setCode(null)} />;

  const remaining = MAX_TEXT - text.length;

  return (
    <>
      {textError > 0 && <ErrorSummary key={textError} />}

      <h1 className="page-title">Gửi phản hồi về chuyến đi</h1>
      <ul className="mt-4 space-y-2 text-[0.9375rem] text-muted-foreground">
        <Assurance icon="user">
          {token ? "Phản hồi được lưu vào mục Phản hồi của tôi." : "Không cần tài khoản."}
        </Assurance>
        <Assurance icon="mask">Số điện thoại, email, biển số được che tự động.</Assurance>
        {/* The 180-day redaction covers source='public' only. Customer rows have
            no retention clock yet (decision 0018, Follow-Up); change this copy with it. */}
        <Assurance icon="clock">
          {token ? "Nội dung được lưu đến khi tài khoản bị xoá." : "Nội dung tự xoá sau 180 ngày."}
        </Assurance>
      </ul>

      <form onSubmit={submit} noValidate className="aurora-card surface mt-7 space-y-7 p-5 md:p-8">
        <div>
          <label htmlFor="fb-text" className="field-label text-lg">
            Chuyện gì đã xảy ra?
          </label>
          <p id="fb-text-hint" className="field-hint">
            Ví dụ: Tài xế vượt đèn đỏ và phóng rất nhanh trên đường Nguyễn Trãi lúc 19h tối nay.
          </p>
          {textError > 0 && (
            <p id="fb-text-error" className="field-error">
              <span className="sr-only">Lỗi: </span>
              {TEXT_ERROR}
            </p>
          )}
          <textarea
            id="fb-text"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (textError && e.target.value.trim()) setTextError(0);
            }}
            maxLength={MAX_TEXT}
            rows={6}
            aria-invalid={textError > 0 || undefined}
            aria-describedby={`fb-text-hint fb-text-count${textError > 0 ? " fb-text-error" : ""}`}
            className="field-input mt-3 py-3 leading-relaxed"
          />
          <p id="fb-text-count" className="mt-1.5 text-right text-sm tabular-nums text-muted-foreground">
            Còn {remaining.toLocaleString("vi-VN")} ký tự
          </p>
        </div>

        <fieldset>
          <legend className="field-label">Kênh</legend>
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            {CHANNELS.map((c) => (
              <label key={c.value} className="option">
                <input
                  type="radio"
                  name="channel"
                  value={c.value}
                  checked={channel === c.value}
                  onChange={() => setChannel(c.value)}
                  className="option-dot"
                />
                <span>{c.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="fb-area" className="field-label">
            Khu vực <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
          </label>
          <select
            id="fb-area"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            className="field-input field-select mt-3"
          >
            <option value="">Chọn khu vực</option>
            {AREA_GROUPS.map((g) => (
              <optgroup key={g.city} label={g.city}>
                {g.areas.map((a) => (
                  <option key={a.code} value={a.code}>
                    {a.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {/* Honeypot (SPEC item 7): off-screen, out of the tab order, never autofilled. */}
        <div className="hp" aria-hidden="true">
          <label htmlFor="fb-website">Website</label>
          <input id="fb-website" name="website" type="text" tabIndex={-1} autoComplete="off" defaultValue="" />
        </div>

        <div className="flex gap-3 text-foreground">
          <WarningMark />
          <p className="font-semibold leading-snug">
            Nếu đang có nguy hiểm tức thời, hãy gọi cơ quan chức năng trước.
          </p>
        </div>

        {/* While the role is being checked we do not yet know which route to use. */}
        <button
          type="submit"
          className="btn btn-primary w-full"
          disabled={submitting || settling(auth)}
          aria-busy={submitting}
        >
          {submitting ? <Spinner /> : null}
          {submitting ? "Đang gửi…" : "Gửi phản hồi"}
        </button>
      </form>

      <section aria-labelledby="lookup-title" className="mt-12 border-t border-border pt-8">
        <h2 id="lookup-title" className="section-title">
          Tra cứu mã
        </h2>
        <p className="mt-1.5 text-muted-foreground">Đã gửi phản hồi? Nhập mã để xem trạng thái.</p>
        <LookupForm />
      </section>
    </>
  );
}

function Assurance({ icon, children }: { icon: "user" | "mask" | "clock"; children: string }) {
  return (
    <li className="flex items-start gap-2.5">
      <span className="mt-px text-primary-strong">
        <Icon name={icon} />
      </span>
      <span>{children}</span>
    </li>
  );
}

function ErrorSummary() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div ref={ref} tabIndex={-1} role="alert" aria-labelledby="error-summary-title" className="error-summary mb-8">
      <h2 id="error-summary-title" className="text-lg font-semibold">
        Có lỗi cần sửa
      </h2>
      <a
        href="#fb-text"
        className="mt-2 inline-block font-medium text-destructive underline underline-offset-4"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("fb-text")?.focus();
        }}
      >
        {TEXT_ERROR}
      </a>
    </div>
  );
}

function Confirmation({ code, saved, onAnother }: { code: string; saved: boolean; onAnother: () => void }) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    headingRef.current?.focus();
  }, []);

  function copy() {
    if (!navigator.clipboard) {
      toast.error("Không sao chép được, vui lòng chép tay");
      return;
    }
    navigator.clipboard.writeText(code).then(
      () => {
        setCopied(true);
        toast.success("Đã sao chép mã");
      },
      () => toast.error("Không sao chép được, vui lòng chép tay"),
    );
  }

  return (
    <>
      <section className="aurora-card confirm-panel reveal p-6 md:p-8">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-full bg-on-band text-band-deep">
            <Icon name="check" className="size-5" />
          </span>
          <h1 ref={headingRef} tabIndex={-1} className="page-title text-on-band outline-none">
            Đã nhận phản hồi
          </h1>
        </div>

        <p className="mt-6 text-on-band-muted">Mã tra cứu của bạn</p>
        <CodeText code={code} className="mt-1 text-3xl md:text-4xl" />

        <button type="button" onClick={copy} className="btn btn-on-band mt-5">
          <Icon name={copied ? "check" : "copy"} />
          {copied ? "Đã sao chép" : "Sao chép mã"}
        </button>
      </section>

      <h2 className="section-title mt-10">Điều gì xảy ra tiếp theo</h2>
      <div className="mt-3 max-w-prose space-y-3 leading-relaxed">
        <p>Phản hồi đã vào hệ thống và đang được phân loại tự động tới đội phụ trách.</p>
        {saved ? (
          <p>
            Phản hồi đã được lưu vào tài khoản. Bạn có thể xem lại trong{" "}
            <Link href="/cua-toi" className="back-link">
              Phản hồi của tôi
            </Link>
            .
          </p>
        ) : (
          <p>
            Hãy lưu lại mã này. Đây là cách duy nhất để xem trạng thái: chúng tôi không gửi email hay
            tin nhắn.
          </p>
        )}
      </div>

      <div className="mt-7 flex flex-col gap-3 sm:flex-row">
        <Link href={statusPath(code)} className="btn btn-primary">
          Xem trạng thái
          <Icon name="arrowRight" />
        </Link>
        <button type="button" onClick={onAnother} className="btn btn-secondary">
          Gửi phản hồi khác
        </button>
      </div>
    </>
  );
}
