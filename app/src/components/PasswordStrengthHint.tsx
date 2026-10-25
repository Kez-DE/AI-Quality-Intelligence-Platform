import { PASSWORD_CRITERIA, validatePassword } from "@/lib/password";

const STRENGTH_LEVELS = [
  { maxScore: 1, label: "Rất yếu", color: "bg-destructive" },
  { maxScore: 2, label: "Yếu", color: "bg-orange-400" },
  { maxScore: 4, label: "Trung bình", color: "bg-yellow-400" },
  { maxScore: 5, label: "Mạnh", color: "bg-xanh-green" },
] as const;

export function PasswordStrengthHint({ password }: { password: string }) {
  if (!password) return null;
  const checks = validatePassword(password);
  const score = Object.values(checks).filter(Boolean).length;
  const level = STRENGTH_LEVELS.find((l) => score <= l.maxScore) ?? STRENGTH_LEVELS[3];
  const filledSegments = score === 0 ? 0 : Math.max(1, Math.ceil((score / 5) * 4));

  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < filledSegments ? level.color : "bg-muted opacity-40"
              }`}
            />
          ))}
        </div>
        <span className="w-16 text-right text-muted-foreground">{level.label}</span>
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-muted-foreground">
        {PASSWORD_CRITERIA.map(({ key, label }) => (
          <li
            key={key}
            className={`flex items-center gap-1.5 ${checks[key] ? "text-xanh-green" : ""}`}
          >
            <span className="shrink-0 font-mono">{checks[key] ? "✓" : "–"}</span>
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
