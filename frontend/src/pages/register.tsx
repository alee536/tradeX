import { useEffect, useState } from "react";
import { useLocation, Link } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import {
  requestSignupOtp,
  verifySignupOtp,
  resendSignupOtp,
  getApiErrorMessage,
} from "@/lib/auth-signup";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Eye, EyeOff, TrendingUp, Shield, Coins, Users, Check } from "lucide-react";
import { CryptoBackground } from "@/components/ui/crypto-background";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

const registerSchema = z.object({
  username: z.string().min(1, "Display name is required"),
  full_name: z.string().min(2, "Full name is required"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirm_password: z.string().min(1, "Please confirm your password"),
  sponsor_code: z.string().optional(),
}).refine((d) => d.password === d.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

const features = [
  { icon: TrendingUp, text: "Up to 100% returns on trading" },
  { icon: Shield, text: "Staged unlock system for security" },
  { icon: Coins, text: "USDT BEP20 secure deposits" },
  { icon: Users, text: "Earn commissions by referring others" },
];

const stats = [
  { value: "$12M+", label: "Total Volume" },
  { value: "8,400+", label: "Active Traders" },
  { value: "99.9%", label: "Uptime" },
];

type StrengthLevel = { score: number; label: string; color: string; bg: string };

function getPasswordStrength(password: string): StrengthLevel {
  if (!password) return { score: 0, label: "", color: "#374151", bg: "rgba(55,65,81,0.3)" };
  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 1) return { score: 1, label: "Weak", color: "#ef4444", bg: "rgba(239,68,68,0.15)" };
  if (score === 2) return { score: 2, label: "Fair", color: "#f97316", bg: "rgba(249,115,22,0.15)" };
  if (score === 3) return { score: 3, label: "Good", color: "#eab308", bg: "rgba(234,179,8,0.15)" };
  return { score: 4, label: "Strong", color: "#22c55e", bg: "rgba(34,197,94,0.15)" };
}

const inputCls = "h-11 text-white placeholder:text-gray-600 border-0 focus-visible:ring-1 focus-visible:ring-blue-500/50";
const inputStyle = { background: "rgba(255,255,255,0.05)", borderRadius: "8px" };

type RegisterStep = "details" | "verify";

export default function Register() {
  const [, setLocation] = useLocation();
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [step, setStep] = useState<RegisterStep>("details");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const { login, isAuthenticated } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    if (isAuthenticated) {
      setLocation("/user/dashboard");
    }
  }, [isAuthenticated, setLocation]);

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", full_name: "", email: "", password: "", confirm_password: "", sponsor_code: "" },
  });

  // Pre-fill sponsor from ?ref=ALEE24 (short link) or legacy ?sp=24TX-XXXXXX
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ref = params.get("ref") || params.get("sp");
    if (ref) {
      form.setValue("sponsor_code", ref.trim().toUpperCase());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  const passwordValue = form.watch("password");
  const strength = getPasswordStrength(passwordValue);

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search).get("sp");
    if (sp) form.setValue("sponsor_code", sp);
  }, [form]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((s) => (s <= 1 ? 0 : s - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  const onSubmitDetails = async (data: RegisterFormValues) => {
    const { confirm_password, ...rest } = data;
    const submitData = { ...rest, sponsor_code: rest.sponsor_code || undefined };
    setIsSubmitting(true);
    try {
      const res = await requestSignupOtp(submitData);
      setPendingEmail(res.email);
      setResendCooldown(res.resend_cooldown_seconds);
      setOtp("");
      setStep("verify");
      toast({
        title: "Check your email",
        description: `We sent a 6-digit code to ${res.email}. It expires in ${res.expires_in_minutes} minutes.`,
      });
    } catch (err) {
      toast({
        title: "Could not send code",
        description: getApiErrorMessage(err, "Please try again."),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const onVerifyOtp = async () => {
    if (otp.length !== 6) {
      toast({
        title: "Enter verification code",
        description: "Please enter the 6-digit code from your email.",
        variant: "destructive",
      });
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await verifySignupOtp(pendingEmail, otp);
      login(res);
      toast({ title: "Welcome to 24TRADEX!", description: "Your account has been created." });
      setTimeout(() => setLocation("/user/dashboard"), 50);
    } catch (err) {
      toast({
        title: "Verification failed",
        description: getApiErrorMessage(err, "Invalid or expired code."),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const onResendOtp = async () => {
    if (resendCooldown > 0 || !pendingEmail) return;
    setIsSubmitting(true);
    try {
      const res = await resendSignupOtp(pendingEmail);
      setResendCooldown(res.resend_cooldown_seconds);
      setOtp("");
      toast({
        title: "Code resent",
        description: `A new code was sent to ${res.email}.`,
      });
    } catch (err) {
      toast({
        title: "Could not resend",
        description: getApiErrorMessage(err, "Please wait and try again."),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex relative" style={{ background: "#070d1a" }}>
      {/* LEFT PANEL */}
      <div
        className="hidden lg:flex flex-col justify-between w-[45%] relative overflow-hidden p-12"
        style={{
          background: "linear-gradient(135deg, #060c18 0%, #0a1628 60%, #080e1c 100%)",
          borderRight: "1px solid rgba(59,130,246,0.12)",
        }}
      >
        <CryptoBackground intensity={0.9} />

        {/* Center content */}
        <div className="relative z-10 flex-1 flex flex-col justify-center py-10">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium mb-8 w-fit"
            style={{ background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.3)", color: "#60a5fa" }}>
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Join the Elite Network
          </div>

          <h1 className="text-lg font-bold text-white leading-tight mb-4">
            Start Your{" "}
            <span style={{ color: "#60a5fa" }}>Crypto Trading</span>{" "}
            Journey Today
          </h1>
          <p className="text-gray-400 text-base mb-10 leading-relaxed">
            Create your account and begin earning through our proven staged trading platform.
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
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative overflow-y-auto">
        <CryptoBackground intensity={0.4} />

        <div className="w-full max-w-md py-12 lg:py-0 relative z-10">
          <div className="mb-7">
            <h2 className="text-2xl font-bold text-white mb-1">
              {step === "details" ? "Create your account" : "Verify your email"}
            </h2>
            <p className="text-gray-500 text-sm">
              {step === "details"
                ? "Join the 24TRADEX trading network"
                : `Enter the code sent to ${pendingEmail}`}
            </p>
          </div>

          {step === "verify" ? (
            <div className="space-y-6">
              <div className="flex justify-center">
                <InputOTP maxLength={6} value={otp} onChange={setOtp}>
                  <InputOTPGroup>
                    <InputOTPSlot index={0} className="bg-white/5 text-white border-white/10" />
                    <InputOTPSlot index={1} className="bg-white/5 text-white border-white/10" />
                    <InputOTPSlot index={2} className="bg-white/5 text-white border-white/10" />
                    <InputOTPSlot index={3} className="bg-white/5 text-white border-white/10" />
                    <InputOTPSlot index={4} className="bg-white/5 text-white border-white/10" />
                    <InputOTPSlot index={5} className="bg-white/5 text-white border-white/10" />
                  </InputOTPGroup>
                </InputOTP>
              </div>
              <Button
                type="button"
                className="w-full h-12 font-semibold text-sm text-white border-0"
                style={{ background: isSubmitting ? "rgba(59,130,246,0.7)" : "#3b82f6", borderRadius: "8px" }}
                disabled={isSubmitting || otp.length !== 6}
                onClick={onVerifyOtp}
              >
                {isSubmitting ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Verifying...</>
                ) : (
                  "Verify & Create Account"
                )}
              </Button>
              <div className="flex flex-col items-center gap-2 text-sm">
                <button
                  type="button"
                  className="text-gray-400 hover:text-white disabled:opacity-40"
                  disabled={resendCooldown > 0 || isSubmitting}
                  onClick={onResendOtp}
                >
                  {resendCooldown > 0
                    ? `Resend code in ${resendCooldown}s`
                    : "Resend verification code"}
                </button>
                <button
                  type="button"
                  className="text-gray-500 hover:text-gray-300"
                  onClick={() => {
                    setStep("details");
                    setOtp("");
                  }}
                >
                  ← Back to signup details
                </button>
              </div>
            </div>
          ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmitDetails)} className="space-y-4">
              {/* Row: Username + Full Name */}
              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Display Name / Username</FormLabel>
                      <FormControl>
                        <Input placeholder="Any name you like" {...field} className={inputCls} style={inputStyle} autoComplete="nickname" />
                      </FormControl>
                      <p className="text-xs text-gray-500">This name can repeat. Login uses email and password.</p>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
                <FormField control={form.control} name="full_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Full Name</FormLabel>
                      <FormControl>
                        <Input placeholder="John Doe" {...field} className={inputCls} style={inputStyle} autoComplete="name" />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
              </div>

              {/* Email */}
              <FormField control={form.control} name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Email Address</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="you@example.com" {...field} className={inputCls} style={inputStyle} autoComplete="email" />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              {/* Password */}
              <FormField control={form.control} name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPass ? "text" : "password"}
                          placeholder="Minimum 8 characters"
                          {...field}
                          className={`${inputCls} pr-10`}
                          style={inputStyle}
                          autoComplete="new-password"
                        />
                        <button type="button"
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                          onClick={() => setShowPass(!showPass)}>
                          {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </FormControl>
                    {/* Strength bar */}
                    {passwordValue && (
                      <div className="mt-2 space-y-1.5">
                        <div className="flex gap-1">
                          {[1, 2, 3, 4].map((lvl) => (
                            <div
                              key={lvl}
                              className="h-1 flex-1 rounded-full transition-all duration-300"
                              style={{
                                background: strength.score >= lvl ? strength.color : "rgba(255,255,255,0.08)",
                              }}
                            />
                          ))}
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs transition-colors" style={{ color: strength.color }}>
                            {strength.label}
                          </span>
                          <div className="flex gap-2 text-xs text-gray-600">
                            {[
                              { ok: passwordValue.length >= 8, text: "8+ chars" },
                              { ok: /[A-Z]/.test(passwordValue), text: "uppercase" },
                              { ok: /[0-9]/.test(passwordValue), text: "number" },
                            ].map(({ ok, text }) => (
                              <span key={text} className="flex items-center gap-0.5" style={{ color: ok ? "#22c55e" : "#4b5563" }}>
                                {ok && <Check className="w-3 h-3" />}{text}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              {/* Confirm Password */}
              <FormField control={form.control} name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Confirm Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showConfirm ? "text" : "password"}
                          placeholder="Repeat your password"
                          {...field}
                          className={`${inputCls} pr-10`}
                          style={inputStyle}
                          autoComplete="new-password"
                        />
                        <button type="button"
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                          onClick={() => setShowConfirm(!showConfirm)}>
                          {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              {/* Sponsor Code */}
              <FormField control={form.control} name="sponsor_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">
                      Sponsor Code <span className="normal-case font-normal text-gray-600">(optional)</span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="ALEE24 or 24TX-XXXXXX" {...field} className={inputCls} style={inputStyle} />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />

              <div className="pt-1">
                <Button
                  type="submit"
                  className="w-full h-12 font-semibold text-sm tracking-wide border-0 cursor-pointer text-white"
                  style={{
                    background: isSubmitting ? "rgba(59,130,246,0.7)" : "#3b82f6",
                    borderRadius: "8px",
                  }}
                  disabled={isSubmitting}
                >
                  {isSubmitting
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending code...</>
                    : "Continue — Send verification code"}
                </Button>
              </div>
            </form>
          </Form>
          )}

          <p className="mt-5 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link href="/login">
              <span className="font-medium cursor-pointer hover:opacity-80 transition-opacity" style={{ color: "#60a5fa" }}>
                Sign in
              </span>
            </Link>
          </p>

          {/* Social links moved to global footer */}
        </div>
      </div>
    </div>
  );
}
