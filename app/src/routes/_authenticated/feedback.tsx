import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Loader2, MessageSquarePlus, MapPin, Tag, AlertCircle, Pencil, ShieldAlert, CheckCircle2, Inbox } from "lucide-react";
import { toast } from "sonner";
import { AREAS, regionLabel } from "@/lib/regions";
import { sentimentLabel, topicLabel, channelLabel, severityLabel } from "@/lib/labels";
import { apiFetch, useMe } from "@/lib/api";

export const Route = createFileRoute("/_authenticated/feedback")({
  component: FeedbackPage,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      filter: search.filter as string | undefined,
    };
  },
});

type Feedback = {
  id: string;
  source: string;
  channel: string;
  text: string;
  topic: string | null;
  sentiment: string | null;
  severity: string | null;
  area: string | null;
  confidence: number | null;
  needs_review: boolean | null;
  reviewed: boolean | null;
  review_reason: string | null;
  created_at: string;
};

const CHANNELS = ["app", "rating", "hotline", "cs", "survey"];
const REFRESH_INTERVAL_MS = 5000;

// Options cho ô sửa nhãn (Human-in-the-loop). Khớp nhãn classifier sinh ra.
const TOPIC_OPTIONS = ["Safety", "Driver Behavior", "App Issue", "Payment", "Pricing", "Delay", "Other"];
const SENTIMENT_OPTIONS = ["negative", "neutral", "positive"];
const SEVERITY_OPTIONS = ["P1", "P2", "P3", "P4", "P5"];

function severityNum(sev: string | null): number {
  if (!sev) return 0;
  const n = parseInt(sev.replace(/^P/i, ""), 10);
  return Number.isFinite(n) ? n : 0;
}

type FilterType = "all" | "needs_review" | "critical" | "low_conf";

function FeedbackPage() {
  const [list, setList] = useState<Feedback[]>([]);
  const [queue, setQueue] = useState<Feedback[]>([]);
  const [newFeedbackIds, setNewFeedbackIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);

  const { data: me } = useMe();

  const search = Route.useSearch();
  const [activeFilter, setActiveFilter] = useState<FilterType>(
    ["all", "needs_review", "critical", "low_conf"].includes(search.filter as string) 
      ? (search.filter as FilterType) 
      : "all"
  );

  const [form, setForm] = useState({
    text: "",
    channel: "app",
    area: AREAS[0].code,
  });

  // Human-in-the-loop: state cho ô sửa nhãn đang mở (theo feedback id).
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<{ topic: string; sentiment: string; severity: string }>({
    topic: "",
    sentiment: "",
    severity: "",
  });
  const [savingId, setSavingId] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  function openEditor(f: Feedback) {
    setEditingId(f.id);
    setEditDraft({
      topic: f.topic ?? TOPIC_OPTIONS[0],
      sentiment: f.sentiment ?? SENTIMENT_OPTIONS[0],
      severity: f.severity ?? SEVERITY_OPTIONS[0],
    });
  }

  async function saveCorrection(id: string) {
    setSavingId(id);
    try {
      await apiFetch(`/api/feedback/${id}/label`, {
        method: "PATCH",
        body: JSON.stringify(editDraft),
      });
      toast.success("Đã cập nhật nhãn — ghi vào correction log");
      setEditingId(null);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không sửa được nhãn");
    } finally {
      setSavingId(null);
    }
  }

  async function reviewAction(id: string) {
    setActingId(id);
    try {
      await apiFetch(`/api/feedback/${id}/review`, {
        method: "PATCH",
        body: JSON.stringify({ action: "approve" }),
      });
      toast.success("Đã duyệt — chuyển khỏi hàng đợi");
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không duyệt được");
    } finally {
      setActingId(null);
    }
  }

  async function load() {
    if (!me?.role) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const streamJson = await apiFetch<{ data?: Feedback[] }>("/api/feedback/recent?limit=200");
      const rows = streamJson.data ?? [];
      const incomingIds = rows.map((row) => row.id);
      const freshIds = incomingIds.filter((id) => !seenIdsRef.current.has(id));
      incomingIds.forEach((id) => seenIdsRef.current.add(id));
      if (initializedRef.current && freshIds.length) {
        setNewFeedbackIds(new Set(freshIds));
        window.setTimeout(() => setNewFeedbackIds(new Set()), 1600);
      }
      initializedRef.current = true;
      setList(rows);
      const queueJson = await apiFetch<{ data?: Feedback[] }>(
        "/api/feedback/recent?limit=200&needs_review=true&reviewed=false",
      );
      setQueue(queueJson.data ?? []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Không đọc được live feedback");
    }
    setLoading(false);
  }

  useEffect(() => {
    if (me?.role) {
      load();
      const id = window.setInterval(load, REFRESH_INTERVAL_MS);
      return () => window.clearInterval(id);
    }
  }, [me?.role]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.text.trim()) return;
    setSubmitting(true);
    try {
      await apiFetch("/api/feedback/submit", {
        method: "POST",
        body: JSON.stringify({
          text: form.text.trim(),
          channel: form.channel,
          area: form.area || null,
        }),
      });
      toast.success("Đã gửi phản hồi — AI đang phân tích & gán nhãn");
      setForm({ ...form, text: "", area: AREAS[0].code });
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không gửi được phản hồi");
    } finally {
      setSubmitting(false);
    }
  }

  // Stream = danh sách chung, loại các id đang nằm trong Queue.
  const queueIds = new Set(queue.map((f) => f.id));
  let stream = list.filter((f) => !queueIds.has(f.id));
  let reviewQueue = queue;

  if (activeFilter === "critical") {
    stream = stream.filter(f => severityNum(f.severity) >= 4);
    reviewQueue = reviewQueue.filter(f => severityNum(f.severity) >= 4);
  } else if (activeFilter === "low_conf") {
    stream = stream.filter(f => f.confidence != null && f.confidence < 0.55);
    reviewQueue = reviewQueue.filter(f => f.confidence != null && f.confidence < 0.55);
  } else if (activeFilter === "needs_review") {
    stream = [];
  }

  const filterLabel = {
    all: "",
    critical: "Nghiêm trọng (P4/P5)",
    low_conf: "Confidence thấp (<55%)",
    needs_review: "Cần duyệt",
  }[activeFilter];

  const stats = {
    total: list.length,
    review: reviewQueue.length,
    critical: list.filter((f) => severityNum(f.severity) >= 4).length,
    lowConf: list.filter((f) => f.confidence != null && f.confidence < 0.55).length,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Thu thập phản hồi</h1>
        <p className="text-sm text-muted-foreground mt-1">
          AI tự phân loại & gán nhãn. Ca nguy hiểm hoặc không chắc được tách sang hàng đợi duyệt.
        </p>
      </div>

      {/* 1. Form phản hồi mới */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquarePlus className="h-4 w-4 text-xanh-green" />
          <h2 className="font-display font-semibold">Phản hồi mới</h2>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <textarea
            required
            rows={3}
            value={form.text}
            onChange={(e) => setForm({ ...form, text: e.target.value })}
            placeholder="VD: Tài xế đi sai đường, không dùng định vị, thái độ khó chịu..."
            className="w-full p-3 rounded-xl border border-border focus:outline-none focus:ring-2 focus:ring-xanh-green/40 resize-none"
          />
          <div className="grid sm:grid-cols-2 gap-2">
            <Select label="Kênh" value={form.channel} onChange={(v) => setForm({ ...form, channel: v })} options={CHANNELS} labelFn={channelLabel} />
            <label className="text-xs">
              <div className="text-muted-foreground mb-1">Khu vực</div>
              <select
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                className="w-full h-9 px-2 rounded-lg border border-border bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
              >
                {AREAS.map((a) => (
                  <option key={a.code} value={a.code}>
                    {a.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Tag className="h-3 w-3" />
            Chủ đề, cảm xúc và mức độ nghiêm trọng do AI tự phân tích sau khi gửi.
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="h-10 px-5 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] disabled:opacity-60"
            style={{ background: "var(--gradient-green)" }}
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Lưu phản hồi"}
          </button>
        </form>
      </section>

      {/* 2. Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard 
            label="Tổng phản hồi" 
            value={stats.total} 
            icon={Inbox} 
            tone="deep" 
            onClick={() => setActiveFilter("all")}
            isActive={activeFilter === "all"}
          />
          <StatCard 
            label="Cần duyệt" 
            value={stats.review} 
            icon={ShieldAlert} 
            tone="coral" 
            onClick={() => setActiveFilter("needs_review")}
            isActive={activeFilter === "needs_review"}
          />
          <StatCard 
            label="P4 / P5" 
            value={stats.critical} 
            icon={AlertCircle} 
            tone="amber" 
            onClick={() => setActiveFilter("critical")}
            isActive={activeFilter === "critical"}
          />
          <StatCard 
            label="Confidence thấp" 
            value={stats.lowConf} 
            icon={AlertCircle} 
            tone="mint" 
            onClick={() => setActiveFilter("low_conf")}
            isActive={activeFilter === "low_conf"}
          />
      </div>

      {/* 3. Hai cột: Luồng phản hồi (trái) | Cần duyệt (phải) */}
      <div className="grid lg:grid-cols-2 gap-4 items-start">
          {/* Cột trái: Luồng phản hồi */}
        <section className="rounded-2xl border border-border bg-card shadow-[var(--shadow-card)]">
          <div className="p-5 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Inbox className="h-4 w-4 text-xanh-deep" />
              <h2 className="font-display font-semibold">
                Luồng phản hồi <span className="text-muted-foreground font-mono text-xs">({stream.length})</span>
              </h2>
              {activeFilter !== "all" && (
                <button 
                  onClick={() => setActiveFilter("all")}
                  className="ml-2 text-[10px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full hover:bg-amber-200"
                >
                  Đang lọc: {filterLabel} ✕
                </button>
              )}
            </div>
            <button onClick={load} className="text-xs font-mono text-xanh-deep hover:underline">
              ↻ refresh
            </button>
          </div>
          {loading && list.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin inline" />
            </div>
          ) : stream.length === 0 ? (
            <div className="p-10 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-5 w-5 inline mr-2" />
              Chưa có phản hồi nào.
            </div>
          ) : (
            <div className="divide-y divide-border max-h-[70vh] overflow-y-auto">
              {stream.map((f) => (
                <FeedbackRow
                  key={f.id}
                  f={f}
                  isNew={newFeedbackIds.has(f.id)}
                  editing={editingId === f.id}
                  editDraft={editDraft}
                  setEditDraft={setEditDraft}
                  onToggleEdit={() => (editingId === f.id ? setEditingId(null) : openEditor(f))}
                  onSave={() => saveCorrection(f.id)}
                  saving={savingId === f.id}
                />
              ))}
            </div>
          )}
        </section>

        {/* Cột phải: Cần duyệt / Review Queue */}
        <section className="rounded-2xl border border-amber-300 bg-amber-50/40 shadow-[var(--shadow-card)]">
          <div className="p-5 border-b border-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-600" />
              <h2 className="font-display font-semibold text-amber-900">
                Cần duyệt / Review Queue <span className="font-mono text-xs">({reviewQueue.length})</span>
              </h2>
              {activeFilter !== "all" && (
                <button 
                  onClick={() => setActiveFilter("all")}
                  className="ml-2 text-[10px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full hover:bg-amber-200"
                >
                  Đang lọc: {filterLabel} ✕
                </button>
              )}
            </div>
          </div>
          {reviewQueue.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              <CheckCircle2 className="h-5 w-5 inline mr-2 text-xanh-green" />
              Không có phản hồi nào cần duyệt.
            </div>
          ) : (
            <div className="divide-y divide-amber-200/60 max-h-[70vh] overflow-y-auto">
              {reviewQueue.map((f) => (
                <FeedbackRow
                  key={f.id}
                  f={f}
                  isNew={newFeedbackIds.has(f.id)}
                  editing={editingId === f.id}
                  editDraft={editDraft}
                  setEditDraft={setEditDraft}
                  onToggleEdit={() => (editingId === f.id ? setEditingId(null) : openEditor(f))}
                  onSave={() => saveCorrection(f.id)}
                  saving={savingId === f.id}
                  onApprove={() => reviewAction(f.id)}
                  acting={actingId === f.id}
                  showActions
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function FeedbackRow({
  f,
  isNew,
  editing,
  editDraft,
  setEditDraft,
  onToggleEdit,
  onSave,
  saving,
  onApprove,
  acting,
  showActions,
}: {
  f: Feedback;
  isNew: boolean;
  editing: boolean;
  editDraft: { topic: string; sentiment: string; severity: string };
  setEditDraft: (d: { topic: string; sentiment: string; severity: string }) => void;
  onToggleEdit: () => void;
  onSave: () => void;
  saving: boolean;
  onApprove?: () => void;
  acting?: boolean;
  showActions?: boolean;
}) {
  return (
    <div className={`p-4 grid grid-cols-12 gap-3 items-center ${isNew ? "live-feedback-row-new" : ""}`}>
      <span className="col-span-2 sm:col-span-1 text-[10px] font-mono uppercase text-muted-foreground">
        {channelLabel(f.channel)}
      </span>
      <div className="col-span-10 sm:col-span-6">
        <p className="text-sm">{f.text}</p>
        {f.review_reason && showActions && (
          <p className="text-[11px] text-amber-700 mt-1 flex items-center gap-1">
            <ShieldAlert className="h-3 w-3" />
            {f.review_reason}
          </p>
        )}
      </div>
      <div className="col-span-12 sm:col-span-5 flex flex-wrap justify-start sm:justify-end gap-1.5 items-center">
        {/* source='public' = sent by a Customer through the Customer web (no account). */}
        {f.source === "public" && <Pill tone="green">Khách hàng</Pill>}
        {f.topic && <Pill icon={Tag}>{topicLabel(f.topic)}</Pill>}
        {f.sentiment && (
          <Pill tone={f.sentiment === "negative" ? "coral" : f.sentiment === "positive" ? "green" : "mint"}>
            {sentimentLabel(f.sentiment)}
          </Pill>
        )}
        {f.severity && <Pill tone="deep">{severityLabel(f.severity)}</Pill>}
        {f.confidence != null && (
          <span className="text-[10px] font-mono text-muted-foreground">{Math.round(f.confidence * 100)}%</span>
        )}
        {f.area && (
          <span className="text-[10px] font-mono text-muted-foreground inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {regionLabel(f.area)}
          </span>
        )}
        {showActions && onApprove && (
          <button
            onClick={onApprove}
            disabled={acting}
            className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-xanh-green/50 text-xanh-deep hover:bg-xanh-green/10 inline-flex items-center gap-1 disabled:opacity-50"
          >
            {acting ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
            duyệt
          </button>
        )}
        <button
          onClick={onToggleEdit}
          className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border hover:border-xanh-green/50 hover:bg-xanh-mint/30 inline-flex items-center gap-1"
        >
          <Pencil className="h-3 w-3" />
          {editing ? "đóng" : "sửa nhãn"}
        </button>
      </div>
      {editing && (
        <div className="col-span-12 mt-2 p-3 rounded-xl bg-muted/40 border border-border grid sm:grid-cols-4 gap-2 items-end">
          <Select label="Chủ đề" value={editDraft.topic} onChange={(v) => setEditDraft({ ...editDraft, topic: v })} options={TOPIC_OPTIONS} labelFn={topicLabel} />
          <Select label="Cảm xúc" value={editDraft.sentiment} onChange={(v) => setEditDraft({ ...editDraft, sentiment: v })} options={SENTIMENT_OPTIONS} labelFn={sentimentLabel} />
          <Select label="Mức độ" value={editDraft.severity} onChange={(v) => setEditDraft({ ...editDraft, severity: v })} options={SEVERITY_OPTIONS} labelFn={severityLabel} />
          <button
            onClick={onSave}
            disabled={saving}
            className="h-9 px-4 rounded-lg text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-[var(--shadow-green)] disabled:opacity-60"
            style={{ background: "var(--gradient-green)" }}
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Lưu nhãn"}
          </button>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
  onClick,
  isActive,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  tone: "deep" | "coral" | "amber" | "mint";
  onClick?: () => void;
  isActive?: boolean;
}) {
  const toneMap: Record<string, string> = {
    deep: "text-xanh-deep",
    coral: "text-xanh-coral",
    amber: "text-amber-600",
    mint: "text-xanh-green",
  };
  return (
    <div 
      onClick={onClick}
      className={`rounded-xl border bg-card p-4 shadow-[var(--shadow-card)] ${onClick ? 'cursor-pointer transition-all hover:shadow-md' : ''} ${isActive ? 'border-xanh-green ring-2 ring-xanh-green/20' : 'border-border'}`}
    >
      <div className="flex items-center justify-between">
        <div className="text-[11px] text-muted-foreground">{label}</div>
        <Icon className={`h-4 w-4 ${toneMap[tone]}`} />
      </div>
      <div className={`font-display text-2xl font-bold mt-1 ${toneMap[tone]}`}>{value}</div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  labelFn,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  labelFn?: (v: string) => string;
}) {
  return (
    <label className="text-xs">
      <div className="text-muted-foreground mb-1">{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-9 px-2 rounded-lg border border-border bg-card focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {labelFn ? labelFn(o) : o}
          </option>
        ))}
      </select>
    </label>
  );
}

function Pill({
  children,
  icon: Icon,
  tone = "mint",
}: {
  children: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  tone?: "mint" | "green" | "coral" | "deep";
}) {
  const map: Record<string, string> = {
    mint: "bg-xanh-mint text-xanh-deep border-xanh-green/30",
    green: "bg-xanh-green/15 text-xanh-deep border-xanh-green/40",
    coral: "bg-xanh-coral/15 text-xanh-coral border-xanh-coral/30",
    deep: "bg-xanh-deep text-white border-xanh-deep",
  };
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border ${map[tone]}`}>
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}
