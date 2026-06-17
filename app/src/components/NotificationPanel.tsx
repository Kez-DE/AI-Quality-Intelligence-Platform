import { useEffect, useRef, useState } from "react";
import { Bell, AlertTriangle, CheckSquare } from "lucide-react";

export interface Notification {
  id: string;
  type: "alert" | "task";
  priority?: "P4" | "P5";
  title: string;
  createdAt: string; // ISO timestamp
  read: boolean;
}

interface NotificationPanelProps {
  notifications: Notification[];
  unreadCount: number;
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
}

function relativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return "vừa xong";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} phút trước`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} giờ trước`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay} ngày trước`;
  const diffMonth = Math.floor(diffDay / 30);
  return `${diffMonth} tháng trước`;
}

export default function NotificationPanel({
  notifications,
  unreadCount,
  onMarkRead,
  onMarkAllRead,
}: NotificationPanelProps) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative h-9 w-9 rounded-xl grid place-items-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        aria-label="Thông báo"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 rounded-full bg-xanh-coral text-[10px] font-bold text-white grid place-items-center">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-2xl border border-border bg-popover text-popover-foreground shadow-[var(--shadow-card)] z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 className="font-display font-semibold text-sm text-xanh-deep">
              Thông báo
            </h3>
            <button
              onClick={onMarkAllRead}
              className="text-xs text-xanh-green hover:text-xanh-deep font-medium transition-colors"
            >
              Đọc tất cả
            </button>
          </div>

          {/* Notification list */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                Không có thông báo mới
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {notifications.map((item) => (
                  <li key={item.id}>
                    <button
                      onClick={() => onMarkRead(item.id)}
                      className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50 ${
                        !item.read ? "bg-xanh-mint/40" : ""
                      }`}
                    >
                      {/* Icon */}
                      <div className="mt-0.5 shrink-0">
                        {item.type === "alert" ? (
                          <AlertTriangle
                            className={`h-4 w-4 ${
                              item.priority === "P5"
                                ? "text-xanh-coral"
                                : "text-xanh-amber"
                            }`}
                          />
                        ) : (
                          <CheckSquare className="h-4 w-4 text-xanh-cyan" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-sm truncate ${
                            !item.read
                              ? "font-medium text-foreground"
                              : "text-muted-foreground"
                          }`}
                        >
                          {item.title}
                        </p>
                        <span className="text-[11px] text-muted-foreground">
                          {relativeTime(item.createdAt)}
                        </span>
                      </div>

                      {/* Unread dot */}
                      {!item.read && (
                        <span className="mt-1.5 h-2 w-2 rounded-full bg-xanh-green shrink-0" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
