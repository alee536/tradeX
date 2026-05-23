/** Shared fetch for landing page stats (coin rate, supply, profit %). */

export type HomePublicSettings = {
  coin_rate: string | number;
  currency_symbol: string;
  total_coin_supply?: string | number;
  profit_percentage?: string | number | null;
  profit_enabled?: boolean;
  last_updated_at?: string;
  min_purchase?: string | number;
  max_purchase?: string | number;
  usdt_wallet_address?: string;
  sponsor_payment_wallet_address?: string;
  sponsor_access_fee_usdt?: number;
};

export async function fetchHomePublicSettings(): Promise<HomePublicSettings> {
  const response = await fetch("/api/settings/public");
  if (!response.ok) {
    throw new Error("Failed to load public settings");
  }
  return response.json();
}

export function formatCoinRate(
  rate: string | number | undefined,
  symbol = "USD",
): string {
  const n = Number(rate);
  if (!Number.isFinite(n) || n <= 0) return "—";
  const prefix = symbol === "USD" || symbol === "$" ? "$" : `${symbol} `;
  return `${prefix}${n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

export function formatTotalSupply(supply: string | number | undefined): string {
  const n = Number(supply);
  if (!Number.isFinite(n) || n < 0) return "—";
  return Math.round(n).toLocaleString();
}

/** Admin profit % for landing calculator; defaults to 10% when unset. */
export function landingProfitPercent(
  profitPercentage: string | number | null | undefined,
): number {
  const n = Number(profitPercentage);
  if (Number.isFinite(n) && n > 0) return n;
  return 10;
}

export function planReturnAmount(
  investUsd: number,
  profitPercent: number,
): { profit: number; total: number } {
  const profit = investUsd * (profitPercent / 100);
  return { profit, total: investUsd + profit };
}
