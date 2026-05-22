import { useEffect, useState } from "react";
import {
  PurchaseClaimSchedule,
  PurchaseClaimStage,
  useCreatePurchaseClaim,
} from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { formatCrypto, formatCurrency } from "@/lib/utils";
import {
  CheckCircle2,
  Clock,
  Hourglass,
  Loader2,
  Lock,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { ClaimPipelineHero } from "./ClaimPipelineHero";

function formatCountdown(totalSeconds?: number | null): string {
  if (totalSeconds == null) return "—";
  const s = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

function getStageButtonConfig(stage: PurchaseClaimStage, isSubmitting: boolean) {
  const pctLabel = `Claim ${stage.percent}%`;

  switch (stage.state) {
    case "approved":
      return {
        label: "In wallet",
        className:
          "w-full bg-white/10 text-muted-foreground border border-white/10 cursor-not-allowed hover:bg-white/10",
        disabled: true,
      };
    case "pending":
      return {
        label: "Processing…",
        className:
          "w-full bg-green-500/15 text-green-300/90 border border-green-500/30 cursor-not-allowed hover:bg-green-500/15",
        disabled: true,
      };
    case "rejected":
      return {
        label: isSubmitting ? "Submitting…" : `Resubmit ${stage.percent}%`,
        className: isSubmitting
          ? "w-full bg-green-600/70 text-white cursor-wait"
          : "w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold",
        disabled: isSubmitting || !stage.can_request,
      };
    case "available":
      return {
        label: isSubmitting ? "Submitting…" : pctLabel,
        className: isSubmitting
          ? "w-full bg-green-600/70 text-white cursor-wait"
          : "w-full bg-green-600 hover:bg-green-700 text-white font-semibold",
        disabled: isSubmitting || !stage.can_request,
      };
    default:
      return {
        label: pctLabel,
        className:
          "w-full bg-white/5 text-muted-foreground/70 border border-white/10 cursor-not-allowed hover:bg-white/5",
        disabled: true,
      };
  }
}

function stageCardShellClass(stage: PurchaseClaimStage) {
  if (stage.state === "approved") {
    return "border-green-500/25 bg-green-500/5 opacity-90";
  }
  if (stage.state === "available") {
    return "border-amber-500/40 bg-amber-500/5 ring-1 ring-amber-500/20";
  }
  if (stage.state === "pending") {
    return "border-blue-500/25 bg-blue-500/5";
  }
  return "border-white/10 bg-black/30";
}

function stageBadge(stage: PurchaseClaimStage) {
  switch (stage.state) {
    case "approved":
      return (
        <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
          <CheckCircle2 className="w-3 h-3 mr-1" /> In wallet
        </Badge>
      );
    case "pending":
      return (
        <Badge className="bg-green-500/20 text-green-400 border-green-500/40">
          <Hourglass className="w-3 h-3 mr-1" /> Crediting…
        </Badge>
      );
    case "rejected":
      return (
        <Badge className="bg-red-500/20 text-red-400 border-red-500/40">
          <XCircle className="w-3 h-3 mr-1" /> Rejected
        </Badge>
      );
    case "available":
      return (
        <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/40">
          <ShieldCheck className="w-3 h-3 mr-1" /> Ready to claim
        </Badge>
      );
    default:
      return (
        <Badge className="bg-white/5 text-muted-foreground border-white/10">
          <Lock className="w-3 h-3 mr-1" /> Locked
        </Badge>
      );
  }
}

function StageCard({
  schedule,
  stage,
  onClaim,
  isSubmitting,
  walletAddress,
  onWalletChange,
  showWalletField,
}: {
  schedule: PurchaseClaimSchedule;
  stage: PurchaseClaimStage;
  onClaim: (stageNo: 1 | 2 | 3) => void;
  isSubmitting: boolean;
  walletAddress: string;
  onWalletChange: (value: string) => void;
  showWalletField: boolean;
}) {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(
    stage.seconds_until_unlock ?? null,
  );

  useEffect(() => {
    setSecondsLeft(stage.seconds_until_unlock ?? null);
    if (stage.seconds_until_unlock == null) {
      return;
    }
    const id = setInterval(() => {
      setSecondsLeft((prev) =>
        prev == null ? prev : Math.max(0, prev - 1),
      );
    }, 1000);
    return () => clearInterval(id);
  }, [stage.seconds_until_unlock, stage.stage]);

  const canClick = stage.can_request && !isSubmitting;
  const button = getStageButtonConfig(stage, isSubmitting);

  return (
    <div
      className={`flex-1 min-w-[180px] rounded-lg border p-4 space-y-3 transition-colors ${stageCardShellClass(stage)}`}
    >
      <div className="flex justify-between items-center">
        <div className="text-sm font-semibold text-white">
          Stage {stage.stage}
        </div>
        {stageBadge(stage)}
      </div>

      <div className="text-2xl font-bold text-white">
        {formatCrypto(stage.amount_coins)}
      </div>
      <div className="text-xs text-muted-foreground">
        ≈ {formatCurrency(stage.amount_usdt)}
      </div>

      <div className="text-xs text-muted-foreground flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {stage.state === "locked"
          ? `Unlocks in ${formatCountdown(secondsLeft)}`
          : stage.state === "available"
            ? "Available now"
            : stage.state === "pending"
              ? "Adding to wallet…"
              : stage.state === "approved"
                ? `Credited ${stage.claim?.approved_at ? new Date(stage.claim.approved_at).toLocaleString() : ""}`
                : stage.claim?.rejection_reason || "Rejected"}
      </div>

      <Button
        size="sm"
        className={button.className}
        disabled={button.disabled}
        onClick={() => canClick && onClaim(stage.stage)}
      >
        {isSubmitting && stage.can_request ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting…
          </>
        ) : (
          button.label
        )}
      </Button>
    </div>
  );
}

export function ClaimScheduleCard({
  schedule,
  onSuccess,
}: {
  schedule: PurchaseClaimSchedule;
  onSuccess: () => void;
}) {
  const { toast } = useToast();
  const claimMutation = useCreatePurchaseClaim({
    mutation: {
      onSuccess: (data) => {
        toast({
          title: "Coins added to wallet",
          description: data.message,
        });
        onSuccess();
      },
      onError: (err: unknown) => {
        toast({
          title: "Claim failed",
          description:
            (err as { message?: string })?.message || "Unable to submit claim.",
          variant: "destructive",
        });
      },
    },
  });

  const submit = (stageNo: 1 | 2 | 3) => {
    claimMutation.mutate({
      data: {
        purchase_id: schedule.purchase_id,
        stage: stageNo,
        wallet_address: wallet.trim() || undefined,
      },
    });
  };

  const actionableStage = schedule.stages.find((s) => s.can_request);

  return (
    <Card className="glass-panel border-l-4 border-l-green-500">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-base">Claim Schedule</span>
            <p className="text-xs text-muted-foreground font-normal mt-1">
              Purchase{" "}
              <span className="font-mono text-cyan-300">
                {schedule.transaction_id}
              </span>{" "}
              · {formatCrypto(schedule.total_coins)} (
              {formatCurrency(schedule.total_usdt)})
            </p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ClaimPipelineHero schedule={schedule} />
        <p className="text-xs text-muted-foreground mb-3">
          Staged payouts: 50% · 25% · 25% — claim adds coins to your wallet instantly. Withdrawals still need admin approval.
        </p>
        <div className="flex flex-wrap gap-3">
          {schedule.stages.map((stage) => (
            <StageCard
              key={stage.stage}
              schedule={schedule}
              stage={stage}
              onClaim={submit}
              isSubmitting={claimMutation.isPending}
              walletAddress=""
              onWalletChange={() => {}}
              showWalletField={false}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
