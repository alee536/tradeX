import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

type Accent = "violet" | "green" | "cyan" | "amber";

const accentMap: Record<Accent, string> = {
  violet: "bg-violet-500/15 text-violet-400 ring-violet-500/30",
  green: "bg-green-500/15 text-green-400 ring-green-500/30",
  cyan: "bg-cyan-500/15 text-cyan-400 ring-cyan-500/30",
  amber: "bg-amber-500/15 text-amber-400 ring-amber-500/30",
};

export function SponsorStatCard({
  icon,
  label,
  value,
  sub,
  accent = "violet",
  loading,
  delayMs = 0,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  sub?: string;
  accent?: Accent;
  loading?: boolean;
  delayMs?: number;
}) {
  return (
    <Card
      className="glass-panel group border-white/10 hover:border-violet-500/25 transition-all duration-300 hover:shadow-[0_0_28px_rgba(139,92,246,0.12)] animate-in fade-in slide-in-from-bottom-3 fill-mode-both"
      style={{ animationDelay: `${delayMs}ms`, animationDuration: "500ms" }}
    >
      <CardContent className="p-4 flex items-center gap-4">
        <div
          className={`p-3 rounded-xl ring-1 transition-transform duration-300 group-hover:scale-110 ${accentMap[accent]}`}
        >
          {icon}
        </div>
        <div>
          <div className="text-2xl font-bold tabular-nums">
            {loading ? <Loader2 className="h-6 w-6 animate-spin text-violet-400" /> : value}
          </div>
          <div className="text-xs text-muted-foreground">{label}</div>
          {sub && <div className="text-[10px] text-muted-foreground/80 mt-0.5">{sub}</div>}
        </div>
      </CardContent>
    </Card>
  );
}
