import { useGetDashboardSummary, useListPurchases } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCrypto, formatCurrency } from "@/lib/utils";
import { Wallet, ArrowDownToLine, Clock, Users, AlertCircle } from "lucide-react";
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
      
      {/* More dashboard content could go here, like recent transactions */}
      <div className="mt-8 rounded-xl border border-white/10 glass-panel p-8 text-center">
         <h2 className="text-xl font-medium text-white mb-2">Terminal Active</h2>
         <p className="text-muted-foreground">All systems operational. Ready for trading execution.</p>
      </div>
    </div>
  );
}
