import { useQuery } from "@tanstack/react-query";
import { apiFetch, useMe } from "@/lib/api";
import type { CockpitOverview } from "@/components/cockpit/types";

export function useCockpitOverview(days = 14) {
  const { data: me } = useMe();
  return useQuery({
    queryKey: ["cockpit-overview", days, me?.department ?? null, me?.role ?? null],
    queryFn: async () => {
      const json = await apiFetch<{ data: CockpitOverview }>(`/api/cockpit/overview?days=${days}`);
      return json.data;
    },
    staleTime: 30_000,
    retry: false,
    enabled: !!me,
  });
}
