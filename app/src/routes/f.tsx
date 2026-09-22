// Trang gửi phản hồi KHÔNG cần đăng nhập (US-076 / decision 0016).
//
// Nằm ngoài cây `_authenticated` một cách có chủ đích: khách đi xanhSM vừa gặp
// sự cố cần báo trong vài chục giây, không phải đăng ký tài khoản trước. QR dán
// trên xe trỏ thẳng vào URL này.
//
// Dùng `publicFetch` chứ không phải `apiFetch`: trang này phải hành xử giống hệt
// nhau dù người mở có đang đăng nhập hay không.
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, Copy, Send, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { publicFetch } from "@/lib/api";
import { AREAS } from "@/lib/regions";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const MAX_TEXT = 4000;
const CHANNELS = ["Ứng dụng", "Hotline", "Website", "Mạng xã hội"];

type SubmitResult = { public_ref: string; status: string; created_at: string | null };

export const Route = createFileRoute("/f")({
  head: () => ({
    meta: [
      { title: "Gửi phản hồi nhanh — xanhSM" },
      {
        name: "description",
        content:
          "Báo sự cố hoặc gửi phản hồi về chuyến đi xanhSM ngay, không cần đăng nhập. Nhận mã tra cứu để theo dõi tiến độ xử lý.",
      },
    ],
  }),
  component: PublicFeedbackPage,
});

function PublicFeedbackPage() {
  const [text, setText] = useState("");
  const [channel, setChannel] = useState(CHANNELS[0]);
  const [area, setArea] = useState(AREAS[0].code);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = text.trim();
    if (!body) {
      toast.error("Vui lòng nhập nội dung phản hồi");
      return;
    }
    setSubmitting(true);
    try {
      const json = await publicFetch<{ data: SubmitResult }>("/api/public/feedback", {
        method: "POST",
        body: JSON.stringify({ text: body, channel, area }),
      });
      setResult(json.data);
      setText("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không gửi được phản hồi");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <Shell>
        <Card className="space-y-5 p-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-emerald-600" />
            <div>
              <h1 className="text-lg font-semibold">Đã nhận phản hồi của bạn</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Phản hồi đã vào hệ thống và đang được phân loại tự động tới đội phụ trách.
              </p>
            </div>
          </div>

          <div className="rounded-xl border bg-muted/40 p-4">
            <Label className="text-xs text-muted-foreground">Mã tra cứu của bạn</Label>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <code className="rounded-lg bg-background px-3 py-2 font-mono text-base tracking-wider">
                {result.public_ref}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  navigator.clipboard
                    ?.writeText(result.public_ref)
                    .then(() => toast.success("Đã sao chép mã"))
                    .catch(() => toast.error("Không sao chép được, vui lòng chép tay"));
                }}
              >
                <Copy className="h-3.5 w-3.5" /> Sao chép
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Hãy lưu lại mã này. Đây là cách duy nhất để xem tiến độ xử lý — chúng tôi không gửi
              email hay tin nhắn, và cũng không lưu danh tính của bạn.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link to="/f/status/$code" params={{ code: result.public_ref }}>
                Xem tiến độ xử lý
              </Link>
            </Button>
            <Button variant="outline" onClick={() => setResult(null)}>
              Gửi phản hồi khác
            </Button>
          </div>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <Card className="p-6">
        <h1 className="text-lg font-semibold">Gửi phản hồi nhanh</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Không cần tài khoản, không cần đăng nhập. Mô tả việc đang xảy ra và gửi.
        </p>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <div>
            <Label className="mb-2 block text-xs text-muted-foreground">Chuyện gì đã xảy ra?</Label>
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, MAX_TEXT))}
              rows={6}
              autoFocus
              placeholder="VD: Tài xế vượt đèn đỏ và phóng rất nhanh trên đường Nguyễn Trãi lúc 19h tối nay."
            />
            <p className="mt-1.5 text-right text-xs text-muted-foreground">
              {text.length}/{MAX_TEXT}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <Label className="mb-2 block text-xs text-muted-foreground">Kênh</Label>
              <Select value={channel} onValueChange={setChannel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHANNELS.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-2 block text-xs text-muted-foreground">Khu vực</Label>
              <Select value={area} onValueChange={setArea}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AREAS.map((a) => (
                    <SelectItem key={a.code} value={a.code}>
                      {a.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-start gap-2 rounded-lg border border-amber-200/60 bg-amber-50/60 p-3 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Số điện thoại, email và biển số trong nội dung sẽ được tự động che trước khi lưu. Nếu
              đang có nguy hiểm tức thời, hãy gọi cơ quan chức năng trước.
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <Button type="submit" disabled={submitting} className="gap-2">
              <Send className="h-4 w-4" /> {submitting ? "Đang gửi..." : "Gửi ngay"}
            </Button>
          </div>
        </form>
      </Card>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-10 md:py-16">
      {children}
      <p className="mt-6 text-center text-xs text-muted-foreground">
        <Link to="/" className="underline">
          xanhSM Quality Intelligence
        </Link>
      </p>
    </main>
  );
}
