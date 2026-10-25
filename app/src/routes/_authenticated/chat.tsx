import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { supabase } from "@/integrations/supabase/client";
import {
  Sparkles,
  Send,
  Loader2,
  Bot,
  User as UserIcon,
  Trash2,
  Edit2,
  Copy,
  Check,
  AlertCircle,
  FileText,
} from "lucide-react";
import { toast } from "sonner";
import { MarkdownContent } from "@/components/MarkdownContent";
import { splitAssistantBlocks } from "@/lib/assistantBlocks";
import {
  type ChatSource,
  linkifyCitations,
  makeCitationComponents,
  srcContent,
  srcTitle,
} from "@/components/SourceCitation";
import { apiFetch, useMe, type StaffRole } from "@/lib/api";

export const Route = createFileRoute("/_authenticated/chat")({
  component: ChatPage,
});

type AgentMeta = {
  provider?: string;
  model?: string;
  latency_ms?: number;
};

type Msg = { id?: string; role: "user" | "assistant"; content: string; meta?: AgentMeta; sources?: any[] };

type AgentChatResponse = {
  data?: AgentMeta & {
    content?: string;
    sources?: any[];
  };
};

const REQUEST_HISTORY_LIMIT = 24;
const ASSISTANT_BLOCK_DELAY_MS = 380;

type ChatRoleConfig = {
  title: string;
  subtitle: string;
  emptyTitle: string;
  placeholder: string;
  suggestions: string[];
};

const CHAT_ROLE_CONFIG: Record<StaffRole, ChatRoleConfig> = {
  staff: {
    title: "AI Tác nghiệp",
    subtitle: "Trả lời theo checklist xử lý, ticket và việc cần làm của phòng bạn.",
    emptyTitle: "Trợ lý tác nghiệp sẵn sàng",
    placeholder: "Hỏi về ticket ưu tiên, checklist xử lý, SLA hoặc SOP của phòng bạn...",
    suggestions: [
      "Ticket nào cần xử lý trước trong phòng tôi?",
      "Cho tôi checklist xử lý phản hồi P5",
      "Có task nào sắp trễ SLA không?",
      "Quy trình xử lý lỗi thanh toán là gì?",
    ],
  },
  manager: {
    title: "AI Quản lý",
    subtitle: "Tổng hợp xu hướng, ưu tiên P0/P1/P2 và đề xuất điều phối cho phòng bạn.",
    emptyTitle: "Trợ lý quản lý sẵn sàng",
    placeholder: "Hỏi về xu hướng, SLA, phân bổ nguồn lực hoặc rủi ro của phòng bạn...",
    suggestions: [
      "Tóm tắt rủi ro chính của phòng tôi trong 24h qua",
      "Task nào có nguy cơ trễ SLA?",
      "Ưu tiên P0/P1 tuần này là gì?",
      "Đề xuất phân công cho spike mới nhất",
    ],
  },
  admin: {
    title: "AI Admin",
    subtitle: "Phân tích toàn hệ thống, so sánh phòng ban và theo dõi pipeline/agent.",
    emptyTitle: "Trợ lý toàn hệ thống sẵn sàng",
    placeholder: "Hỏi về toàn hệ thống, phòng ban, agent, pipeline hoặc rủi ro vận hành...",
    suggestions: [
      "Tổng quan toàn hệ thống 24h qua",
      "So sánh khu vực hoặc phòng ban có rủi ro cao",
      "Agent/pipeline có vấn đề gì cần chú ý?",
      "Đề xuất hành động liên phòng cho các spike P5",
    ],
  },
};


const markdownComponents = {
  p: ({ children }: any) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }: any) => (
    <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>
  ),
  li: ({ children }: any) => <li className="pl-1">{children}</li>,
  table: ({ children }: any) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-xanh-green/20 bg-card shadow-sm">
      <table className="min-w-full border-collapse text-left text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }: any) => <thead className="bg-xanh-mint/70">{children}</thead>,
  tbody: ({ children }: any) => <tbody className="divide-y divide-border">{children}</tbody>,
  tr: ({ children }: any) => <tr className="divide-x divide-border align-top">{children}</tr>,
  th: ({ children }: any) => (
    <th className="whitespace-nowrap px-3 py-2 font-semibold text-xanh-deep">{children}</th>
  ),
  td: ({ children }: any) => <td className="min-w-32 px-3 py-2 text-foreground/90">{children}</td>,
  strong: ({ children }: any) => (
    <strong className="font-semibold text-xanh-deep">{children}</strong>
  ),
  code: ({ children }: any) => (
    <code className="rounded bg-card/70 px-1 py-0.5 font-mono text-[0.85em] text-xanh-deep">
      {children}
    </code>
  ),
};


function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { data: me } = useMe();

  // Only Staff roles pass the layout gate; while /api/me loads, show the
  // least-privileged copy (the backend enforces the real scope).
  const role: StaffRole =
    me?.role && me.role !== "pending" && me.role !== "guest" ? me.role : "staff";
  const chatConfig = CHAT_ROLE_CONFIG[role];
  const scopeText =
    role === "admin"
      ? "Toàn hệ thống"
      : me?.department
        ? `Phòng ${me.department}`
        : "Chưa gán phòng ban";

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

  async function clearChat() {
    try {
      setError(null);
      setCopiedIndex(null);
      setMessages([]);
      const { data: u } = await supabase.auth.getUser();
      if (u?.user) {
        const { error } = await supabase.from("chat_messages").delete().eq("user_id", u.user.id);
        if (error) throw error;
      }
      toast.success("Đã xóa cuộc trò chuyện, bạn có thể bắt đầu lại!");
    } catch (err: any) {
      toast.error("Lỗi khi xóa: " + (err.message || "Không xác định"));
    }
  }

  async function editMessage(index: number) {
    if (loading) return;
    const targetMsg = messages[index];
    if (targetMsg.role !== "user") return;

    const newMessages = messages.slice(0, index);
    const textToEdit = targetMsg.content;

    setInput(textToEdit);
    setError(null);
    setMessages(newMessages);

    const { data: u } = await supabase.auth.getUser();
    if (u?.user) {
      const idsToDelete = messages
        .slice(index)
        .map((m) => m.id)
        .filter((id): id is string => Boolean(id));
      if (idsToDelete.length > 0) {
        // @ts-ignore
        supabase
          .from("chat_messages")
          .delete()
          .in("id", idsToDelete)
          .then(({ error }) => {
            if (error) console.error("Edit delete error:", error);
          });
      }
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;
    setInput("");
    setLoading(true);
    setError(null);
    setCopiedIndex(null);

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
    await supabase.from("chat_messages").insert({ user_id: u.user.id, role: "user", content });

    try {
      const endpoint = "/api/agent/chat"; // backend tự phân tầng theo role + phòng ban (ReAct Agent)
      const reply = await apiFetch<AgentChatResponse>(
        endpoint,
        {
          method: "POST",
          body: JSON.stringify({
            messages: next
              .slice(-REQUEST_HISTORY_LIMIT)
              .map(({ role, content }) => ({ role, content })),
          }),
        },
        45_000, // ReAct agent có thể chạy nhiều vòng gọi tool + LLM, cần nhiều thời gian hơn request thường
      );
      const replyContent = reply.data?.content?.trim();
      if (!replyContent) throw new Error("AI không trả về nội dung.");

      const aMsg: Msg = {
        role: "assistant",
        content: replyContent,
        meta: {
          provider: reply.data?.provider,
          model: reply.data?.model,
          latency_ms: reply.data?.latency_ms,
        },
        sources: reply.data?.sources,
      };
      setMessages((m) => [...m, aMsg]);
      await supabase
        .from("chat_messages")
        .insert({ user_id: u.user.id, role: "assistant", content: replyContent });
    } catch (err: any) {
      const message = err.message ?? "AI lỗi";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  async function copyMessage(content: string, index: number) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      window.setTimeout(
        () => setCopiedIndex((current) => (current === index ? null : current)),
        1600,
      );
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-xanh-green" />
            {chatConfig.title}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {chatConfig.subtitle} <span className="font-medium text-xanh-deep">({scopeText})</span>
          </p>
        </div>
        <button
          onClick={clearChat}
          type="button"
          className="relative z-50 cursor-pointer flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg text-sm font-semibold text-xanh-deep hover:bg-muted transition-colors shadow-sm active:scale-95"
        >
          <Trash2 className="h-4 w-4" /> Cuộc trò chuyện mới
        </button>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden">
        <div className="flex-[6] rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-10">
              <div
                className="h-14 w-14 rounded-2xl grid place-items-center text-white mx-auto shadow-[var(--shadow-green)]"
                style={{ background: "var(--gradient-green)" }}
              >
                <Bot className="h-7 w-7" />
              </div>
              <h3 className="font-display font-semibold mt-3">{chatConfig.emptyTitle}</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Bắt đầu bằng một trong các gợi ý dưới đây hoặc gõ câu hỏi của bạn.
              </p>
              <div className="grid sm:grid-cols-2 gap-2 max-w-xl mx-auto mt-5">
                {chatConfig.suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-sm rounded-xl border border-border bg-card p-3 hover:border-xanh-green/40 hover:bg-xanh-mint/30 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Bubble
              key={m.id ?? i}
              role={m.role}
              content={m.content}
              meta={m.meta}
              isLast={i === messages.length - 1 || (m.role === "user" && i === messages.length - 2)}
              onEdit={m.role === "user" ? () => editMessage(i) : undefined}
              onCopy={m.role === "assistant" ? () => copyMessage(m.content, i) : undefined}
              copied={copiedIndex === i}
              sources={m.sources}
            />
          ))}

          {loading && <Bubble role="assistant" content="" loading />}
          <div ref={bottomRef} />
        </div>

        {error && (
          <div className="border-t border-border bg-destructive/10 px-4 py-2 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{error}</span>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="border-t border-border p-3 flex items-end gap-2 bg-card"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder={chatConfig.placeholder}
            rows={1}
            className="min-h-11 max-h-32 flex-1 resize-none rounded-xl border border-border px-4 py-3 text-sm leading-5 focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            aria-label="Gửi tin nhắn"
            className="h-11 w-11 rounded-xl text-white font-semibold grid place-items-center shadow-[var(--shadow-green)] disabled:opacity-60 shrink-0"
            style={{ background: "var(--gradient-green)" }}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
        </div>
        {(messages.some(m => m.sources?.length) || loading) && (
          <div className="flex-[4] rounded-2xl border border-border bg-card shadow-[var(--shadow-card)] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border bg-muted/30">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <FileText className="h-4 w-4 text-xanh-green" />
                Nguồn tài liệu tham khảo
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {loading ? (
                <div className="text-center text-sm text-muted-foreground mt-10">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2 text-xanh-green" />
                  Đang tra cứu tài liệu SOP/SLA...
                </div>
              ) : (
                messages[messages.length - 1]?.sources?.map((s: any, idx: number) => (
                  <div key={idx} className="rounded-xl border border-border p-3 text-sm hover:border-xanh-green/50 transition-colors bg-card">
                    <div className="font-semibold text-xanh-deep mb-1 line-clamp-1">{srcTitle(s)}{s.heading ? ` - ${s.heading}` : ""}</div>
                    {typeof s.similarity === "number" && (
                      <div className="text-xs text-muted-foreground mb-2">Độ tương đồng: {Math.round(s.similarity * 100)}%</div>
                    )}
                    <p className="text-muted-foreground line-clamp-4 text-xs">{srcContent(s)}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Bubble({
  role,
  content,
  meta,
  loading,
  isLast,
  onEdit,
  onCopy,
  copied,
  sources,
}: {
  role: "user" | "assistant";
  content: string;
  meta?: AgentMeta;
  loading?: boolean;
  isLast?: boolean;
  onEdit?: () => void;
  onCopy?: () => void;
  copied?: boolean;
  sources?: ChatSource[];
}) {
  const isUser = role === "user";
  const metaText = [meta?.provider, meta?.model, meta?.latency_ms ? `${meta.latency_ms}ms` : ""]
    .filter(Boolean)
    .join(" · ");

  if (!isUser) {
    return (
      <div className="flex gap-3">
        <div
          className="h-8 w-8 rounded-lg grid place-items-center shrink-0 text-white"
          style={{ background: "var(--gradient-green)" }}
        >
          <Bot className="h-4 w-4" />
        </div>
        {loading ? (
          <ThinkingBlocks />
        ) : (
          <AssistantResponse
            content={content}
            metaText={metaText}
            animate={!!isLast}
            copied={copied}
            onCopy={onCopy}
            sources={sources}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-3 flex-row-reverse">
      <div className="h-8 w-8 rounded-lg grid place-items-center shrink-0 bg-xanh-deep text-white">
        <UserIcon className="h-4 w-4" />
      </div>
      <div className="relative group max-w-[82%] rounded-2xl rounded-tr-sm bg-xanh-deep px-4 py-2.5 text-sm leading-relaxed text-white whitespace-pre-wrap">
        {content}

        {onEdit && isLast && (
          <button
            onClick={onEdit}
            title="Sửa câu hỏi"
            className="absolute -left-10 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-muted text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-xanh-deep"
          >
            <Edit2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

function AssistantResponse({
  content,
  metaText,
  animate,
  onCopy,
  copied,
  sources,
}: {
  content: string;
  metaText: string;
  animate: boolean;
  onCopy?: () => void;
  copied?: boolean;
  sources?: ChatSource[];
}) {
  const blocks = splitAssistantBlocks(content);
  const citationComponents = { ...markdownComponents, ...makeCitationComponents(sources) };
  const [visibleCount, setVisibleCount] = useState(
    animate ? Math.min(1, blocks.length) : blocks.length,
  );

  useEffect(() => {
    if (!animate) {
      setVisibleCount(blocks.length);
      return;
    }

    setVisibleCount(Math.min(1, blocks.length));
    const timers = blocks.slice(1).map((_, index) =>
      window.setTimeout(
        () => {
          setVisibleCount(index + 2);
        },
        (index + 1) * ASSISTANT_BLOCK_DELAY_MS,
      ),
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [animate, blocks.length, content]);

  return (
    <div className="group relative max-w-[86%] space-y-2">
      {blocks.slice(0, visibleCount).map((block, index) => (
        <div
          key={`${index}-${block.title ?? block.body.slice(0, 24)}`}
          className="rounded-xl border border-xanh-green/20 bg-xanh-mint/40 px-4 py-3 text-sm leading-relaxed text-foreground shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-300"
        >
          <div className="flex gap-3">
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-xanh-green ring-4 ring-xanh-green/15" />
            <div className="min-w-0 flex-1">
              {block.title && (
                <div className="mb-1 font-semibold text-xanh-deep">{block.title}</div>
              )}
              <MarkdownContent components={citationComponents}>
                {sources?.length ? linkifyCitations(block.body) : block.body}
              </MarkdownContent>
            </div>
          </div>
        </div>
      ))}

      {visibleCount < blocks.length && (
        <div className="inline-flex rounded-xl border border-border bg-card px-3 py-2 shadow-sm animate-in fade-in duration-200">
          <Dot /> <Dot d={150} /> <Dot d={300} />
        </div>
      )}



      {onCopy && visibleCount >= blocks.length && (
        <button
          onClick={onCopy}
          title="Sao chép câu trả lời"
          className="absolute -right-10 top-1 p-1.5 rounded-full bg-card border border-border text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-xanh-deep"
        >
          {copied ? <Check className="h-4 w-4 text-xanh-green" /> : <Copy className="h-4 w-4" />}
        </button>
      )}
    </div>
  );
}

function ThinkingBlocks() {
  return (
    <div className="max-w-[86%] space-y-2">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="rounded-xl border border-xanh-green/20 bg-xanh-mint/30 px-4 py-3 shadow-sm animate-pulse"
          style={{ animationDelay: `${index * 160}ms` }}
        >
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-xanh-green/70" />
            <span
              className={`h-2 rounded-full bg-xanh-deep/15 ${index === 0 ? "w-40" : index === 1 ? "w-56" : "w-32"}`}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Dot({ d = 0 }: { d?: number }) {
  return (
    <span
      className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-xanh-deep/60"
      style={{ animationDelay: `${d}ms` }}
    />
  );
}
