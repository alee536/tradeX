import { useState } from "react";
import { useGetSponsorStats, useListSponsoredUsers } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCrypto, formatCurrency, copyToClipboard } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Copy, CheckCircle2, Users, Target, Gift, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Sponsor() {
  const { toast } = useToast();
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: stats, isLoading: loadingStats } = useGetSponsorStats();
  const { data: users, isLoading: loadingUsers } = useListSponsoredUsers({ 
    page,
    search: searchQuery || undefined
  });

  const handleCopyLink = async () => {
    if (stats?.sponsor_link) {
      const fullLink = `${window.location.origin}${stats.sponsor_link}`;
      await copyToClipboard(fullLink);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Sponsors</h1>
        <p className="text-muted-foreground mt-2">Build your trading network and earn rewards.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
         <Card className="glass-panel border-l-4 border-l-secondary md:col-span-2">
            <CardHeader>
               <CardTitle>Sponsor Link</CardTitle>
               <CardDescription>Share this link to invite new traders</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
               <div className="flex items-center gap-2">
                  <div className="bg-black/40 border border-white/10 px-4 py-2 rounded-md flex-1 text-sm font-mono truncate text-primary">
                     {stats ? `${window.location.origin}${stats.sponsor_link}` : "Loading..."}
                  </div>
                  <Button onClick={handleCopyLink} variant="secondary" className="bg-secondary/20 text-secondary hover:bg-secondary/30 border border-secondary/50">
                     {copiedLink ? <CheckCircle2 className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                     Copy Link
                  </Button>
               </div>
               <div className="flex items-center gap-2">
                  <div className="bg-black/40 border border-white/10 px-4 py-2 rounded-md w-48 text-center font-mono font-bold tracking-widest text-white">
                     {stats?.sponsor_code || "---"}
                  </div>
                  <Button onClick={handleCopyCode} variant="outline" className="border-white/10 bg-black/20">
                     {copiedCode ? <CheckCircle2 className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
               </div>
            </CardContent>
         </Card>

         <Card className="glass-panel">
            <CardHeader className="pb-2">
               <CardTitle className="text-sm font-medium text-muted-foreground">Total Earnings</CardTitle>
            </CardHeader>
            <CardContent>
               <div className="text-3xl font-bold text-secondary mb-1">
                  {loadingStats ? <Loader2 className="h-6 w-6 animate-spin" /> : formatCurrency(stats?.sponsor_earnings || 0)}
               </div>
               <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Gift className="h-3 w-3" /> Auto-credited to balance
               </div>
            </CardContent>
         </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
         <Card className="glass-panel">
            <CardContent className="p-4 flex items-center gap-4">
               <div className="p-3 bg-primary/10 rounded-lg text-primary">
                  <Users className="h-6 w-6" />
               </div>
               <div>
                  <div className="text-2xl font-bold">{stats?.total_sponsored || 0}</div>
                  <div className="text-xs text-muted-foreground">Total Network</div>
               </div>
            </CardContent>
         </Card>
         <Card className="glass-panel">
            <CardContent className="p-4 flex items-center gap-4">
               <div className="p-3 bg-green-500/10 rounded-lg text-green-500">
                  <Target className="h-6 w-6" />
               </div>
               <div>
                  <div className="text-2xl font-bold">{stats?.active_sponsored || 0}</div>
                  <div className="text-xs text-muted-foreground">Active Traders</div>
               </div>
            </CardContent>
         </Card>
         <Card className="glass-panel">
            <CardContent className="p-4 flex items-center gap-4">
               <div className="p-3 bg-blue-500/10 rounded-lg text-blue-500">
                  <Gift className="h-6 w-6" />
               </div>
               <div>
                  <div className="text-2xl font-bold">{stats?.sponsored_purchases || 0}</div>
                  <div className="text-xs text-muted-foreground">Network Purchases</div>
               </div>
            </CardContent>
         </Card>
      </div>

      <Card className="glass-panel border-white/10 mt-8">
        <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <CardTitle>Sponser Members</CardTitle>
          <form onSubmit={handleSearch} className="flex items-center gap-2 w-full sm:w-auto">
             <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search by username..." 
                  className="pl-9 bg-black/20 border-white/10" 
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
             </div>
             <Button type="submit" variant="secondary" className="bg-white/10 hover:bg-white/20">Search</Button>
          </form>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-white/10 overflow-hidden bg-black/20">
            <Table>
              <TableHeader className="bg-white/5">
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableHead>User</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Purchases</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingUsers ? (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-primary" />
                    </TableCell>
                  </TableRow>
                ) : users?.results?.length ? (
                  users.results.map((user) => (
                    <TableRow key={user.id} className="border-white/5 hover:bg-white/5">
                      <TableCell>
                        <div className="font-medium text-white">{user.username}</div>
                        <div className="text-xs text-muted-foreground">{user.full_name}</div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(user.date_joined).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                         {user.status === 'active' ? (
                            <Badge className="bg-green-500/20 text-green-500 border-none">Active</Badge>
                         ) : (
                            <Badge variant="outline" className="text-muted-foreground">Inactive</Badge>
                         )}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                         {formatCrypto(user.purchase_amount || 0)}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                      No network members found.
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