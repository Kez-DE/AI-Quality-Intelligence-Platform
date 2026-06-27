import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bell,
  Brain,
  Car,
  CheckCircle2,
  Clock,
  Layers,
  MessageSquare,
  Shield,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";
import { Card } from "@/components/ui/card";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AI Quality Intelligence Platform — xanhSM" },
      {
        name: "description",
        content:
          "Quality Operation Cockpit cho xanhSM. AI phân tích phản hồi & đánh giá để phát hiện sớm vấn đề chất lượng dịch vụ smart mobility.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Nền trang trí — gradient mềm + lưới, tạo chiều sâu cho landing */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-32 -right-24 h-[28rem] w-[28rem] rounded-full bg-xanh-green/20 blur-3xl" />
        <div className="absolute top-1/4 -left-32 h-[24rem] w-[24rem] rounded-full bg-xanh-cyan/15 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-[20rem] w-[20rem] rounded-full bg-xanh-mint/40 blur-3xl" />
      </div>

      {/* Nav */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-background/70 border-b border-border/60">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="h-9 w-9 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]"
              style={{ background: "var(--gradient-green)" }}
            >
              <Car className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="font-display font-bold text-sm">AI Quality Intelligence</div>
              <div className="text-[11px] font-mono text-muted-foreground">xanhSM · Cockpit</div>
            </div>
          </div>
          <Link
            to="/auth"
            className="h-9 px-4 rounded-lg text-sm font-semibold text-white flex items-center gap-1.5 shadow-[var(--shadow-green)] hover:scale-[1.02] transition-transform"
            style={{ background: "var(--gradient-green)" }}
          >
            Đăng nhập
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-16 pb-12">
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-xanh-mint text-xanh-deep text-xs font-mono border border-xanh-green/30 mb-4">
              <Sparkles className="h-3.5 w-3.5" />
              Smart Mobility · Feedback Analytics
            </div>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.05]">
              Biến hàng nghìn phản hồi mỗi ngày thành{" "}
              <span className="text-xanh-green">hành động vận hành</span>.
            </h1>
            <p className="mt-5 text-lg text-muted-foreground max-w-2xl">
              Quality Operation Cockpit cho xanhSM — phân loại tự động, phát hiện
              spike, sinh alert & ticket theo SLA, và một AI assistant giúp manager
              ra quyết định nhanh.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                to="/auth"
                className="h-12 px-6 rounded-xl text-white font-semibold flex items-center gap-2 shadow-[var(--shadow-green)] hover:scale-[1.02] transition-transform"
                style={{ background: "var(--gradient-green)" }}
              >
                Bắt đầu miễn phí
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/auth"
                className="h-12 px-6 rounded-xl border border-border bg-card/80 backdrop-blur font-semibold flex items-center gap-2 hover:border-xanh-green/40 transition-colors"
              >
                Đăng nhập
              </Link>
            </div>

            {/* Hàng tin cậy — điểm nhấn năng lực lõi */}
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-mono text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" /> Realtime ingest
              </span>
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-success" /> PII masking
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Brain className="h-3.5 w-3.5 text-success" /> Multi-agent LLM
              </span>
            </div>
          </div>
          <div className="lg:col-span-5">
            <PreviewCard />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
        <SectionTitle
          icon={Sparkles}
          eyebrow="TÍNH NĂNG"
          title="Một khoang lái — toàn bộ vòng đời chất lượng"
          sub="Từ thu thập phản hồi đến hành động vận hành, tất cả trong một cockpit."
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Feature
            icon={MessageSquare}
            title="Thu thập phản hồi"
            desc="Nhập tay hoặc kết nối nhiều nguồn: app, hotline, CS, survey."
          />
          <Feature
            icon={Brain}
            title="AI phân loại tự động"
            desc="Topic, sentiment, severity, urgency — confidence cho mỗi case."
          />
          <Feature
            icon={BarChart3}
            title="Bảng điều khiển & biểu đồ"
            desc="KPI, trend, heatmap khu vực × giờ, breakdown theo chủ đề."
          />
          <Feature
            icon={Bell}
            title="Alert & SLA"
            desc="Phát hiện spike bất thường, tự sinh cảnh báo theo độ ưu tiên."
          />
          <Feature
            icon={Sparkles}
            title="AI Chat Assistant"
            desc="Hỏi đáp với AI để diễn giải dữ liệu và đề xuất hành động."
          />
          <Feature
            icon={Workflow}
            title="Correction Log"
            desc="Vòng phản hồi cải tiến — AI học từ kết quả xử lý thực tế."
          />
        </div>
      </section>

      {/* Personas */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
        <SectionTitle
          icon={Layers}
          eyebrow="AI CẦN DỰ ÁN NÀY?"
          title="Phục vụ tài xế xe công nghệ & doanh nghiệp như VinGroup / xanhSM"
          sub="Mỗi vai trò vận hành đều có góc nhìn riêng trên cùng một nguồn dữ liệu."
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { icon: Layers, t: "CS Team", d: "Xử lý phản hồi nhanh hơn, ưu tiên tự động." },
            { icon: Zap, t: "Operations", d: "Nhìn ra khu vực & khung giờ đang xấu đi." },
            { icon: Shield, t: "Safety", d: "Phát hiện case nguy hiểm sớm, escalate ngay." },
          ].map((p) => {
            const Icon = p.icon;
            return (
              <Card
                key={p.t}
                className="rounded-2xl border bg-card/80 backdrop-blur p-5 hover:border-xanh-green/40 hover:shadow-[var(--shadow-card)] transition-all"
              >
                <div className="h-11 w-11 rounded-xl bg-xanh-mint grid place-items-center">
                  <Icon className="h-5 w-5 text-xanh-deep" />
                </div>
                <div className="font-display font-semibold mt-3">{p.t}</div>
                <div className="text-sm text-muted-foreground mt-1 leading-relaxed">{p.d}</div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-20">
        <div
          className="relative overflow-hidden rounded-3xl p-10 sm:p-12 text-white text-center shadow-[var(--shadow-green)]"
          style={{ background: "var(--gradient-hero)" }}
        >
          <div className="pointer-events-none absolute -top-16 -right-10 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
          <div className="relative">
            <h2 className="font-display text-3xl sm:text-4xl font-bold">
              Sẵn sàng phát hiện sự cố sớm?
            </h2>
            <p className="mt-3 opacity-90 max-w-xl mx-auto">
              Đăng nhập vào Quality Operation Cockpit — bắt đầu phân tích phản hồi
              và chat với AI ngay hôm nay.
            </p>
            <Link
              to="/auth"
              className="inline-flex mt-6 h-12 px-7 rounded-xl bg-card text-xanh-deep font-semibold items-center gap-2 hover:scale-[1.02] transition-transform shadow-lg"
            >
              Đăng nhập <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-border/60 py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-xs font-mono text-muted-foreground flex flex-wrap justify-between gap-2">
          <span>xanhSM · AI Quality Intelligence Platform</span>
          <span>Data Engineering · AI/NLP · Operations</span>
        </div>
      </footer>
    </div>
  );
}

function SectionTitle({
  icon: Icon,
  eyebrow,
  title,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  eyebrow?: string;
  title: string;
  sub?: string;
}) {
  return (
    <div className="flex items-start gap-3 mb-8">
      <div className="h-11 w-11 rounded-xl bg-primary/10 text-primary grid place-items-center shrink-0">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        {eyebrow && (
          <div className="text-xs font-mono font-semibold uppercase tracking-wider text-xanh-deep">
            {eyebrow}
          </div>
        )}
        <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1 leading-tight">
          {title}
        </h2>
        {sub && <p className="text-sm text-muted-foreground mt-2 max-w-2xl">{sub}</p>}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  trend,
  tone = "default",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
  trend?: string;
  tone?: "default" | "good";
}) {
  return (
    <Card
      className={`p-4 bg-card/80 backdrop-blur hover:shadow-[var(--shadow-card)] transition-all ${
        tone === "good" ? "ring-1 ring-primary/30" : ""
      }`}
    >
      <div className="flex items-start justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div className="mt-2 font-display text-2xl font-bold tracking-tight text-xanh-deep">
        {value}
      </div>
      {(trend || sub) && (
        <div className="mt-1 flex items-center gap-1.5 text-[11px]">
          {trend && (
            <span className="inline-flex items-center gap-0.5 font-semibold text-success">
              <TrendingUp className="h-3 w-3" />
              {trend}
            </span>
          )}
          {sub && <span className="text-muted-foreground">{sub}</span>}
        </div>
      )}
    </Card>
  );
}

function Feature({
  icon: Icon,
  title,
  desc,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  desc: string;
}) {
  return (
    <Card className="rounded-2xl border bg-card/80 backdrop-blur p-5 hover:border-xanh-green/40 hover:shadow-[var(--shadow-card)] transition-all">
      <div
        className="h-11 w-11 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]"
        style={{ background: "var(--gradient-green)" }}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="font-display font-semibold mt-3">{title}</div>
      <div className="text-sm text-muted-foreground mt-1 leading-relaxed">{desc}</div>
    </Card>
  );
}

function PreviewCard() {
  return (
    <Card className="rounded-3xl border bg-card/80 backdrop-blur p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary grid place-items-center">
            <Activity className="h-4 w-4" />
          </div>
          <div className="text-xs font-mono text-muted-foreground">QUALITY · SNAPSHOT</div>
        </div>
        <span className="text-[10px] font-mono text-xanh-green inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-xanh-green animate-pulse" /> LIVE
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          icon={MessageSquare}
          label="Feedback/ngày"
          value="12,480"
          trend="8.2%"
          tone="good"
        />
        <StatCard icon={Brain} label="Auto-classified" value="97.4%" sub="confidence cao" tone="good" />
        <StatCard icon={Clock} label="MTTD sự cố" value="4.2′" sub="phát hiện" />
        <StatCard icon={CheckCircle2} label="SLA on-time" value="94%" sub="đúng hẹn" />
      </div>
      <div className="mt-4 rounded-xl border border-xanh-coral/30 bg-xanh-coral/5 p-3">
        <div className="text-[10px] font-mono text-xanh-coral mb-1 flex items-center gap-1.5">
          <Bell className="h-3 w-3" /> ALERT · 2′ trước
        </div>
        <div className="text-sm font-semibold">Spike khiếu nại thanh toán · TP.HCM Q7</div>
        <div className="text-xs text-muted-foreground">+280% trong 30 phút · 14 case · P0</div>
      </div>
    </Card>
  );
}
