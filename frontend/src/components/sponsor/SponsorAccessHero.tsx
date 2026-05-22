import type { ReactNode } from "react";
import type { SponsorStats } from "@workspace/api-client-react";
import {
  ArrowRight,
  Check,
  Clock,
  Link2,
  Send,
  ShieldCheck,
  Sparkles,
  Wallet,
} from "lucide-react";
import {
  getSponsorPipelineState,
  sponsorStepVisual,
  type SponsorPipelineState,
  type SponsorStepVisual,
} from "./sponsor-utils";

function stepRingClass(visual: SponsorStepVisual) {
  if (visual === "done") {
    return "bg-violet-500/90 text-white border-violet-400 shadow-[0_0_14px_rgba(139,92,246,0.45)]";
  }
  if (visual === "active") {
    return "bg-transparent text-violet-300 border-violet-400 border-2 shadow-[0_0_12px_rgba(139,92,246,0.35)] animate-pulse";
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
  visual: SponsorStepVisual;
}) {
  return (
    <div className="flex flex-col items-center gap-2 min-w-[64px]">
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-full border transition-all duration-300 ${stepRingClass(visual)}`}
      >
        {visual === "done" ? <Check className="h-5 w-5" /> : icon}
      </div>
      <span
        className={`text-xs font-medium text-center ${
          visual === "active"
            ? "text-violet-300"
            : visual === "done"
              ? "text-violet-200/90"
              : "text-muted-foreground"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function statusMessage(pipeline: SponsorPipelineState, fee: number) {
  if (pipeline.allLive) {
    return {
      title: "Your sponsor link is live",
      body: "Share your ref link — new sign-ups attach to your network for lifetime earnings.",
      tone: "success" as const,
    };
  }
  if (pipeline.isRejected) {
    return {
      title: "Access request rejected",
      body: "Contact support if you need to submit again with updated payment proof.",
      tone: "error" as const,
    };
  }
  if (pipeline.active === "review") {
    return {
      title: "Admin review in progress",
      body: "Payment received — we are verifying your 5 USDT fee and referral code.",
      tone: "pending" as const,
    };
  }
  if (pipeline.active === "submit") {
    return {
      title: "Submit your request",
      body: "Enter your referral code and payment details below.",
      tone: "info" as const,
    };
  }
  return {
    title: `Activate sponsor access — ${fee} USDT`,
    body: "Pay the one-time fee, then submit proof to unlock your public ref link.",
    tone: "info" as const,
  };
}

export function SponsorAccessHero({
  stats,
  fee,
}: {
  stats?: SponsorStats;
  fee: number;
}) {
  const pipeline = getSponsorPipelineState(
    stats?.sponsor_access_status,
    !!stats?.pending_request,
  );
  const msg = statusMessage(pipeline, fee);

  const payVisual = sponsorStepVisual("pay", pipeline);
  const submitVisual = sponsorStepVisual("submit", pipeline);
  const reviewVisual = sponsorStepVisual("review", pipeline);
  const liveVisual = sponsorStepVisual("live", pipeline);

  const toneBorder =
    msg.tone === "success"
      ? "border-green-500/25 from-green-500/10"
      : msg.tone === "error"
        ? "border-red-500/25 from-red-500/10"
        : msg.tone === "pending"
          ? "border-amber-500/25 from-amber-500/10"
          : "border-violet-500/25 from-violet-500/10";

  return (
    <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1">
        <PipelineStep label="Pay fee" icon={<Wallet className="h-5 w-5" />} visual={payVisual} />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/50" />
        <PipelineStep label="Submit" icon={<Send className="h-5 w-5" />} visual={submitVisual} />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/50" />
        <PipelineStep label="Review" icon={<ShieldCheck className="h-5 w-5" />} visual={reviewVisual} />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground/50" />
        <PipelineStep label="Link live" icon={<Link2 className="h-5 w-5" />} visual={liveVisual} />
      </div>

      <div
        className={`rounded-xl border bg-gradient-to-b to-transparent p-4 sm:p-5 ${toneBorder}`}
      >
        <div className="flex items-center gap-2 mb-2">
          {pipeline.allLive ? (
            <Sparkles className="h-4 w-4 text-green-400" />
          ) : pipeline.active === "review" ? (
            <Clock className="h-4 w-4 text-amber-400 animate-pulse" />
          ) : (
            <Link2 className="h-4 w-4 text-violet-400" />
          )}
          <h3 className="text-sm font-semibold text-white">{msg.title}</h3>
        </div>
        <p className="text-sm text-muted-foreground">{msg.body}</p>
        {stats?.sponsor_ref_slug && pipeline.allLive && (
          <p className="mt-3 font-mono text-sm text-cyan-300/90 truncate">
            s24tx.com/ref/{stats.sponsor_ref_slug}
          </p>
        )}
      </div>
    </div>
  );
}
