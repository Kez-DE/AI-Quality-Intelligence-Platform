import type { LucideProps } from "lucide-react";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-2xl border border-border bg-white/80 backdrop-blur shadow-[var(--shadow-card)] ${className}`}
    >
      {children}
    </section>
  );
}

export function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  right,
}: {
  icon: React.ComponentType<LucideProps>;
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

export function Pill({
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

export function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground">
      <span className="h-2 w-3 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

export function BigStat({ value, label }: { value: string; label: string }) {
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
