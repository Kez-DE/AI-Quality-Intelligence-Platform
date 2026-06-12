import { useEffect, useMemo, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import type { Database as DatabaseSchema } from "@/integrations/supabase/types";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  Brain,
  Car,
  CheckCircle2,
  ClipboardList,
  Cpu,
  Database,
  Eye,
  Filter,
  Gauge,
  Headphones,
  Layers,
  LineChart as LineChartIcon,
  MapPin,
  MessageSquare,
  Radar,
  Radio,
  Shield,
  Siren,
  Sparkles,
  Tag,
  Target,
  TrendingUp,
  Users,
  Workflow,
  Zap,
} from "lucide-react";

/* ============================================================
   AI Quality Intelligence Platform — Quality Operation Cockpit
   Brand: XanhSM (green / teal / mint)
   ============================================================ */

export default function QualityCockpit() {
  const [tab, setTab] = useState<"cockpit" | "story" | "architecture" | "value">("cockpit");

  return (
    <div className="min-h-screen text-foreground">
      <TopBar tab={tab} setTab={setTab} />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24">
        <Hero />
        {tab === "cockpit" && <CockpitView />}
        {tab === "story" && <StoryView />}
        {tab === "architecture" && <ArchitectureView />}
        {tab === "value" && <ValueView />}
        <Footer />
      </main>
    </div>
  );
}

/* ---------- Top bar ---------- */

function TopBar({
  tab,
  setTab,
}: {
  tab: string;
  setTab: (t: "cockpit" | "story" | "architecture" | "value") => void;
}) {
  const tabs = [
    { id: "cockpit", label: "Cockpit", icon: Gauge },
    { id: "story", label: "Bài toán & Giải pháp", icon: Sparkles },
    { id: "architecture", label: "Kiến trúc", icon: Layers },
    { id: "value", label: "Giá trị & Người dùng", icon: Target },
  ] as const;
  return (
    <header className="sticky top-0 z-30 backdrop-blur-xl bg-background/70 border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className="h-9 w-9 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]"
            style={{ background: "var(--gradient-green)" }}
          >
            <Car className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="font-display font-bold text-base">AI Quality Intelligence</div>
            <div className="text-[11px] text-muted-foreground font-mono">
              xanhSM · Quality Operation Cockpit
            </div>
          </div>
        </div>
        <nav className="hidden md:flex items-center gap-1 p-1 bg-muted/60 rounded-xl border border-border/60">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 text-sm rounded-lg flex items-center gap-1.5 transition-all ${
                  active
                    ? "bg-white text-xanh-deep shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full bg-xanh-mint text-xanh-deep border border-xanh-green/30">
            <span className="h-1.5 w-1.5 rounded-full bg-xanh-green animate-pulse" />
            LIVE · near-real-time
          </span>
        </div>
      </div>
      {/* Mobile tabs */}
      <div className="md:hidden flex overflow-x-auto gap-1 px-3 pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap ${
              tab === t.id ? "bg-xanh-deep text-white" : "bg-muted text-muted-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </header>
  );
}

/* ---------- Hero ---------- */

function Hero() {
  return (
    <section className="relative pt-10 pb-8">
      <div className="grid lg:grid-cols-12 gap-8 items-end">
        <div className="lg:col-span-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-xanh-mint text-xanh-deep text-xs font-mono border border-xanh-green/30 mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            Smart Mobility · Feedback Analytics for xanhSM
          </div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
            Biến hàng nghìn phản hồi mỗi ngày thành{" "}
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: "var(--gradient-green)" }}
            >
              hành động vận hành
            </span>
            .
          </h1>
          <p className="mt-5 text-lg text-muted-foreground max-w-2xl">
            <strong className="text-foreground">AI Quality Intelligence Platform</strong> là khoang
            lái điều hành chất lượng dịch vụ — phân loại, phát hiện spike, sinh alert & ticket theo
            SLA, giúp xanhSM xử lý sự cố <em>trước khi</em> chúng trở thành khủng hoảng.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {[
              "Problem → Solution",
              "Real-time",
              "Alert · SLA",
              "Human-in-the-loop",
              "Correction Log",
              "Operational Intelligence",
            ].map((k) => (
              <span
                key={k}
                className="text-xs font-mono px-2.5 py-1 rounded-md bg-white border border-border text-xanh-deep"
              >
                {k}
              </span>
            ))}
          </div>
        </div>
        <div className="lg:col-span-4">
          <HeroStats />
        </div>
      </div>
    </section>
  );
}

function HeroStats() {
  const stats = [
    { label: "Feedback / ngày", value: "12,480", sub: "+8.2% WoW", icon: MessageSquare },
    { label: "Auto-classified", value: "97.4%", sub: "confidence ≥ 0.82", icon: Brain },
    { label: "MTTD sự cố", value: "4.2′", sub: "↓ từ 6 giờ", icon: Zap },
    { label: "SLA on-time", value: "94%", sub: "tuần qua", icon: Gauge },
  ];
  return (
    <div className="rounded-2xl p-5 border border-border bg-white/80 backdrop-blur shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-mono text-muted-foreground">QUALITY · SNAPSHOT</div>
        <span className="text-[10px] font-mono text-xanh-deep bg-xanh-mint px-2 py-0.5 rounded-full">
          last 24h
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="rounded-xl p-3 border border-border bg-gradient-to-br from-white to-xanh-mint/30"
            >
              <Icon className="h-4 w-4 text-xanh-green" />
              <div className="mt-2 font-display text-2xl font-bold text-xanh-deep">{s.value}</div>
              <div className="text-[11px] text-muted-foreground">{s.label}</div>
              <div className="text-[10px] font-mono text-xanh-green mt-0.5">{s.sub}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ============================================================
   COCKPIT VIEW
   ============================================================ */

function CockpitView() {
  return (
    <div className="mt-6 space-y-6">
      <KpiStrip />
      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          <TrendCard />
          <CategoryBreakdown />
          <LiveFeed />
        </div>
        <aside className="lg:col-span-4 space-y-6">
          <AlertsPanel />
          <Heatmap />
          <DriverWatchlist />
        </aside>
      </div>
      <TicketBoard />
    </div>
  );
}

function KpiStrip() {
  const items = [
    {
      label: "Feedback hôm nay",
      value: "12,480",
      delta: "+8.2%",
      icon: MessageSquare,
      tone: "green",
    },
    { label: "Negative rate", value: "11.6%", delta: "-1.3%", icon: TrendingUp, tone: "green" },
    { label: "Spike phát hiện", value: "3", delta: "Hà Nội · Đà Nẵng", icon: Siren, tone: "amber" },
    {
      label: "Open tickets",
      value: "47",
      delta: "P0: 2 · P1: 9",
      icon: ClipboardList,
      tone: "deep",
    },
    { label: "Human review", value: "18", delta: "queue avg 2.1′", icon: Eye, tone: "cyan" },
    { label: "Correction log", value: "126", delta: "tuần này", icon: Workflow, tone: "green" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((i) => {
        const Icon = i.icon;
        const toneCls =
          i.tone === "amber"
            ? "text-xanh-amber"
            : i.tone === "cyan"
              ? "text-xanh-cyan"
              : i.tone === "deep"
                ? "text-xanh-deep"
                : "text-xanh-green";
        return (
          <div
            key={i.label}
            className="rounded-xl border border-border bg-white p-3 shadow-[var(--shadow-card)]"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">{i.label}</span>
              <Icon className={`h-3.5 w-3.5 ${toneCls}`} />
            </div>
            <div className="mt-1 font-display text-xl font-bold text-xanh-deep">{i.value}</div>
            <div className="text-[10px] font-mono text-muted-foreground">{i.delta}</div>
          </div>
        );
      })}
    </div>
  );
}

function TrendCard() {
  // Synthetic 14-day data
  const data = [42, 50, 48, 61, 58, 72, 88, 84, 76, 70, 95, 110, 92, 80];
  const negData = [6, 8, 7, 11, 9, 12, 18, 22, 17, 14, 28, 35, 21, 17];
  const max = Math.max(...data);
  const w = 600;
  const h = 180;
  const stepX = w / (data.length - 1);
  const path = (arr: number[]) =>
    arr.map((v, i) => `${i === 0 ? "M" : "L"} ${i * stepX} ${h - (v / max) * h}`).join(" ");
  return (
    <Card>
      <SectionHeader
        icon={LineChartIcon}
        title="Xu hướng phản hồi (14 ngày)"
        subtitle="Tổng phản hồi · Phản hồi tiêu cực · Spike alert"
        right={
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <Legend color="var(--xanh-green)" label="total" />
            <Legend color="var(--xanh-coral)" label="negative" />
          </div>
        }
      />
      <div className="px-5 pb-5">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-44">
          <defs>
            <linearGradient id="gTotal" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--xanh-green)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--xanh-green)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* grid */}
          {[0.25, 0.5, 0.75].map((p) => (
            <line
              key={p}
              x1="0"
              x2={w}
              y1={h * p}
              y2={h * p}
              stroke="oklch(0.92 0.03 170)"
              strokeDasharray="2 4"
            />
          ))}
          <path d={`${path(data)} L ${w} ${h} L 0 ${h} Z`} fill="url(#gTotal)" />
          <path d={path(data)} fill="none" stroke="var(--xanh-green)" strokeWidth="2.5" />
          <path
            d={path(negData)}
            fill="none"
            stroke="var(--xanh-coral)"
            strokeWidth="2"
            strokeDasharray="3 3"
          />
          {/* spike marker */}
          <circle cx={11 * stepX} cy={h - (data[11] / max) * h} r="6" fill="var(--xanh-coral)" />
          <text
            x={11 * stepX + 10}
            y={h - (data[11] / max) * h - 4}
            fontSize="10"
            fill="var(--xanh-coral)"
            fontFamily="JetBrains Mono"
          >
            spike · Hà Nội
          </text>
        </svg>
      </div>
    </Card>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground">
      <span className="h-2 w-3 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

function CategoryBreakdown() {
  const cats = [
    { name: "Tài xế", pct: 32, color: "var(--xanh-green)", icon: Users },
    { name: "Xe / phương tiện", pct: 18, color: "var(--xanh-cyan)", icon: Car },
    { name: "Ứng dụng", pct: 16, color: "var(--xanh-deep)", icon: Cpu },
    { name: "Giá & thanh toán", pct: 14, color: "var(--xanh-amber)", icon: Tag },
    { name: "An toàn", pct: 11, color: "var(--xanh-coral)", icon: Shield },
    { name: "Khác", pct: 9, color: "oklch(0.6 0.02 180)", icon: Layers },
  ];
  return (
    <Card>
      <SectionHeader
        icon={BarChart3}
        title="Phân loại theo chủ đề"
        subtitle="AI multi-label · confidence trung bình 0.87"
      />
      <div className="px-5 pb-5 space-y-3">
        {cats.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.name}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="flex items-center gap-2">
                  <Icon className="h-3.5 w-3.5" style={{ color: c.color }} />
                  <span className="font-medium">{c.name}</span>
                </span>
                <span className="font-mono text-xs text-muted-foreground">{c.pct}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${c.pct * 2.5}%`, background: c.color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function LiveFeed() {
  const [feed, setFeed] = useState<DatabaseSchema["public"]["Tables"]["feedback"]["Row"][]>([]);
  const [newFeedIds, setNewFeedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [streamStatus, setStreamStatus] = useState<"connecting" | "live" | "error">("connecting");
  const apiBase = import.meta.env.VITE_BACKEND_API_URL ?? "http://127.0.0.1:8000";
  const seenIdsRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);

  useEffect(() => {
    let active = true;
    let clearNewIdsTimer: number | undefined;

    async function loadFeed() {
      try {
        const res = await fetch(`${apiBase}/api/feedback/recent?limit=8`);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json = (await res.json()) as {
          data?: DatabaseSchema["public"]["Tables"]["feedback"]["Row"][];
        };
        if (!active) return;
        const rows = json.data ?? [];
        const incomingIds = rows.map((row) => row.id);
        const freshIds = incomingIds.filter((id) => !seenIdsRef.current.has(id));
        incomingIds.forEach((id) => seenIdsRef.current.add(id));

        if (initializedRef.current && freshIds.length) {
          setNewFeedIds(new Set(freshIds));
          if (clearNewIdsTimer) window.clearTimeout(clearNewIdsTimer);
          clearNewIdsTimer = window.setTimeout(() => setNewFeedIds(new Set()), 1600);
        }
        initializedRef.current = true;
        setFeed(rows);
        setStreamStatus("live");
      } catch {
        if (active) setStreamStatus("error");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadFeed();
    const polling = window.setInterval(loadFeed, 1000);

    return () => {
      active = false;
      window.clearInterval(polling);
      if (clearNewIdsTimer) window.clearTimeout(clearNewIdsTimer);
    };
  }, [apiBase]);

  return (
    <Card>
      <SectionHeader
        icon={Radio}
        title="Live feedback stream"
        subtitle="Multi-channel · app, rating, hotline, CS, survey"
        right={
          <span
            className={`text-[11px] font-mono inline-flex items-center gap-1.5 ${
              streamStatus === "error" ? "text-xanh-coral" : "text-xanh-green"
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
            {streamStatus === "live"
              ? "streaming"
              : streamStatus === "error"
                ? "disconnected"
                : "connecting"}
          </span>
        }
      />
      <div className="divide-y divide-border">
        {loading ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Đang tải phản hồi...
          </div>
        ) : feed.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Chưa có phản hồi. Thêm dữ liệu tại trang Phản hồi để xem luồng trực tiếp.
          </div>
        ) : (
          feed.map((f) => (
            <div
              key={f.id}
              className={`px-5 py-3 grid grid-cols-12 gap-3 items-center hover:bg-xanh-mint/30 transition-colors ${
                newFeedIds.has(f.id) ? "live-feedback-row-new" : ""
              }`}
            >
              <span className="col-span-2 sm:col-span-1 text-[10px] font-mono uppercase text-muted-foreground">
                {f.channel}
              </span>
              <p className="col-span-10 sm:col-span-7 text-sm">{f.text}</p>
              <div className="col-span-12 sm:col-span-4 flex flex-wrap justify-start sm:justify-end gap-1.5">
                {f.topic && <Pill tone="mint">{f.topic}</Pill>}
                {f.sentiment && (
                  <Pill tone={f.sentiment === "negative" ? "coral" : "green"}>{f.sentiment}</Pill>
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
          ))
        )}
      </div>
    </Card>
  );
}

function AlertsPanel() {
  const alerts = [
    {
      sev: "P0",
      title: "Spike khiếu nại thanh toán",
      desc: "TP.HCM Q7 · +280% trong 30 phút · 14 case",
      time: "2′ trước",
    },
    {
      sev: "P1",
      title: "App version 4.12.0 lỗi xác nhận chuyến",
      desc: "iOS · 38 phản hồi trong 1 giờ",
      time: "12′",
    },
    {
      sev: "P1",
      title: "Tuyến Nội Bài → Cầu Giấy điểm thấp bất thường",
      desc: "rating TB 3.1 · giảm 1.4 so với baseline",
      time: "27′",
    },
    {
      sev: "P2",
      title: "Cụm 6 tài xế lặp phàn nàn 'thái độ'",
      desc: "Đà Nẵng · ngưỡng cảnh báo driver-watch",
      time: "1h",
    },
  ];
  return (
    <Card>
      <SectionHeader
        icon={Bell}
        title="Alerts đang mở"
        subtitle="Anomaly detection · spike & pattern"
      />
      <div className="px-3 pb-3 space-y-2">
        {alerts.map((a) => (
          <div
            key={a.title}
            className="rounded-xl border border-border bg-white p-3 hover:border-xanh-green/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2">
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                    a.sev === "P0"
                      ? "bg-xanh-coral text-white"
                      : a.sev === "P1"
                        ? "bg-xanh-amber text-xanh-deep"
                        : "bg-xanh-mint text-xanh-deep"
                  }`}
                >
                  {a.sev}
                </span>
                <div>
                  <div className="text-sm font-semibold leading-tight">{a.title}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{a.desc}</div>
                </div>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground whitespace-nowrap">
                {a.time}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Heatmap() {
  // 7 days x 6 time buckets
  const days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const slots = ["06", "09", "12", "15", "18", "21"];
  const data = days.map(() => slots.map(() => Math.round(Math.random() * 100)));
  const color = (v: number) => {
    if (v < 25) return "oklch(0.95 0.05 160)";
    if (v < 50) return "oklch(0.85 0.1 160)";
    if (v < 75) return "oklch(0.72 0.16 145)";
    return "oklch(0.6 0.2 35)";
  };
  return (
    <Card>
      <SectionHeader
        icon={Radar}
        title="Heatmap khu vực × giờ"
        subtitle="Mật độ phản hồi tiêu cực"
      />
      <div className="px-4 pb-4">
        <div className="flex gap-1 pl-7 mb-1">
          {slots.map((s) => (
            <div key={s} className="flex-1 text-center text-[10px] font-mono text-muted-foreground">
              {s}h
            </div>
          ))}
        </div>
        {days.map((d, di) => (
          <div key={d} className="flex items-center gap-1 mb-1">
            <span className="w-6 text-[10px] font-mono text-muted-foreground">{d}</span>
            {data[di].map((v, si) => (
              <div
                key={si}
                title={`${d} · ${slots[si]}h · ${v}`}
                className="flex-1 h-6 rounded"
                style={{ background: color(v) }}
              />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

function DriverWatchlist() {
  const drivers = [
    { id: "DRV-2841", area: "HN-Cầu Giấy", count: 7, rate: 2.4 },
    { id: "DRV-1027", area: "HCM-Q1", count: 5, rate: 2.9 },
    { id: "DRV-3398", area: "ĐN-Hải Châu", count: 4, rate: 3.1 },
  ];
  return (
    <Card>
      <SectionHeader
        icon={Users}
        title="Driver watchlist"
        subtitle="Pattern phàn nàn lặp lại · 7 ngày"
      />
      <div className="px-3 pb-3 space-y-2">
        {drivers.map((d) => (
          <div
            key={d.id}
            className="flex items-center justify-between rounded-xl border border-border bg-white p-3"
          >
            <div>
              <div className="font-mono text-sm font-semibold text-xanh-deep">{d.id}</div>
              <div className="text-[11px] text-muted-foreground">{d.area}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-semibold text-xanh-coral">{d.count} phàn nàn</div>
              <div className="text-[11px] text-muted-foreground font-mono">rating {d.rate}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TicketBoard() {
  const cols = [
    {
      name: "Triage",
      color: "var(--xanh-deep)",
      items: [
        { id: "T-9012", title: "Khiếu nại trừ tiền 2 lần", sla: "1h", sev: "P0" },
        { id: "T-9011", title: "App treo khi xác nhận chuyến", sla: "4h", sev: "P1" },
      ],
    },
    {
      name: "Assigned",
      color: "var(--xanh-cyan)",
      items: [
        { id: "T-8997", title: "Tài xế DRV-2841 — pattern lặp", sla: "1d", sev: "P2" },
        { id: "T-8990", title: "Tuyến Nội Bài rating thấp", sla: "8h", sev: "P1" },
      ],
    },
    {
      name: "In progress",
      color: "var(--xanh-green)",
      items: [{ id: "T-8975", title: "Điều hoà xe yếu — fleet ops", sla: "2d", sev: "P2" }],
    },
    {
      name: "Resolved · feed correction log",
      color: "var(--xanh-deep)",
      items: [
        { id: "T-8902", title: "Sự cố thanh toán Momo", sla: "✓", sev: "P0" },
        { id: "T-8888", title: "Hotline overflow Q1", sla: "✓", sev: "P1" },
      ],
    },
  ];
  return (
    <Card>
      <SectionHeader
        icon={ClipboardList}
        title="Ticket board · SLA tracking"
        subtitle="Từ alert → ticket → xử lý → correction log feedback loop"
        right={
          <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
            <Filter className="h-3.5 w-3.5" /> all severities
          </div>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-4">
        {cols.map((c) => (
          <div
            key={c.name}
            className="rounded-xl border border-border bg-gradient-to-b from-white to-muted/40 p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <span
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: c.color }}
              >
                {c.name}
              </span>
              <span className="text-[10px] font-mono text-muted-foreground">{c.items.length}</span>
            </div>
            <div className="space-y-2">
              {c.items.map((it) => (
                <div
                  key={it.id}
                  className="rounded-lg border border-border bg-white p-2.5 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-muted-foreground">{it.id}</span>
                    <Pill tone={it.sev === "P0" ? "coral" : it.sev === "P1" ? "amber" : "mint"}>
                      {it.sev}
                    </Pill>
                  </div>
                  <p className="text-sm mt-1 leading-snug">{it.title}</p>
                  <div className="text-[10px] font-mono text-muted-foreground mt-1">
                    SLA · {it.sla}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ============================================================
   STORY VIEW
   ============================================================ */

function StoryView() {
  const pains = [
    {
      icon: MessageSquare,
      t: "Feedback quá nhiều",
      d: "Hàng nghìn phản hồi/ngày, đọc thủ công không xuể.",
    },
    {
      icon: Layers,
      t: "Dữ liệu phân tán",
      d: "App, rating, hotline, CS, survey — mỗi nơi một định dạng.",
    },
    { icon: Tag, t: "Khó phân loại", d: "Tài xế, xe, app, giá, thanh toán, an toàn lẫn vào nhau." },
    {
      icon: TrendingUp,
      t: "Không thấy xu hướng",
      d: "Không biết khu vực/khung giờ/tuyến nào đang xấu đi.",
    },
    {
      icon: Workflow,
      t: "Không có vòng cải tiến",
      d: "Không giao việc, không SLA, không feedback loop.",
    },
  ];
  const steps = [
    {
      icon: Database,
      t: "1 · Ingestion",
      d: "Thu thập từ app, rating, hotline, CS, survey, social.",
    },
    { icon: Filter, t: "2 · Clean & PII mask", d: "Chuẩn hoá, loại trùng, ẩn thông tin nhạy cảm." },
    {
      icon: Brain,
      t: "3 · AI/NLP analyze",
      d: "Phân loại chủ đề, cảm xúc, severity, urgency, confidence.",
    },
    {
      icon: Eye,
      t: "4 · Human-in-the-loop",
      d: "Case nhạy cảm hoặc confidence thấp → human review.",
    },
    {
      icon: Siren,
      t: "5 · Alert & Ticket",
      d: "Spike / vấn đề nghiêm trọng → auto-alert + ticket.",
    },
    { icon: Gauge, t: "6 · SLA execution", d: "Đội vận hành xử lý theo SLA, escalate nếu trễ." },
    {
      icon: Workflow,
      t: "7 · Correction log",
      d: "Kết quả phản hồi ngược lại để model học tốt hơn.",
    },
  ];
  return (
    <div className="mt-6 space-y-8">
      {/* Context */}
      <Card>
        <SectionHeader
          icon={Sparkles}
          title="Bối cảnh thực tế"
          subtitle="xanhSM & các hãng smart mobility nhận hàng nghìn phản hồi mỗi ngày"
        />
        <div className="px-6 pb-6 grid md:grid-cols-3 gap-4">
          <BigStat value="1,000+" label="phản hồi/ngày/thành phố" />
          <BigStat value="5+" label="kênh dữ liệu khác nhau" />
          <BigStat value="<1h" label="cửa sổ vàng để xử lý sự cố" />
        </div>
      </Card>

      {/* Pain points */}
      <Card>
        <SectionHeader
          icon={AlertTriangle}
          title="Pain points"
          subtitle="Vì sao đọc thủ công không còn khả thi"
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 p-5">
          {pains.map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.t}
                className="rounded-xl border border-border bg-white p-4 hover:border-xanh-coral/40 transition-colors"
              >
                <Icon className="h-5 w-5 text-xanh-coral" />
                <div className="font-display font-semibold mt-2">{p.t}</div>
                <div className="text-sm text-muted-foreground mt-1">{p.d}</div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Solution intro */}
      <Card className="overflow-hidden">
        <div className="p-6 sm:p-8 text-white" style={{ background: "var(--gradient-hero)" }}>
          <div className="text-xs font-mono opacity-80">SOLUTION</div>
          <h2 className="font-display text-3xl sm:text-4xl font-bold mt-1">
            AI Quality Intelligence Platform
          </h2>
          <p className="mt-3 max-w-2xl opacity-90">
            Không chỉ là dashboard sentiment — đây là hệ thống{" "}
            <strong>khép kín từ dữ liệu đến hành động</strong>: phân loại, chấm ưu tiên, phát hiện
            spike, sinh alert, tạo ticket, theo SLA, và học liên tục qua correction log.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {[
              "Multi-source ingestion",
              "NLP topic + sentiment",
              "Severity & urgency scoring",
              "Anomaly spike detection",
              "Auto ticket + SLA",
              "Human-in-the-loop",
            ].map((k) => (
              <span
                key={k}
                className="text-xs font-mono px-2.5 py-1 rounded-md bg-white/15 border border-white/25"
              >
                {k}
              </span>
            ))}
          </div>
        </div>
      </Card>

      {/* Workflow */}
      <Card>
        <SectionHeader
          icon={Workflow}
          title="Quy trình hoạt động"
          subtitle="7 bước · từ raw feedback đến hành động cải tiến"
        />
        <div className="p-5 grid md:grid-cols-2 lg:grid-cols-4 gap-3">
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.t} className="relative rounded-xl border border-border bg-white p-4">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-xanh-mint grid place-items-center">
                    <Icon className="h-4 w-4 text-xanh-deep" />
                  </div>
                  <div className="font-display font-semibold text-sm">{s.t}</div>
                </div>
                <div className="text-xs text-muted-foreground mt-2">{s.d}</div>
                {i < steps.length - 1 && (
                  <ArrowRight className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-xanh-green/60" />
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

/* ============================================================
   ARCHITECTURE VIEW
   ============================================================ */

function ArchitectureView() {
  const layers = [
    {
      name: "Ingestion Layer",
      icon: Radio,
      color: "var(--xanh-cyan)",
      items: ["App events", "Rating API", "Hotline ASR", "CS tickets", "Survey", "Social"],
    },
    {
      name: "Storage Layer",
      icon: Database,
      color: "var(--xanh-deep)",
      items: ["Raw lake (S3)", "Bronze · Silver · Gold", "Vector store", "Feature store"],
    },
    {
      name: "AI / NLP Layer",
      icon: Brain,
      color: "var(--xanh-green)",
      items: [
        "Language detect & PII mask",
        "Topic classifier (multi-label)",
        "Sentiment & emotion",
        "Severity / urgency scoring",
        "Anomaly & spike detection",
        "LLM summarizer & insight",
      ],
    },
    {
      name: "Workflow Layer",
      icon: Workflow,
      color: "var(--xanh-amber)",
      items: [
        "Rule engine",
        "Alert dispatcher",
        "Ticketing & SLA",
        "Human review queue",
        "Correction log",
      ],
    },
    {
      name: "Cockpit Layer",
      icon: Gauge,
      color: "var(--xanh-deep)",
      items: [
        "KPI & trend",
        "Heatmap khu vực × giờ",
        "Driver / route watch",
        "Ticket board",
        "Reports",
      ],
    },
  ];
  return (
    <div className="mt-6 space-y-6">
      <Card>
        <SectionHeader
          icon={Layers}
          title="Kiến trúc 5 lớp"
          subtitle="Data Engineering + AI/NLP + Workflow operations"
        />
        <div className="p-5 space-y-3">
          {layers.map((l, i) => {
            const Icon = l.icon;
            return (
              <div key={l.name} className="rounded-xl border border-border bg-white p-4">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="h-9 w-9 rounded-lg grid place-items-center text-white"
                      style={{ background: l.color }}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-display font-semibold">
                        {i + 1}. {l.name}
                      </div>
                      <div className="text-[11px] font-mono text-muted-foreground">
                        layer · {i + 1}/5
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {l.items.map((it) => (
                      <span
                        key={it}
                        className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-muted text-foreground/80 border border-border"
                      >
                        {it}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <SectionHeader
          icon={Activity}
          title="Dòng dữ liệu end-to-end"
          subtitle="Raw → Processed → Insight → Action → Learning"
        />
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {[
              { t: "Raw feedback", c: "var(--xanh-cyan)" },
              { t: "Cleaned + enriched", c: "var(--xanh-mint)" },
              { t: "AI insights", c: "var(--xanh-green)" },
              { t: "Alerts & Tickets", c: "var(--xanh-amber)" },
              { t: "Correction Log", c: "var(--xanh-deep)" },
            ].map((s, i, arr) => (
              <div key={s.t} className="relative">
                <div
                  className="rounded-xl p-4 text-white font-display font-semibold text-sm"
                  style={{ background: s.c }}
                >
                  {s.t}
                </div>
                {i < arr.length - 1 && (
                  <ArrowRight className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-4 font-mono">
            Feedback loop: Correction Log → re-train / rules update → AI insights chính xác hơn theo
            thời gian.
          </p>
        </div>
      </Card>
    </div>
  );
}

/* ============================================================
   VALUE VIEW
   ============================================================ */

function ValueView() {
  const personas = [
    { icon: Headphones, t: "CS Team", d: "Xử lý phản hồi nhanh hơn, tự động gán nhóm + ưu tiên." },
    { icon: Activity, t: "Operations", d: "Nhìn ra khu vực / khung giờ / tuyến đang xấu đi." },
    { icon: Shield, t: "Safety", d: "Phát hiện case nguy hiểm sớm, escalate ngay lập tức." },
    { icon: Cpu, t: "Product", d: "Biết app version nào đang gây lỗi, đo tác động." },
    { icon: Users, t: "Driver Management", d: "Phát hiện tài xế có pattern phàn nàn lặp lại." },
    {
      icon: BarChart3,
      t: "Management / BOD",
      d: "Báo cáo chất lượng dịch vụ tự động theo tuần / tháng.",
    },
  ];
  const values = [
    { v: "↓ 80%", l: "thời gian phát hiện sự cố (MTTD)" },
    { v: "↓ 60%", l: "phản hồi bị bỏ sót" },
    { v: "↑ 3×", l: "tốc độ xử lý ticket P0/P1" },
    { v: "100%", l: "phản hồi được phân loại tự động" },
  ];
  return (
    <div className="mt-6 space-y-6">
      <Card>
        <SectionHeader
          icon={Target}
          title="Ai cần dự án này?"
          subtitle="Từ tài xế xe công nghệ đến doanh nghiệp như VinGroup / xanhSM"
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 p-5">
          {personas.map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.t}
                className="rounded-xl border border-border bg-white p-4 hover:shadow-md transition-shadow"
              >
                <div className="h-9 w-9 rounded-lg bg-xanh-mint grid place-items-center">
                  <Icon className="h-5 w-5 text-xanh-deep" />
                </div>
                <div className="font-display font-semibold mt-2">{p.t}</div>
                <div className="text-sm text-muted-foreground mt-1">{p.d}</div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="p-6 sm:p-8 text-white" style={{ background: "var(--gradient-hero)" }}>
          <div className="text-xs font-mono opacity-80">BUSINESS VALUE</div>
          <h2 className="font-display text-3xl font-bold mt-1">
            Giá trị kinh doanh có thể đo được
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
            {values.map((v) => (
              <div
                key={v.l}
                className="rounded-xl bg-white/10 border border-white/20 p-4 backdrop-blur"
              >
                <div className="font-display text-3xl font-bold">{v.v}</div>
                <div className="text-xs opacity-90 mt-1">{v.l}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <SectionHeader
          icon={CheckCircle2}
          title="Kết luận"
          subtitle="Smart Mobility cần một khoang lái chất lượng dịch vụ"
        />
        <div className="p-6 space-y-3 text-sm leading-relaxed">
          <p>
            <strong>AI Quality Intelligence Platform</strong> chuyển hàng nghìn phản hồi rời rạc mỗi
            ngày thành <em>insight</em>, <em>alert</em>, <em>ticket</em> và{" "}
            <em>hành động cải tiến chất lượng</em> — theo đúng cách một khoang lái điều hành
            (Quality Operation Cockpit) phục vụ quản lý.
          </p>
          <p>
            Đây là hệ thống kết hợp <strong>Data Engineering · AI/NLP · Workflow vận hành</strong> —
            phù hợp với mô hình smart mobility quy mô lớn như xanhSM, giúp doanh nghiệp phát hiện
            sớm vấn đề, ưu tiên đúng, và xử lý trước khi ảnh hưởng diện rộng.
          </p>
        </div>
      </Card>
    </div>
  );
}

/* ============================================================
   PRIMITIVES
   ============================================================ */

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-2xl border border-border bg-white/80 backdrop-blur shadow-[var(--shadow-card)] ${className}`}
    >
      {children}
    </section>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  right,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 p-5 border-b border-border/60">
      <div className="flex items-start gap-3">
        <div className="h-9 w-9 rounded-lg bg-xanh-mint grid place-items-center">
          <Icon className="h-4 w-4 text-xanh-deep" />
        </div>
        <div>
          <div className="font-display font-semibold text-base">{title}</div>
          {subtitle && <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>}
        </div>
      </div>
      {right}
    </div>
  );
}

function Pill({
  children,
  tone = "mint",
}: {
  children: React.ReactNode;
  tone?: "mint" | "green" | "coral" | "amber" | "deep" | "cyan";
}) {
  const map: Record<string, string> = {
    mint: "bg-xanh-mint text-xanh-deep border-xanh-green/30",
    green: "bg-xanh-green/15 text-xanh-deep border-xanh-green/40",
    coral: "bg-xanh-coral/15 text-xanh-coral border-xanh-coral/30",
    amber: "bg-xanh-amber/20 text-xanh-deep border-xanh-amber/40",
    deep: "bg-xanh-deep text-white border-xanh-deep",
    cyan: "bg-xanh-cyan/20 text-xanh-deep border-xanh-cyan/40",
  };
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${map[tone]}`}>
      {children}
    </span>
  );
}

function BigStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-border bg-gradient-to-br from-white to-xanh-mint/40 p-5 text-center">
      <div
        className="font-display text-4xl font-bold bg-clip-text text-transparent"
        style={{ backgroundImage: "var(--gradient-green)" }}
      >
        {value}
      </div>
      <div className="text-sm text-muted-foreground mt-1">{label}</div>
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-16 pt-8 border-t border-border/60 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
      <span className="font-mono">xanhSM · AI Quality Intelligence Platform — demo cockpit</span>
      <span className="font-mono">Data Engineering · AI/NLP · Operations</span>
    </footer>
  );
}
