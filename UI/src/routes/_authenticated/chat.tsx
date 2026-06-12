import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useServerFn } from "@tanstack/react-start";
import { chatWithAI } from "@/lib/ai.functions";
import { Sparkles, Send, Loader2, Bot, User as UserIcon } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/chat")({
  component: ChatPage,
});

type Msg = { id?: string; role: "user" | "assistant"; content: string };

const SUGGESTED = [
  "Tổng hợp 5 vấn đề chất lượng dịch vụ nổi cộm tuần qua",
  "Khu vực nào đang có phản hồi tiêu cực tăng bất thường?",
  "Đề xuất hành động cho spike khiếu nại thanh toán",
  "Phân tích pattern phàn nàn của tài xế DRV-2841",
];

function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const chatFn = useServerFn(chatWithAI);

  useEffect(() => {
    supabase
      .from("chat_messages")
      .select("id,role,content")
      .order("created_at", { ascending: true })
      .limit(200)
      .then(({ data }) => {
        if (data) setMessages(data as Msg[]);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;
    setInput("");
    setLoading(true);

    const { data: u } = await supabase.auth.getUser();
    if (!u.user) {
      toast.error("Chưa đăng nhập");
      setLoading(false);
      return;
    }

    const userMsg: Msg = { role: "user", content };
    const next = [...messages, userMsg];
    setMessages(next);

    // persist user message
    await supabase
      .from("chat_messages")
      .insert({ user_id: u.user.id, role: "user", content });

    try {
      const reply = await chatFn({
        data: { messages: next.map(({ role, content }) => ({ role, content })) },
      });
      const aMsg: Msg = { role: "assistant", content: reply.content };
      setMessages((m) => [...m, aMsg]);
      await supabase
        .from("chat_messages")
        .insert({ user_id: u.user.id, role: "assistant", content: reply.content });
    } catch (err: any) {
      toast.error(err.message ?? "AI lỗi");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      <div className="mb-4">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-xanh-green" />
          AI Assistant
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Trợ lý AI giúp diễn giải dữ liệu phản hồi và đề xuất hành động vận hành.
        </p>
      </div>

      <div className="flex-1 rounded-2xl border border-border bg-white shadow-[var(--shadow-card)] overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-10">
              <div
                className="h-14 w-14 rounded-2xl grid place-items-center text-white mx-auto shadow-[var(--shadow-green)]"
                style={{ background: "var(--gradient-green)" }}
              >
                <Bot className="h-7 w-7" />
              </div>
              <h3 className="font-display font-semibold mt-3">Hỏi gì AI cũng đáp</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Bắt đầu bằng một trong các gợi ý dưới đây hoặc gõ câu hỏi của bạn.
              </p>
              <div className="grid sm:grid-cols-2 gap-2 max-w-xl mx-auto mt-5">
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-sm rounded-xl border border-border bg-white p-3 hover:border-xanh-green/40 hover:bg-xanh-mint/30 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Bubble key={m.id ?? i} role={m.role} content={m.content} />
          ))}

          {loading && (
            <Bubble role="assistant" content="" loading />
          )}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="border-t border-border p-3 flex gap-2 bg-white"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hỏi AI về dữ liệu phản hồi, xu hướng, đề xuất hành động..."
            className="flex-1 h-11 px-4 rounded-xl border border-border focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="h-11 px-4 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] disabled:opacity-60"
            style={{ background: "var(--gradient-green)" }}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}

function Bubble({
  role,
  content,
  loading,
}: {
  role: "user" | "assistant";
  content: string;
  loading?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`h-8 w-8 rounded-lg grid place-items-center shrink-0 ${
          isUser ? "bg-xanh-deep text-white" : "text-white"
        }`}
        style={!isUser ? { background: "var(--gradient-green)" } : undefined}
      >
        {isUser ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
          isUser
            ? "bg-xanh-deep text-white rounded-tr-sm"
            : "bg-xanh-mint/40 text-foreground border border-xanh-green/20 rounded-tl-sm"
        }`}
      >
        {loading ? (
          <span className="inline-flex gap-1">
            <Dot /> <Dot d={150} /> <Dot d={300} />
          </span>
        ) : (
          content
        )}
      </div>
    </div>
  );
}

function Dot({ d = 0 }: { d?: number }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 rounded-full bg-xanh-deep/60 animate-bounce"
      style={{ animationDelay: `${d}ms` }}
    />
  );
}
