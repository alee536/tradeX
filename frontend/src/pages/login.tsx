import { useState, useEffect } from "react";
import { useLocation, Link } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { useLogin } from "@workspace/api-client-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Eye, EyeOff, TrendingUp, Shield, Coins, Users } from "lucide-react";
import { CryptoBackground } from "@/components/ui/crypto-background";

const loginSchema = z.object({
  email: z.string().email("Email is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const features = [
  { icon: TrendingUp, text: "Up to 100% returns on trading" },
  { icon: Shield, text: "Staged unlock system for security" },
  { icon: Coins, text: "USDT BEP20 secure deposits" },
  { icon: Users, text: "Referral rewards program" },
];

const stats = [
  { value: "$12M+", label: "Total Volume" },
  { value: "8,400+", label: "Active Traders" },
  { value: "99.9%", label: "Uptime" },
];

export default function Login() {
  const [, setLocation] = useLocation();
  const [showPass, setShowPass] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const { toast } = useToast();
  const loginMutation = useLogin();

  useEffect(() => {
    if (isAuthenticated) {
      setLocation("/user/dashboard");
    }
  }, [isAuthenticated, setLocation]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("session") === "expired") {
      toast({
        title: "Session expired",
        description: "Please sign in again to continue.",
        variant: "destructive",
      });
      params.delete("session");
      const next = params.get("next");
      const query = next ? `?next=${next}` : "";
      window.history.replaceState({}, "", `/login${query}`);
    }
  }, [toast]);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (data: LoginFormValues) => {
    loginMutation.mutate({ data: { username: data.email, password: data.password } }, {
      onSuccess: (res) => {
        console.log('login success response:', res);
        login(res);
        console.log('after login, token in localStorage:', localStorage.getItem('24tradex_token'));
        // give context a tick to update before navigating
        setTimeout(() => setLocation("/user/dashboard"), 50);
      },
      onError: (err: any) => {
        toast({
          title: "Login failed",
          description: err?.message || "Invalid credentials",
          variant: "destructive",
        });
      }
    });
  };

  return (
    <div className="min-h-screen w-full flex relative" style={{ background: "#070d1a" }}>
      {/* LEFT PANEL */}
      <div
        className="hidden lg:flex flex-col justify-between w-[55%] relative overflow-hidden p-12"
        style={{
          background: "linear-gradient(135deg, #060c18 0%, #0a1628 60%, #080e1c 100%)",
          borderRight: "1px solid rgba(59,130,246,0.12)",
        }}
      >
        <CryptoBackground intensity={1} />

        {/* Center content */}
        <div className="relative z-10 flex-1 flex flex-col justify-center py-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-8 w-fit"
            style={{ background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)", color: "#60a5fa" }}>
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Platform Live — Trade Now
          </div>

          <h1 className="text-lg font-bold text-white leading-tight mb-4">
            Grow Your Wealth with{" "}
            <span style={{ color: "#60a5fa" }}>Smart Crypto</span>{" "}
            Trading
          </h1>
          <p className="text-gray-400 text-lg mb-10 leading-relaxed">
            Join thousands of traders earning passive income through our secure, staged trading platform.
          </p>

          <div className="space-y-4">
            {features.map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.25)" }}>
                  <Icon className="w-4 h-4" style={{ color: "#60a5fa" }} />
                </div>
                <span className="text-gray-300 text-sm">{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="relative z-10 grid grid-cols-3 gap-4 pt-8"
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          {stats.map(({ value, label }) => (
            <div key={label}>
              <div className="text-xl font-bold" style={{ color: "#60a5fa" }}>{value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative">
        <CryptoBackground intensity={0.4} />

        <div className="w-full max-w-md relative z-10">
          <div className="mb-6 flex items-center gap-3">
            <img
              src={`${import.meta.env.BASE_URL}logo.png`}
              alt="24TRADEX Logo"
              className="h-14 w-14 rounded-xl object-contain"
              loading="eager"
            />
            <div>
              <p className="text-base font-semibold text-white">24TRADEX</p>
              <p className="text-xs text-gray-500">Secure trading platform</p>
            </div>
          </div>
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-1">Welcome back</h2>
            <p className="text-gray-500 text-sm">Sign in to your trading account</p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField control={form.control} name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Email Address</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter your email"
                        {...field}
                        className="h-12 text-white placeholder:text-gray-600 border-0 focus-visible:ring-1 focus-visible:ring-blue-500/50"
                        style={{ background: "rgba(255,255,255,0.05)", borderRadius: "8px" }}
                        autoComplete="email"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField control={form.control} name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPass ? "text" : "password"}
                          placeholder="Enter your password"
                          {...field}
                          className="h-12 pr-10 text-white placeholder:text-gray-600 border-0 focus-visible:ring-1 focus-visible:ring-blue-500/50"
                          style={{ background: "rgba(255,255,255,0.05)", borderRadius: "8px" }}
                          autoComplete="current-password"
                        />
                        <button
                          type="button"
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                          onClick={() => setShowPass(!showPass)}
                        >
                          {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end">
                <Link href="/forgot-password">
                  <span className="text-xs text-gray-500 hover:text-blue-400 cursor-pointer transition-colors">
                    Forgot password?
                  </span>
                </Link>
              </div>

              <Button
                type="submit"
                className="w-full h-12 font-semibold text-sm tracking-wide border-0 cursor-pointer text-white"
                style={{
                  background: loginMutation.isPending ? "rgba(59,130,246,0.7)" : "#3b82f6",
                  borderRadius: "8px",
                }}
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...</>
                  : "Sign In"}
              </Button>
            </form>
          </Form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Don't have an account?{" "}
            <Link href="/register">
              <span className="font-medium cursor-pointer hover:opacity-80 transition-opacity" style={{ color: "#60a5fa" }}>
                Create account
              </span>
            </Link>
          </p>

          {/* Social links moved to global footer */}
        </div>
      </div>
    </div>
  );
}
