import {
  useGetDashboardSummary,
  useListPurchases,
} from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCrypto, formatCurrency } from "@/lib/utils";
import { Wallet, ArrowDownToLine, Clock, Users, AlertCircle, TrendingUp, Percent, Plus } from "lucide-react";
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
}: {
  profit: {
    enabled: boolean;
    profit_percentage?: number;
    stage1_hours?: number;
    stage2_hours?: number;
    stage3_hours?: number;
    purchase_count?: number;
    base_usdt?: number;
    estimated_profit_usdt?: number;
    total_after_profit_usdt?: number;
    total_claimed_usdt?: number;
    total_claimed_coins?: number;
    claim_via_stages?: boolean;
  } | undefined;
  isLoading: boolean;
}) {
  const [, setLocation] = useLocation();

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

  const pct = profit.profit_percentage ?? 0;
  const base = profit.base_usdt ?? 0;
  const profitAdd = profit.estimated_profit_usdt ?? 0;
  const total = profit.total_after_profit_usdt ?? 0;

  return (
    <Card className="glass-panel border-l-4 border-l-amber-500 md:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-amber-400" />
          Profit / Reward
        </CardTitle>
        <span className="text-xs font-semibold text-amber-300 bg-amber-500/10 px-2 py-1 rounded flex items-center gap-1">
          <Percent className="h-3 w-3" />
          {pct}% on your profile deposits
        </span>
      </CardHeader>
      <CardContent>
        {/* Formula: base + profit% = total */}
        <div className="mb-4 rounded-lg border border-amber-500/25 bg-gradient-to-r from-amber-500/10 to-transparent p-4">
          <p className="text-xs text-muted-foreground mb-2">
            Based on {(profit.purchase_count ?? 0)} approved purchase{(profit.purchase_count ?? 0) === 1 ? "" : "s"} on your profile
          </p>
          <div className="flex flex-wrap items-center gap-2 text-sm sm:text-base font-mono">
            <span className="text-white font-semibold">{formatCurrency(base)}</span>
            <Plus className="h-4 w-4 text-amber-400 shrink-0" />
            <span className="text-amber-300 font-semibold">
              {pct}% ({formatCurrency(profitAdd)})
            </span>
            <span className="text-muted-foreground">=</span>
            <span className="text-green-400 font-bold text-lg">{formatCurrency(total)}</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            Each purchase total includes +{pct}% profit. Claim on Withdraw: {profit.stage1_hours ?? 72}h → 50%, then +{profit.stage2_hours ?? 24}h → 25%, then +{profit.stage3_hours ?? 24}h → 25% (no admin approval).
          </p>
        </div>

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
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-white/10 pt-4">
          <Button
            size="sm"
            className="bg-amber-500 hover:bg-amber-600 text-black font-semibold"
            onClick={() => setLocation("/withdraw")}
          >
            <ArrowDownToLine className="h-4 w-4 mr-2" />
            Claim stages on Withdraw
          </Button>
          <p className="text-xs text-muted-foreground">
            Profit is paid in 50% / 25% / 25% slices — instant credit, not a withdrawal.
          </p>
        </div>
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

      {/* Profit rate highlight when enabled */}
      {!isLoading && summary?.profit?.enabled && (
        <Card className="glass-panel border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-transparent to-violet-500/5 animate-in fade-in duration-500">
          <CardContent className="p-4 flex flex-wrap items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20 border border-amber-500/30">
              <Percent className="h-6 w-6 text-amber-400" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <p className="text-sm font-semibold text-white">
                Your profit rate: {summary.profit.profit_percentage ?? 0}%
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Deposits {formatCurrency(summary.profit.base_usdt ?? 0)} + {summary.profit.profit_percentage ?? 0}% bonus{" "}
                <span className="text-amber-300">({formatCurrency(summary.profit.estimated_profit_usdt ?? 0)})</span>
                {" "}= {formatCurrency(summary.profit.total_after_profit_usdt ?? 0)} total value
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Total with profit</p>
              <p className="text-2xl font-bold text-green-400">
                {formatCurrency(summary.profit.total_after_profit_usdt ?? 0)}
              </p>
            </div>
          </CardContent>
        </Card>
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
              <div className="space-y-1">
                <div className="text-2xl font-bold text-white">
                  <AnimatedCounter value={summary?.total_purchased || 0} />
                </div>
                {summary?.profit?.enabled && (summary.profit.base_usdt ?? 0) > 0 && (
                  <p className="text-[11px] text-amber-300/90">
                    USDT deposits: {formatCurrency(summary.profit.base_usdt ?? 0)}
                  </p>
                )}
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
        <ProfitRewardCard profit={summary?.profit} isLoading={isLoading} />
      </div>
      
      {/* More dashboard content could go here, like recent transactions */}
      <div className="mt-8 rounded-xl border border-white/10 glass-panel p-8 text-center">
         <h2 className="text-xl font-medium text-white mb-2">Terminal Active</h2>
         <p className="text-muted-foreground">All systems operational. Ready for trading execution.</p>
      </div>
    </div>
  );
}
