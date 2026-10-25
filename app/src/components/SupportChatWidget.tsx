// Trợ lý CSKH/đồng hành nổi (floating) — dùng cho trang chủ và mọi account ops.
// - Đã đăng nhập (trong app): gọi /api/agent/chat — backend tự phân tầng theo role + phòng ban
//   (staff→SOP/cách làm + task phòng mình; manager→+báo cáo; admin→full).
// - Trang chủ/landing (prop publicOnly): LUÔN chạy tầng công khai — gửi public_only=true để
//   backend ép Public FAQ/CSKH, không lộ dữ liệu nội bộ kể cả khi ops/admin đang đăng nhập.
//   Người chưa đăng nhập: tư vấn rule-based + liên hệ công khai; muốn gửi phản hồi thì trỏ sang
//   Customer web (không cần tài khoản).
// Bong bóng trả lời render Markdown (in đậm, danh sách, bảng). Trích dẫn [Nguồn N] bấm được
// để mở chi tiết tài liệu ngay trong widget.
import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, X, Send, Sparkles, Phone, Mail, ArrowLeft, FileText, RotateCcw } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { apiFetch, CUSTOMER_WEB_URL, useMe } from "@/lib/api";
import { MarkdownContent } from "@/components/MarkdownContent";

// Liên hệ CÔNG KHAI — lấy từ data/public_kb. Hiển thị đầy đủ, không che.
const HOTLINE = "1555";
const EMAIL_CSKH = "support.vn@greensm.com";
const DPO_EMAIL = "DPOoffice@greensm.com";
const DPO_PHONE = "1900 2097";
// Customer web: nơi khách gửi phản hồi không cần tài khoản và nhận mã tra cứu.
const FEEDBACK_LINK = `[trang Gửi phản hồi](${CUSTOMER_WEB_URL})`;

type Source = { index: number; title: string; heading: string; department: string; content: string };
type Msg = { role: "user" | "assistant"; content: string; sources?: Source[] };

// Gợi ý theo VAI TRÒ + NGHIỆP VỤ (role/department). Backend đã phân tầng tool + scope phòng ban.
function suggestionsFor(me?: { role?: string | null; department?: string | null }): string[] {
  const role = me?.role;
  const dept = me?.department;
  if (role === "admin")
    return ["Tổng quan toàn hệ thống hôm nay", "Khu vực nóng nhất", "Ticket tồn đọng sắp trễ SLA", "So sánh hiệu suất các phòng"];
  if (role === "manager")
    return [
      dept ? `Báo cáo phòng ${dept} tuần này` : "Báo cáo phòng tuần này",
      "Khu vực nóng nhất của phòng",
      "Ticket sắp vi phạm SLA",
      "Vấn đề nổi cộm cần ưu tiên",
    ];
  if (role === "staff")
    return [
      dept ? `Quy trình xử lý sự cố phòng ${dept}?` : "Quy trình xử lý sự cố?",
      "SOP cho task tôi đang làm",
      "Task ưu tiên của phòng tôi",
      "Cách xử lý khiếu nại đúng SLA",
    ];
  return ["Cách gửi phản hồi?", "Liên hệ CSKH", "Báo sự cố / cần giúp đỡ", "Yêu cầu hoàn tiền"];
}

const greeting = (): Msg => ({
  role: "assistant",
  content: "Xin chào 👋 Mình là **trợ lý đồng hành** của xanhSM. Bạn cần hỗ trợ gì?",
});

// Tư vấn rule-based (chưa đăng nhập). Markdown-friendly. Chỉ thông tin khách hàng + liên hệ công khai.
function cannedReply(q: string): string {
  const s = q.toLowerCase();
  if (
    /(xâm hại|xam hai|xâm phạm|hành hung|hanh hung|bị đánh|bi danh|đánh tôi|bị thương|hành hạ|tấn công|tan cong|cướp|cuop|trộm|sàm sỡ|sam so|quấy rối|quay roi|đe dọa|đe doạ|de doa|hăm dọa|bạo lực|bao luc|tai nạn|tai nan|khẩn cấp|khan cap|nguy hiểm|nguy hiem|bắt cóc|bat coc|cứu|giúp với|giup voi|sợ hãi|so hai|bị hại)/.test(
      s,
    )
  )
    return `Mình rất tiếc về việc bạn đang gặp phải, và mình ở đây để hỗ trợ bạn. 💚\n\n⚠️ **Nếu đang gặp nguy hiểm/khẩn cấp:** gọi ngay **113** (Công an) hoặc **115** (Cấp cứu).\n\nVới sự cố chuyến đi xanhSM (tài xế, an toàn, quấy rối): gọi **Hotline ${HOTLINE}** (24/7) và giữ lại bằng chứng (mã chuyến, ảnh, thời gian).\n\nĐể gửi khiếu nại chính thức: gửi tại ${FEEDBACK_LINK} (không cần tài khoản) và giữ mã tra cứu để theo dõi trạng thái. Email: ${EMAIL_CSKH}.`;
  if (
    /(cách gửi|cach gui|gửi phản hồi|gui phan hoi|gửi đánh giá|gửi góp ý|gửi feedback|làm sao gửi|lam sao gui|đánh giá chuyến|review chuyến)/.test(
      s,
    )
  )
    return `Bạn có thể gửi phản hồi về chuyến đi qua các cách sau: 😊\n\n1. **Trong ứng dụng:** vào **Tài khoản → Trung tâm hỗ trợ**, chọn nhóm vấn đề, điền nội dung và tạo yêu cầu (nên đính kèm mã chuyến, ảnh giao dịch/ảnh lỗi).\n2. **Hotline:** ${HOTLINE}.\n3. **Email:** ${EMAIL_CSKH}.\n\nHoặc gửi ngay tại ${FEEDBACK_LINK} — không cần tài khoản, bạn nhận mã tra cứu để theo dõi trạng thái.`;
  if (/(hoàn tiền|refund|trừ tiền|thanh toán|cước phí|hoá đơn|hóa đơn)/.test(s))
    return `Để yêu cầu **hoàn tiền/khiếu nại thanh toán**: gửi phản hồi tại ${FEEDBACK_LINK} kèm mã chuyến đi. Cần gấp: **Hotline ${HOTLINE}** hoặc email ${EMAIL_CSKH} (nên kèm mã chuyến + thời gian phát sinh).`;
  if (/(đặt xe|gọi xe|booking|điểm đón|đặt chuyến)/.test(s))
    return `Để **đặt xe**: mở ứng dụng Green SM, chọn điểm đón và điểm đến, xác nhận loại xe rồi đặt. 🚗 Nếu app lỗi, gọi **Hotline ${HOTLINE}** hoặc gửi phản hồi tại ${FEEDBACK_LINK}.`;
  if (/(khuyến mãi|mã giảm|ưu đãi|voucher|điểm thưởng)/.test(s))
    return "Mã **khuyến mãi & ưu đãi** hiển thị trong ứng dụng Green SM ở mục “Ưu đãi”. 🎁 Áp dụng mã ở bước xác nhận chuyến trước khi đặt.";
  if (/(tài khoản|đăng nhập|mật khẩu|đăng ký)/.test(s))
    return `Bạn quản lý **tài khoản** trong ứng dụng Green SM. Quên mật khẩu: dùng “Quên mật khẩu” để nhận liên kết đặt lại. Gửi phản hồi không cần tài khoản: ${FEEDBACK_LINK}.`;
  if (/(dữ liệu|riêng tư|cá nhân|bảo mật|xóa tài khoản|gdpr)/.test(s))
    return `Về **quyền dữ liệu cá nhân** (truy cập, chỉnh sửa, xóa, rút đồng ý), liên hệ bộ phận bảo vệ dữ liệu: **${DPO_EMAIL}** hoặc **${DPO_PHONE}**.`;
  if (/(điểm|chỉ số|chất lượng|hài lòng|sla)/.test(s))
    return `Các **chỉ số chất lượng dịch vụ** hiện chỉ dành cho đội vận hành nội bộ. 📊 Nếu bạn muốn góp ý về chất lượng, hãy gửi tại ${FEEDBACK_LINK}.`;
  if (/(cskh|liên hệ|hotline|tổng đài|gọi điện|số điện thoại|số máy|email)/.test(s))
    return `**Kênh hỗ trợ chính thức của xanhSM:** ☎️\n\n- **Hotline 24/7:** ${HOTLINE}\n- **Email CSKH:** ${EMAIL_CSKH}\n- Hoặc mục Hỗ trợ trong ứng dụng Green SM.`;
  if (
    /(khiếu nại|khieu nai|phản ánh|phan anh|tố cáo|to cao|phản hồi|phan hoi|góp ý|gop y|đánh giá|danh gia|review|vấn đề|van de|sự việc|su viec|không hài lòng|bức xúc|buc xuc|giúp|giup|hỗ trợ|ho tro|cần|can)/.test(
      s,
    )
  )
    return `Mình sẽ hướng dẫn bạn nhé. 🙌 Để được hỗ trợ và xử lý chính thức, hãy gửi tại ${FEEDBACK_LINK} — không cần tài khoản. Phản hồi được chuyển tới đội phù hợp, bạn dùng mã tra cứu để theo dõi trạng thái.\n\nCần hỗ trợ ngay: **Hotline ${HOTLINE}** (24/7) · ${EMAIL_CSKH}.`;
  return `Mình là **trợ lý CSKH xanhSM** 💚 — hỗ trợ thông tin về dịch vụ (đặt xe, thanh toán, an toàn, khuyến mãi).\n\nNếu cần phản ánh/khiếu nại hoặc gặp sự cố, hãy gửi tại ${FEEDBACK_LINK}. Hỗ trợ ngay: **Hotline ${HOTLINE}** · ${EMAIL_CSKH}.`;
}

const MD_CLS =
  "text-sm leading-relaxed break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:my-1.5 [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5 [&_h2]:mt-2 [&_h2]:mb-1 [&_h2]:border-0 [&_h2]:pb-0 [&_h2]:text-sm [&_h3]:mt-2 [&_h3]:text-sm [&_table]:my-2";

// Biến trích dẫn nội tuyến [Nguồn 1] hoặc [1] trong câu trả lời thành link 'src:N' để bấm mở tài liệu.
function linkifyCitations(text: string, sources?: Source[]): string {
  if (!sources || sources.length === 0) return text;
  const valid = new Set(sources.map((s) => String(s.index)));
  return text
    .replace(/\[\s*Nguồn\s*(\d+)\s*\]/gi, (m, n) => (valid.has(n) ? `[Nguồn ${n}](src:${n})` : m))
    .replace(/\[(\d+)\](?!\()/g, (m, n) => (valid.has(n) ? `[${n}](src:${n})` : m));
}

// Renderer thẻ <a>: href 'src:N' → nút bấm mở tài liệu nguồn; còn lại là link thường.
function makeCitationComponents(sources: Source[] | undefined, onOpen: (s: Source) => void) {
  return {
    a: (props: any) => {
      const href: unknown = props?.href;
      const match = typeof href === "string" ? href.match(/^src:(\d+)$/) : null;
      if (match && sources) {
        const src = sources.find((s) => s.index === Number(match[1]));
        if (src) {
          return (
            <button
              type="button"
              onClick={() => onOpen(src)}
              className="mx-0.5 inline-flex items-center rounded border border-primary/40 bg-primary/10 px-1 align-baseline text-[11px] font-semibold text-primary transition-colors hover:bg-primary/20"
            >
              {props.children}
            </button>
          );
        }
      }
      return (
        <a href={typeof href === "string" ? href : undefined} target="_blank" rel="noreferrer" className="text-primary underline">
          {props.children}
        </a>
      );
    },
  };
}

export default function SupportChatWidget({ publicOnly = false }: { publicOnly?: boolean } = {}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [activeSource, setActiveSource] = useState<Source | null>(null);
  // Chips gợi ý chỉ hiện TRƯỚC khi user gửi tin nhắn đầu tiên; gửi xong ẩn vĩnh viễn trong phiên.
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [msgs, setMsgs] = useState<Msg[]>([greeting()]);
  // Chỉ cần role khi đã đăng nhập và ở trong app — không gọi /api/me ẩn danh từ trang chủ.
  const { data: me } = useMe({ enabled: authed && !publicOnly });
  // Trang chủ/landing (publicOnly): luôn dùng gợi ý CSKH công khai, bỏ qua role thật.
  const suggestions = useMemo(
    () => suggestionsFor(authed && !publicOnly ? me : undefined),
    [authed, me, publicOnly],
  );
  // Dòng trạng thái: trang chủ (publicOnly) hỗ trợ công khai; trong app trả lời theo quyền.
  const statusLine = publicOnly
    ? "Online · hỗ trợ thông tin công khai"
    : "Online · trả lời theo quyền của bạn";
  const endRef = useRef<HTMLDivElement>(null);

  function resetChat() {
    setMsgs([greeting()]);
    setShowSuggestions(true);
    setActiveSource(null);
    setInput("");
  }

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setAuthed(!!data.session));
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open, busy]);

  async function send(text?: string) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setShowSuggestions(false); // ẩn chips ngay khi có tin nhắn hợp lệ đầu tiên (không hiện lại)
    const history = [...msgs, { role: "user" as const, content: q }];
    setMsgs(history);
    setInput("");
    setBusy(true);
    let reply = "";
    let sources: Source[] | undefined;
    try {
      if (authed) {
        const res = await apiFetch<{ data?: { content?: string; sources?: Source[] } }>(
          "/api/agent/chat",
          {
            method: "POST",
            body: JSON.stringify({
              messages: history.slice(-8).map(({ role, content }) => ({ role, content })),
              // publicOnly (trang chủ) → backend ép tầng công khai (Public FAQ/CSKH),
              // không truy cập dữ liệu/tool nội bộ kể cả khi đang đăng nhập ops/admin.
              public_only: publicOnly,
            }),
          },
        );
        reply = res.data?.content?.trim() || cannedReply(q);
        sources = res.data?.sources;
      } else {
        await new Promise((r) => setTimeout(r, 400));
        reply = cannedReply(q);
      }
    } catch {
      reply = cannedReply(q);
    } finally {
      setBusy(false);
    }
    setMsgs((m) => [...m, { role: "assistant", content: reply, sources }]);
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full text-primary-foreground shadow-xl shadow-primary/30 transition-all duration-200 hover:scale-110 active:scale-95"
        style={{ background: "var(--gradient-green)" }}
        aria-label="Mở trợ lý"
      >
        {open ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
        {!open && <span className="absolute right-0 top-0 h-3 w-3 animate-pulse rounded-full bg-destructive ring-2 ring-background" />}
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[540px] max-h-[calc(100vh-8rem)] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center gap-3 p-4 text-white" style={{ background: "var(--gradient-hero)" }}>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20"><Sparkles className="h-5 w-5" /></div>
            <div className="flex-1">
              <div className="font-display font-semibold leading-none">Trợ lý đồng hành xanhSM</div>
              <div className="mt-1 flex items-center gap-1.5 text-xs opacity-90">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" /> {statusLine}
              </div>
            </div>
            <button
              onClick={resetChat}
              title="Mới cuộc trò chuyện"
              aria-label="Mới cuộc trò chuyện"
              className="flex h-8 shrink-0 items-center gap-1 rounded-lg bg-white/15 px-2 text-xs font-medium text-white transition-colors hover:bg-white/25"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Mới
            </button>
          </div>

          {/* Khu vực hội thoại + overlay chi tiết nguồn */}
          <div className="relative flex-1 overflow-hidden">
            <div className="h-full space-y-3 overflow-y-auto p-4">
              {msgs.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-1 duration-200`}>
                  <div className={`max-w-[88%] rounded-2xl px-3 py-2 ${
                    m.role === "user" ? "rounded-br-sm bg-primary text-primary-foreground text-sm whitespace-pre-line" : "rounded-bl-sm bg-muted text-foreground"
                  }`}>
                    {m.role === "user" ? (
                      m.content
                    ) : (
                      <>
                        <MarkdownContent
                          className={MD_CLS}
                          components={makeCitationComponents(m.sources, setActiveSource) as any}
                        >
                          {linkifyCitations(m.content, m.sources)}
                        </MarkdownContent>
                        {m.sources && m.sources.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5 border-t border-border/60 pt-2">
                            {m.sources.map((src) => (
                              <button
                                key={`${src.index}-${src.heading}`}
                                onClick={() => setActiveSource(src)}
                                className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
                                title={`${src.title} › ${src.heading}`}
                              >
                                <FileText className="h-3 w-3" /> Nguồn {src.index}
                              </button>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="flex justify-start animate-in fade-in duration-150">
                  <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm bg-muted px-3.5 py-3">
                    <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                    <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "160ms" }} />
                    <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "320ms" }} />
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {activeSource && (
              <div className="absolute inset-0 z-10 flex flex-col bg-card animate-in fade-in slide-in-from-right-2 duration-200">
                <div className="flex items-center gap-2 border-b p-3">
                  <button onClick={() => setActiveSource(null)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
                    <ArrowLeft className="h-4 w-4" /> Quay lại
                  </button>
                  <span className="ml-auto text-[11px] font-mono text-muted-foreground">Nguồn {activeSource.index} · {activeSource.department}</span>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  <h3 className="font-display text-sm font-bold text-xanh-deep">{activeSource.title}</h3>
                  {activeSource.heading && <div className="mt-0.5 text-xs text-muted-foreground">{activeSource.heading}</div>}
                  <MarkdownContent className="mt-3 text-sm [&_p]:my-1.5 [&_h2]:text-sm [&_h2]:border-0 [&_h3]:text-sm">
                    {activeSource.content}
                  </MarkdownContent>
                </div>
              </div>
            )}
          </div>

          {showSuggestions && (
            <div className="flex flex-wrap gap-1.5 px-3 pb-2 pt-2">
              {suggestions.map((s) => (
                <button key={s} onClick={() => send(s)} disabled={busy}
                  className="rounded-full bg-secondary px-2.5 py-1 text-xs text-secondary-foreground transition-colors hover:bg-accent disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center gap-3 border-t px-3 py-2 text-[11px] text-muted-foreground">
            <a href={`tel:${HOTLINE}`} className="inline-flex items-center gap-1 hover:text-foreground"><Phone className="h-3 w-3" />{HOTLINE}</a>
            <a href={`mailto:${EMAIL_CSKH}`} className="inline-flex items-center gap-1 hover:text-foreground"><Mail className="h-3 w-3" />{EMAIL_CSKH}</a>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 border-t bg-background p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Hỏi về dịch vụ, quy trình, cách xử lý…"
              className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none transition-colors focus:border-primary"
            />
            <button type="submit" disabled={busy} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-transform hover:scale-105 active:scale-95 disabled:opacity-50">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
