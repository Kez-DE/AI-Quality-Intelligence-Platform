// Trợ lý CSKH nổi (floating) cho Khách + trang chủ.
// - Đã đăng nhập (khách): gọi /api/agent/chat — backend tự phân tầng guest→RAG công khai
//   (CHỈ KB công khai, KHÔNG chạm dữ liệu nội bộ).
// - Trang chủ (chưa đăng nhập): trả lời tư vấn rule-based + thông tin liên hệ công khai.
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
  "Yêu cầu hoàn tiền",
  "Báo sự cố chuyến đi",
];

// Tư vấn rule-based (dùng khi chưa đăng nhập). Chỉ thông tin khách hàng + liên hệ công khai.
function cannedReply(q: string): string {
  const s = q.toLowerCase();
  if (/(gửi|phản hồi|đánh giá|góp ý|review)/.test(s))
    return `Bạn có thể gửi phản hồi ngay tại mục “Gửi phản hồi · đánh giá” trên trang Khách hàng (cần đăng nhập), hoặc qua Hotline ${HOTLINE} / email ${EMAIL_CSKH}. AI sẽ tự phân loại và chuyển tới đội xử lý phù hợp.`;
  if (/(điểm|chỉ số|chất lượng|hài lòng|sla)/.test(s))
    return "Các chỉ số dịch vụ công khai (điểm dịch vụ, tỉ lệ hài lòng, thời gian đáp ứng, tỉ lệ hoàn thành) hiển thị ngay ở phần “Chỉ số dịch vụ công khai” trên trang Khách hàng.";
  if (/(cskh|liên hệ|hotline|tổng đài|hỗ trợ|gọi)/.test(s))
    return `Kênh hỗ trợ chính thức:\n• Hotline 24/7: ${HOTLINE}\n• Email CSKH: ${EMAIL_CSKH}\n• Hoặc mục Hỗ trợ trong ứng dụng Green SM.`;
  if (/(hoàn tiền|refund|trừ tiền|thanh toán|cước|hoá đơn|hóa đơn)/.test(s))
    return `Để yêu cầu hoàn tiền hoặc khiếu nại thanh toán: gửi phản hồi chủ đề “Thanh toán” kèm mã chuyến đi, hoặc liên hệ Hotline ${HOTLINE} / email ${EMAIL_CSKH}. Nên cung cấp mã chuyến + thời gian phát sinh để xử lý nhanh.`;
  if (/(đặt xe|gọi xe|booking|điểm đón|đặt chuyến)/.test(s))
    return "Để đặt xe: mở ứng dụng Green SM, chọn điểm đón và điểm đến, xác nhận loại xe rồi đặt. Nếu app gặp lỗi, bạn có thể báo qua mục Hỗ trợ hoặc Hotline " + HOTLINE + ".";
  if (/(an toàn|tai nạn|sự cố|khẩn cấp|nguy hiểm|quấy rối)/.test(s))
    return `Trường hợp khẩn cấp về tính mạng, gọi 113 ngay. Với sự cố chuyến đi (tài xế, an toàn), hãy gọi Hotline ${HOTLINE} và gửi phản hồi kèm mã chuyến để được ưu tiên xử lý.`;
  if (/(khuyến mãi|mã giảm|ưu đãi|voucher|điểm thưởng)/.test(s))
    return "Mã khuyến mãi & ưu đãi hiện trong ứng dụng Green SM ở mục “Ưu đãi”. Áp dụng mã ở bước xác nhận chuyến trước khi đặt.";
  if (/(tài khoản|đăng nhập|mật khẩu|đăng ký)/.test(s))
    return "Bạn quản lý tài khoản ngay trong ứng dụng Green SM. Quên mật khẩu: dùng “Quên mật khẩu” để nhận liên kết đặt lại qua email/SĐT đã đăng ký.";
  if (/(dữ liệu|riêng tư|cá nhân|bảo mật|xóa|gdpr)/.test(s))
    return `Về quyền dữ liệu cá nhân (truy cập, chỉnh sửa, xóa, rút đồng ý), liên hệ bộ phận bảo vệ dữ liệu: ${DPO_EMAIL} hoặc ${DPO_PHONE}.`;
  return `Mình là trợ lý CSKH xanhSM, hỗ trợ bạn về: gửi phản hồi, xem chỉ số dịch vụ, liên hệ CSKH (Hotline ${HOTLINE}), hoàn tiền, đặt xe, an toàn, khuyến mãi. Bạn cần hỗ trợ gì ạ?`;
}

export default function SupportChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: "assistant",
      content: `Xin chào 👋 Mình là trợ lý CSKH xanhSM. Mình chỉ hỗ trợ thông tin dành cho khách hàng (đặt xe, phản hồi, thanh toán, khuyến mãi, an toàn). Hotline ${HOTLINE} · ${EMAIL_CSKH}.`,
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
