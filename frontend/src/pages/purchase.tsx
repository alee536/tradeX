import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  useListPurchases,
  useCreatePurchase,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { getListPurchasesQueryKey } from "@workspace/api-client-react";
import { usePublicCoinSettings } from "@/hooks/use-public-coin-settings";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  Loader2,
  Wallet,
  CheckCircle2,
  Clock,
  XCircle,
  ArrowRight,
  Send,
  ShieldCheck,
  Coins,
} from "lucide-react";
import { formatCrypto } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { PurchaseDepositPanel } from "@/components/purchase/PurchaseDepositPanel";
import { PURCHASE_PAYMENT_WALLET } from "@/components/purchase/purchase-wallet";

const purchaseSchema = z.object({
  amount: z.coerce.number().positive("Amount must be positive"),
  txid: z.string().min(5, "Transaction hash is required"),
  wallet_address: z.string().min(10, "Your sending wallet address is required"),
});

type PurchaseFormValues = z.infer<typeof purchaseSchema>;

export default function Purchase() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: liveSettings } = usePublicCoinSettings();
  const { data: purchases, isLoading: loadingPurchases } = useListPurchases(
    { page: 1 },
    { query: { refetchInterval: 8000 } },
  );
  const createPurchase = useCreatePurchase();
  const [uploadModal, setUploadModal] = useState<{
    isOpen: boolean;
    purchaseId?: number;
    transactionId?: string;
  }>({ isOpen: false });
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const depositWallet =
    liveSettings?.usdt_wallet_address || PURCHASE_PAYMENT_WALLET;

  const form = useForm<PurchaseFormValues>({
    resolver: zodResolver(purchaseSchema),
    defaultValues: {
      amount: 0,
      txid: "",
      wallet_address: "",
    },
  });

  const watchedAmount = Number(form.watch("amount") || 0);
  const coinRate = Number(liveSettings?.coin_rate || 0);
  const estimatedCoins =
    coinRate > 0 && watchedAmount > 0 ? watchedAmount / coinRate : 0;

  const onSubmit = (data: PurchaseFormValues) => {
    createPurchase.mutate(
      { data },
      {
        onSuccess: () => {
          toast({
            title: "Purchase request submitted",
            description:
              "Your request is in the admin approval queue. Coins will appear on your dashboard after approval.",
          });
          form.reset();
          queryClient.invalidateQueries({ queryKey: getListPurchasesQueryKey() });
        },
        onError: (err: any) => {
          toast({
            title: "Submission failed",
            description: err?.message || "Failed to submit purchase request",
            variant: "destructive",
          });
        },
      },
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return (
          <Badge className="bg-green-500/20 text-green-500 border-green-500/50">
            <CheckCircle2 className="w-3 h-3 mr-1" /> Approved
          </Badge>
        );
      case "rejected":
        return (
          <Badge variant="destructive" className="bg-red-500/20 text-red-500 border-red-500/50">
            <XCircle className="w-3 h-3 mr-1" /> Rejected
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" className="bg-blue-500/20 text-blue-500 border-blue-500/50">
            <Clock className="w-3 h-3 mr-1" /> Pending approval
          </Badge>
        );
    }
  };

  const openDocumentUploadModal = (purchaseId: number, transactionId: string) => {
    setUploadModal({ isOpen: true, purchaseId, transactionId });
    setUploadedFiles([]);
  };

  const handleFileSelection = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleDocumentUpload = async () => {
    if (!uploadModal.purchaseId || uploadedFiles.length === 0) {
      toast({
        title: "No files selected",
        description: "Please select at least one file to upload.",
        variant: "destructive",
      });
      return;
    }

    setUploadingFile(true);
    try {
      for (const file of uploadedFiles) {
        const formData = new FormData();
        formData.append("document", file);

        const response = await fetch(
          `/api/purchases/${uploadModal.purchaseId}/upload-rejection-document`,
          {
            method: "POST",
            body: formData,
            credentials: "same-origin",
          },
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || "Failed to upload document");
        }
      }

      toast({
        title: "Documents uploaded successfully",
        description:
          "Your supporting documents have been submitted. Admins will review them shortly.",
      });

      setUploadModal({ isOpen: false });
      setUploadedFiles([]);
      queryClient.invalidateQueries({ queryKey: getListPurchasesQueryKey() });
    } catch (error) {
      toast({
        title: "Upload failed",
        description:
          error instanceof Error ? error.message : "Failed to upload documents",
        variant: "destructive",
      });
    } finally {
      setUploadingFile(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Purchase Tokens</h1>
        <p className="text-muted-foreground mt-2">
          Transfer USDT (BEP20), submit your payment details, then wait for admin approval.
        </p>
      </div>

      {/* Flow steps */}
      <div className="flex flex-wrap items-center justify-center gap-2 text-xs sm:text-sm text-muted-foreground rounded-xl border border-white/10 bg-black/20 px-4 py-3">
        <span className="flex items-center gap-1 text-cyan-300">
          <Wallet className="h-4 w-4" /> Pay
        </span>
        <ArrowRight className="h-3 w-3 opacity-40" />
        <span className="flex items-center gap-1">
          <Send className="h-4 w-4" /> Submit details
        </span>
        <ArrowRight className="h-3 w-3 opacity-40" />
        <span className="flex items-center gap-1">
          <ShieldCheck className="h-4 w-4" /> Admin queue
        </span>
        <ArrowRight className="h-3 w-3 opacity-40" />
        <span className="flex items-center gap-1 text-green-400/90">
          <Coins className="h-4 w-4" /> Coins on dashboard
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Deposit Instructions</CardTitle>
            <CardDescription>Send USDT (BEP20) to the address below, then fill the form</CardDescription>
          </CardHeader>
          <CardContent>
            <PurchaseDepositPanel
              walletAddress={depositWallet}
              minPurchase={liveSettings?.min_purchase}
              onCopied={() => toast({ title: "Deposit address copied" })}
            />
          </CardContent>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Purchase Form</CardTitle>
            <CardDescription>
              Enter the amount you sent and your transaction hash after transferring USDT
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="amount"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Amount sent (USDT)</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Wallet className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                          <Input
                            type="number"
                            step="any"
                            placeholder="0.00"
                            {...field}
                            className="pl-9 bg-black/20"
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="mt-2 space-y-2">
                  <div className="text-sm font-medium leading-none text-foreground">
                    Expected coins (after approval)
                  </div>
                  <Input
                    readOnly
                    value={
                      coinRate > 0 && watchedAmount > 0
                        ? (watchedAmount / coinRate).toLocaleString(undefined, {
                            maximumFractionDigits: 8,
                          })
                        : "0"
                    }
                    className="bg-black/10 font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Calculated as amount ÷ coin price. Credited to your dashboard once admin
                    approves and assigns coins.
                  </p>
                </div>

                <div className="rounded-2xl border border-cyan-500/20 bg-linear-to-br from-cyan-500/10 via-slate-950 to-slate-900 p-4 shadow-[0_0_40px_rgba(34,211,238,0.12)]">
                  <p className="text-xs uppercase tracking-[0.22em] text-cyan-300/80">
                    Live coin preview
                  </p>
                  <div className="mt-2 flex items-end justify-between gap-4">
                    <div>
                      <div className="text-3xl font-semibold text-white">
                        {estimatedCoins > 0
                          ? estimatedCoins.toLocaleString(undefined, {
                              maximumFractionDigits: 6,
                            })
                          : "0"}
                      </div>
                      <div className="text-sm text-muted-foreground">Coins you will receive</div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>Current rate</div>
                      <div className="font-mono text-cyan-300">
                        1 Coin ={" "}
                        {liveSettings
                          ? `${formatCrypto(Number(liveSettings.coin_rate || 0), liveSettings.currency_symbol || "USD")}`
                          : "Loading..."}
                      </div>
                    </div>
                  </div>
                </div>

                <FormField
                  control={form.control}
                  name="txid"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Transaction hash (TXID)</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Paste your BEP20 transaction hash"
                          {...field}
                          className="bg-black/20 font-mono text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="wallet_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Your sending wallet (BEP20)</FormLabel>
                      <FormControl>
                        <Input placeholder="0x..." {...field} className="bg-black/20 font-mono text-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold mt-4"
                  disabled={createPurchase.isPending}
                >
                  {createPurchase.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Submitting...
                    </>
                  ) : (
                    "Submit Purchase"
                  )}
                </Button>
                <p className="text-xs text-center text-muted-foreground">
                  Request goes to the admin approval queue. You will be notified when approved.
                </p>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Recent Purchases</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {loadingPurchases ? (
            Array(3)
              .fill(0)
              .map((_, i) => (
                <Card key={i} className="glass-panel opacity-50">
                  <CardContent className="p-6 space-y-3">
                    <div className="h-4 bg-white/10 rounded w-1/2 animate-pulse" />
                    <div className="h-8 bg-white/10 rounded w-3/4 animate-pulse" />
                  </CardContent>
                </Card>
              ))
          ) : purchases?.results?.length ? (
            purchases.results.slice(0, 6).map((purchase) => (
              <Card
                key={purchase.id}
                className="glass-panel hover:bg-white/[0.07] transition-colors"
              >
                <CardContent className="p-5 flex flex-col gap-2">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-mono text-muted-foreground">
                      {purchase.transaction_id}
                    </span>
                    {getStatusBadge(purchase.status)}
                  </div>
                  <div className="text-2xl font-bold text-white">
                    {formatCrypto(purchase.amount)}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Coins:{" "}
                    {(purchase as any).assigned_coins
                      ? formatCrypto(Number((purchase as any).assigned_coins), "24X")
                      : purchase.status === "approved"
                        ? "Approved — assigning"
                        : "Pending approval"}
                  </div>
                  {purchase.txid && (
                    <p className="text-xs font-mono text-muted-foreground truncate" title={purchase.txid}>
                      TX: {purchase.txid}
                    </p>
                  )}
                  <div className="text-xs text-muted-foreground mt-2">
                    Date: {new Date(purchase.created_at).toLocaleDateString()}
                  </div>
                  {purchase.status === "rejected" && purchase.rejection_reason && (
                    <div className="rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300 space-y-2">
                      <div>
                        <strong>Reason:</strong> {purchase.rejection_reason}
                      </div>
                      {purchase.rejection_notes && (
                        <div>
                          <strong>Notes:</strong> {purchase.rejection_notes}
                        </div>
                      )}
                      <button
                        type="button"
                        className="text-white bg-red-500/30 hover:bg-red-500/50 px-2 py-1 rounded text-xs font-semibold transition-colors mt-2 w-full"
                        onClick={() =>
                          openDocumentUploadModal(purchase.id, purchase.transaction_id)
                        }
                      >
                        Upload Supporting Documents
                      </button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <div className="col-span-full p-8 text-center text-muted-foreground border border-white/10 border-dashed rounded-lg">
              No purchase history found.
            </div>
          )}
        </div>
      </div>

      {uploadModal.isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="glass-panel w-full max-w-md">
            <CardHeader>
              <CardTitle>Upload Supporting Documents</CardTitle>
              <CardDescription>Purchase {uploadModal.transactionId}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-3">
                  Upload documents (PDF, images, etc.) to support your appeal. Max 10MB per file.
                </p>

                <div
                  className="border-2 border-dashed border-white/20 rounded-lg p-6 text-center cursor-pointer hover:border-white/40 transition-colors"
                  onClick={() => document.getElementById("fileInput")?.click()}
                >
                  <input
                    id="fileInput"
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.gif,.doc,.docx,.xls,.xlsx"
                    onChange={handleFileSelection}
                    className="hidden"
                  />
                  <p className="text-sm text-muted-foreground">
                    {uploadedFiles.length === 0
                      ? "Click to select files or drag and drop"
                      : `${uploadedFiles.length} file(s) selected`}
                  </p>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {uploadedFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 bg-white/5 rounded"
                      >
                        <span className="text-sm">{file.name}</span>
                        <button
                          type="button"
                          onClick={() =>
                            setUploadedFiles(uploadedFiles.filter((_, i) => i !== idx))
                          }
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-blue-500/10 border border-blue-500/20 rounded p-3 text-xs text-blue-300">
                <strong>Note:</strong> Admins will review your documents and may revert the
                rejection if they are satisfied with your explanation.
              </div>
            </CardContent>
            <div className="flex gap-2 p-6 border-t border-white/10">
              <Button
                variant="outline"
                onClick={() => {
                  setUploadModal({ isOpen: false });
                  setUploadedFiles([]);
                }}
                disabled={uploadingFile}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDocumentUpload}
                disabled={uploadingFile || uploadedFiles.length === 0}
                className="flex-1"
              >
                {uploadingFile ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...
                  </>
                ) : (
                  "Upload Documents"
                )}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
