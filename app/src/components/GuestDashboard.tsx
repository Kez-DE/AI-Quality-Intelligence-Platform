// Guest (Khách) dashboard — port các panel từ Customer Hub Proaaa, render trong AppShell.
// Chỉ số công khai hiển thị tĩnh (đại diện); form gửi phản hồi gọi API thật /api/feedback/submit.
import { useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { AREAS, regionLabel } from "@/lib/regions";
import { toast } from "sonner";
import {
  Activity, BarChart3, Bot, CheckCircle2, ChevronRight, Clock, Compass, Cpu,
  Eye, Heart, Info, MapPin, MessageSquare, PenLine, Send, Shield, Sparkles,
  Star, Tag, ThumbsDown, ThumbsUp, TrendingUp, AlertTriangle, Smile, Meh, Frown,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import SupportChatWidget from "@/components/SupportChatWidget";

/* ---------------- Dữ liệu hiển thị (đại diện, công khai) ---------------- */
const trendData = Array.from({ length: 14 }).map((_, i) => {
  const total = 120 + Math.round(Math.sin(i / 2) * 30 + i * 6 + ((i * 37) % 20));
  const negative = Math.round(total * (0.12 + ((i * 13) % 8) / 100));
  return { day: `${i + 1}/06`, total, negative };
});

const topicData = [
  { topic: "App", value: 38.2, color: "var(--color-chart-1)" },
  { topic: "Khác", value: 24.8, color: "var(--color-chart-2)" },
  { topic: "Tài xế", value: 17.1, color: "var(--color-chart-3)" },
  { topic: "Thanh toán", value: 9.0, color: "var(--color-chart-4)" },
  { topic: "Xe", value: 6.5, color: "var(--color-chart-5)" },
  { topic: "Giá", value: 4.4, color: "oklch(0.55 0.12 200)" },
];

const slaData = [
  { name: "T2", sla: 96 }, { name: "T3", sla: 94 }, { name: "T4", sla: 97 },
  { name: "T5", sla: 98 }, { name: "T6", sla: 93 }, { name: "T7", sla: 95 },
  { name: "CN", sla: 92 },
];

const regions = [
  { name: "Hà Nội", trips: 12480, score: 4.6 },
  { name: "TP. HCM", trips: 18320, score: 4.4 },
  { name: "Đà Nẵng", trips: 4210, score: 4.7 },
  { name: "Hải Phòng", trips: 2870, score: 4.5 },
  { name: "Cần Thơ", trips: 1980, score: 4.3 },
];

const pipeline = [
  { icon: PenLine, label: "Bạn gửi phản hồi", desc: "Qua app · hotline · form" },
  { icon: Cpu, label: "AI phân tích", desc: "Phân loại chủ đề · cảm xúc" },
  { icon: AlertTriangle, label: "Phát hiện vấn đề", desc: "Cảnh báo nội bộ tới đội vận hành" },
  { icon: Shield, label: "Xử lý & phản hồi", desc: "Đội CSKH liên hệ lại với bạn" },
];

const benefits = [
  { icon: Eye, title: "Minh bạch chỉ số", desc: "Bạn thấy số liệu chất lượng mà xanhSM công bố." },
  { icon: PenLine, title: "Gửi phản hồi 24/7", desc: "Mỗi phản hồi được AI gắn nhãn ngay lập tức." },
  { icon: Star, title: "Đánh giá chuyến đi", desc: "Cho điểm và để lại review về tài xế, xe, dịch vụ." },
  { icon: Bot, title: "Trợ lý AI", desc: "Hỏi đáp về dịch vụ, hướng dẫn dùng app — phản hồi tức thì." },
  { icon: Heart, title: "Theo dõi xử lý", desc: "Biết trạng thái phản hồi: tiếp nhận → đang xử lý → hoàn tất." },
  { icon: Shield, title: "Bảo mật thông tin", desc: "Dữ liệu cá nhân được mã hóa, không chia sẻ ra bên ngoài." },
];

type Review = {
  id: number; rating: number; time: string; channel: string; region: string;
  text: string; sentiment: string; topic: string; status: string;
};

const sentimentMap: Record<string, { icon: any; label: string; cls: string }> = {
  positive: { icon: Smile, label: "Tích cực", cls: "text-success bg-success/10 border-success/30" },
  neutral: { icon: Meh, label: "Trung lập", cls: "text-warning bg-warning/10 border-warning/30" },
  negative: { icon: Frown, label: "Tiêu cực", cls: "text-destructive bg-destructive/10 border-destructive/30" },
};

function StatCard({ icon: Icon, label, value, sub, trend, tone = "default" }: {
  icon: any; label: string; value: string; sub?: string;
  trend?: { v: string }; tone?: "default" | "good";
}) {
  return (
    <Card className={`p-5 bg-card/80 backdrop-blur transition-all hover:shadow-lg ${tone === "good" ? "ring-1 ring-primary/30" : ""}`}>
      <div className="flex items-start justify-between">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight font-display">{value}</div>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {trend && (
          <span className="inline-flex items-center gap-1 font-medium text-success">
            <TrendingUp className="h-3 w-3" />{trend.v}
          </span>
        )}
        {sub && <span className="text-muted-foreground">{sub}</span>}
      </div>
    </Card>
  );
}

function SectionTitle({ icon: Icon, title, sub, right }: {
  icon: any; title: string; sub?: string; right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-display text-lg font-semibold leading-none">{title}</h2>
          {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" onClick={() => onChange(n)} className="transition-transform hover:scale-110">
          <Star className={`h-7 w-7 ${n <= value ? "fill-warning text-warning" : "text-muted-foreground/40"}`} />
        </button>
      ))}
    </div>
  );
}

export default function GuestDashboard() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [channel, setChannel] = useState("Ứng dụng");
  const [region, setRegion] = useState(AREAS[0].code);
  const [submitting, setSubmitting] = useState(false);
  const pieData = useMemo(() => topicData.map((t) => ({ name: t.topic, value: t.value, color: t.color })), []);

  async function submitFeedback(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch<{ data: any }>("/api/feedback/submit", {
        method: "POST",
        body: JSON.stringify({ text: text.trim(), channel, area: region }),
      });
      const d = res.data || {};
      setReviews((prev) => [
        {
          id: Date.now(),
          rating,
          time: "Vừa xong",
          channel,
          region,
          text: text.trim(),
          sentiment: d.sentiment || (rating >= 4 ? "positive" : rating >= 3 ? "neutral" : "negative"),
          topic: d.topic || "Khác",
          status: "Đã tiếp nhận",
        },
        ...prev,
      ]);
      setText("");
      setRating(5);
      toast.success("Đã gửi phản hồi — AI đã phân loại và chuyển tới đội xử lý.");
    } catch (err: any) {
      toast.error(err?.message || "Không gửi được phản hồi");
    } finally {
      setSubmitting(false);
    }
  }

  const tooltipStyle = { background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, fontSize: 12 };

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border bg-gradient-to-br from-primary/10 via-card to-card p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute -left-10 -bottom-20 h-60 w-60 rounded-full bg-xanh-mint/50 blur-3xl" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <Badge variant="outline" className="mb-3 gap-1.5"><Compass className="h-3 w-3" /> Xin chào, Khách hàng</Badge>
            <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
              Theo dõi <span className="text-primary">chất lượng dịch vụ</span> & gửi phản hồi của bạn
            </h1>
            <p className="mt-2 text-muted-foreground">
              Bạn đang xem các chỉ số mà xanhSM công bố. Mỗi đánh giá của bạn được AI phân tích và chuyển tới đội xử lý.
            </p>
          </div>
          <a href="#guest-feedback" className="inline-flex shrink-0 items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90">
            <PenLine className="h-4 w-4" /> Gửi phản hồi ngay
          </a>
        </div>
      </section>

      {/* Read-only banner */}
      <div className="flex items-start gap-3 rounded-xl border border-info/20 bg-info/5 p-4">
        <Info className="mt-0.5 h-5 w-5 shrink-0 text-info" />
        <div className="text-sm">
          <div className="font-medium">Chế độ xem dành cho Khách</div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            Bạn có thể xem các chỉ số công khai và gửi phản hồi/đánh giá. Tính năng xuất báo cáo & dữ liệu nội bộ chỉ dành cho đội vận hành.
          </div>
        </div>
      </div>

      {/* Public KPIs */}
      <section>
        <SectionTitle icon={BarChart3} title="Chỉ số dịch vụ công khai" sub="Cập nhật realtime từ xanhSM" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
          <StatCard icon={Star} label="Điểm dịch vụ" value="4.6/5" sub="trên 32K đánh giá" tone="good" />
          <StatCard icon={ThumbsUp} label="Tỉ lệ hài lòng" value="96.5%" sub="30 ngày" trend={{ v: "1.2%" }} tone="good" />
          <StatCard icon={Clock} label="TG đáp ứng TB" value="3.2 phút" sub="đặt xe → đón" />
          <StatCard icon={CheckCircle2} label="Tỉ lệ hoàn thành" value="98.1%" sub="chuyến đi thành công" tone="good" />
          <StatCard icon={Activity} label="Phản hồi xử lý" value="< 4h" sub="thời gian xử lý TB" />
        </div>
      </section>

      {/* Feedback form (functional) */}
      <section id="guest-feedback">
        <Card className="p-6">
          <SectionTitle icon={PenLine} title="Gửi phản hồi · đánh giá" sub="Mỗi đánh giá của bạn giúp xanhSM cải thiện dịch vụ." />
          <form onSubmit={submitFeedback} className="space-y-4">
            <div>
              <Label className="mb-2 block text-xs text-muted-foreground">Bạn đánh giá chuyến đi này thế nào?</Label>
              <div className="flex items-center gap-3">
                <StarRating value={rating} onChange={setRating} />
                <span className="text-sm font-medium">
                  {rating === 5 ? "Tuyệt vời" : rating === 4 ? "Tốt" : rating === 3 ? "Bình thường" : rating === 2 ? "Chưa tốt" : "Tệ"}
                </span>
              </div>
            </div>
            <div>
              <Label className="mb-2 block text-xs text-muted-foreground">Nội dung phản hồi</Label>
              <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} placeholder="VD: Tài xế lịch sự, xe sạch sẽ, đến đúng giờ..." />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <Label className="mb-2 block text-xs text-muted-foreground">Kênh</Label>
                <Select value={channel} onValueChange={setChannel}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["Ứng dụng", "Hotline", "Website", "Mạng xã hội"].map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="mb-2 block text-xs text-muted-foreground">Khu vực</Label>
                <Select value={region} onValueChange={setRegion}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {AREAS.map((a) => <SelectItem key={a.code} value={a.code}>{a.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Tag className="h-3.5 w-3.5" /> AI sẽ tự phân tích cảm xúc và chuyển tới đội phù hợp.
              </p>
              <Button type="submit" disabled={submitting} className="gap-2">
                <Send className="h-4 w-4" /> {submitting ? "Đang gửi..." : "Gửi phản hồi"}
              </Button>
            </div>
          </form>
        </Card>
      </section>

      {/* Your reviews (in-session) */}
      {reviews.length > 0 && (
        <section>
          <SectionTitle
            icon={MessageSquare}
            title="Phản hồi của bạn"
            sub={`${reviews.length} phản hồi đã gửi trong phiên này · AI tự gán nhãn`}
            right={
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="gap-1"><ThumbsUp className="h-3 w-3 text-success" />{reviews.filter((r) => r.sentiment === "positive").length}</Badge>
                <Badge variant="outline" className="gap-1"><ThumbsDown className="h-3 w-3 text-destructive" />{reviews.filter((r) => r.sentiment === "negative").length}</Badge>
              </div>
            }
          />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {reviews.map((r) => {
              const s = sentimentMap[r.sentiment] || sentimentMap.neutral;
              return (
                <div key={r.id} className="rounded-xl border bg-background/60 p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5].map((n) => <Star key={n} className={`h-3.5 w-3.5 ${n <= r.rating ? "fill-warning text-warning" : "text-muted-foreground/30"}`} />)}
                    </div>
                    <Badge variant="outline" className="border-info/30 bg-info/10 text-info">{r.status}</Badge>
                  </div>
                  <p className="mb-3 text-sm leading-relaxed text-foreground/90">{r.text}</p>
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <Badge variant="outline" className={`gap-1 ${s.cls}`}><s.icon className="h-3 w-3" />{s.label}</Badge>
                    <Badge variant="secondary" className="gap-1"><Tag className="h-3 w-3" />{r.topic}</Badge>
                    <Badge variant="secondary" className="gap-1"><MapPin className="h-3 w-3" />{regionLabel(r.region)}</Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Pipeline */}
      <section>
        <SectionTitle icon={Cpu} title="Phản hồi của bạn đi đâu?" sub="Hành trình từ feedback đến xử lý" />
        <Card className="p-6">
          <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-4 md:gap-2">
            {pipeline.map((p, i) => (
              <div key={p.label} className="flex items-center gap-2">
                <div className="flex-1 rounded-2xl border bg-gradient-to-br from-card to-secondary/40 p-5 transition-shadow hover:shadow-md">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><p.icon className="h-5 w-5" /></div>
                    <span className="text-[10px] font-semibold text-muted-foreground">BƯỚC {i + 1}</span>
                  </div>
                  <div className="text-sm font-semibold">{p.label}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{p.desc}</div>
                </div>
                {i < pipeline.length - 1 && <ChevronRight className="hidden h-5 w-5 shrink-0 text-muted-foreground md:block" />}
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* Trend + Topics */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={Activity} title="Xu hướng phản hồi · 14 ngày" sub="Số lượng phản hồi của cộng đồng" />
          <div className="h-72">
            <ResponsiveContainer>
              <AreaChart data={trendData} margin={{ left: -20, right: 10 }}>
                <defs>
                  <linearGradient id="gGuestTotal" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gGuestNeg" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-chart-3)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="var(--color-chart-3)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="day" stroke="var(--color-muted-foreground)" fontSize={11} />
                <YAxis stroke="var(--color-muted-foreground)" fontSize={11} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="total" name="Tổng phản hồi" stroke="var(--color-chart-1)" fill="url(#gGuestTotal)" strokeWidth={2.5} />
                <Area type="monotone" dataKey="negative" name="Tiêu cực" stroke="var(--color-chart-3)" fill="url(#gGuestNeg)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6">
          <SectionTitle icon={Tag} title="Chủ đề phổ biến" sub="AI tự phân loại" />
          <div className="h-44">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={2}>
                  {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 space-y-2">
            {topicData.slice(0, 5).map((t) => (
              <div key={t.topic}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: t.color }} />{t.topic}</span>
                  <span className="font-medium">{t.value}%</span>
                </div>
                <Progress value={t.value * 2} className="h-1.5" />
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* Regions + On-time rate */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={MapPin} title="Chất lượng theo khu vực" sub="Điểm trung bình cộng đồng đánh giá" />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {regions.map((r) => (
              <div key={r.name} className="flex items-center justify-between rounded-xl border bg-background/50 p-3 transition-colors hover:bg-secondary/40">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><MapPin className="h-4 w-4" /></div>
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">{r.trips.toLocaleString("vi-VN")} chuyến</div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-sm font-semibold"><Star className="h-4 w-4 fill-warning text-warning" />{r.score}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <SectionTitle icon={Clock} title="Tỉ lệ đúng hẹn tuần này" sub="Mục tiêu ≥ 95%" />
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={slaData} margin={{ left: -25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="name" fontSize={11} stroke="var(--color-muted-foreground)" />
                <YAxis fontSize={11} domain={[85, 100]} stroke="var(--color-muted-foreground)" />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="sla" radius={[6, 6, 0, 0]}>
                  {slaData.map((d, i) => <Cell key={i} fill={d.sla >= 95 ? "var(--color-chart-1)" : "var(--color-chart-3)"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Benefits */}
      <section>
        <SectionTitle icon={Sparkles} title="Bạn được gì với tài khoản Khách?" sub="6 quyền lợi chính" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {benefits.map((f) => (
            <div key={f.title} className="rounded-xl border bg-gradient-to-br from-card to-secondary/30 p-5 transition-colors hover:border-primary/40">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground"><f.icon className="h-5 w-5" /></div>
                <div>
                  <div className="text-sm font-semibold">{f.title}</div>
                  <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{f.desc}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <SupportChatWidget />
    </div>
  );
}
