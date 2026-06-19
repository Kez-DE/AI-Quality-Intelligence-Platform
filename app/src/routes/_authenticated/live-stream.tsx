import { createFileRoute } from "@tanstack/react-router";
import { Radio } from "lucide-react";
import LiveStreamPanel from "@/components/LiveStreamPanel";
import { useMe } from "@/lib/api";

export const Route = createFileRoute("/_authenticated/live-stream")({
  component: LiveStreamPage,
});

function LiveStreamPage() {
  const { data: me } = useMe();

  if (me && me.role !== "admin") {
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Radio className="h-7 w-7 text-xanh-green" />
          Live Stream
        </h1>
        <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 px-6 py-12 text-center text-sm text-muted-foreground">
          Live Stream là thao tác toàn hệ thống, chỉ dành cho quản trị viên.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div
          className="h-11 w-11 rounded-2xl grid place-items-center text-white shadow-[var(--shadow-green)]"
          style={{ background: "var(--gradient-green)" }}
        >
          <Radio className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground">Live Stream</h1>
          <p className="text-sm text-muted-foreground">
            Bật/tắt luồng ingest phản hồi demo và cấu hình auto ticket.
          </p>
        </div>
      </div>

      <LiveStreamPanel />
    </div>
  );
}
