import { Activity, ArrowDown, Brain, Database, Filter, Gauge, Layers, Radio, Workflow } from "lucide-react";
import { Card, SectionHeader } from "../primitives";

const LAYERS = [
  {
    num: "1",
    name: "Ingestion Layer",
    icon: Radio,
    color: "var(--xanh-cyan)",
    bg: "oklch(0.96 0.04 200)",
    items: ["App events", "Rating API", "Hotline ASR", "CS tickets", "Survey", "Social"],
    desc: "Thu thập đa kênh, chuẩn hoá schema",
  },
  {
    num: "2",
    name: "Storage Layer",
    icon: Database,
    color: "var(--xanh-deep)",
    bg: "oklch(0.96 0.03 220)",
    items: ["Raw lake (S3)", "Bronze · Silver · Gold", "Vector store", "Feature store"],
    desc: "Lưu trữ phân tầng, PII masking",
  },
  {
    num: "3",
    name: "AI / NLP Layer",
    icon: Brain,
    color: "var(--xanh-green)",
    bg: "oklch(0.96 0.05 165)",
    items: ["PII mask & lang detect", "Topic classifier (multi-label)", "Sentiment & emotion", "Severity / urgency scoring", "Anomaly & spike detection", "LLM summarizer"],
    desc: "Phân tích tự động, confidence scoring",
  },
  {
    num: "4",
    name: "Workflow Layer",
    icon: Workflow,
    color: "var(--xanh-amber)",
    bg: "oklch(0.96 0.05 90)",
    items: ["Rule engine", "Alert dispatcher", "Ticketing & SLA", "Human review queue", "Correction log"],
    desc: "Điều phối hành động, SLA enforcement",
  },
  {
    num: "5",
    name: "Cockpit Layer",
    icon: Gauge,
    color: "var(--xanh-deep)",
    bg: "oklch(0.96 0.03 220)",
    items: ["KPI & trend dashboard", "Heatmap khu vực × giờ", "Alert & ticket board", "Team leaderboard", "Report generation"],
    desc: "Giao diện vận hành & ra quyết định",
  },
];

const FLOW_NODES = [
  { t: "Raw feedback", c: "var(--xanh-cyan)", sub: "5+ kênh" },
  { t: "Cleaned + enriched", c: "var(--xanh-mint)", sub: "PII masked" },
  { t: "AI insights", c: "var(--xanh-green)", sub: "NLP pipeline" },
  { t: "Alerts & Tickets", c: "var(--xanh-amber)", sub: "Auto-routing" },
  { t: "Correction Log", c: "var(--xanh-deep)", sub: "Feedback loop" },
];

const TECH_STACK = [
  { cat: "Backend", items: ["FastAPI", "Python 3.12", "Supabase Realtime"] },
  { cat: "AI / NLP", items: ["DeepSeek LLM", "Cohere Embed", "RAG keyword"] },
  { cat: "Storage", items: ["PostgreSQL (Supabase)", "pgvector", "S3-compatible"] },
  { cat: "Frontend", items: ["React 19", "TanStack Query", "Vite + Tailwind"] },
  { cat: "Deploy", items: ["Railway (6 services)", "GitHub Actions", "Self-hosted runner"] },
];

export function ArchitectureView() {
  return (
    <div className="mt-6 space-y-6">
      {/* 5 lớp */}
      <Card>
        <SectionHeader icon={Layers} title="Kiến trúc 5 lớp" subtitle="Data Engineering · AI/NLP · Workflow · Operations" />
        <div className="p-5 space-y-2">
          {LAYERS.map((l, i) => {
            const Icon = l.icon;
            return (
              <div key={l.name} className="relative">
                <div
                  className="rounded-xl border border-border p-4 transition-shadow hover:shadow-sm"
                  style={{ background: l.bg }}
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-10 w-10 rounded-xl grid place-items-center text-white flex-shrink-0 shadow-sm" style={{ background: l.color }}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] font-bold" style={{ color: l.color }}>
                            L{l.num}
                          </span>
                          <div className="font-display font-semibold text-sm">{l.name}</div>
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">{l.desc}</div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {l.items.map((it) => (
                        <span key={it} className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-card/80 text-foreground/80 border border-border/60 backdrop-blur">
                          {it}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                {i < LAYERS.length - 1 && (
                  <div className="flex justify-center my-1">
                    <ArrowDown className="h-4 w-4 text-muted-foreground/40" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      {/* Data flow */}
      <Card>
        <SectionHeader icon={Activity} title="Dòng dữ liệu end-to-end" subtitle="Raw → Processed → Insight → Action → Learning loop" />
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {FLOW_NODES.map((s, i, arr) => (
              <div key={s.t} className="relative">
                <div className="rounded-xl p-4 text-white" style={{ background: s.c }}>
                  <div className="font-display font-semibold text-sm">{s.t}</div>
                  <div className="text-[10px] opacity-80 mt-1 font-mono">{s.sub}</div>
                </div>
                {i < arr.length - 1 && (
                  <div className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 items-center z-10">
                    <div className="h-px w-4 bg-muted-foreground/30" />
                    <div className="h-0 w-0 border-t-4 border-b-4 border-l-4 border-t-transparent border-b-transparent border-l-muted-foreground/40" />
                  </div>
                )}
              </div>
            ))}
          </div>
          {/* feedback loop arrow */}
          <div className="mt-5 pt-4 border-t border-border/60">
            <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
              <div className="h-px flex-1 bg-xanh-green/30" />
              <span className="whitespace-nowrap text-xanh-deep font-semibold">↺ Correction Loop</span>
              <div className="h-px flex-1 bg-xanh-green/30" />
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-center">
              Correction Log → re-train / rule update → AI insights ngày càng chính xác hơn
            </p>
          </div>
        </div>
      </Card>

      {/* Tech stack */}
      <Card>
        <SectionHeader icon={Database} title="Tech stack" subtitle="Công nghệ triển khai thực tế" />
        <div className="p-5 grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {TECH_STACK.map((s) => (
            <div key={s.cat} className="rounded-xl border border-border bg-card p-4">
              <div className="text-[10px] font-mono font-bold text-xanh-deep uppercase tracking-wider mb-2">{s.cat}</div>
              <div className="space-y-1">
                {s.items.map((it) => (
                  <div key={it} className="text-xs text-foreground/80 flex items-center gap-1.5">
                    <span className="h-1 w-1 rounded-full bg-xanh-green flex-shrink-0" />
                    {it}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
