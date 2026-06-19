import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Loader2, Play, RefreshCw, RotateCcw, Square } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";

export type LiveStreamStatus = {
  running: boolean;
  offset: number;
  batch_size: number;
  interval_seconds: number;
  loop: boolean;
  auto_ticket: boolean;
  ticket_every_batches: number;
  batches_ingested: number;
  ticket_running: boolean;
  last_result: { inserted: number; skipped: number; complete: boolean } | null;
  last_error: string | null;
  last_ticket_at: string | null;
  last_ticket_result: unknown;
  last_ticket_error: string | null;
};

export default function LiveStreamPanel() {
  const qc = useQueryClient();
  const [batchSize, setBatchSize] = useState(150);
  const [interval, setIntervalSec] = useState(10);
  const [loop, setLoop] = useState(false);
  const [reset, setReset] = useState(true);
  const [autoTicket, setAutoTicket] = useState(true);
  const [ticketEvery, setTicketEvery] = useState(10);

  const statusQuery = useQuery({
    queryKey: ["live-stream-status"],
    queryFn: async () => {
      const json = await apiFetch<{ data: LiveStreamStatus }>("/api/live-stream/status");
      return json.data;
    },
    refetchInterval: 5_000,
  });

  const s = statusQuery.data;
  const isRunning = s?.running ?? false;
  const isComplete = Boolean(s?.last_result?.complete && !isRunning);

  useEffect(() => {
    if (s?.last_result?.complete && !isRunning) setReset(true);
  }, [s?.last_result?.complete, isRunning]);

  const startMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        batch_size: String(clamp(batchSize, 1, 500)),
        interval_seconds: String(clamp(interval, 1, 3600)),
        loop: String(loop),
        reset: String(reset || isComplete),
        auto_ticket: String(autoTicket),
        ticket_every_batches: String(clamp(ticketEvery, 1, 100)),
      });
      const json = await apiFetch<{ data: LiveStreamStatus }>(`/api/live-stream/start?${params}`, {
        method: "POST",
      });
      return json.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["live-stream-status"], data);
      toast.success("Live stream đã bật");
      qc.invalidateQueries({ queryKey: ["live-stream-status"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Không thể bật live stream"),
  });

  const stopMutation = useMutation({
    mutationFn: async () => {
      const json = await apiFetch<{ data: LiveStreamStatus }>("/api/live-stream/stop", {
        method: "POST",
      });
      return json.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["live-stream-status"], data);
      toast.success("Live stream đã tắt");
      qc.invalidateQueries({ queryKey: ["live-stream-status"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Không thể tắt live stream"),
  });

  const isBusy = statusQuery.isFetching || startMutation.isPending || stopMutation.isPending;

  return (
    <div className="space-y-5">
      <div
        className={`rounded-xl border p-4 flex flex-wrap items-center gap-4 ${
          isRunning ? "border-emerald-200 bg-emerald-50" : "border-gray-200 bg-gray-50"
        }`}
      >
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              isRunning ? "bg-emerald-500 animate-pulse" : "bg-gray-400"
            }`}
          />
          <span className="text-sm font-semibold">{isRunning ? "Đang chạy" : "Đã dừng"}</span>
        </div>
        {s && (
          <>
            <span className="text-xs text-muted-foreground">
              Batch {s.batches_ingested} · offset {s.offset}
            </span>
            {s.last_result && (
              <span className="text-xs text-muted-foreground">
                Batch cuối: +{s.last_result.inserted} inserted, {s.last_result.skipped} skipped
                {s.last_result.complete && " · Hết data"}
              </span>
            )}
            {s.last_error && (
              <span className="text-xs text-red-600 font-mono">Lỗi: {s.last_error}</span>
            )}
          </>
        )}
        <button
          type="button"
          onClick={() => qc.invalidateQueries({ queryKey: ["live-stream-status"] })}
          className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Tải lại trạng thái live stream"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>

      {isComplete && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          Dataset đã chạy tới cuối. Lần bật tiếp theo sẽ reset offset về 0 để stream có dữ liệu.
        </div>
      )}

      <div className="rounded-xl border border-border bg-white p-5 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Cấu hình
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <NumberField
            label="Batch size"
            min={1}
            max={500}
            value={batchSize}
            disabled={isRunning}
            onChange={setBatchSize}
          />
          <NumberField
            label="Interval (giây)"
            min={1}
            max={3600}
            value={interval}
            disabled={isRunning}
            onChange={setIntervalSec}
          />
          <NumberField
            label="Ticket mỗi N batch"
            min={1}
            max={100}
            value={ticketEvery}
            disabled={isRunning}
            onChange={setTicketEvery}
          />
        </div>
        <div className="flex flex-wrap gap-4">
          <CheckboxField
            label="Lặp lại (loop)"
            checked={loop}
            disabled={isRunning}
            onChange={setLoop}
          />
          <CheckboxField
            label="Tự tạo ticket"
            checked={autoTicket}
            disabled={isRunning}
            onChange={setAutoTicket}
          />
          <CheckboxField
            label="Reset offset khi bật"
            checked={reset}
            disabled={isRunning || isComplete}
            onChange={setReset}
          />
        </div>

        <div className="flex items-center gap-3 pt-1">
          {!isRunning ? (
            <button
              type="button"
              disabled={isBusy}
              onClick={() => startMutation.mutate()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Bật Live Stream
            </button>
          ) : (
            <button
              type="button"
              disabled={isBusy}
              onClick={() => stopMutation.mutate()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              Dừng Live Stream
            </button>
          )}
          {!isRunning && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <RotateCcw className="h-3 w-3" />
              {reset || isComplete ? "Sẽ reset offset về 0 khi bật" : "Tiếp tục từ offset hiện tại"}
            </span>
          )}
        </div>
      </div>

      {s?.last_ticket_at && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm space-y-1">
          <div className="font-semibold text-blue-800 flex items-center gap-2">
            <Activity className="h-4 w-4" /> Spike Detection cuối
          </div>
          <div className="text-xs text-blue-700">
            {new Date(s.last_ticket_at).toLocaleString("vi-VN")}
            {s.ticket_running && (
              <span className="ml-2 text-blue-500 animate-pulse">· đang chạy...</span>
            )}
          </div>
          {s.last_ticket_error && (
            <div className="text-xs text-red-600 font-mono">Lỗi: {s.last_ticket_error}</div>
          )}
        </div>
      )}
    </div>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className="space-y-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(clamp(Number(e.target.value), min, max))}
        disabled={disabled}
        className="w-full h-8 px-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-xanh-green/40 disabled:opacity-50"
      />
    </label>
  );
}

function CheckboxField({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="rounded border-gray-300 text-xanh-green focus:ring-xanh-green/40"
      />
      {label}
    </label>
  );
}

function clamp(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}
