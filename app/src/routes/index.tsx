import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, type ComponentType } from "react";
import {
  Activity,
  ArrowRight,
  Bot,
  Cpu,
  Heart,
  MessageSquare,
  Shield,
  Sparkles,
  Star,
  TrendingUp,
  Zap,
  Radio,
  Eye,
  BarChart3,
  Compass,
  Quote,
  ChevronRight,
} from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import SupportChatWidget from "@/components/SupportChatWidget";
import heroPoster from "@/assets/hero-poster.jpg";
import posterPassenger from "@/assets/poster-passenger.jpg";
import posterDashboard from "@/assets/poster-dashboard.jpg";
import posterDriver from "@/assets/poster-driver.jpg";

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

const trend = Array.from({ length: 18 }).map((_, i) => ({
  d: i,
  v: 50 + Math.round(Math.sin(i / 1.6) * 22 + i * 2.4),
}));

const bigStats = [
  { value: "12.4K", label: "Phản hồi / ngày", sub: "+18% so với tuần trước", icon: MessageSquare },
  { value: "94.7%", label: "Độ chính xác AI", sub: "Sentiment + topic + urgency", icon: Cpu },
  { value: "< 2′", label: "Thời gian phản hồi", sub: "Trung bình toàn hệ thống", icon: Zap },
  { value: "96.2%", label: "Khách hài lòng", sub: "Đánh giá ≥ 4 sao", icon: Heart },
];

const features = [
  {
    icon: Radio,
    title: "Lắng nghe đa kênh",
    desc: "App, hotline, mạng xã hội, email — gom về một nơi.",
  },
  {
    icon: Bot,
    title: "AI phân loại tự động",
    desc: "Sentiment, chủ đề, mức ưu tiên trong vài giây.",
  },
  { icon: Eye, title: "Phát hiện bất thường", desc: "Cảnh báo sớm khi có đột biến phàn nàn." },
  { icon: BarChart3, title: "Dashboard trực quan", desc: "Biểu đồ, heatmap, leaderboard." },
  {
    icon: Shield,
    title: "Bảo mật & riêng tư",
    desc: "Mã hoá đầu cuối, tuân thủ chuẩn dữ liệu VN.",
  },
  { icon: Compass, title: "Đề xuất hành động", desc: "AI gợi ý kịch bản xử lý cho từng phản hồi." },
];

const testimonials = [
  {
    name: "Chị Linh",
    role: "Khách hàng thân thiết",
    quote: "Phản hồi của tôi được phản hồi lại trong chưa đầy 5 phút. Rất bất ngờ!",
    img: posterPassenger,
  },
  {
    name: "Anh Tuấn",
    role: "Tài xế xanhSM",
    quote: "Tôi biết được điểm cần cải thiện mỗi tuần qua dashboard cá nhân.",
    img: posterDriver,
  },
];

const liveFeed = [
  {
    time: "vừa xong",
    text: "Tài xế thân thiện, xe rất sạch sẽ ✨",
    sent: "positive",
    topic: "Thái độ",
  },
  {
    time: "1′ trước",
    text: "App tính phí hơi cao so với quãng đường",
    sent: "negative",
    topic: "Giá cước",
  },
  { time: "3′ trước", text: "Đặt xe nhanh, đến đúng giờ", sent: "positive", topic: "Đúng giờ" },
  {
    time: "5′ trước",
    text: "Tài xế chạy hơi nhanh ở khu dân cư",
    sent: "neutral",
    topic: "An toàn",
  },
];

function Landing() {
  return (
    <div className="min-h-screen text-foreground overflow-x-hidden">
      <Header />
      <PosterHero />
      <MarqueeBand />
      <BentoShowcase />
      <StatsPoster />
      <FeatureWall />
      <LiveAndTestimonial />
      <FinalCTA />
      <Footer />
      <SupportChatWidget publicOnly />
    </div>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/70 border-b border-border/50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-chart-2 grid place-items-center shadow-lg shadow-primary/30">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg tracking-tight">
            xanhSM <span className="text-primary">Cockpit</span>
          </span>
        </Link>
        <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
          <a href="#showcase" className="hover:text-foreground transition">
            Sản phẩm
          </a>
          <a href="#features" className="hover:text-foreground transition">
            Tính năng
          </a>
          <a href="#voices" className="hover:text-foreground transition">
            Khách hàng
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/auth">
            <Button variant="ghost" size="sm">
              Đăng nhập
            </Button>
          </Link>
          <Link to="/auth">
            <Button
              size="sm"
              className="bg-gradient-to-r from-primary to-chart-2 text-primary-foreground shadow-lg shadow-primary/30"
            >
              Bắt đầu <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}

function PosterHero() {
  return (
    <section className="relative">
      <div className="max-w-7xl mx-auto px-6 pt-10 pb-20">
        {/* Poster frame */}
        <div className="relative rounded-[2.5rem] overflow-hidden border border-border shadow-[0_30px_80px_-20px_rgba(0,180,200,0.45)]">
          <img
            src={heroPoster}
            alt="Xe điện xanhSM lao đi giữa thành phố"
            width={1600}
            height={1280}
            className="w-full h-[680px] object-cover scale-105"
          />
          {/* Cinematic scrims: dark bottom-left for headline legibility, cyan vignette right */}
          <div className="absolute inset-0 bg-gradient-to-tr from-[#03161c]/95 via-[#04222a]/55 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#02131a]/85 via-[#02131a]/10 to-transparent" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_85%_15%,rgba(63,201,214,0.35),transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_0%_100%,rgba(0,0,0,0.55),transparent_60%)]" />

          {/* Top-left tag */}
          <div className="absolute top-6 left-6 flex items-center gap-2 z-10">
            <span className="flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-2.5 w-2.5 rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
            </span>
            <span className="text-[11px] uppercase tracking-[0.28em] text-white/85 font-semibold drop-shadow">
              Live · xanhSM Cockpit · 2026
            </span>
          </div>

          {/* Top-right edition badge */}
          <div className="absolute top-6 right-6 hidden md:flex items-center gap-3 bg-black/40 backdrop-blur-md rounded-full px-4 py-2 border border-white/15 z-10">
            <span className="text-[10px] tracking-[0.3em] text-white/60">EDITION</span>
            <span className="font-bold text-white">Nº 06 / 27</span>
          </div>

          {/* Headline */}
          <div className="absolute left-6 md:left-12 bottom-10 right-6 md:right-12 z-10">
            <Badge className="mb-5 bg-primary/25 text-white border border-primary/50 backdrop-blur-md shadow-lg">
              Nền tảng lắng nghe khách hàng #1 cho vận tải xanh
            </Badge>
            <h1
              className="font-display font-extrabold tracking-tight text-white leading-[0.92] text-5xl md:text-7xl lg:text-[88px]"
              style={{ textShadow: "0 2px 24px rgba(0,0,0,0.55), 0 1px 0 rgba(0,0,0,0.35)" }}
            >
              Mỗi phản hồi <br />
              <span className="bg-gradient-to-r from-[#5EEAD4] via-[#22D3EE] to-[#67E8F9] bg-clip-text text-transparent drop-shadow-[0_2px_18px_rgba(34,211,238,0.35)]">
                là một chuyến đi tốt hơn.
              </span>
            </h1>
            <p
              className="mt-6 max-w-2xl text-base md:text-lg text-white/90"
              style={{ textShadow: "0 1px 12px rgba(0,0,0,0.6)" }}
            >
              Cockpit gom phản hồi từ mọi kênh, dùng AI phân loại trong vài giây, và biến chúng
              thành hành động — để khách hàng, tài xế và đội vận hành cùng đi nhanh hơn.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/auth">
                <Button
                  size="lg"
                  className="h-12 px-7 bg-gradient-to-r from-primary to-chart-2 text-primary-foreground shadow-xl shadow-primary/40"
                >
                  Trải nghiệm miễn phí <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
              <Link to="/auth">
                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 px-7 bg-white/10 hover:bg-white/20 backdrop-blur-md border-white/25 text-white"
                >
                  Mở workspace <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Floating stat cards */}
          <div className="hidden lg:block absolute right-10 top-1/2 -translate-y-1/2 space-y-4">
            <FloatCard icon={MessageSquare} value="12,418" label="Phản hồi hôm nay" />
            <FloatCard icon={TrendingUp} value="+18.4%" label="Hài lòng / tuần" accent />
            <FloatCard icon={Activity} value="0.9s" label="Phân loại AI" />
          </div>
        </div>
      </div>
    </section>
  );
}

function FloatCard({
  icon: Icon,
  value,
  label,
  accent,
}: {
  icon: ComponentType<{ className?: string }>;
  value: string;
  label: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-3 bg-background/85 backdrop-blur-xl border border-border rounded-2xl pl-3 pr-5 py-3 shadow-2xl shadow-primary/20 ${accent ? "ring-2 ring-primary/50" : ""}`}
    >
      <div className="w-10 h-10 rounded-xl bg-primary/15 grid place-items-center">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <div>
        <div className="font-extrabold text-lg leading-none">{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{label}</div>
      </div>
    </div>
  );
}

function MarqueeBand() {
  const items = [
    "Real-time AI",
    "Sentiment 94.7%",
    "12K+ phản hồi / ngày",
    "−42% phàn nàn lặp",
    "5× nhanh hơn",
    "24/7 cảnh báo",
    "Bảo mật chuẩn VN",
  ];
  return (
    <div className="relative bg-gradient-to-r from-primary via-chart-2 to-primary py-4 overflow-hidden border-y border-primary/30">
      <div className="flex gap-12 animate-[marquee_30s_linear_infinite] whitespace-nowrap font-bold text-primary-foreground text-lg tracking-wide">
        {[...items, ...items, ...items].map((t, i) => (
          <span key={i} className="flex items-center gap-12">
            {t} <Sparkles className="w-4 h-4" />
          </span>
        ))}
      </div>
      <style>{`@keyframes marquee { from { transform: translateX(0) } to { transform: translateX(-50%) } }`}</style>
    </div>
  );
}

function BentoShowcase() {
  return (
    <section id="showcase" className="max-w-7xl mx-auto px-6 py-24">
      <div className="flex items-end justify-between flex-wrap gap-6 mb-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-primary font-bold mb-3">
            ▌ Sản phẩm
          </p>
          <h2 className="text-4xl md:text-6xl font-black tracking-tight max-w-2xl leading-[1.05]">
            Một bảng điều khiển,{" "}
            <span className="bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent">
              vô hạn cảm hứng.
            </span>
          </h2>
        </div>
        <p className="text-muted-foreground max-w-md">
          Mọi mô-đun được thiết kế cho người Việt — gõ tiếng Việt, đọc tiếng Việt, hành động bằng
          tiếng Việt.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Big visual card */}
        <div className="col-span-12 lg:col-span-7 relative rounded-3xl overflow-hidden border border-border bg-card group">
          <img
            src={posterDashboard}
            alt="Dashboard AI"
            loading="lazy"
            width={1200}
            height={900}
            className="w-full h-[420px] object-cover group-hover:scale-105 transition duration-700"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/30 to-transparent" />
          <div className="absolute bottom-0 p-8">
            <Badge className="bg-primary/20 text-primary border-primary/40 mb-3">AI Cockpit</Badge>
            <h3 className="text-3xl font-black mb-2">Mọi chỉ số. Một cái nhìn.</h3>
            <p className="text-muted-foreground max-w-md">
              Heatmap khu vực, trend cảm xúc, top complaint — cập nhật mỗi 30 giây.
            </p>
          </div>
        </div>

        {/* Mini trend card */}
        <div className="col-span-12 md:col-span-6 lg:col-span-5 rounded-3xl border border-border bg-gradient-to-br from-card to-secondary/30 p-7 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs uppercase tracking-widest text-muted-foreground font-bold">
              Phản hồi 24h
            </span>
            <Badge className="bg-success/15 text-foreground border border-success/40">▲ 18%</Badge>
          </div>
          <div className="text-5xl font-black mb-2">12,418</div>
          <div className="text-sm text-muted-foreground mb-4">
            Tự động phân loại bởi AI — không cần can thiệp.
          </div>
          <div className="flex-1 min-h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.78 0.12 200)" stopOpacity={0.7} />
                    <stop offset="100%" stopColor="oklch(0.78 0.12 200)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Tooltip
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke="oklch(0.78 0.12 200)"
                  strokeWidth={3}
                  fill="url(#g1)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentiment poster card */}
        <div className="col-span-12 md:col-span-6 lg:col-span-4 rounded-3xl border border-border overflow-hidden relative bg-card">
          <img
            src={posterPassenger}
            alt="Khách hàng"
            loading="lazy"
            width={900}
            height={1200}
            className="w-full h-[360px] object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
          <div className="absolute bottom-0 p-6">
            <div className="flex gap-1 mb-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-warning text-warning" />
              ))}
            </div>
            <h4 className="font-bold text-lg leading-tight">
              "Tôi cảm thấy được lắng nghe — và xe đến đúng 2 phút sau."
            </h4>
            <p className="text-sm text-muted-foreground mt-2">— Linh, Quận 1</p>
          </div>
        </div>

        {/* Numbers card */}
        <div className="col-span-12 md:col-span-6 lg:col-span-4 rounded-3xl border border-border bg-foreground text-background p-7 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full bg-primary/40 blur-3xl" />
          <p className="text-xs uppercase tracking-widest text-background/70 font-bold">Tác động</p>
          <div className="mt-4 text-7xl font-black tracking-tight bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent">
            −42%
          </div>
          <p className="mt-2 font-semibold">Phàn nàn lặp lại sau 90 ngày</p>
          <p className="text-sm text-background/70 mt-3">
            Nhờ AI đề xuất hành động ngay khi phát hiện vấn đề.
          </p>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div>
              <div className="text-2xl font-bold">5×</div>
              <div className="text-xs text-background/60">Xử lý nhanh hơn</div>
            </div>
            <div>
              <div className="text-2xl font-bold">24/7</div>
              <div className="text-xs text-background/60">Giám sát liên tục</div>
            </div>
          </div>
        </div>

        {/* Driver poster */}
        <div className="col-span-12 lg:col-span-4 rounded-3xl border border-border overflow-hidden relative">
          <img
            src={posterDriver}
            alt="Tài xế"
            loading="lazy"
            width={900}
            height={1100}
            className="w-full h-[360px] object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/60 via-transparent to-transparent mix-blend-multiply" />
          <div className="absolute bottom-0 p-6 text-foreground">
            <Badge className="bg-background/80 text-foreground border-border mb-2">Tài xế</Badge>
            <h4 className="text-xl font-bold leading-tight">
              "Mỗi tuần tôi biết mình cần cải thiện điều gì."
            </h4>
            <p className="text-sm text-foreground/80 mt-2">— Tuấn, tài xế 4.9★</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function StatsPoster() {
  return (
    <section className="bg-gradient-to-b from-transparent via-secondary/40 to-transparent py-20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          {bigStats.map((s, i) => (
            <div
              key={i}
              className="relative rounded-3xl bg-card border border-border p-7 overflow-hidden group hover:-translate-y-1 transition"
            >
              <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/30 transition" />
              <s.icon className="w-7 h-7 text-primary mb-5" />
              <div className="text-5xl font-black tracking-tight">{s.value}</div>
              <div className="mt-2 font-semibold">{s.label}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureWall() {
  return (
    <section id="features" className="max-w-7xl mx-auto px-6 py-24">
      <div className="text-center mb-14">
        <p className="text-xs uppercase tracking-[0.3em] text-primary font-bold mb-3">
          ▌ Tính năng
        </p>
        <h2 className="text-4xl md:text-6xl font-black tracking-tight">
          Được dựng bằng{" "}
          <span className="bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent">
            trí tuệ thật.
          </span>
        </h2>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        {features.map((f, i) => (
          <div
            key={i}
            className="group relative rounded-3xl p-7 bg-card border border-border overflow-hidden hover:border-primary/60 transition"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/0 to-primary/0 group-hover:from-primary/10 group-hover:to-chart-2/10 transition" />
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-chart-2 grid place-items-center mb-5 shadow-lg shadow-primary/30">
                <f.icon className="w-7 h-7 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-bold mb-2">{f.title}</h3>
              <p className="text-muted-foreground">{f.desc}</p>
              <div className="mt-5 flex items-center text-primary text-sm font-semibold opacity-0 group-hover:opacity-100 transition">
                Tìm hiểu <ChevronRight className="w-4 h-4 ml-1" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function LiveAndTestimonial() {
  const [items, setItems] = useState(liveFeed);
  useEffect(() => {
    const id = setInterval(() => {
      setItems((prev) => [
        {
          time: "vừa xong",
          text: [
            "Xe sạch, tài xế lịch sự",
            "Ứng dụng dễ dùng",
            "Cần thêm điểm đón gần trung tâm",
            "Tài xế tới sớm hơn dự kiến",
          ][Math.floor(Math.random() * 4)],
          sent: ["positive", "positive", "neutral", "positive"][Math.floor(Math.random() * 4)],
          topic: ["Thái độ", "UX", "Vị trí", "Đúng giờ"][Math.floor(Math.random() * 4)],
        },
        ...prev
          .slice(0, 3)
          .map((i) => ({ ...i, time: i.time === "vừa xong" ? "1′ trước" : i.time })),
      ]);
    }, 3500);
    return () => clearInterval(id);
  }, []);

  return (
    <section id="live" className="max-w-7xl mx-auto px-6 py-24 grid lg:grid-cols-5 gap-8">
      <div className="lg:col-span-3">
        <p className="text-xs uppercase tracking-[0.3em] text-primary font-bold mb-3">
          ▌ Live feed
        </p>
        <h2 className="text-3xl md:text-5xl font-black mb-3">
          Phản hồi đang chảy về <span className="text-primary">ngay lúc này.</span>
        </h2>
        <p className="text-muted-foreground mb-7 max-w-lg">
          AI phân loại cảm xúc và chủ đề trong dưới một giây — đội vận hành nhìn thấy ngay.
        </p>
        <div className="rounded-3xl border border-border bg-card p-3">
          <div className="space-y-2">
            {items.map((it, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-4 rounded-2xl bg-secondary/40 hover:bg-secondary/70 transition animate-fade-in"
              >
                <div
                  className={`w-2 h-12 rounded-full ${it.sent === "positive" ? "bg-success" : it.sent === "negative" ? "bg-destructive" : "bg-warning"}`}
                />
                <div className="flex-1">
                  <div className="text-sm font-medium">{it.text}</div>
                  <div className="flex gap-2 mt-1.5 items-center">
                    <Badge variant="outline" className="text-xs">
                      {it.topic}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{it.time}</span>
                  </div>
                </div>
                <Badge
                  className={`${it.sent === "positive" ? "bg-success/20 text-foreground" : it.sent === "negative" ? "bg-destructive/20 text-destructive" : "bg-warning/20 text-foreground"} border-0`}
                >
                  {it.sent === "positive"
                    ? "Tích cực"
                    : it.sent === "negative"
                      ? "Tiêu cực"
                      : "Trung tính"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div id="voices" className="lg:col-span-2 space-y-5">
        <p className="text-xs uppercase tracking-[0.3em] text-primary font-bold mb-3">
          ▌ Tiếng nói
        </p>
        {testimonials.map((t, i) => (
          <div
            key={i}
            className="relative rounded-3xl overflow-hidden border border-border bg-card"
          >
            <img src={t.img} alt={t.name} loading="lazy" className="w-full h-48 object-cover" />
            <div className="p-6">
              <Quote className="w-6 h-6 text-primary mb-2" />
              <p className="font-semibold text-lg leading-snug">{t.quote}</p>
              <div className="mt-4 flex items-center justify-between">
                <div>
                  <div className="font-bold">{t.name}</div>
                  <div className="text-xs text-muted-foreground">{t.role}</div>
                </div>
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }).map((_, k) => (
                    <Star key={k} className="w-4 h-4 fill-warning text-warning" />
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section className="max-w-7xl mx-auto px-6 py-20">
      <div className="relative rounded-[2.5rem] overflow-hidden p-12 md:p-20 text-center border border-border bg-gradient-to-br from-primary via-chart-2 to-chart-5">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.3),transparent_60%)]" />
        <div className="relative">
          <Badge className="bg-background/90 text-foreground border-0 mb-6">
            Bắt đầu trong 60 giây
          </Badge>
          <h2 className="text-4xl md:text-6xl font-black text-primary-foreground leading-[1.05] max-w-3xl mx-auto">
            Đừng đoán điều khách hàng muốn. <br />
            Hãy <span className="italic">nghe</span> họ nói.
          </h2>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link to="/auth">
              <Button
                size="lg"
                className="h-13 px-8 bg-background text-foreground hover:bg-background/90"
              >
                Tạo tài khoản miễn phí <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
            <Link to="/auth">
              <Button
                size="lg"
                variant="outline"
                className="h-13 px-8 bg-transparent text-primary-foreground border-primary-foreground/40 hover:bg-primary-foreground/10"
              >
                Xem dashboard mẫu
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border mt-10">
      <div className="max-w-7xl mx-auto px-6 py-10 flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-chart-2 grid place-items-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-bold text-foreground">xanhSM Cockpit</span> · © 2026
        </div>
        <div className="flex gap-6">
          <a href="#" className="hover:text-foreground">
            Điều khoản
          </a>
          <a href="#" className="hover:text-foreground">
            Bảo mật
          </a>
          <a href="#" className="hover:text-foreground">
            Liên hệ
          </a>
        </div>
      </div>
    </footer>
  );
}
