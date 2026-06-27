// Trợ lý CSKH nổi (floating) cho Khách + trang chủ.
// - Đã đăng nhập (khách): gọi /api/agent/chat — backend tự phân tầng guest→RAG công khai
//   (CHỈ KB công khai, KHÔNG chạm dữ liệu nội bộ).
// - Trang chủ (chưa đăng nhập): tư vấn rule-based + thông tin liên hệ công khai; mọi vấn đề
//   cần xử lý đều điều hướng: liên hệ khẩn cấp + đăng nhập để gửi phản hồi chính thức.
// Mọi câu trả lời chỉ xoay quanh hỗ trợ khách hàng, hướng dẫn — không lộ dữ liệu nội bộ.
import { useEffect, useRef, useState } from "react";
import { Bot, X, Send, Sparkles, Phone, Mail } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { apiFetch } from "@/lib/api";

// Liên hệ công khai — lấy từ data/public_kb (ho_tro_khieu_nai.md).
const HOTLINE = "1555";
const EMAIL_CSKH = "support.vn@greensm.com";
const DPO_EMAIL = "DPOoffice@greensm.com";
const DPO_PHONE = "1900 2097";

type Msg = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "Cách gửi phản hồi?",
  "Liên hệ CSKH",
  "Báo sự cố / cần giúp đỡ",
  "Yêu cầu hoàn tiền",
];

// Tư vấn rule-based (dùng khi CHƯA đăng nhập). Chỉ thông tin khách hàng + liên hệ công khai.
// Mọi vấn đề cần xử lý → điều hướng: liên hệ khẩn cấp/Hotline + đăng nhập để gửi phản hồi.
function cannedReply(q: string): string {
  const s = q.toLowerCase();

  // 1) Khẩn cấp / an toàn / bị xâm hại — ưu tiên cao nhất, trả lời ân cần + điều hướng hỗ trợ.
  if (
    /(xâm hại|xam hai|xâm phạm|hành hung|hanh hung|bị đánh|bi danh|đánh tôi|bị thương|hành hạ|tấn công|tan cong|cướp|cuop|trộm|sàm sỡ|sam so|quấy rối|quay roi|đe dọa|đe doạ|de doa|hăm dọa|bạo lực|bao luc|tai nạn|tai nan|khẩn cấp|khan cap|nguy hiểm|nguy hiem|bắt cóc|bat coc|cứu|giúp với|giup voi|sợ hãi|so hai|bị hại)/.test(
      s,
    )
  )
    return `Mình rất tiếc về việc bạn đang gặp phải và mình ở đây để hỗ trợ bạn.\n\n⚠️ Nếu bạn đang gặp nguy hiểm hoặc cần hỗ trợ khẩn cấp, hãy gọi ngay 113 (Công an) hoặc 115 (Cấp cứu).\n\nVới sự cố liên quan chuyến đi xanhSM (tài xế, an toàn, quấy rối): gọi Hotline ${HOTLINE} (24/7) ngay và giữ lại bằng chứng (mã chuyến, ảnh chụp, thời gian).\n\nĐể gửi khiếu nại/phản hồi chính thức và được theo dõi xử lý: hãy bấm "Đăng nhập" ở góc trên, rồi vào mục "Gửi phản hồi" trên trang Khách hàng. Email hỗ trợ: ${EMAIL_CSKH}.`;

  // 2) Chủ đề cụ thể.
  if (/(hoàn tiền|refund|trừ tiền|thanh toán|cước phí|hoá đơn|hóa đơn)/.test(s))
    return `Để yêu cầu hoàn tiền/khiếu nại thanh toán: hãy bấm "Đăng nhập" rồi gửi phản hồi chủ đề "Thanh toán" kèm mã chuyến đi trên trang Khách hàng (AI sẽ chuyển tới đội xử lý). Cần gấp: Hotline ${HOTLINE} hoặc email ${EMAIL_CSKH} — nên cung cấp mã chuyến + thời gian phát sinh.`;
  if (/(đặt xe|gọi xe|booking|điểm đón|đặt chuyến)/.test(s))
    return `Để đặt xe: mở ứng dụng Green SM, chọn điểm đón và điểm đến, xác nhận loại xe rồi đặt. Nếu app gặp lỗi, hãy gọi Hotline ${HOTLINE} hoặc đăng nhập để gửi phản hồi.`;
  if (/(khuyến mãi|mã giảm|ưu đãi|voucher|điểm thưởng)/.test(s))
    return "Mã khuyến mãi & ưu đãi hiển thị trong ứng dụng Green SM ở mục “Ưu đãi”. Áp dụng mã ở bước xác nhận chuyến trước khi đặt.";
  if (/(tài khoản|đăng nhập|mật khẩu|đăng ký)/.test(s))
    return "Bạn quản lý tài khoản trong ứng dụng Green SM. Quên mật khẩu: dùng “Quên mật khẩu” để nhận liên kết đặt lại qua email/SĐT đã đăng ký. Đăng nhập trên trang này để gửi phản hồi và theo dõi xử lý.";
  if (/(dữ liệu|riêng tư|cá nhân|bảo mật|xóa tài khoản|gdpr)/.test(s))
    return `Về quyền dữ liệu cá nhân (truy cập, chỉnh sửa, xóa, rút đồng ý), liên hệ bộ phận bảo vệ dữ liệu: ${DPO_EMAIL} hoặc ${DPO_PHONE}.`;
  if (/(điểm|chỉ số|chất lượng|hài lòng|sla)/.test(s))
    return "Các chỉ số dịch vụ công khai (điểm dịch vụ, tỉ lệ hài lòng, thời gian đáp ứng, tỉ lệ hoàn thành) hiển thị ở phần “Chỉ số dịch vụ công khai” trên trang Khách hàng.";
  if (/(cskh|liên hệ|hotline|tổng đài|gọi điện|số điện thoại|số máy)/.test(s))
    return `Kênh hỗ trợ chính thức:\n• Hotline 24/7: ${HOTLINE}\n• Email CSKH: ${EMAIL_CSKH}\n• Hoặc mục Hỗ trợ trong ứng dụng Green SM.`;

  // 3) Khiếu nại / phản hồi / cần giúp đỡ (chung) — điều hướng đăng nhập + gửi phản hồi.
  if (
    /(khiếu nại|khieu nai|phản ánh|phan anh|tố cáo|to cao|phản hồi|phan hoi|góp ý|gop y|đánh giá|danh gia|review|vấn đề|van de|sự việc|su viec|không hài lòng|bức xúc|buc xuc|giúp|giup|hỗ trợ|ho tro|cần|can)/.test(
      s,
    )
  )
    return `Để được hỗ trợ và xử lý chính thức, bạn hãy bấm "Đăng nhập" (góc trên bên phải) rồi vào mục "Gửi phản hồi · đánh giá" trên trang Khách hàng — AI sẽ tự phân loại và chuyển phản hồi của bạn tới đội phù hợp, và bạn theo dõi được trạng thái xử lý.\n\nCần hỗ trợ ngay: Hotline ${HOTLINE} (24/7) · ${EMAIL_CSKH}.`;

  // 4) Mặc định — vẫn điều hướng liên hệ + đăng nhập gửi phản hồi.
  return `Mình là trợ lý CSKH xanhSM, hỗ trợ thông tin về dịch vụ (đặt xe, thanh toán, an toàn, khuyến mãi).\n\nNếu bạn cần phản ánh/khiếu nại hoặc gặp sự cố, hãy bấm "Đăng nhập" rồi gửi phản hồi trên trang Khách hàng để được theo dõi xử lý. Hỗ trợ ngay: Hotline ${HOTLINE} · ${EMAIL_CSKH}.`;
}

export default function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: "assistant",
      content: `Xin chào 👋 Mình là trợ lý CSKH xanhSM. Mình hỗ trợ thông tin dành cho khách hàng (đặt xe, phản hồi, thanh toán, khuyến mãi, an toàn). Nếu bạn gặp sự cố hoặc cần khiếu nại, mình sẽ hướng dẫn bạn liên hệ đúng kênh và đăng nhập để gửi phản hồi. Hotline ${HOTLINE} · ${EMAIL_CSKH}.`,
    },
  ]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setAuthed(!!data.session));
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open]);

  async function send(text?: string) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    const history = [...msgs, { role: "user" as const, content: q }];
    setMsgs(history);
    setInput("");
    setBusy(true);
    try {
      if (authed) {
        // Khách đã đăng nhập → backend guest RAG (chỉ KB công khai, không dữ liệu nội bộ).
        const res = await apiFetch<{ data?: { content?: string } }>("/api/agent/chat", {
          method: "POST",
          body: JSON.stringify({
            messages: history.slice(-8).map(({ role, content }) => ({ role, content })),
          }),
        });
        const reply = res.data?.content?.trim();
        setMsgs((m) => [...m, { role: "assistant", content: reply || cannedReply(q) }]);
      } else {
        // Trang chủ chưa đăng nhập → tư vấn rule-based + liên hệ công khai.
        await new Promise((r) => setTimeout(r, 350));
        setMsgs((m) => [...m, { role: "assistant", content: cannedReply(q) }]);
      }
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: cannedReply(q) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full text-primary-foreground shadow-xl shadow-primary/30 transition-transform hover:scale-105 active:scale-95"
        style={{ background: "var(--gradient-green)" }}
        aria-label="Mở trợ lý CSKH"
      >
        {open ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
        {!open && <span className="absolute right-0 top-0 h-3 w-3 animate-pulse rounded-full bg-destructive ring-2 ring-background" />}
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[520px] max-h-[calc(100vh-8rem)] w-[360px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border bg-card shadow-2xl">
          <div className="p-4 text-white" style={{ background: "var(--gradient-hero)" }}>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20"><Sparkles className="h-5 w-5" /></div>
              <div className="flex-1">
                <div className="font-display font-semibold leading-none">Trợ lý CSKH xanhSM</div>
                <div className="mt-1 flex items-center gap-1.5 text-xs opacity-90">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" /> Online · chỉ hỗ trợ khách hàng
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[82%] whitespace-pre-line rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user" ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-muted text-foreground"
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
            {busy && <div className="flex justify-start"><div className="rounded-2xl rounded-bl-sm bg-muted px-3 py-2 text-sm text-muted-foreground">Đang soạn…</div></div>}
            <div ref={endRef} />
          </div>

          <div className="flex flex-wrap gap-1.5 px-3 pb-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} disabled={busy}
                className="rounded-full bg-secondary px-2.5 py-1 text-xs text-secondary-foreground transition-colors hover:bg-accent disabled:opacity-50">
                {s}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3 border-t px-3 py-2 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Phone className="h-3 w-3" />{HOTLINE}</span>
            <span className="inline-flex items-center gap-1"><Mail className="h-3 w-3" />{EMAIL_CSKH}</span>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 border-t bg-background p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Hỏi về dịch vụ, đặt xe, phản hồi…"
              className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <button type="submit" disabled={busy} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground disabled:opacity-50">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
