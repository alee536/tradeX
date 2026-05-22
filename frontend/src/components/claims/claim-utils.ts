import type { PurchaseClaimSchedule, PurchaseClaimStage } from "@workspace/api-client-react";

export function splitCountdown(totalSeconds: number | null | undefined) {
  const s = Math.max(0, Math.floor(totalSeconds ?? 0));
  return {
    hours: Math.floor(s / 3600),
    minutes: Math.floor((s % 3600) / 60),
    seconds: s % 60,
  };
}

/** Locked stage currently counting down (backend seconds_until_unlock). */
export function getActiveTimerStage(
  stages: PurchaseClaimStage[],
): PurchaseClaimStage | undefined {
  return stages.find(
    (s) => s.state === "locked" && (s.seconds_until_unlock ?? 0) > 0,
  );
}

/** First stage user can act on (claim or resubmit after reject). */
export function getActionableStage(
  stages: PurchaseClaimStage[],
): PurchaseClaimStage | undefined {
  return stages.find((s) => s.can_request);
}

export function getCycleWindow(
  schedule: PurchaseClaimSchedule,
  timerStage: PurchaseClaimStage,
): { startMs: number; endMs: number } | null {
  if (!timerStage.unlock_at) return null;
  const endMs = new Date(timerStage.unlock_at).getTime();
  let startMs: number | null = null;

  if (timerStage.stage === 1 && schedule.reference_time) {
    startMs = new Date(schedule.reference_time).getTime();
  } else if (timerStage.stage > 1) {
    const prev = schedule.stages.find((s) => s.stage === timerStage.stage - 1);
    const approvedAt = prev?.claim?.approved_at;
    if (approvedAt) {
      startMs = new Date(approvedAt).getTime();
    }
  }

  if (startMs == null || endMs <= startMs) return null;
  return { startMs, endMs };
}

export function getCycleProgressPercent(
  schedule: PurchaseClaimSchedule,
  timerStage: PurchaseClaimStage,
): number {
  const window = getCycleWindow(schedule, timerStage);
  if (!window) return 0;
  const now = Date.now();
  const elapsed = now - window.startMs;
  const total = window.endMs - window.startMs;
  return Math.min(100, Math.max(0, (elapsed / total) * 100));
}

export function getCycleHoursLabel(
  schedule: PurchaseClaimSchedule,
  timerStage: PurchaseClaimStage,
): string {
  const window = getCycleWindow(schedule, timerStage);
  if (!window) return timerStage.stage === 1 ? "72h cycle" : "24h cycle";
  const hours = Math.round((window.endMs - window.startMs) / 3600000);
  return `${hours}h cycle`;
}

export type PipelineStepId = "deposit" | "timer" | "claim" | "complete";

export function getPipelineSteps(schedule: PurchaseClaimSchedule) {
  const hasDeposit = Boolean(schedule.reference_time);
  const timerStage = getActiveTimerStage(schedule.stages);
  const actionable = getActionableStage(schedule.stages);
  const allApproved = schedule.stages.every(
    (s: PurchaseClaimStage) => s.state === "approved",
  );

  let active: PipelineStepId = "deposit";
  if (!hasDeposit) {
    active = "deposit";
  } else if (allApproved) {
    active = "complete";
  } else if (timerStage) {
    active = "timer";
  } else if (actionable) {
    active = "claim";
  } else {
    active = "timer";
  }

  const depositDone = hasDeposit;
  const timerDone = !timerStage && hasDeposit;
  const claimDone = allApproved;

  return {
    active,
    depositDone,
    timerDone,
    claimDone,
    allApproved,
  };
}
