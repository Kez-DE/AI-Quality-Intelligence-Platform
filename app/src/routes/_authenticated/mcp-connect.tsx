import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Plug, Copy, Check, Loader2, ShieldAlert, Info } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, useMe, ROLE_LABELS } from "@/lib/api";

export const Route = createFileRoute("/_authenticated/mcp-connect")({
  component: McpConnectPage,
});

type McpTokenResponse = {
  token: string;
  url: string;
  connect_command: string;
  note: string;
};

function McpConnectPage() {
  const { data: me } = useMe();
  const [copiedField, setCopiedField] = useState<"token" | "command" | null>(null);

  const mutation = useMutation({
    mutationFn: () => apiFetch<{ data: McpTokenResponse }>("/api/mcp/token", { method: "POST" }),
    onError: (err: Error) => toast.error(err.message || "Không tạo được token MCP"),
  });

  const result = mutation.data?.data;

  const copy = async (field: "token" | "command", text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      toast.success("Đã sao chép");
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      toast.error("Không sao chép được — hãy chọn và copy thủ công");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <div
          className="h-11 w-11 rounded-2xl grid place-items-center text-white shrink-0"
          style={{ background: "var(--gradient-green)" }}
        >
          <Plug className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">Kết nối MCP</h1>
          <p className="text-sm text-muted-foreground">
            Dùng Claude (hoặc client MCP khác) truy vấn dữ liệu chất lượng dịch vụ trực tiếp — không cần cài gì ở máy chủ.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border bg-card p-5 space-y-4">
        <div className="flex items-start gap-2.5 rounded-xl bg-muted/50 p-3 text-sm text-muted-foreground">
          <Info className="h-4 w-4 mt-0.5 shrink-0" />
          <p>
            Token gắn với tài khoản của bạn ({me?.email}) — quyền truy cập theo đúng vai trò
            <span className="font-medium text-foreground"> {me?.role ? ROLE_LABELS[me.role] : ""}</span>
            {me?.department ? <> và phòng <span className="font-medium text-foreground">{me.department}</span></> : null}
            {" "}hiện tại. Nếu quản trị viên đổi quyền của bạn sau này, token này tự cập nhật theo — không cần lấy token mới.
          </p>
        </div>

        {!me?.department && me?.role !== "admin" && me?.role !== "guest" && (
          <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
            <p>Tài khoản của bạn chưa được gán phòng ban — token sẽ chỉ gửi được phản hồi (như khách) cho tới khi admin gán phòng.</p>
          </div>
        )}

        {!result ? (
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary text-primary-foreground px-4 py-3 text-sm font-medium transition hover:opacity-90 disabled:opacity-60"
          >
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plug className="h-4 w-4" />}
            Tạo token kết nối MCP
          </button>
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              {result.note}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Token (chỉ hiện một lần)</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded-lg border bg-muted px-3 py-2 text-xs font-mono">
                  {result.token}
                </code>
                <button
                  onClick={() => copy("token", result.token)}
                  className="shrink-0 rounded-lg border p-2 hover:bg-muted"
                  aria-label="Sao chép token"
                >
                  {copiedField === "token" ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Câu lệnh kết nối Claude Code / Claude Desktop</label>
              <div className="flex items-start gap-2">
                <code className="flex-1 whitespace-pre-wrap break-all rounded-lg border bg-muted px-3 py-2 text-xs font-mono">
                  {result.connect_command}
                </code>
                <button
                  onClick={() => copy("command", result.connect_command)}
                  className="shrink-0 rounded-lg border p-2 hover:bg-muted"
                  aria-label="Sao chép câu lệnh"
                >
                  {copiedField === "command" ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Dán lệnh trên vào terminal nơi bạn chạy Claude Code (hoặc thêm tương ứng vào cấu hình Claude Desktop).
              </p>
            </div>

            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="text-xs text-muted-foreground underline hover:text-foreground disabled:opacity-60"
            >
              Tạo token mới (token cũ vẫn còn hiệu lực trừ khi bị thu hồi)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
