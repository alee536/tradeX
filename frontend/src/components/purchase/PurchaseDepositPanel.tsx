import { useState } from "react";
import { Copy, CheckCircle2, Wallet, QrCode, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { copyToClipboard } from "@/lib/utils";
import { PURCHASE_DEPOSIT_QR_SRC, PURCHASE_PAYMENT_WALLET } from "./purchase-wallet";

type PurchaseDepositPanelProps = {
  walletAddress: string;
  minPurchase?: number | string;
  onCopied?: () => void;
};

export function PurchaseDepositPanel({
  walletAddress,
  minPurchase,
  onCopied,
}: PurchaseDepositPanelProps) {
  const [copied, setCopied] = useState(false);
  const address = walletAddress || PURCHASE_PAYMENT_WALLET;

  const handleCopy = async () => {
    await copyToClipboard(address);
    setCopied(true);
    onCopied?.();
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-cyan-500/25 bg-gradient-to-br from-cyan-500/10 via-black/30 to-black/20 p-5">
      <div className="flex items-start gap-2 mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
        <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-100/90">
          Only send <strong className="text-white">USDT on BSC / BEP20</strong> to this address.
          Other networks may result in lost funds.
        </p>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <Wallet className="h-5 w-5 text-cyan-400" />
        <div>
          <p className="font-semibold text-white">Deposit USDT (BEP20)</p>
          <p className="text-xs text-muted-foreground">Scan QR or copy the receiver address</p>
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-[auto_1fr] items-start">
        <div className="flex flex-col items-center gap-2 mx-auto sm:mx-0">
          <div className="rounded-xl bg-white p-2 shadow-lg max-w-[200px]">
            <img
              src={PURCHASE_DEPOSIT_QR_SRC}
              alt="USDT BEP20 deposit QR code"
              width={180}
              height={180}
              className="rounded-lg w-full h-auto object-contain"
            />
          </div>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <QrCode className="h-3 w-3" /> Scan to pay
          </span>
        </div>

        <div className="space-y-3 min-w-0">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
              Receiver (BSC / BEP20)
            </p>
            <div className="flex items-start gap-2">
              <code className="flex-1 text-xs sm:text-sm bg-black/50 px-3 py-2.5 rounded-lg border border-white/10 break-all font-mono text-cyan-300">
                {address}
              </code>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleCopy}
                className="shrink-0 border-cyan-500/30"
              >
                {copied ? (
                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <ol className="text-sm text-muted-foreground space-y-1.5 list-decimal list-inside">
            <li>Transfer your USDT amount to the address above (BEP20 only).</li>
            <li>Enter the same amount and your blockchain TXID in the form.</li>
            <li>Click <strong className="text-white">Submit Purchase</strong> — request joins the admin approval queue.</li>
            <li>After approval, coins appear on your dashboard.</li>
          </ol>
          {minPurchase != null && Number(minPurchase) > 0 && (
            <p className="text-xs text-muted-foreground">
              Minimum purchase: <strong className="text-white">{minPurchase} USDT</strong>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
