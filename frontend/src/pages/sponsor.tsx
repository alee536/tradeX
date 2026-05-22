import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  useGetSponsorStats,
  useListSponsoredUsers,
  useCreateSponsorAccessRequest,
  getGetSponsorStatsQueryKey,
} from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCrypto, formatCurrency, copyToClipboard } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { SponsorAccessHero } from "@/components/sponsor/SponsorAccessHero";
import { SponsorStatCard } from "@/components/sponsor/SponsorStatCard";
import {
  Loader2,
  Copy,
  CheckCircle2,
  Users,
  Target,
  Gift,
  Search,
  Link2,
  Clock,
  AlertCircle,
  Share2,
  Network,
  Wallet,
  Send,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

const requestSchema = z.object({
  ref_slug: z
    .string()
    .min(4, "Code must be at least 4 characters")
    .max(20, "Code must be at most 20 characters")
    .regex(/^[A-Za-z0-9]+$/, "Letters and numbers only (e.g. ALEE24)"),
  payment_txid: z.string().min(5, "Transaction ID is required"),
  payment_wallet: z.string().min(10, "Your wallet address is required"),
});

type RequestFormValues = z.infer<typeof requestSchema>;

function accessStatusLabel(status?: string) {
  switch (status) {
    case "active":
      return { text: "Active", className: "bg-green-500/20 text-green-500" };
    case "pending":
      return { text: "Pending review", className: "bg-amber-500/20 text-amber-400" };
    case "rejected":
      return { text: "Rejected", className: "bg-red-500/20 text-red-400" };
    default:
      return { text: "Not activated", className: "bg-white/10 text-muted-foreground" };
  }
}

export default function Sponsor() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useGetSponsorStats();
  const { data: users, isLoading: loadingUsers } = useListSponsoredUsers({
    page,
    search: searchQuery || undefined,
  });

  const { data: liveSettings } = useQuery({
    queryKey: ["public-coin-settings"],
    queryFn: async () => {
      const response = await fetch("/api/settings/public");
      if (!response.ok) throw new Error("Failed to load settings");
      return response.json() as Promise<{
        usdt_wallet_address: string;
        sponsor_payment_wallet_address?: string;
        sponsor_access_fee_usdt?: number;
      }>;
    },
  });

  const accessMutation = useCreateSponsorAccessRequest({
    mutation: {
      onSuccess: () => {
        toast({
          title: "Request submitted",
          description: "Admin will review your payment and activate your sponsor link.",
        });
        queryClient.invalidateQueries({ queryKey: getGetSponsorStatsQueryKey() });
        refetchStats();
        form.reset();
      },
      onError: (err: any) => {
        toast({
          title: "Request failed",
          description: err?.message || "Could not submit sponsor access request.",
          variant: "destructive",
        });
      },
    },
  });

  const form = useForm<RequestFormValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: { ref_slug: "", payment_txid: "", payment_wallet: "" },
  });

  const isActive = stats?.sponsor_access_status === "active";
  const isPending =
    stats?.sponsor_access_status === "pending" || !!stats?.pending_request;
  const canRequest = stats?.can_request ?? false;
  const fee = stats?.access_fee_usdt ?? liveSettings?.sponsor_access_fee_usdt ?? 5;
  const sponsorPaymentWallet =
    stats?.sponsor_payment_wallet
    ?? liveSettings?.sponsor_payment_wallet_address
    ?? "";
  const publicLink = stats?.sponsor_link;
  const statusBadge = accessStatusLabel(stats?.sponsor_access_status);

  const handleCopyLink = async () => {
    if (publicLink) {
      await copyToClipboard(publicLink);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
      toast({ title: "Sponsor link copied" });
    }
  };

  const handleCopyCode = async () => {
    if (stats?.sponsor_code) {
      await copyToClipboard(stats.sponsor_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
      toast({ title: "Sponsor code copied" });
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(search);
    setPage(1);
  };

  const onSubmitRequest = (values: RequestFormValues) => {
    accessMutation.mutate({
      data: {
        ref_slug: values.ref_slug.toUpperCase(),
        payment_txid: values.payment_txid,
        payment_wallet: values.payment_wallet,
      },
    });
  };

  const handleCopyWallet = async () => {
    if (sponsorPaymentWallet) {
      await copyToClipboard(sponsorPaymentWallet);
      toast({ title: "Sponsor payment wallet copied" });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page hero */}
      <div className="relative overflow-hidden rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-600/15 via-transparent to-cyan-500/10 p-6 sm:p-8 animate-in fade-in duration-500">
        <div className="absolute -top-16 -right-16 h-48 w-48 rounded-full bg-violet-500/20 blur-3xl animate-pulse pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 h-40 w-40 rounded-full bg-cyan-500/15 blur-3xl animate-pulse pointer-events-none [animation-delay:1s]" />
        <div className="relative flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-500/20 border border-violet-400/30 shadow-[0_0_24px_rgba(139,92,246,0.35)]">
            <Network className="h-7 w-7 text-violet-300" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight bg-gradient-to-r from-violet-200 via-cyan-200 to-violet-100 bg-clip-text text-transparent">
              Sponsor
            </h1>
            <p className="text-muted-foreground mt-2 max-w-xl">
              Grow your team with a short ref link. One-time {fee} USDT fee — lifetime access after approval.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-green-400/90 bg-green-500/10 border border-green-500/20 rounded-full px-3 py-1.5 shrink-0">
            <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
            Referral program
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SponsorStatCard
          icon={<Gift className="h-6 w-6" />}
          label="Total earnings"
          value={formatCurrency(stats?.sponsor_earnings || 0)}
          sub="Auto-credited"
          accent="amber"
          loading={loadingStats}
          delayMs={0}
        />
        <SponsorStatCard
          icon={<Users className="h-6 w-6" />}
          label="Total network"
          value={stats?.total_sponsored ?? 0}
          accent="violet"
          loading={loadingStats}
          delayMs={80}
        />
        <SponsorStatCard
          icon={<Target className="h-6 w-6" />}
          label="Active traders"
          value={stats?.active_sponsored ?? 0}
          accent="green"
          loading={loadingStats}
          delayMs={160}
        />
        <SponsorStatCard
          icon={<Share2 className="h-6 w-6" />}
          label="Network purchases"
          value={stats?.sponsored_purchases ?? 0}
          accent="cyan"
          loading={loadingStats}
          delayMs={240}
        />
      </div>

      {/* Access card + pipeline */}
      <Card className="glass-panel border-l-4 border-l-violet-500/60 overflow-hidden">
        <CardHeader className="flex flex-row items-start justify-between gap-4 border-b border-white/5 bg-gradient-to-r from-violet-500/5 to-transparent">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5 text-violet-400" />
              Sponsor Link Access
            </CardTitle>
            <CardDescription>
              s24tx.com/ref/YOURCODE — clean, shareable, lifetime after approval
            </CardDescription>
          </div>
          <Badge className={`border-none shrink-0 ${statusBadge.className}`}>{statusBadge.text}</Badge>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {loadingStats ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : (
            <>
              <SponsorAccessHero stats={stats} fee={fee} />

              {isActive && publicLink ? (
                <div className="space-y-4 animate-in fade-in duration-300">
                  <div className="flex items-center gap-2">
                    <div className="bg-black/40 border border-violet-500/20 px-4 py-3 rounded-lg flex-1 text-sm font-mono truncate text-cyan-300 shadow-inner">
                      {publicLink}
                    </div>
                    <Button
                      onClick={handleCopyLink}
                      className="bg-violet-600/80 hover:bg-violet-600 text-white border border-violet-400/40 shadow-[0_0_16px_rgba(139,92,246,0.3)]"
                    >
                      {copiedLink ? (
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                      ) : (
                        <Copy className="h-4 w-4 mr-2" />
                      )}
                      Copy Link
                    </Button>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <span>
                      Code: <strong className="text-white font-mono">{stats?.sponsor_ref_slug}</strong>
                    </span>
                    {stats?.sponsor_activated_at && (
                      <span>Activated: {new Date(stats.sponsor_activated_at).toLocaleDateString()}</span>
                    )}
                    <Badge variant="outline" className="text-green-400 border-green-500/30">
                      {stats?.sponsor_payment_status === "paid" ? "Paid" : stats?.sponsor_payment_status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="bg-black/40 border border-white/10 px-4 py-2 rounded-md font-mono font-bold tracking-widest text-white">
                      {stats?.sponsor_code || "---"}
                    </div>
                    <Button onClick={handleCopyCode} variant="outline" className="border-white/10 bg-black/20">
                      {copiedCode ? <CheckCircle2 className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                    <span className="text-xs text-muted-foreground">Legacy internal code</span>
                  </div>
                </div>
              ) : isPending ? (
                <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent p-4 animate-in fade-in">
                  <div className="p-2 rounded-lg bg-amber-500/20">
                    <Clock className="h-5 w-5 text-amber-400 animate-pulse" />
                  </div>
                  <div>
                    <p className="font-medium text-amber-200">Request pending admin review</p>
                    {stats?.pending_request && (
                      <p className="text-sm text-muted-foreground mt-1">
                        Code <code className="text-violet-300">{stats.pending_request.ref_slug}</code> ·{" "}
                        {stats.pending_request.fee_usdt} USDT
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      You cannot submit another request until this is approved or rejected.
                    </p>
                  </div>
                </div>
              ) : canRequest ? (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 to-black/20 p-4 text-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <Wallet className="h-4 w-4 text-violet-400" />
                      <p className="font-medium text-white">One-time fee: {fee} USDT (BEP20)</p>
                    </div>
                    <p className="text-muted-foreground mb-3">
                      Send exactly {fee} USDT to the platform wallet, then submit proof and your desired code.
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <code className="text-xs bg-black/50 px-3 py-2 rounded-lg border border-white/10 break-all font-mono">
                        {sponsorPaymentWallet || "Loading wallet..."}
                      </code>
                      <Button type="button" size="sm" variant="outline" onClick={handleCopyWallet} className="border-violet-500/30">
                        <Copy className="h-3 w-3 mr-1" /> Copy
                      </Button>
                    </div>
                  </div>

                  <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmitRequest)} className="space-y-4 max-w-lg">
                      <FormField
                        control={form.control}
                        name="ref_slug"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Desired referral code</FormLabel>
                            <FormControl>
                              <Input
                                placeholder="ALEE24"
                                className="font-mono uppercase bg-black/30 border-violet-500/20 focus-visible:ring-violet-500/50"
                                {...field}
                                onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="payment_txid"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Payment transaction ID</FormLabel>
                            <FormControl>
                              <Input placeholder="BEP20 tx hash" className="bg-black/30 border-white/10" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="payment_wallet"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Your sending wallet address</FormLabel>
                            <FormControl>
                              <Input placeholder="0x..." className="bg-black/30 border-white/10" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <Button
                        type="submit"
                        disabled={accessMutation.isPending}
                        className="w-full sm:w-auto bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white border-0 shadow-[0_0_20px_rgba(139,92,246,0.35)]"
                      >
                        {accessMutation.isPending ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting...
                          </>
                        ) : (
                          <>
                            <Send className="h-4 w-4 mr-2" />
                            Request sponsor access ({fee} USDT)
                          </>
                        )}
                      </Button>
                    </form>
                  </Form>
                </div>
              ) : (
                <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4">
                  <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
                  <p className="text-sm text-muted-foreground">
                    {stats?.sponsor_access_status === "rejected"
                      ? "Your previous request was rejected. Contact support if you need to re-apply."
                      : "Sponsor link access is not available for your account."}
                  </p>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Members table */}
      <Card className="glass-panel border-white/10 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-violet-400" />
            <CardTitle>Sponsor Members</CardTitle>
          </div>
          <form onSubmit={handleSearch} className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by username..."
                className="pl-9 bg-black/20 border-white/10 focus-visible:ring-violet-500/40"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Button type="submit" variant="secondary" className="bg-violet-500/15 hover:bg-violet-500/25 text-violet-200 border border-violet-500/30">
              Search
            </Button>
          </form>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="rounded-lg border border-white/10 overflow-hidden bg-black/20">
            <Table>
              <TableHeader className="bg-violet-500/5">
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableHead>User</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Purchases</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingUsers ? (
                  <>
                    {[1, 2, 3].map((i) => (
                      <TableRow key={i} className="border-white/5">
                        <TableCell colSpan={4}>
                          <Skeleton className="h-10 w-full" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                ) : users?.results?.length ? (
                  users.results.map((user, idx) => (
                    <TableRow
                      key={user.id}
                      className="border-white/5 hover:bg-violet-500/5 transition-colors animate-in fade-in fill-mode-both"
                      style={{ animationDelay: `${idx * 40}ms`, animationDuration: "400ms" }}
                    >
                      <TableCell>
                        <div className="font-medium text-white">{user.username}</div>
                        <div className="text-xs text-muted-foreground">{user.full_name}</div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(user.date_joined).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {user.status === "active" ? (
                          <Badge className="bg-green-500/20 text-green-500 border-none">
                            <CheckCircle2 className="w-3 h-3 mr-1" /> Active
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">
                            Inactive
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-cyan-300/90">
                        {formatCrypto(user.purchase_amount || 0)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-28 text-center">
                      <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <Users className="h-8 w-8 opacity-30" />
                        <span>No network members yet. Share your link when active.</span>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
