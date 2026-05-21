import {
  useClaimProfitReward,
  useGetDashboardSummary,
  useListPurchases,
} from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCrypto, formatCurrency } from "@/lib/utils";
import { Wallet, ArrowDownToLine, Clock, Users, AlertCircle, TrendingUp, Gift, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { useLocation } from "wouter";

// Simple animated counter component
function AnimatedCounter({ value, isCurrency = false, symbol = "24TX" }: { value: number, isCurrency?: boolean, symbol?: string }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let start = 0;
    const duration = 1000; // 1 second
    const increment = value / (duration / 16); // 60fps
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(start);
      }
    }, 16);

    return () => clearInterval(timer);
  }, [value]);

  if (isCurrency) {
    return <span>{formatCurrency(displayValue)}</span>;
  }
  return <span>{formatCrypto(displayValue, symbol)}</span>;
}

function formatCountdown(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

function ProfitRewardCard({
  profit,
  isLoading,
  onClaimSuccess,
}: {
  profit: {
    enabled: boolean;
    profit_percentage?: number;
    profit_cycle_hours?: number;
    base_usdt?: number;
    estimated_profit_usdt?: number;
    total_after_profit_usdt?: number;
    claimable_usdt?: number;
    claimable_coins?: number;
    can_claim?: boolean;
    total_claimed_usdt?: number;
    total_claimed_coins?: number;
    next_claim_at?: string | null;
    seconds_until_claim?: number | null;
  } | undefined;
  isLoading: boolean;
  onClaimSuccess?: () => void;
}) {
  const claimMutation = useClaimProfitReward({
    mutation: {
      onSuccess: () => {
        onClaimSuccess?.();
      },
    },
  });
  const [secondsLeft, setSecondsLeft] = useState<number | null>(
    profit?.seconds_until_claim ?? null
  );

  useEffect(() => {
    if (!profit?.enabled) return;
    setSecondsLeft(profit.seconds_until_claim ?? null);
    const id = setInterval(() => {
      setSecondsLeft((prev) => (prev === null ? null : Math.max(0, prev - 1)));
    }, 1000);
    return () => clearInterval(id);
  }, [profit?.enabled, profit?.seconds_until_claim]);

  if (isLoading) {
    return (
      <Card className="glass-panel border-l-4 border-l-amber-500 md:col-span-2">
        <CardContent className="p-6">
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!profit?.enabled) return null;

  return (
    <Card className="glass-panel border-l-4 border-l-amber-500 md:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-amber-400" />
          Profit / Reward
        </CardTitle>
        <span className="text-xs font-semibold text-amber-300 bg-amber-500/10 px-2 py-1 rounded">
          {profit.profit_percentage ?? 0}% active
        </span>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Purchase base (USDT)</p>
            <p className="text-xl font-bold text-white">{formatCurrency(profit.base_usdt ?? 0)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Estimated profit</p>
            <p className="text-xl font-bold text-amber-300">
              +{formatCurrency(profit.estimated_profit_usdt ?? 0)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Total after profit</p>
            <p className="text-xl font-bold text-green-400">
              {formatCurrency(profit.total_after_profit_usdt ?? 0)}
            </p>
          </div>
        </div>
        {(profit.total_claimed_usdt ?? 0) > 0 && (
          <p className="text-xs text-muted-foreground mt-3">
            Lifetime claimed: {formatCurrency(profit.total_claimed_usdt ?? 0)} (
            {formatCrypto(profit.total_claimed_coins ?? 0)})
          </p>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-muted-foreground border-t border-white/10 pt-4">
          <Gift className="h-4 w-4 text-amber-400 shrink-0" />
          {profit.can_claim ? (
            <span className="text-green-400 font-medium">Reward ready to claim</span>
          ) : (
            <span>
              Next reward:{" "}
              <span className="text-white font-medium">
                {secondsLeft !== null ? formatCountdown(secondsLeft) : "—"}
              </span>
              {profit.profit_cycle_hours ? (
                <span className="ml-2">(every {profit.profit_cycle_hours}h)</span>
              ) : null}
            </span>
          )}
          {profit.next_claim_at && !profit.can_claim && (
            <span className="text-xs w-full sm:w-auto">
              at {new Date(profit.next_claim_at).toLocaleString()}
            </span>
          )}
          <Button
            size="sm"
            className="ml-auto bg-amber-500 hover:bg-amber-600 text-black font-semibold"
            disabled={!profit.can_claim || claimMutation.isPending}
            onClick={() => claimMutation.mutate()}
          >
            {claimMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Claiming…
              </>
            ) : (
              `Claim +${formatCurrency(profit.claimable_usdt ?? profit.estimated_profit_usdt ?? 0)}`
            )}
          </Button>
        </div>
        {claimMutation.isError && (
          <p className="text-xs text-red-400 mt-2">
            {(claimMutation.error as Error)?.message || "Claim failed. Try again later."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: summary, isLoading, refetch } = useGetDashboardSummary();
  const { data: purchases } = useListPurchases({ page: 1 }, { query: { refetchInterval: 8000 } });
  const [, setLocation] = useLocation();
  const rejectedPurchases = purchases?.results?.filter((p) => p.status === "rejected") || [];

  // Poll dashboard summary every 8 seconds to show assigned coins without reload
  useEffect(() => {
    const id = setInterval(() => {
      refetch?.();
    }, 8000);
    return () => clearInterval(id);
  }, [refetch]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground mt-2">Welcome to your trading terminal.</p>
      </div>

      {/* Rejection Alerts */}
      {rejectedPurchases.length > 0 && (
        <div className="space-y-2">
          {rejectedPurchases.map((purchase) => (
            <Card key={purchase.id} className="glass-panel border-l-4 border-l-red-500 bg-red-500/5">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-red-300 mb-1">
                      Purchase {purchase.transaction_id} was rejected
                    </h3>
                    <p className="text-sm text-red-200/80 mb-2">
                      <strong>Reason:</strong> {purchase.rejection_reason}
                    </p>
                    {purchase.rejection_notes && (
                      <p className="text-sm text-red-200/70 mb-2">
                        <strong>Admin Notes:</strong> {(purchase as any).rejection_notes}
                      </p>
                    )}
                    <button
                      onClick={() => setLocation("/purchase")}
                      className="text-sm font-semibold text-red-300 hover:text-red-200 transition-colors"
                    >
                      View Details & Upload Documents →
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass-panel border-l-4 border-l-primary">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Coins
            </CardTitle>
            <Wallet className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-30" />
            ) : (
              <div className="text-2xl font-bold text-white">
                <AnimatedCounter value={summary?.total_purchased || 0} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-l-4 border-l-green-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Available Coins
            </CardTitle>
            <ArrowDownToLine className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-30" />
            ) : (
              <div className="space-y-1">
                <div className="text-2xl font-bold text-white">
                  <AnimatedCounter value={(summary as any)?.available_withdrawal || 0} />
                </div>
                <div className="text-xs text-muted-foreground">
                  USDT equivalent: {formatCurrency((summary as any)?.available_withdrawal_usdt || 0)}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Latest rate: 1 Coin = {formatCurrency((summary as any)?.current_coin_rate || 0)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Locked Coins
            </CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-30" />
            ) : (
              <div className="space-y-1">
                <div className="text-2xl font-bold text-white">
                  <AnimatedCounter value={summary?.pending_withdrawal || 0} />
                </div>
                <div className="text-xs text-muted-foreground">Assigned but still locked by vesting</div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-l-4 border-l-secondary">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              SPONSER REWARDS
            </CardTitle>
            <Users className="h-4 w-4 text-secondary" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-30" />
            ) : (
              <div className="text-2xl font-bold text-white">
                <AnimatedCounter value={summary?.sponsor_earnings || 0} isCurrency />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ProfitRewardCard
          profit={summary?.profit}
          isLoading={isLoading}
          onClaimSuccess={() => refetch?.()}
        />
      </div>
      
      {/* More dashboard content could go here, like recent transactions */}
      <div className="mt-8 rounded-xl border border-white/10 glass-panel p-8 text-center">
         <h2 className="text-xl font-medium text-white mb-2">Terminal Active</h2>
         <p className="text-muted-foreground">All systems operational. Ready for trading execution.</p>
      </div>
    </div>
  );
}
