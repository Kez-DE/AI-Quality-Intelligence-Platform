import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import {
  Headphones,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  MessageSquare,
  Send,
  MapPin,
  ShieldAlert,
  ChevronRight,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { useMe, apiFetch } from "@/lib/api";
import { regionLabel } from "@/lib/regions";

export const Route = createFileRoute("/_authenticated/support")({
  component: SupportPage,
});

type Task = {
  id: string;
  title: string;
  summary: string | null;
  assigned_team: string;
  topic: string | null;
  area: string | null;
  priority: string;
  status: string;
  owner_id: string | null;
  owner_email: string | null;
  due_at: string | null;
  created_at: string;
};

type Alert = {
  id: string;
  title: string;
  severity: string;
  status: string;
  task_id: string;
  created_at: string;
};

const CANNED_RESPONSES = [
  { id: "c1", title: "Xin lỗi & Sẽ xử lý", text: "XanhSM chân thành xin lỗi vì trải nghiệm không tốt của bạn. Chúng tôi đã ghi nhận phản hồi và đang tiến hành xử lý ngay lập tức." },
  { id: "c2", title: "Cảm ơn đóng góp", text: "Cảm ơn bạn đã đóng góp ý kiến. XanhSM luôn nỗ lực cải thiện dịch vụ mỗi ngày." },
  { id: "c3", title: "Kiểm tra tài xế", text: "Chúng tôi đã ghi nhận thông tin và sẽ tiến hành xác minh với tài xế. Cảm ơn bạn đã báo cáo." },
  { id: "c4", title: "Hoàn tiền", text: "Chúng tôi đã tiếp nhận yêu cầu và sẽ tiến hành kiểm tra giao dịch. Nếu có sai sót, bộ phận kế toán sẽ hoàn tiền cho bạn trong vòng 24h." },
];

function isOverdue(task: Task): boolean {
  if (!task.due_at) return false;
  if (task.status === "resolved") return false;
  return new Date(task.due_at) < new Date();
}

function SupportPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedAlerts, setSelectedAlerts] = useState<Alert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [filterPriority, setFilterPriority] = useState<string>("All");
  
  const [cannedReply, setCannedReply] = useState("");
  const [resolving, setResolving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const { data: me } = useMe();
  const isManagerOrStaff = me?.role === "admin" || me?.role === "manager" || me?.role === "staff";

  // Lấy các Ticket được gán cho Team CSKH (hoặc tất cả nếu là admin)
  // Thực tế API tasks đã có Team Isolation (backend xử lý), nên chỉ cần fetch open.
  const loadData = useCallback(async () => {
    if (!isManagerOrStaff) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "100");
      params.set("status", "open");
      if (filterPriority !== "All") params.set("priority", filterPriority);
      
      const json = await apiFetch<{ data: Task[] }>(`/api/tasks?${params.toString()}`);
      // Lọc local ưu tiên hiển thị Task quá hạn hoặc Priority cao lên trên
      let loadedTasks = json.data || [];
      loadedTasks.sort((a, b) => {
        if (isOverdue(a) && !isOverdue(b)) return -1;
        if (!isOverdue(a) && isOverdue(b)) return 1;
        if (a.priority < b.priority) return -1;
        if (a.priority > b.priority) return 1;
        return 0;
      });
      setTasks(loadedTasks);
    } catch {
      toast.error("Không thể tải danh sách hàng đợi.");
    } finally {
      setLoading(false);
    }
  }, [isManagerOrStaff, filterPriority]);

  useEffect(() => {
    if (me?.role && isManagerOrStaff) {
      loadData();
    }
  }, [me?.role, loadData]);

  const selectTask = async (taskId: string) => {
    if (selectedTaskId === taskId) return;
    setSelectedTaskId(taskId);
    setCannedReply("");
    setConfirming(false);
    setAlertsLoading(true);
    try {
      const json = await apiFetch<{ data: Alert[] }>(`/api/tasks/${taskId}/alerts`);
      setSelectedAlerts(json.data || []);
    } catch {
      toast.error("Không thể tải chi tiết ticket.");
    } finally {
      setAlertsLoading(false);
    }
  };

  const resolveTicket = async () => {
    if (!selectedTaskId) return;
    if (!cannedReply.trim()) {
      toast.error("Vui lòng nhập hoặc chọn mẫu phản hồi");
      return;
    }
    setResolving(true);
    try {
      // Đổi trạng thái task thành resolved
      await apiFetch(`/api/tasks/${selectedTaskId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "resolved" }),
      });
      toast.success("Đã phản hồi & đóng Ticket thành công!");
      setTasks((prev) => prev.filter((t) => t.id !== selectedTaskId));
      setSelectedTaskId(null);
      setCannedReply("");
    } catch {
      toast.error("Lỗi khi xử lý Ticket.");
    } finally {
      setResolving(false);
    }
  };

  if (!isManagerOrStaff) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Bạn không có quyền truy cập trang Hỗ trợ CSKH.
      </div>
    );
  }

  const selectedTask = tasks.find((t) => t.id === selectedTaskId);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4 animate-in fade-in slide-in-from-bottom-2">
      <div>
        <h1 className="font-display text-3xl font-bold flex items-center gap-2">
          <Headphones className="h-8 w-8 text-xanh-deep" />
          Bảng điều phối Hỗ trợ CSKH
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hàng đợi ưu tiên theo SLA. Các ticket báo đỏ đã quá hạn xử lý.
        </p>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden h-full">
        {/* Left Panel: Queue */}
        <div className="w-1/3 flex flex-col bg-card border border-border rounded-2xl shadow-[var(--shadow-card)] overflow-hidden">
          <div className="p-4 border-b border-border bg-muted/20">
            <h3 className="font-semibold text-sm flex justify-between items-center text-xanh-deep mb-3">
              <span>Hàng đợi ({tasks.length})</span>
            </h3>
            {/* Filter Priority */}
            <div className="flex items-center gap-2">
               <Filter className="h-3 w-3 text-muted-foreground" />
               <span className="text-[11px] font-mono text-muted-foreground">Lọc mức độ:</span>
               <div className="flex gap-1">
                 {["All", "P1", "P2", "P3"].map(p => (
                   <button
                     key={p}
                     onClick={() => setFilterPriority(p)}
                     className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase ${filterPriority === p ? "bg-xanh-deep text-white" : "bg-muted text-muted-foreground border border-border"}`}
                   >
                     {p}
                   </button>
                 ))}
               </div>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto divide-y divide-border">
            {loading ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : tasks.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                Hàng đợi trống. Tuyệt vời!
              </div>
            ) : (
              tasks.map((task) => {
                const overdue = isOverdue(task);
                const isSelected = selectedTaskId === task.id;
                return (
                  <div
                    key={task.id}
                    onClick={() => selectTask(task.id)}
                    className={`p-3 cursor-pointer transition-colors ${
                      isSelected ? "bg-xanh-mint/50 ring-1 ring-inset ring-xanh-green/40" : "hover:bg-muted/30"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <div className="flex gap-1.5 flex-wrap">
                        <span className={`text-[10px] font-mono font-bold px-1.5 rounded ${overdue ? "bg-xanh-coral/15 text-xanh-coral" : "bg-xanh-amber/20 text-xanh-deep"}`}>
                          {overdue ? "QUÁ HẠN" : task.priority}
                        </span>
                        <span className="text-[10px] uppercase font-mono text-muted-foreground">
                          {task.area ? regionLabel(task.area) : "N/A"}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {new Date(task.created_at).toLocaleTimeString("vi-VN", { hour: '2-digit', minute:'2-digit' })}
                      </span>
                    </div>
                    <div className={`font-semibold text-sm line-clamp-1 ${overdue ? "text-xanh-coral" : "text-xanh-deep"}`}>
                      {task.title}
                    </div>
                    <div className="text-xs text-muted-foreground line-clamp-1 mt-1">
                      {task.summary}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel: Ticket Detail & Canned Response */}
        <div className="w-2/3 bg-card border border-border rounded-2xl shadow-[var(--shadow-card)] flex flex-col overflow-hidden">
          {!selectedTask ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground space-y-4">
              <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center">
                <MessageSquare className="h-8 w-8 opacity-20" />
              </div>
              <p>Chọn một Ticket trong hàng đợi để xử lý</p>
            </div>
          ) : (
            <>
              {/* Ticket Meta */}
              <div className="p-5 border-b border-border bg-muted/10">
                <div className="flex items-center gap-2 mb-2">
                   <span className="text-xs uppercase font-mono bg-xanh-deep text-white px-2 py-0.5 rounded">
                     {selectedTask.priority}
                   </span>
                   {selectedTask.area && (
                     <span className="text-xs flex items-center text-muted-foreground font-mono bg-muted px-2 py-0.5 border border-border rounded">
                       <MapPin className="h-3 w-3 mr-1" /> {regionLabel(selectedTask.area)}
                     </span>
                   )}
                   {isOverdue(selectedTask) && (
                     <span className="text-xs flex items-center text-xanh-coral font-bold bg-xanh-coral/15 px-2 py-0.5 rounded">
                       <AlertTriangle className="h-3 w-3 mr-1" /> QUÁ HẠN SLA
                     </span>
                   )}
                </div>
                <h2 className="text-xl font-bold text-xanh-deep">{selectedTask.title}</h2>
                <div className="text-sm text-muted-foreground mt-2 bg-card p-3 rounded-lg border border-border">
                  {selectedTask.summary}
                </div>
              </div>

              {/* Underlying Alerts list */}
              <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-muted/5">
                <h4 className="font-semibold text-sm flex items-center gap-2 text-xanh-deep">
                  <ShieldAlert className="h-4 w-4" />
                  Ghi nhận liên quan ({selectedAlerts.length})
                </h4>
                {alertsLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <div className="space-y-2">
                    {selectedAlerts.map(alert => (
                      <div key={alert.id} className="p-3 bg-card border border-border rounded-lg text-sm flex gap-3">
                         <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${alert.severity === "P5" ? "bg-red-500" : "bg-amber-500"}`} />
                         <div>
                            <p className="font-medium">{alert.title}</p>
                            <p className="text-[11px] font-mono text-muted-foreground mt-1">
                               {new Date(alert.created_at).toLocaleString("vi-VN")}
                            </p>
                         </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Reply Section */}
              <div className="p-5 border-t border-border bg-card">
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-xanh-deep flex items-center gap-2">
                      <MessageSquare className="h-4 w-4" /> Phản hồi khách hàng
                    </label>
                    {/* Canned Responses Chips */}
                    <div className="flex gap-2">
                      {CANNED_RESPONSES.map(c => (
                        <button
                          key={c.id}
                          onClick={() => setCannedReply(c.text)}
                          className="px-2.5 py-1 text-[11px] font-semibold bg-muted hover:bg-xanh-mint/50 border border-border rounded-full transition-colors text-xanh-deep"
                        >
                          {c.title}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <textarea 
                    value={cannedReply}
                    onChange={(e) => setCannedReply(e.target.value)}
                    placeholder="Nhập nội dung phản hồi hoặc chọn mẫu câu soạn sẵn..."
                    className="w-full h-24 p-3 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-xanh-green/30 text-sm resize-none bg-muted/5"
                  />

                  <div className="flex justify-end">
                    {confirming ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Xác nhận đóng ticket này?</span>
                        <button
                          onClick={resolveTicket}
                          disabled={resolving}
                          className="flex items-center gap-1.5 px-4 py-2 bg-xanh-coral text-white rounded-xl text-sm font-bold hover:bg-xanh-coral/90 transition-all disabled:opacity-50"
                        >
                          {resolving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                          Đóng
                        </button>
                        <button
                          onClick={() => setConfirming(false)}
                          disabled={resolving}
                          className="px-4 py-2 rounded-xl text-sm font-semibold bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
                        >
                          Hủy
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirming(true)}
                        disabled={!cannedReply.trim()}
                        className="flex items-center gap-2 px-5 py-2.5 bg-xanh-deep text-white rounded-xl text-sm font-bold shadow-md hover:bg-xanh-deep/90 transition-all disabled:opacity-50 disabled:shadow-none"
                      >
                        <Send className="h-4 w-4" />
                        Phản hồi & Đóng Ticket
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
