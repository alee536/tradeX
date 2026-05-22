/** Platform BEP20 wallet for coin purchases — keep in sync with USDT_PURCHASE_WALLET_ADDRESS. */
export const PURCHASE_PAYMENT_WALLET =
  "0xffaFa174689476EdEfA9017Bf302F3E5095D9f48";

/**
 * Static QR in public/ — must use Vite BASE_URL so production (Django /static/frontend/) works.
 */
export function purchaseDepositQrUrl(): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}purchase-deposit-qr.png`;
}

/** Fallback if the bundled PNG fails to load (CDN / cache / path issues). */
export function purchaseDepositQrFallback(walletAddress: string): string {
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=12&data=${encodeURIComponent(walletAddress)}`;
}
