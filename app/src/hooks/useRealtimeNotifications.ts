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

export function useRealtimeNotifications() {
  const [notifications, setNotifications] = React.useState<Notification[]>([]);

  const unreadCount = React.useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  );

  const markAsRead = React.useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
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
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "alerts" },
        (payload) => {
          const record = payload.new as Record<string, unknown>;
          const createdAtValue = String(record.created_at ?? new Date().toISOString());
          const notification: Notification = {
            id: String(record.id ?? crypto.randomUUID()),
            type: "alert",
            title: String(record.title ?? "New Alert"),
            severity: record.severity ? String(record.severity) : undefined,
            priority: record.severity === "P4" || record.severity === "P5" ? (record.severity as "P4" | "P5") : undefined,
            team: record.team ? String(record.team) : undefined,
            created_at: createdAtValue,
            createdAt: createdAtValue,
            read: false,
          };

          setNotifications((prev) =>
            [notification, ...prev].slice(0, MAX_NOTIFICATIONS)
          );

          if (
            notification.severity === "P5" ||
            notification.severity === "P4"
          ) {
            toast.error(notification.title);
          }
        }
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "tasks" },
        (payload) => {
          const record = payload.new as Record<string, unknown>;
          const createdAtValue = String(record.created_at ?? new Date().toISOString());
          const notification: Notification = {
            id: String(record.id ?? crypto.randomUUID()),
            type: "task",
            title: String(record.title ?? "New Task"),
            team: record.team ? String(record.team) : undefined,
            created_at: createdAtValue,
            createdAt: createdAtValue,
            read: false,
          };

          setNotifications((prev) =>
            [notification, ...prev].slice(0, MAX_NOTIFICATIONS)
          );

          toast.info(notification.title);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return { notifications, unreadCount, markAsRead, markAllRead, clearAll };
}
