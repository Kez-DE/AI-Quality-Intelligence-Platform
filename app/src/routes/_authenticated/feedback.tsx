import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Loader2, MessageSquarePlus, MapPin, Tag, AlertCircle, Pencil } from "lucide-react";
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
  confidence: number | null;
  created_at: string;
};

// Ngưỡng confidence: dưới mức này coi như AI "không chắc" -> gắn cờ cần người duyệt.
const REVIEW_THRESHOLD = 0.5;

const CHANNELS = ["app", "rating", "hotline", "cs", "survey"];

// 16 khu vực chuẩn (HN/HCM/ĐN) — khớp data/reference/area_catalog.json.
// value = area code (lưu DB, khớp spike detector), label = tên hiển thị.
const AREAS: { code: string; label: string }[] = [
  { code: "HN-Cau-Giay", label: "Cầu Giấy, Hà Nội" },
  { code: "HN-Ha-Dong", label: "Hà Đông, Hà Nội" },
  { code: "HN-Dong-Da", label: "Đống Đa, Hà Nội" },
  { code: "HN-Hoan-Kiem", label: "Hoàn Kiếm, Hà Nội" },
  { code: "HN-Tay-Ho", label: "Tây Hồ, Hà Nội" },
  { code: "HN-Long-Bien", label: "Long Biên, Hà Nội" },
  { code: "HCM-Quan-1", label: "Quận 1, Hồ Chí Minh" },
  { code: "HCM-Binh-Thanh", label: "Bình Thạnh, Hồ Chí Minh" },
  { code: "HCM-Thu-Duc", label: "Thủ Đức, Hồ Chí Minh" },
  { code: "HCM-Quan-7", label: "Quận 7, Hồ Chí Minh" },
  { code: "HCM-Tan-Binh", label: "Tân Bình, Hồ Chí Minh" },
  { code: "HCM-Go-Vap", label: "Gò Vấp, Hồ Chí Minh" },
  { code: "DN-Hai-Chau", label: "Hải Châu, Đà Nẵng" },
  { code: "DN-Son-Tra", label: "Sơn Trà, Đà Nẵng" },
  { code: "DN-Ngu-Hanh-Son", label: "Ngũ Hành Sơn, Đà Nẵng" },
  { code: "DN-Thanh-Khe", label: "Thanh Khê, Đà Nẵng" },
];

// Nhịp làm mới danh sách phản hồi (ms). 5s đủ "live" mà không nhảy liên tục/giật.
const REFRESH_INTERVAL_MS = 5000;

// Options cho ô sửa nhãn (Human-in-the-loop). Khớp nhãn classifier sinh ra.
const TOPIC_OPTIONS = ["Safety", "Driver Behavior", "App Issue", "Payment", "Pricing", "Delay", "Other"];
const SENTIMENT_OPTIONS = ["negative", "neutral", "positive"];
const SEVERITY_OPTIONS = ["P1", "P2", "P3", "P4", "P5"];
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
    const { data: s } = await supabase.auth.getSession();
    const token = s.session?.access_token;
    if (!token) {
      toast.error("Chưa đăng nhập");
      setSavingId(null);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/feedback/${id}/label`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(editDraft),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail.slice(0, 200)}`);
      }
      toast.success("Đã cập nhật nhãn — ghi vào correction log");
      setEditingId(null);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không sửa được nhãn");
    } finally {
      setSavingId(null);
    }
  }

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
    const id = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.text.trim()) return;
    setSubmitting(true);
    const { data: s } = await supabase.auth.getSession();
    const token = s.session?.access_token;
    if (!token) {
      toast.error("Chưa đăng nhập");
      setSubmitting(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/feedback/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          text: form.text.trim(),
          channel: form.channel,
          area: form.area || null,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`${res.status}: ${detail.slice(0, 200)}`);
      }
      toast.success("Đã gửi phản hồi — AI đang phân tích & gán nhãn");
      setForm({ ...form, text: "", area: AREAS[0].code });
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không gửi được phản hồi");
    } finally {
      setSubmitting(false);
    }
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
          <div className="grid sm:grid-cols-2 gap-2">
            <Select label="Kênh" value={form.channel} onChange={(v) => setForm({ ...form, channel: v })} options={CHANNELS} />
            <label className="text-xs">
              <div className="text-muted-foreground mb-1">Khu vực</div>
              <select
                value={form.area}
                onChange={(e) => setForm({ ...form, area: e.target.value })}
                className="w-full h-9 px-2 rounded-lg border border-border bg-white focus:outline-none focus:ring-2 focus:ring-xanh-green/40"
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
                } ${
                  f.confidence != null && f.confidence < REVIEW_THRESHOLD
                    ? "bg-amber-50/60 border-l-2 border-l-amber-400"
                    : ""
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
                  {f.confidence != null &&
                    (f.confidence < REVIEW_THRESHOLD ? (
                      <Pill icon={AlertCircle} tone="coral">
                        cần duyệt · {Math.round(f.confidence * 100)}%
                      </Pill>
                    ) : (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        {Math.round(f.confidence * 100)}%
                      </span>
                    ))}
                  {f.area && (
                    <span className="text-[10px] font-mono text-muted-foreground inline-flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {f.area}
                    </span>
                  )}
                  <button
                    onClick={() => (editingId === f.id ? setEditingId(null) : openEditor(f))}
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border hover:border-xanh-green/50 hover:bg-xanh-mint/30 inline-flex items-center gap-1"
                  >
                    <Pencil className="h-3 w-3" />
                    {editingId === f.id ? "đóng" : "sửa nhãn"}
                  </button>
                </div>
                {editingId === f.id && (
                  <div className="col-span-12 mt-2 p-3 rounded-xl bg-muted/40 border border-border grid sm:grid-cols-4 gap-2 items-end">
                    <Select label="Chủ đề" value={editDraft.topic} onChange={(v) => setEditDraft({ ...editDraft, topic: v })} options={TOPIC_OPTIONS} />
                    <Select label="Cảm xúc" value={editDraft.sentiment} onChange={(v) => setEditDraft({ ...editDraft, sentiment: v })} options={SENTIMENT_OPTIONS} />
                    <Select label="Severity" value={editDraft.severity} onChange={(v) => setEditDraft({ ...editDraft, severity: v })} options={SEVERITY_OPTIONS} />
                    <button
                      onClick={() => saveCorrection(f.id)}
                      disabled={savingId === f.id}
                      className="h-9 px-4 rounded-lg text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-[var(--shadow-green)] disabled:opacity-60"
                      style={{ background: "var(--gradient-green)" }}
                    >
                      {savingId === f.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Lưu nhãn"}
                    </button>
                  </div>
                )}
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
