// Tra cứu tiến độ một phản hồi ẩn danh bằng mã (US-076 / decision 0016).
//
// Mã là thứ duy nhất chứng minh quyền xem — không có tài khoản nào để kiểm.
// Backend chỉ trả về đúng 5 trường và không trả lại nội dung đã gửi, nên một mã
// lọt ra ngoài cũng không làm lộ nội dung phản hồi.
import { useCallback, useEffect, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Clock, Loader2, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { publicFetch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

type PublicStatus = {
  public_ref: string;
  status: "received" | "under_review" | "resolved";
  created_at: string | null;
  topic: string | null;
  severity: string | null;
};

const STATUS_LABEL: Record<PublicStatus["status"], string> = {
  received: "Đã tiếp nhận",
  under_review: "Đang xem xét",
  resolved: "Đã xử lý",
};

export const Route = createFileRoute("/f_/status/$code")({
  head: () => ({
    meta: [{ title: "Tra cứu phản hồi — xanhSM" }],
  }),
  component: PublicStatusPage,
});

function PublicStatusPage() {
  const { code } = Route.useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState(code);
  const [data, setData] = useState<PublicStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const lookup = useCallback(async (ref: string) => {
    setLoading(true);
    setError(null);
    try {
      const json = await publicFetch<{ data: PublicStatus }>(
        `/api/public/feedback/${encodeURIComponent(ref)}`,
      );
      setData(json.data);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Không tra cứu được");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setInput(code);
    if (code) void lookup(code);
    else setData(null);
  }, [code, lookup]);

  function search(e: React.FormEvent) {
    e.preventDefault();
    const ref = input.trim();
    if (!ref) return;
    if (ref !== code) void navigate({ to: "/f/status/$code", params: { code: ref } });
    else void lookup(ref);
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-10 md:py-16">
      <Card className="space-y-5 p-6">
        <div>
          <h1 className="text-lg font-semibold">Tra cứu phản hồi</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Nhập mã bạn nhận được sau khi gửi. Không cần đăng nhập.
          </p>
        </div>

        <form onSubmit={search} className="flex flex-wrap items-end gap-2">
          <div className="min-w-[12rem] flex-1">
            <Label className="mb-2 block text-xs text-muted-foreground">Mã tra cứu</Label>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="VD: 8kQ2rT7xLm4A"
              className="font-mono"
            />
          </div>
          <Button type="submit" disabled={loading || !input.trim()} className="gap-2">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Tra cứu
          </Button>
        </form>

        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {data && (
          <div className="space-y-4 rounded-xl border bg-muted/40 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span className="font-medium">{STATUS_LABEL[data.status]}</span>
              {data.severity && <Badge variant="outline">{data.severity}</Badge>}
              {data.topic && <Badge variant="secondary">{data.topic}</Badge>}
            </div>

            {data.created_at && (
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                Gửi lúc {new Date(data.created_at).toLocaleString("vi-VN")}
              </p>
            )}

            <p className="text-xs text-muted-foreground">
              Trang này chỉ hiển thị tiến độ. Nội dung bạn đã gửi không được trả lại ở đây, để một
              mã bị lộ cũng không làm lộ phản hồi.
            </p>

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={loading}
              onClick={() => void lookup(data.public_ref)}
            >
              <RefreshCw className="h-3.5 w-3.5" /> Làm mới
            </Button>
          </div>
        )}
      </Card>

      <p className="mt-6 text-center text-xs text-muted-foreground">
        <Link to="/f" className="underline">
          Gửi phản hồi mới
        </Link>
      </p>
    </main>
  );
}
