import * as React from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";

const MAX_NOTIFICATIONS = 50;

export interface Notification {
  id: string;
  type: "alert" | "task";
  title: string;
  severity?: string;
  priority?: "P4" | "P5";
  team?: string;
  created_at: string;
  createdAt: string;
  read: boolean;
}

export function useRealtimeNotifications(
  currentUserId?: string | null,
  viewerRole?: string | null,
  viewerDepartment?: string | null,
) {
  const [notifications, setNotifications] = React.useState<Notification[]>([]);
  // Tránh báo trùng: mỗi task chỉ báo "được giao cho bạn" một lần / phiên.
  const notifiedAssignments = React.useRef<Set<string>>(new Set());

  // Bản sao của can_view_team ở backend. RLS chỉ gate realtime theo ROLE
  // (is_ops_staff), không theo phòng ban — nên nếu client không tự lọc thì nhân viên
  // Vận hành nhận toast tiêu đề mọi ticket của Tài chính, Rủi ro & Gian lận...
  // tức là vượt rào RBAC bằng kênh realtime.
  const canSeeTeam = React.useCallback(
    (team: unknown) => {
      if (viewerRole === "admin") return true;
      if (!viewerDepartment) return false;
      return typeof team === "string" && team === viewerDepartment;
    },
    [viewerRole, viewerDepartment],
  );

  const unreadCount = React.useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications],
  );

  const markAsRead = React.useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllRead = React.useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearAll = React.useCallback(() => {
    setNotifications([]);
  }, []);

  React.useEffect(() => {
    const channel = supabase
      .channel("realtime-notifications")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "alerts" }, (payload) => {
        const record = payload.new as Record<string, unknown>;
        if (!canSeeTeam(record.assigned_team)) return;
        const createdAtValue = String(record.created_at ?? new Date().toISOString());
        const notification: Notification = {
          id: String(record.id ?? crypto.randomUUID()),
          type: "alert",
          title: String(record.title ?? "New Alert"),
          severity: record.severity ? String(record.severity) : undefined,
          priority:
            record.severity === "P4" || record.severity === "P5"
              ? (record.severity as "P4" | "P5")
              : undefined,
          // Cột thật là assigned_team; `record.team` không tồn tại nên badge phòng ban
          // trước giờ luôn rỗng.
          team: record.assigned_team ? String(record.assigned_team) : undefined,
          created_at: createdAtValue,
          createdAt: createdAtValue,
          read: false,
        };

        setNotifications((prev) => [notification, ...prev].slice(0, MAX_NOTIFICATIONS));

        if (notification.severity === "P5" || notification.severity === "P4") {
          toast.error(notification.title);
        }
      })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "tasks" }, (payload) => {
        const record = payload.new as Record<string, unknown>;
        if (!canSeeTeam(record.assigned_team)) return;
        const createdAtValue = String(record.created_at ?? new Date().toISOString());
        const notification: Notification = {
          id: String(record.id ?? crypto.randomUUID()),
          type: "task",
          title: String(record.title ?? "New Task"),
          team: record.assigned_team ? String(record.assigned_team) : undefined,
          created_at: createdAtValue,
          createdAt: createdAtValue,
          read: false,
        };

        setNotifications((prev) => [notification, ...prev].slice(0, MAX_NOTIFICATIONS));

        toast.info(notification.title);
      })
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "tasks" }, (payload) => {
        // Luồng dispatch: manager giao task cho staff (owner_id được set).
        // Chỉ báo cho đúng nhân viên được giao, mỗi task một lần / phiên.
        const record = payload.new as Record<string, unknown>;
        const ownerId = record.owner_id ? String(record.owner_id) : null;
        const taskId = String(record.id ?? "");
        if (!currentUserId || !ownerId || ownerId !== currentUserId) return;
        if (!taskId || notifiedAssignments.current.has(taskId)) return;
        notifiedAssignments.current.add(taskId);

        const priority = record.priority ? String(record.priority) : undefined;
        const isUrgent = priority === "P5" || priority === "P4";
        const title = String(record.title ?? "Công việc mới");
        const createdAtValue = new Date().toISOString();
        const notification: Notification = {
          id: `assign-${taskId}-${Date.now()}`,
          type: "task",
          title: `Bạn được giao: ${title}`,
          priority: isUrgent ? (priority as "P4" | "P5") : undefined,
          team: record.assigned_team ? String(record.assigned_team) : undefined,
          created_at: createdAtValue,
          createdAt: createdAtValue,
          read: false,
        };

        setNotifications((prev) => [notification, ...prev].slice(0, MAX_NOTIFICATIONS));

        if (isUrgent) {
          toast.error(`🚨 Việc cần xử lý ngay: ${title}`);
        } else {
          toast.info(`Bạn được giao việc mới: ${title}`);
        }
      })
      // Không có callback thì kênh chết im lặng (token hết hạn, WS rớt, grant bị thu hồi)
      // và chuông thông báo chỉ ngừng kêu — không ai biết để tải lại trang.
      .subscribe((status) => {
        if (status === "CHANNEL_ERROR" || status === "TIMED_OUT" || status === "CLOSED") {
          console.error(`[realtime] notifications channel ${status}`);
        }
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [currentUserId, canSeeTeam]);

  return { notifications, unreadCount, markAsRead, markAllRead, clearAll };
}
