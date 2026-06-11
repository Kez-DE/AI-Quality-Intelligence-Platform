import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Loader2, MessageSquarePlus, MapPin, Tag, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/feedback")({
  component: FeedbackPage,
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
  created_at: string;
};

const TOPICS = ["Tài xế", "Xe", "Ứng dụng", "Giá & thanh toán", "An toàn", "Khác"];
const SENTIMENTS = ["positive", "neutral", "negative"];
const SEVERITIES = ["P0", "P1", "P2", "P3"];
const CHANNELS = ["app", "rating", "hotline", "cs", "survey"];
const API_BASE = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";

function FeedbackPage() {
  const [list, setList] = useState<Feedback[]>([]);
  const [newFeedbackIds, setNewFeedbackIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);

  const [form, setForm] = useState({
    text: "",
    channel: "app",
    topic: "Tài xế",
    sentiment: "negative",
    severity: "P2",
    area: "",
  });

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/feedback/recent?limit=100`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const json = (await res.json()) as { data?: Feedback[] };
      const rows = json.data ?? [];
      const incomingIds = rows.map((row) => row.id);
      const freshIds = incomingIds.filter((id) => !seenIdsRef.current.has(id));
      incomingIds.forEach((id) => seenIdsRef.current.add(id));
      if (initializedRef.current && freshIds.length) {
        setNewFeedbackIds(new Set(freshIds));
        window.setTimeout(() => setNewFeedbackIds(new Set()), 1600);
      }
      initializedRef.current = true;
      setList(rows);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Không đọc được live feedback");
    }
    setLoading(false);
  }

  useEffect(() => {
    load();
    const id = window.setInterval(load, 1000);
    return () => window.clearInterval(id);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.text.trim()) return;
    setSubmitting(true);
    const { data: u } = await supabase.auth.getUser();
    if (!u.user) {
      toast.error("Chưa đăng nhập");
      setSubmitting(false);
      return;
    }
    const { error } = await supabase.from("feedback").insert({
      user_id: u.user.id,
      source: "manual",
      channel: form.channel,
      text: form.text.trim(),
      topic: form.topic,
      sentiment: form.sentiment,
      severity: form.severity,
      area: form.area || null,
      confidence: 1,
    });
    setSubmitting(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Đã thêm phản hồi");
    setForm({ ...form, text: "", area: "" });
    load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Thu thập phản hồi</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Nhập tay hoặc dán phản hồi từ nhiều kênh — hệ thống lưu lại để phân tích.
        </p>
      </div>

      <section className="rounded-2xl border border-border bg-white p-5 shadow-[var(--shadow-card)]">
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
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-2">
            <Select label="Kênh" value={form.channel} onChange={(v) => setForm({ ...form, channel: v })} options={CHANNELS} />
            <Select label="Chủ đề" value={form.topic} onChange={(v) => setForm({ ...form, topic: v })} options={TOPICS} />
            <Select label="Cảm xúc" value={form.sentiment} onChange={(v) => setForm({ ...form, sentiment: v })} options={SENTIMENTS} />
            <Select label="Severity" value={form.severity} onChange={(v) => setForm({ ...form, severity: v })} options={SEVERITIES} />
            <label className="text-xs">
              <div className="text-muted-foreground mb-1">Khu vực</div>
              <input
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                placeholder="VD: HN-Cầu Giấy"
                className="w-full h-9 px-3 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
              />
            </label>
          </div>
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

      <section className="rounded-2xl border border-border bg-white shadow-[var(--shadow-card)]">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <h2 className="font-display font-semibold">
            Đã thu thập <span className="text-muted-foreground font-mono text-xs">({list.length})</span>
          </h2>
          <button onClick={load} className="text-xs font-mono text-xanh-deep hover:underline">
            ↻ refresh
          </button>
        </div>
        {loading ? (
          <div className="p-10 text-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin inline" />
          </div>
        ) : list.length === 0 ? (
          <div className="p-10 text-center text-sm text-muted-foreground">
            <AlertCircle className="h-5 w-5 inline mr-2" />
            Chưa có phản hồi nào. Hãy thêm phản hồi đầu tiên ở trên.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {list.map((f) => (
              <div
                key={f.id}
                className={`p-4 grid grid-cols-12 gap-3 items-center hover:bg-xanh-mint/20 ${
                  newFeedbackIds.has(f.id) ? "live-feedback-row-new" : ""
                }`}
              >
                <span className="col-span-2 sm:col-span-1 text-[10px] font-mono uppercase text-muted-foreground">
                  {f.channel}
                </span>
                <p className="col-span-10 sm:col-span-7 text-sm">{f.text}</p>
                <div className="col-span-12 sm:col-span-4 flex flex-wrap justify-start sm:justify-end gap-1.5 items-center">
                  {f.topic && <Pill icon={Tag}>{f.topic}</Pill>}
                  {f.sentiment && (
                    <Pill tone={f.sentiment === "negative" ? "coral" : f.sentiment === "positive" ? "green" : "mint"}>
                      {f.sentiment}
                    </Pill>
                  )}
                  {f.severity && <Pill tone="deep">{f.severity}</Pill>}
                  {f.area && (
                    <span className="text-[10px] font-mono text-muted-foreground inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {f.area}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="text-xs">
      <div className="text-muted-foreground mb-1">{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-9 px-2 rounded-lg border border-border bg-white focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
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
