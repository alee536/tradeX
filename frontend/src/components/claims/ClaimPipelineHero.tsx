import { useEffect, useState, type ReactNode } from "react";
import type { PurchaseClaimSchedule } from "@workspace/api-client-react";
import { Progress } from "@/components/ui/progress";
import {
  ArrowRight,
  Check,
  Clock,
  Gift,
  Wallet,
  PartyPopper,
} from "lucide-react";
import {
  getActiveTimerStage,
  getCycleHoursLabel,
  getCycleProgressPercent,
  getPipelineSteps,
  splitCountdown,
} from "./claim-utils";

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

type StepVisual = "done" | "active" | "upcoming";

function stepClass(visual: StepVisual) {
  if (visual === "done") {
    return "bg-amber-500/90 text-black border-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.35)]";
  }
  if (visual === "active") {
    return "bg-transparent text-amber-400 border-amber-400 border-2 shadow-[0_0_10px_rgba(245,158,11,0.25)]";
  }
  return "bg-white/5 text-muted-foreground border-white/15";
}

function PipelineStep({
  label,
  icon,
  visual,
}: {
  label: string;
  icon: ReactNode;
  visual: StepVisual;
}) {
  return (
    <div className="flex flex-col items-center gap-2 min-w-[64px]">
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-full border transition-all ${stepClass(visual)}`}
      >
        {visual === "done" ? <Check className="h-5 w-5" /> : icon}
      </div>
      <span
        className={`text-xs font-medium text-center ${visual === "active" ? "text-amber-400" : visual === "done" ? "text-amber-300/90" : "text-muted-foreground"}`}
      >
        {label}
      </span>
    </div>
  );
}

function CountdownBox({ value, unit }: { value: number; unit: string }) {
  return (
    <div className="flex-1 min-w-[72px] rounded-lg border border-white/10 bg-black/40 px-3 py-3 text-center">
      <div className="text-2xl sm:text-3xl font-bold tabular-nums text-white">
        {pad2(value)}
      </div>
      <div className="text-[10px] sm:text-xs uppercase tracking-wider text-muted-foreground mt-1">
        {unit}
      </div>
    </div>
  );
}

export function ClaimPipelineHero({ schedule }: { schedule: PurchaseClaimSchedule }) {
  const timerStage = getActiveTimerStage(schedule.stages);
  const pipeline = getPipelineSteps(schedule);

  const [secondsLeft, setSecondsLeft] = useState<number | null>(
    timerStage?.seconds_until_unlock ?? null,
  );

  useEffect(() => {
    setSecondsLeft(timerStage?.seconds_until_unlock ?? null);
    if (timerStage?.seconds_until_unlock == null) return;
    const id = setInterval(() => {
      setSecondsLeft((prev) => (prev == null ? prev : Math.max(0, prev - 1)));
    }, 1000);
    return () => clearInterval(id);
  }, [timerStage?.seconds_until_unlock, timerStage?.stage]);

  const countdown = splitCountdown(secondsLeft);
  const progress =
    timerStage != null
      ? getCycleProgressPercent(schedule, timerStage)
      : pipeline.allApproved
        ? 100
        : 0;
  const cycleLabel =
    timerStage != null
      ? getCycleHoursLabel(schedule, timerStage)
      : pipeline.allApproved
        ? "All stages complete"
        : "Awaiting next step";

  const depositVisual: StepVisual = pipeline.depositDone
    ? "done"
    : pipeline.active === "deposit"
      ? "active"
      : "upcoming";

  const timerVisual: StepVisual = pipeline.allApproved
    ? "done"
    : pipeline.active === "timer"
      ? "active"
      : pipeline.timerDone
        ? "done"
        : "upcoming";

  const claimVisual: StepVisual = pipeline.allApproved
    ? "done"
    : pipeline.active === "claim"
      ? "active"
      : pipeline.claimDone
        ? "done"
        : "upcoming";

  const completeVisual: StepVisual = pipeline.allApproved ? "done" : "upcoming";

  return (
    <div className="space-y-5 mb-6">
      {/* ============== Step pipeline (AMY-style) ============== */}
      <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1">
        <PipelineStep
          label="Deposit"
          icon={<Wallet className="h-5 w-5" />}
          visual={depositVisual}
        />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/60" />
        <PipelineStep
          label="Timer"
          icon={<Clock className="h-5 w-5" />}
          visual={timerVisual}
        />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/60" />
        <PipelineStep
          label="Claim"
          icon={<Gift className="h-5 w-5" />}
          visual={claimVisual}
        />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/60" />
        <PipelineStep
          label="Complete"
          icon={<PartyPopper className="h-5 w-5" />}
          visual={completeVisual}
        />
      </div>

      {/* ============== Countdown + progress ============== */}
      <div className="rounded-xl border border-amber-500/20 bg-gradient-to-b from-amber-500/10 to-transparent p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="h-4 w-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-white">Countdown Timer</h3>
        </div>

        {timerStage && secondsLeft != null && secondsLeft > 0 ? (
          <>
            <div className="flex gap-2 sm:gap-3 mb-4">
              <CountdownBox value={countdown.hours} unit="Hours" />
              <CountdownBox value={countdown.minutes} unit="Minutes" />
              <CountdownBox value={countdown.seconds} unit="Seconds" />
            </div>
            <Progress
              value={progress}
              className="h-2 bg-black/40 [&>div]:bg-gradient-to-r [&>div]:from-amber-600 [&>div]:to-amber-400"
            />
            <p className="text-xs text-amber-300/80 mt-2 text-center">{cycleLabel}</p>
            <p className="text-xs text-muted-foreground mt-1 text-center">
              Stage {timerStage.stage} unlocks ({timerStage.percent}% payout)
            </p>
          </>
        ) : pipeline.allApproved ? (
          <p className="text-sm text-green-400 text-center py-4">
            All claim stages completed for this purchase.
          </p>
        ) : schedule.stages.some((s) => s.state === "available") ? (
          <p className="text-sm text-amber-300 text-center py-4">
            Timer complete — claim your {schedule.stages.find((s) => s.can_request)?.percent}% payout. Coins go to your wallet instantly.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">
            Processing your claim schedule…
          </p>
        )}
      </div>
    </div>
  );
}
