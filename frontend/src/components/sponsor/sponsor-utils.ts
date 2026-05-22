/** Sponsor link access pipeline — mirrors claim pipeline step logic */

export type SponsorStepVisual = "done" | "active" | "upcoming";

export type SponsorPipelineActive = "pay" | "submit" | "review" | "live";

export interface SponsorPipelineState {
  payDone: boolean;
  submitDone: boolean;
  reviewDone: boolean;
  liveDone: boolean;
  active: SponsorPipelineActive;
  allLive: boolean;
  isRejected: boolean;
}

export function getSponsorPipelineState(
  accessStatus?: string,
  hasPendingRequest?: boolean,
): SponsorPipelineState {
  if (accessStatus === "active") {
    return {
      payDone: true,
      submitDone: true,
      reviewDone: true,
      liveDone: true,
      active: "live",
      allLive: true,
      isRejected: false,
    };
  }

  if (accessStatus === "rejected") {
    return {
      payDone: true,
      submitDone: true,
      reviewDone: false,
      liveDone: false,
      active: "review",
      allLive: false,
      isRejected: true,
    };
  }

  if (accessStatus === "pending" || hasPendingRequest) {
    return {
      payDone: true,
      submitDone: true,
      reviewDone: false,
      liveDone: false,
      active: "review",
      allLive: false,
      isRejected: false,
    };
  }

  return {
    payDone: false,
    submitDone: false,
    reviewDone: false,
    liveDone: false,
    active: "pay",
    allLive: false,
    isRejected: false,
  };
}

export function sponsorStepVisual(
  step: SponsorPipelineActive,
  pipeline: SponsorPipelineState,
): SponsorStepVisual {
  if (pipeline.allLive) return "done";

  const order: SponsorPipelineActive[] = ["pay", "submit", "review", "live"];
  const stepIdx = order.indexOf(step);
  const activeIdx = order.indexOf(pipeline.active);

  if (stepIdx < activeIdx) return "done";
  if (stepIdx === activeIdx) return "active";
  return "upcoming";
}
