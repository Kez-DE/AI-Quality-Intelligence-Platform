import {
  Activity,
  BarChart3,
  CheckCircle2,
  Clock,
  Cpu,
  Headphones,
  Shield,
  Star,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { Card, SectionHeader } from "../primitives";

const PERSONAS = [
  {
    icon: Headphones,
    t: "CS Team",
    d: "Xử lý phản hồi nhanh hơn, tự động gán nhóm + ưu tiên theo severity.",
    benefit: "↓ 60% thời gian xử lý",
  },
  {
    icon: Activity,
    t: "Operations",
    d: "Nhìn ra khu vực / khung giờ / tuyến đang xấu đi trước khi leo thang.",
    benefit: "Phát hiện spike < 5′",
  },
  {
    icon: Shield,
    t: "Safety",
    d: "Phát hiện case nguy hiểm sớm, escalate ngay lập tức qua alert P5.",
    benefit: "Zero-miss critical case",
  },
  {
    icon: Cpu,
    t: "Product / Tech",
    d: "Biết app version nào đang gây lỗi, đo tác động và roll-back có dữ liệu.",
    benefit: "Root cause trong 1 click",
  },
  {
    icon: Users,
    t: "Driver Management",
    d: "Phát hiện tài xế / tuyến có pattern phàn nàn lặp lại, can thiệp sớm.",
    benefit: "Pattern detection 7 ngày",
  },
  {
    icon: BarChart3,
    t: "Management / BOD",
    d: "Báo cáo chất lượng dịch vụ tự động theo tuần / tháng — không cần họp daily.",
    benefit: "Auto-report mỗi ngày",
  },
];

const VALUES = [
  { icon: TrendingDown, v: "↓ 80%", l: "MTTD sự cố", sub: "từ ~6h xuống < 5 phút", tone: "green" },
  { icon: CheckCircle2, v: "↓ 60%", l: "Phản hồi bị bỏ sót", sub: "tự động phân loại & route", tone: "green" },
  { icon: Zap, v: "↑ 3×", l: "Tốc độ xử lý P4/P5", sub: "alert → ticket → done", tone: "amber" },
  { icon: Star, v: "100%", l: "Phản hồi được phân loại", sub: "confidence avg ≥ 0.85", tone: "cyan" },
];

const BEFORE_AFTER = [
  { before: "Đọc feedback thủ công, lọc từ nhiều sheet Excel", after: "Pipeline tự động phân loại 100% theo chủ đề & severity" },
  { before: "Phát hiện sự cố khi khách hàng gọi hotline (~6h trễ)", after: "Spike detection real-time — alert trong < 5 phút" },
  { before: "Giao ticket bằng email, không theo SLA", after: "Auto-ticket với SLA, escalation tự động khi trễ" },
  { before: "Không biết model AI có cải thiện không", after: "Correction log → feedback loop → model ngày càng chính xác" },
];

function ToneCls(tone: string) {
  if (tone === "amber") return { icon: "text-xanh-amber", bg: "bg-xanh-amber/10", border: "border-xanh-amber/30" };
  if (tone === "cyan") return { icon: "text-xanh-cyan", bg: "bg-xanh-cyan/10", border: "border-xanh-cyan/30" };
  return { icon: "text-xanh-green", bg: "bg-xanh-mint", border: "border-xanh-green/30" };
}

export function ValueView() {
  return (
    <div className="mt-6 space-y-6">
      {/* Business value KPIs */}
      <Card className="overflow-hidden">
        <div className="relative p-6 sm:p-10 text-white overflow-hidden" style={{ background: "var(--gradient-hero)" }}>
          <div className="pointer-events-none absolute -top-20 -right-20 h-64 w-64 rounded-full opacity-10" style={{ background: "var(--xanh-cyan)" }} />
          <div className="relative">
            <div className="text-xs font-mono opacity-70 mb-2">BUSINESS VALUE</div>
            <h2 className="font-display text-3xl font-bold">Giá trị kinh doanh có thể đo được</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
              {VALUES.map((v) => {
                const Icon = v.icon;
                return (
                  <div key={v.l} className="rounded-xl bg-white/10 border border-white/20 p-4 backdrop-blur hover:bg-white/15 transition-colors">
                    <Icon className="h-5 w-5 mb-2 opacity-80" />
                    <div className="font-display text-3xl font-bold">{v.v}</div>
                    <div className="text-sm font-semibold mt-1">{v.l}</div>
                    <div className="text-xs opacity-70 mt-0.5 font-mono">{v.sub}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </Card>

      {/* Before / After */}
      <Card>
        <SectionHeader icon={TrendingUp} title="Trước & Sau khi có hệ thống" subtitle="Chuyển đổi quy trình vận hành chất lượng" />
        <div className="p-5">
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div className="text-xs font-mono font-bold text-xanh-coral px-3">TRƯỚC ✗</div>
            <div className="text-xs font-mono font-bold text-xanh-green px-3">SAU ✓</div>
          </div>
          <div className="space-y-2">
            {BEFORE_AFTER.map((row, i) => (
              <div key={i} className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-xanh-coral/20 bg-xanh-coral/5 p-3 text-xs text-foreground/80 leading-relaxed">
                  {row.before}
                </div>
                <div className="rounded-lg border border-xanh-green/25 bg-xanh-mint/60 p-3 text-xs text-xanh-deep leading-relaxed font-medium">
                  {row.after}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Personas */}
      <Card>
        <SectionHeader icon={Target} title="Ai cần hệ thống này?" subtitle="Từ tài xế đến Ban lãnh đạo — mỗi vai trò đều có giá trị" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 p-5">
          {PERSONAS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.t} className="rounded-xl border border-border bg-card p-4 hover:shadow-md hover:-translate-y-0.5 transition-all group">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="h-9 w-9 rounded-lg bg-xanh-mint grid place-items-center">
                    <Icon className="h-5 w-5 text-xanh-deep" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-xanh-mint text-xanh-deep border border-xanh-green/30">
                    {p.benefit}
                  </span>
                </div>
                <div className="font-display font-semibold">{p.t}</div>
                <div className="text-sm text-muted-foreground mt-1 leading-relaxed">{p.d}</div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Kết luận */}
      <Card>
        <SectionHeader icon={CheckCircle2} title="Kết luận" subtitle="Smart Mobility cần một khoang lái chất lượng dịch vụ — ngay hôm nay" />
        <div className="p-6 space-y-4">
          <div className="grid sm:grid-cols-3 gap-3">
            {[
              { icon: Clock, t: "Phát hiện sớm", d: "Spike detection < 5 phút, thay vì phát hiện khi leo thang lên C-level.", color: "var(--xanh-cyan)" },
              { icon: Zap, t: "Hành động đúng lúc", d: "Alert → Ticket → SLA → Resolved. Vòng lặp khép kín, không bỏ sót.", color: "var(--xanh-green)" },
              { icon: TrendingUp, t: "Cải tiến liên tục", d: "Correction log → model tốt hơn → ít false alarm → đội ops tin tưởng hệ thống.", color: "var(--xanh-amber)" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.t} className="rounded-xl border border-border bg-gradient-to-br from-card to-xanh-mint/20 p-4">
                  <div className="h-8 w-8 rounded-lg grid place-items-center mb-3" style={{ background: `color-mix(in oklch, ${item.color} 15%, white)` }}>
                    <Icon className="h-4 w-4" style={{ color: item.color }} />
                  </div>
                  <div className="font-display font-semibold text-sm">{item.t}</div>
                  <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{item.d}</div>
                </div>
              );
            })}
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed border-t border-border/60 pt-4">
            <strong className="text-foreground">AI Quality Intelligence Platform</strong> chuyển hàng nghìn phản hồi rời rạc thành{" "}
            <em>insight, alert, ticket và hành động</em> — theo đúng cách một khoang lái điều hành phục vụ quản lý smart mobility quy mô lớn như xanhSM.
          </p>
        </div>
      </Card>
    </div>
  );
}
