import { createContext, useContext, useState } from "react";

export interface CockpitFilter {
  topic: string | null;
  area: string | null;
  severity: string | null;
}

interface CockpitFilterCtx {
  filter: CockpitFilter;
  setTopic: (t: string | null) => void;
  setArea: (a: string | null) => void;
  setSeverity: (s: string | null) => void;
  clear: () => void;
}

const Ctx = createContext<CockpitFilterCtx | null>(null);

export function CockpitFilterProvider({ children }: { children: React.ReactNode }) {
  const [filter, setFilter] = useState<CockpitFilter>({ topic: null, area: null, severity: null });
  return (
    <Ctx.Provider
      value={{
        filter,
        setTopic: (t) => setFilter((f) => ({ ...f, topic: t })),
        setArea: (a) => setFilter((f) => ({ ...f, area: a })),
        setSeverity: (s) => setFilter((f) => ({ ...f, severity: s })),
        clear: () => setFilter({ topic: null, area: null, severity: null }),
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useCockpitFilter() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useCockpitFilter must be inside CockpitFilterProvider");
  return ctx;
}
