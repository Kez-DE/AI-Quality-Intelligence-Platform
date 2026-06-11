import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  BarChart3,
  Bell,
  Brain,
  Car,
  Layers,
  MessageSquare,
  Shield,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react";

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
    <div className="min-h-screen">
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
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: "var(--gradient-green)" }}
              >
                hành động vận hành
              </span>
              .
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
                className="h-12 px-6 rounded-xl border border-border bg-white font-semibold flex items-center gap-2 hover:border-xanh-green/40"
              >
                Đăng nhập
              </Link>
            </div>
          </div>
          <div className="lg:col-span-5">
            <PreviewCard />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="text-xs font-mono text-xanh-deep">FEATURES</div>
          <h2 className="font-display text-3xl sm:text-4xl font-bold mt-1">
            Một khoang lái — toàn bộ vòng đời chất lượng
          </h2>
        </div>
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
            title="Dashboard & charts"
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
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="text-xs font-mono text-xanh-deep">AI CẦN DỰ ÁN NÀY?</div>
          <h2 className="font-display text-3xl sm:text-4xl font-bold mt-1">
            Phục vụ tài xế xe công nghệ & doanh nghiệp như VinGroup / xanhSM
          </h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { icon: Layers, t: "CS Team", d: "Xử lý phản hồi nhanh hơn, ưu tiên tự động." },
            { icon: Zap, t: "Operations", d: "Nhìn ra khu vực & khung giờ đang xấu đi." },
            { icon: Shield, t: "Safety", d: "Phát hiện case nguy hiểm sớm, escalate ngay." },
          ].map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.t}
                className="rounded-2xl border border-border bg-white p-5 hover:shadow-[var(--shadow-card)] transition-shadow"
              >
                <div className="h-10 w-10 rounded-lg bg-xanh-mint grid place-items-center">
                  <Icon className="h-5 w-5 text-xanh-deep" />
                </div>
                <div className="font-display font-semibold mt-3">{p.t}</div>
                <div className="text-sm text-muted-foreground mt-1">{p.d}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-20">
        <div
          className="rounded-3xl p-10 text-white text-center"
          style={{ background: "var(--gradient-hero)" }}
        >
          <h2 className="font-display text-3xl sm:text-4xl font-bold">
            Sẵn sàng phát hiện sự cố sớm?
          </h2>
          <p className="mt-3 opacity-90 max-w-xl mx-auto">
            Đăng nhập vào Quality Operation Cockpit — bắt đầu phân tích phản hồi
            và chat với AI ngay hôm nay.
          </p>
          <Link
            to="/auth"
            className="inline-flex mt-6 h-12 px-7 rounded-xl bg-white text-xanh-deep font-semibold items-center gap-2 hover:scale-[1.02] transition-transform"
          >
            Đăng nhập <ArrowRight className="h-4 w-4" />
          </Link>
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
    <div className="rounded-2xl border border-border bg-white p-5 hover:border-xanh-green/40 transition-colors">
      <div
        className="h-10 w-10 rounded-lg grid place-items-center text-white"
        style={{ background: "var(--gradient-green)" }}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="font-display font-semibold mt-3">{title}</div>
      <div className="text-sm text-muted-foreground mt-1">{desc}</div>
    </div>
  );
}

function PreviewCard() {
  return (
    <div className="rounded-3xl border border-border bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-mono text-muted-foreground">QUALITY · SNAPSHOT</div>
        <span className="text-[10px] font-mono text-xanh-green inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-xanh-green animate-pulse" /> LIVE
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[
          { v: "12,480", l: "Feedback/ngày" },
          { v: "97.4%", l: "Auto-classified" },
          { v: "4.2′", l: "MTTD sự cố" },
          { v: "94%", l: "SLA on-time" },
        ].map((s) => (
          <div
            key={s.l}
            className="rounded-xl p-3 border border-border bg-gradient-to-br from-white to-xanh-mint/40"
          >
            <div className="font-display text-2xl font-bold text-xanh-deep">{s.v}</div>
            <div className="text-[11px] text-muted-foreground">{s.l}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-xl border border-border p-3 bg-gradient-to-br from-xanh-mint/20 to-white">
        <div className="text-[10px] font-mono text-muted-foreground mb-1">
          ALERT · 2′ trước
        </div>
        <div className="text-sm font-semibold">Spike khiếu nại thanh toán · TP.HCM Q7</div>
        <div className="text-xs text-muted-foreground">
          +280% trong 30 phút · 14 case · P0
        </div>
      </div>
    </div>
  );
}
