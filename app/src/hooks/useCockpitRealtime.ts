import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

/** Subscribe Supabase Realtime cho feedback/alerts/tasks.
 *  Trả về cờ `pulse` (true ~1s sau mỗi event mới) để kích hiệu ứng LIVE badge. */
export function useCockpitRealtime() {
  const queryClient = useQueryClient();
  const [pulse, setPulse] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pulseRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function onEvent() {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["cockpit-overview"] });
        queryClient.invalidateQueries({ queryKey: ["feedback-recent"] });
        queryClient.invalidateQueries({ queryKey: ["alerts-recent"] });
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
      }, 500);

      setPulse(true);
      if (pulseRef.current) clearTimeout(pulseRef.current);
      pulseRef.current = setTimeout(() => setPulse(false), 1200);
    }

    const channel = supabase
      .channel("cockpit-realtime")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "feedback" }, onEvent)
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "feedback" }, onEvent)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "alerts" }, onEvent)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "tasks" }, onEvent)
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "tasks" }, onEvent)
      .subscribe();

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (pulseRef.current) clearTimeout(pulseRef.current);
      supabase.removeChannel(channel);
    };
  }, [queryClient]);

  return { pulse };
}
