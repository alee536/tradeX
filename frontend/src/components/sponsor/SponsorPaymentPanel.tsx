import { useState } from "react";
import { Copy, CheckCircle2, Wallet, QrCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { copyToClipboard } from "@/lib/utils";
import { SPONSOR_ACCESS_FEE_USDT } from "./sponsor-fee";

type SponsorPaymentPanelProps = {
  walletAddress: string;
  onCopied?: () => void;
};

function qrImageUrl(address: string): string {
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=12&data=${encodeURIComponent(address)}`;
}

export function SponsorPaymentPanel({ walletAddress, onCopied }: SponsorPaymentPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!walletAddress) return;
    await copyToClipboard(walletAddress);
    setCopied(true);
    onCopied?.();
    setTimeout(() => setCopied(false), 2000);
  };

  if (!walletAddress) {
    return (
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-6 text-center text-muted-foreground text-sm">
        Loading payment details...
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-500/10 via-black/30 to-black/20 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Wallet className="h-5 w-5 text-violet-400" />
        <div>
          <p className="font-semibold text-white">
            Pay exactly {SPONSOR_ACCESS_FEE_USDT} USDT (BEP20)
          </p>
          <p className="text-xs text-muted-foreground">One-time sponsor access fee</p>
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-[auto_1fr] items-start">
        <div className="flex flex-col items-center gap-2 mx-auto sm:mx-0">
          <div className="rounded-xl bg-white p-2 shadow-lg">
            <img
              src={qrImageUrl(walletAddress)}
              alt="Sponsor payment QR code"
              width={180}
              height={180}
              className="rounded-lg"
            />
          </div>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <QrCode className="h-3 w-3" /> Scan to pay
          </span>
        </div>

        <div className="space-y-3 min-w-0">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
              BNB Chain (BEP20) wallet
            </p>
            <div className="flex items-start gap-2">
              <code className="flex-1 text-xs sm:text-sm bg-black/50 px-3 py-2.5 rounded-lg border border-white/10 break-all font-mono text-cyan-300">
                {walletAddress}
              </code>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleCopy}
                className="shrink-0 border-violet-500/30"
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
            <li>Send <strong className="text-white">{SPONSOR_ACCESS_FEE_USDT} USDT</strong> on BNB Chain only.</li>
            <li>Copy your payment TXID and your sending wallet.</li>
            <li>Submit the form below with your desired sponsor code.</li>
            <li>Admin approves → your code and ref link are activated for life.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
