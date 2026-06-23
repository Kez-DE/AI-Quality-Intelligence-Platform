import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Database,
  Eye,
  Filter,
  Gauge,
  Layers,
  MessageSquare,
  Siren,
  Sparkles,
  Tag,
  TrendingUp,
  Workflow,
} from "lucide-react";
import { BigStat, Card, SectionHeader } from "../primitives";

const PAINS = [
  { icon: MessageSquare, t: "Feedback quá nhiều", d: "Hàng nghìn phản hồi/ngày — đọc thủ công không xuể, không có ưu tiên.", color: "var(--xanh-coral)" },
  { icon: Layers, t: "Dữ liệu phân tán", d: "App, rating, hotline, CS, survey — mỗi kênh một định dạng riêng biệt.", color: "var(--xanh-amber)" },
  { icon: Tag, t: "Khó phân loại", d: "Tài xế, xe, app, giá, thanh toán, an toàn lẫn vào nhau, không có taxonomy.", color: "var(--xanh-amber)" },
  { icon: TrendingUp, t: "Mù xu hướng", d: "Không biết khu vực / khung giờ / tuyến nào đang xấu đi theo thời gian.", color: "var(--xanh-coral)" },
  { icon: Workflow, t: "Không có vòng cải tiến", d: "Không giao việc, không SLA, không feedback loop — sự cố lặp lại.", color: "var(--xanh-coral)" },
];

const STEPS = [
  { icon: Database, t: "Ingestion", d: "App, rating, hotline, CS, survey, social", num: "01" },
  { icon: Filter, t: "Clean & PII mask", d: "Chuẩn hoá, loại trùng, ẩn thông tin nhạy cảm", num: "02" },
  { icon: Brain, t: "AI / NLP analyze", d: "Topic, sentiment, severity, urgency, confidence", num: "03" },
  { icon: Eye, t: "Human-in-the-loop", d: "Case nhạy cảm hoặc confidence thấp → human review", num: "04" },
  { icon: Siren, t: "Alert & Ticket", d: "Spike / vấn đề nghiêm trọng → auto-alert + ticket", num: "05" },
  { icon: Gauge, t: "SLA execution", d: "Đội vận hành xử lý theo SLA, escalate nếu trễ", num: "06" },
  { icon: Workflow, t: "Correction log", d: "Phản hồi ngược → model học & rule cập nhật", num: "07" },
];

const CAPABILITIES = [
  "Multi-source ingestion",
  "NLP topic + sentiment",
  "Severity & urgency scoring",
  "Anomaly spike detection",
  "Auto ticket + SLA",
  "Human-in-the-loop",
  "Correction log",
  "RBAC phòng ban",
];

export function StoryView() {
  return (
    <div className="mt-6 space-y-8">
      {/* Bối cảnh */}
      <Card>
        <SectionHeader icon={Sparkles} title="Bối cảnh thực tế" subtitle="xanhSM — Smart Mobility nhận hàng nghìn phản hồi mỗi ngày" />
        <div className="px-6 pb-6 grid md:grid-cols-3 gap-4">
          <BigStat value="1,000+" label="phản hồi / ngày / thành phố" />
          <BigStat value="5+" label="kênh dữ liệu khác nhau" />
          <BigStat value="< 1h" label="cửa sổ vàng xử lý sự cố" />
        </div>
      </Card>

      {/* Pain points */}
      <Card>
        <SectionHeader icon={AlertTriangle} title="Vì sao đọc thủ công không còn khả thi?" subtitle="5 điểm đau cốt lõi của vận hành chất lượng truyền thống" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 p-5">
          {PAINS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.t} className="group rounded-xl border border-border bg-white p-4 hover:shadow-md transition-all hover:-translate-y-0.5">
                <div className="h-9 w-9 rounded-lg grid place-items-center mb-3" style={{ background: `color-mix(in oklch, ${p.color} 15%, white)` }}>
                  <Icon className="h-4.5 w-4.5" style={{ color: p.color }} />
                </div>
                <div className="font-display font-semibold text-sm">{p.t}</div>
                <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{p.d}</div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Solution hero */}
      <Card className="overflow-hidden">
        <div className="relative p-6 sm:p-10 text-white overflow-hidden" style={{ background: "var(--gradient-hero)" }}>
          {/* decorative bg circles */}
          <div className="pointer-events-none absolute -top-20 -right-20 h-64 w-64 rounded-full opacity-10" style={{ background: "var(--xanh-cyan)" }} />
          <div className="pointer-events-none absolute -bottom-16 -left-16 h-48 w-48 rounded-full opacity-10" style={{ background: "var(--xanh-mint)" }} />
          <div className="relative">
            <div className="inline-flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full bg-white/15 border border-white/25 mb-4">
              <Sparkles className="h-3.5 w-3.5" /> SOLUTION
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold mt-1 leading-tight">
              AI Quality Intelligence Platform
            </h2>
            <p className="mt-4 max-w-2xl opacity-90 text-sm sm:text-base leading-relaxed">
              Không chỉ là dashboard sentiment — đây là hệ thống{" "}
              <strong>khép kín từ dữ liệu đến hành động</strong>: phân loại tự động, phát hiện spike, sinh alert, tạo ticket theo SLA, và học liên tục qua correction log.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {CAPABILITIES.map((k) => (
                <span key={k} className="text-xs font-mono px-2.5 py-1 rounded-md bg-white/15 border border-white/25 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3 w-3 opacity-70" />{k}
                </span>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Workflow 7 bước */}
      <Card>
        <SectionHeader icon={Workflow} title="Quy trình 7 bước" subtitle="Từ raw feedback đến hành động cải tiến — khép kín" />
        <div className="p-5">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const isLast = i === STEPS.length - 1;
              return (
                <div key={s.t} className="relative">
                  <div className="rounded-xl border border-border bg-white p-4 h-full">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="h-8 w-8 rounded-lg bg-xanh-mint grid place-items-center flex-shrink-0">
                        <Icon className="h-4 w-4 text-xanh-deep" />
                      </div>
                      <span className="font-mono text-[10px] text-xanh-green font-bold">{s.num}</span>
                    </div>
                    <div className="font-display font-semibold text-sm">{s.t}</div>
                    <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{s.d}</div>
                  </div>
                  {!isLast && (
                    <ArrowRight className="hidden lg:block absolute -right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-xanh-green/50 z-10" />
                  )}
                </div>
              );
            })}
          </div>
          {/* loop annotation */}
          <div className="mt-4 flex items-center justify-center gap-2 text-xs font-mono text-muted-foreground">
            <span className="h-px w-8 bg-xanh-green/40" />
            Correction log → re-train → AI chính xác hơn theo thời gian
            <span className="h-px w-8 bg-xanh-green/40" />
          </div>
        </div>
      </Card>
    </div>
  );
}
