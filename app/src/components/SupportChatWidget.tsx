// Trợ lý CSKH/đồng hành nổi (floating) — dùng cho Khách, trang chủ, và mọi account ops.
// - Đã đăng nhập: gọi /api/agent/chat — backend tự phân tầng theo role + phòng ban
//   (guest→KB công khai; staff→SOP/cách làm + task phòng mình; manager→+báo cáo; admin→full).
// - Trang chủ (chưa đăng nhập): tư vấn rule-based + liên hệ công khai.
// Bong bóng trả lời render Markdown (in đậm, danh sách, bảng). Trích dẫn [Nguồn N] bấm được
// để mở chi tiết tài liệu ngay trong widget.
import { useEffect, useRef, useState } from "react";
import { Bot, X, Send, Sparkles, Phone, Mail, ArrowLeft, FileText } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { apiFetch } from "@/lib/api";
import { MarkdownContent } from "@/components/MarkdownContent";

// Liên hệ CÔNG KHAI — lấy từ data/public_kb. Hiển thị đầy đủ, không che.
const HOTLINE = "1555";
const EMAIL_CSKH = "support.vn@greensm.com";
const DPO_EMAIL = "DPOoffice@greensm.com";
const DPO_PHONE = "1900 2097";

type Source = { index: number; title: string; heading: string; department: string; content: string };
type Msg = { role: "user" | "assistant"; content: string; sources?: Source[] };

const SUGGESTIONS = [
  "Cách gửi phản hồi?",
  "Liên hệ CSKH",
  "Báo sự cố / cần giúp đỡ",
  "Yêu cầu hoàn tiền",
];

// Tư vấn rule-based (chưa đăng nhập). Markdown-friendly. Chỉ thông tin khách hàng + liên hệ công khai.
function cannedReply(q: string): string {
  const s = q.toLowerCase();
  if (
    /(xâm hại|xam hai|xâm phạm|hành hung|hanh hung|bị đánh|bi danh|đánh tôi|bị thương|hành hạ|tấn công|tan cong|cướp|cuop|trộm|sàm sỡ|sam so|quấy rối|quay roi|đe dọa|đe doạ|de doa|hăm dọa|bạo lực|bao luc|tai nạn|tai nan|khẩn cấp|khan cap|nguy hiểm|nguy hiem|bắt cóc|bat coc|cứu|giúp với|giup voi|sợ hãi|so hai|bị hại)/.test(
      s,
    )
  )
    return `Mình rất tiếc về việc bạn đang gặp phải, và mình ở đây để hỗ trợ bạn. 💚\n\n⚠️ **Nếu đang gặp nguy hiểm/khẩn cấp:** gọi ngay **113** (Công an) hoặc **115** (Cấp cứu).\n\nVới sự cố chuyến đi xanhSM (tài xế, an toàn, quấy rối): gọi **Hotline ${HOTLINE}** (24/7) và giữ lại bằng chứng (mã chuyến, ảnh, thời gian).\n\nĐể gửi khiếu nại chính thức và được theo dõi xử lý: bấm **"Đăng nhập"** rồi vào mục **"Gửi phản hồi"**. Email: ${EMAIL_CSKH}.`;
  if (
    /(cách gửi|cach gui|gửi phản hồi|gui phan hoi|gửi đánh giá|gửi góp ý|gửi feedback|làm sao gửi|lam sao gui|đánh giá chuyến|review chuyến)/.test(
      s,
    )
  )
    return `Bạn có thể gửi phản hồi về chuyến đi qua các cách sau: 😊\n\n1. **Trong ứng dụng:** vào **Tài khoản → Trung tâm hỗ trợ**, chọn nhóm vấn đề, điền nội dung và tạo yêu cầu (nên đính kèm mã chuyến, ảnh giao dịch/ảnh lỗi).\n2. **Hotline:** ${HOTLINE}.\n3. **Email:** ${EMAIL_CSKH}.\n\nHoặc bấm **"Đăng nhập"** rồi vào mục **"Gửi phản hồi · đánh giá"** để gửi và theo dõi trạng thái xử lý.`;
  if (/(hoàn tiền|refund|trừ tiền|thanh toán|cước phí|hoá đơn|hóa đơn)/.test(s))
    return `Để yêu cầu **hoàn tiền/khiếu nại thanh toán**: bấm **"Đăng nhập"** rồi gửi phản hồi chủ đề "Thanh toán" kèm mã chuyến đi. Cần gấp: **Hotline ${HOTLINE}** hoặc email ${EMAIL_CSKH} (nên kèm mã chuyến + thời gian phát sinh).`;
  if (/(đặt xe|gọi xe|booking|điểm đón|đặt chuyến)/.test(s))
    return `Để **đặt xe**: mở ứng dụng Green SM, chọn điểm đón và điểm đến, xác nhận loại xe rồi đặt. 🚗 Nếu app lỗi, gọi **Hotline ${HOTLINE}** hoặc đăng nhập để gửi phản hồi.`;
  if (/(khuyến mãi|mã giảm|ưu đãi|voucher|điểm thưởng)/.test(s))
    return "Mã **khuyến mãi & ưu đãi** hiển thị trong ứng dụng Green SM ở mục “Ưu đãi”. 🎁 Áp dụng mã ở bước xác nhận chuyến trước khi đặt.";
  if (/(tài khoản|đăng nhập|mật khẩu|đăng ký)/.test(s))
    return "Bạn quản lý **tài khoản** trong ứng dụng Green SM. Quên mật khẩu: dùng “Quên mật khẩu” để nhận liên kết đặt lại. Đăng nhập trên trang này để gửi phản hồi và theo dõi xử lý.";
  if (/(dữ liệu|riêng tư|cá nhân|bảo mật|xóa tài khoản|gdpr)/.test(s))
    return `Về **quyền dữ liệu cá nhân** (truy cập, chỉnh sửa, xóa, rút đồng ý), liên hệ bộ phận bảo vệ dữ liệu: **${DPO_EMAIL}** hoặc **${DPO_PHONE}**.`;
  if (/(điểm|chỉ số|chất lượng|hài lòng|sla)/.test(s))
    return "Các **chỉ số dịch vụ công khai** (điểm dịch vụ, tỉ lệ hài lòng, thời gian đáp ứng, tỉ lệ hoàn thành) hiển thị ở phần “Chỉ số dịch vụ công khai” trên trang Khách hàng. 📊";
  if (/(cskh|liên hệ|hotline|tổng đài|gọi điện|số điện thoại|số máy|email)/.test(s))
    return `**Kênh hỗ trợ chính thức của xanhSM:** ☎️\n\n- **Hotline 24/7:** ${HOTLINE}\n- **Email CSKH:** ${EMAIL_CSKH}\n- Hoặc mục Hỗ trợ trong ứng dụng Green SM.`;
  if (
    /(khiếu nại|khieu nai|phản ánh|phan anh|tố cáo|to cao|phản hồi|phan hoi|góp ý|gop y|đánh giá|danh gia|review|vấn đề|van de|sự việc|su viec|không hài lòng|bức xúc|buc xuc|giúp|giup|hỗ trợ|ho tro|cần|can)/.test(
      s,
    )
  )
    return `Mình sẽ hướng dẫn bạn nhé. 🙌 Để được hỗ trợ và xử lý chính thức, hãy bấm **"Đăng nhập"** rồi vào mục **"Gửi phản hồi · đánh giá"** — AI sẽ tự phân loại và chuyển tới đội phù hợp, bạn theo dõi được trạng thái xử lý.\n\nCần hỗ trợ ngay: **Hotline ${HOTLINE}** (24/7) · ${EMAIL_CSKH}.`;
  return `Mình là **trợ lý CSKH xanhSM** 💚 — hỗ trợ thông tin về dịch vụ (đặt xe, thanh toán, an toàn, khuyến mãi).\n\nNếu cần phản ánh/khiếu nại hoặc gặp sự cố, hãy bấm **"Đăng nhập"** rồi gửi phản hồi trên trang Khách hàng. Hỗ trợ ngay: **Hotline ${HOTLINE}** · ${EMAIL_CSKH}.`;
}

const MD_CLS =
  "text-sm leading-relaxed break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:my-1.5 [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5 [&_h2]:mt-2 [&_h2]:mb-1 [&_h2]:border-0 [&_h2]:pb-0 [&_h2]:text-sm [&_h3]:mt-2 [&_h3]:text-sm [&_table]:my-2";

export default function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [activeSource, setActiveSource] = useState<Source | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: "assistant",
      content: `Xin chào 👋 Mình là **trợ lý đồng hành** của xanhSM. Mình hỗ trợ thông tin khách hàng và hướng dẫn xử lý công việc theo quyền của bạn. Hotline ${HOTLINE} · ${EMAIL_CSKH}.`,
    },
  ]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setAuthed(!!data.session));
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open, busy]);

  async function send(text?: string) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    const history = [...msgs, { role: "user" as const, content: q }];
    setMsgs(history);
    setInput("");
    setBusy(true);
    let reply = "";
    let sources: Source[] | undefined;
    try {
      if (authed) {
        const res = await apiFetch<{ data?: { content?: string; sources?: Source[] } }>("/api/agent/chat", {
          method: "POST",
          body: JSON.stringify({
            messages: history.slice(-8).map(({ role, content }) => ({ role, content })),
          }),
        });
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
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" /> Online · trả lời theo quyền của bạn
              </div>
            </div>
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
                        <MarkdownContent className={MD_CLS}>{m.content}</MarkdownContent>
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

          <div className="flex flex-wrap gap-1.5 px-3 pb-2 pt-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} disabled={busy}
                className="rounded-full bg-secondary px-2.5 py-1 text-xs text-secondary-foreground transition-colors hover:bg-accent disabled:opacity-50">
                {s}
              </button>
            ))}
          </div>

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
