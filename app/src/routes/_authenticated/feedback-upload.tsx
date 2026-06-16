import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { REGIONS } from "@/lib/regions";

const CHANNELS = [
  { value: "app", label: "Ứng dụng (App)" },
  { value: "hotline", label: "Hotline" },
  { value: "survey", label: "Khảo sát" },
  { value: "social", label: "Mạng xã hội" },
];

export const Route = createFileRoute("/_authenticated/feedback-upload")({
  component: FeedbackUploadPage,
});

function FeedbackUploadPage() {
  const [text, setText] = useState("");
  const [channel, setChannel] = useState("app");
  const [area, setArea] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) {
      toast.error("Vui lòng nhập nội dung phản hồi");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) {
        toast.error("Phiên đăng nhập hết hạn, vui lòng đăng nhập lại");
        return;
      }

      const backendUrl = (import.meta as any).env?.VITE_BACKEND_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/api/feedback/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: text.trim(), channel, area }),
      });

      const json = await res.json();
      if (!res.ok) {
        toast.error(json.detail || "Gửi phản hồi thất bại");
        return;
      }

      setResult(json.data);
      toast.success("Gửi phản hồi thành công! AI đã tự phân loại.");
      setText("");
      setArea("");
    } catch (err: any) {
      toast.error(`Lỗi kết nối: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Gửi phản hồi</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Nhập nội dung phản hồi. Hệ thống AI sẽ tự động phân loại chủ đề, cảm xúc và mức độ nghiêm trọng.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Nội dung phản hồi *</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Nhập phản hồi của bạn ở đây..."
            rows={5}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-xanh-deep/30"
            maxLength={2000}
          />
          <div className="text-xs text-muted-foreground mt-1">{text.length}/2000 ký tự</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Kênh gửi</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            >
              {CHANNELS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Khu vực</label>
            <select
              value={area}
              onChange={(e) => setArea(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
            >
              <option value="">-- Chọn khu vực --</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.label}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="w-full py-2.5 rounded-lg bg-xanh-deep text-white font-medium text-sm hover:bg-xanh-deep/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Đang gửi..." : "Gửi phản hồi"}
        </button>
      </form>

      {result && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-2">
          <h3 className="font-semibold text-green-800">✅ AI đã phân loại</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-muted-foreground">Chủ đề:</span> <strong>{result.topic}</strong></div>
            <div><span className="text-muted-foreground">Cảm xúc:</span> <strong>{result.sentiment}</strong></div>
            <div><span className="text-muted-foreground">Mức độ:</span> <strong>{result.severity}</strong></div>
            <div><span className="text-muted-foreground">Độ tin cậy:</span> <strong>{Math.round((result.confidence || 0) * 100)}%</strong></div>
          </div>
          {result.needs_review && (
            <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 mt-2">
              ⚠️ Phản hồi này cần nhân viên duyệt lại ({result.review_reason})
            </p>
          )}
        </div>
      )}
    </div>
  );
}
