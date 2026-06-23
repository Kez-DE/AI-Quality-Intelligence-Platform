import { useState } from "react";
import { Car, Gauge, Layers, Sparkles, Target } from "lucide-react";
import { CockpitFilterProvider } from "./cockpit/CockpitFilterContext";
import { CockpitView } from "./cockpit/CockpitView";
import { ArchitectureView } from "./cockpit/presentation/ArchitectureView";
import { StoryView } from "./cockpit/presentation/StoryView";
import { ValueView } from "./cockpit/presentation/ValueView";
import { HeroStats } from "./cockpit/widgets/HeroStats";

export default function QualityCockpit() {
  const [tab, setTab] = useState<"cockpit" | "story" | "architecture" | "value">("cockpit");

  return (
    <div className="min-h-screen text-foreground">
      <TopBar tab={tab} setTab={setTab} />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24">
        <Hero />
        <CockpitFilterProvider>
          {tab === "cockpit" && <CockpitView />}
        </CockpitFilterProvider>
        {tab === "story" && <StoryView />}
        {tab === "architecture" && <ArchitectureView />}
        {tab === "value" && <ValueView />}
        <Footer />
      </main>
    </div>
  );
}

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
          <div className="h-9 w-9 rounded-xl grid place-items-center text-white shadow-[var(--shadow-green)]" style={{ background: "var(--gradient-green)" }}>
            <Car className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="font-display font-bold text-base">AI Quality Intelligence</div>
            <div className="text-[11px] text-muted-foreground font-mono">xanhSM · Quality Operation Cockpit</div>
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
                  active ? "bg-white text-xanh-deep shadow-sm font-semibold" : "text-muted-foreground hover:text-foreground"
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
      <div className="md:hidden flex overflow-x-auto gap-1 px-3 pb-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap ${tab === t.id ? "bg-xanh-deep text-white" : "bg-muted text-muted-foreground"}`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </header>
  );
}

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
            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-green)" }}>
              hành động vận hành
            </span>
            .
          </h1>
          <p className="mt-5 text-lg text-muted-foreground max-w-2xl">
            <strong className="text-foreground">AI Quality Intelligence Platform</strong> là khoang lái điều hành chất lượng dịch vụ — phân loại, phát hiện spike, sinh alert & ticket theo SLA, giúp xanhSM xử lý sự cố <em>trước khi</em> chúng trở thành khủng hoảng.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {["Problem → Solution", "Real-time", "Alert · SLA", "Human-in-the-loop", "Correction Log", "Operational Intelligence"].map((k) => (
              <span key={k} className="text-xs font-mono px-2.5 py-1 rounded-md bg-white border border-border text-xanh-deep">{k}</span>
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

function Footer() {
  return (
    <footer className="mt-16 pt-8 border-t border-border/60 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
      <span className="font-mono">xanhSM · AI Quality Intelligence Platform — demo cockpit</span>
      <span className="font-mono">Data Engineering · AI/NLP · Operations</span>
    </footer>
  );
}
