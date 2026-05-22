import { useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { CryptoBackground } from "@/components/ui/crypto-background";
import { Loader2, ArrowLeft, KeyRound } from "lucide-react";
import {
  requestPasswordReset,
  resendPasswordResetOtp,
  confirmPasswordReset,
  getApiErrorMessage,
} from "@/lib/auth-password-reset";

type Step = "email" | "reset";

const emailSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});

const resetSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type EmailFormValues = z.infer<typeof emailSchema>;
type ResetFormValues = z.infer<typeof resetSchema>;

const inputCls = "h-11 text-white placeholder:text-gray-600 border-0 focus-visible:ring-1 focus-visible:ring-blue-500/50";
const inputStyle = { background: "rgba(255,255,255,0.05)", borderRadius: "8px" };

export default function ForgotPassword() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [step, setStep] = useState<Step>("email");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  const emailForm = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  const resetForm = useForm<ResetFormValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", confirm_password: "" },
  });

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((s) => (s <= 1 ? 0 : s - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  const onRequestEmail = async (data: EmailFormValues) => {
    setIsSubmitting(true);
    try {
      const res = await requestPasswordReset(data.email);
      setPendingEmail(res.email);
      setResendCooldown(res.resend_cooldown_seconds ?? 60);
      setOtp("");
      setStep("reset");
      toast({
        title: "Check your email",
        description: res.message,
      });
    } catch (err) {
      toast({
        title: "Request failed",
        description: getApiErrorMessage(err),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const onResend = async () => {
    if (!pendingEmail || resendCooldown > 0) return;
    setIsSubmitting(true);
    try {
      const res = await resendPasswordResetOtp(pendingEmail);
      setResendCooldown(res.resend_cooldown_seconds ?? 60);
      setOtp("");
      toast({ title: "Code resent", description: res.message });
    } catch (err) {
      toast({
        title: "Could not resend",
        description: getApiErrorMessage(err),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const onConfirmReset = async (data: ResetFormValues) => {
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
      const res = await confirmPasswordReset(pendingEmail, otp, data.password);
      toast({ title: "Password updated", description: res.message });
      setLocation("/login");
    } catch (err) {
      toast({
        title: "Reset failed",
        description: getApiErrorMessage(err),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative p-6" style={{ background: "#070d1a" }}>
      <CryptoBackground intensity={0.5} />
      <div className="w-full max-w-md relative z-10">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/20 border border-blue-400/30">
            <KeyRound className="h-7 w-7 text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">
            {step === "email" ? "Forgot password" : "Reset password"}
          </h1>
          <p className="text-gray-500 text-sm">
            {step === "email"
              ? "Enter your account email and we will send a verification code."
              : `Code sent to ${pendingEmail}`}
          </p>
        </div>

        {step === "email" ? (
          <Form {...emailForm}>
            <form onSubmit={emailForm.handleSubmit(onRequestEmail)} className="space-y-4">
              <FormField
                control={emailForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Email</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="you@example.com"
                        autoComplete="email"
                        className={inputCls}
                        style={inputStyle}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <Button
                type="submit"
                className="w-full h-12 text-white border-0"
                style={{ background: "#3b82f6", borderRadius: "8px" }}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...</>
                ) : (
                  "Send verification code"
                )}
              </Button>
            </form>
          </Form>
        ) : (
          <div className="space-y-6">
            <div className="flex justify-center">
              <InputOTP maxLength={6} value={otp} onChange={setOtp}>
                <InputOTPGroup>
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <InputOTPSlot
                      key={i}
                      index={i}
                      className="bg-white/5 text-white border-white/10"
                    />
                  ))}
                </InputOTPGroup>
              </InputOTP>
            </div>

            <Form {...resetForm}>
              <form onSubmit={resetForm.handleSubmit(onConfirmReset)} className="space-y-4">
                <FormField
                  control={resetForm.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">New password</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Minimum 8 characters"
                          autoComplete="new-password"
                          className={inputCls}
                          style={inputStyle}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={resetForm.control}
                  name="confirm_password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-400 text-xs uppercase tracking-wider">Confirm password</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          autoComplete="new-password"
                          className={inputCls}
                          style={inputStyle}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage className="text-xs" />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="w-full h-12 text-white border-0"
                  style={{ background: "#3b82f6", borderRadius: "8px" }}
                  disabled={isSubmitting || otp.length !== 6}
                >
                  {isSubmitting ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Updating...</>
                  ) : (
                    "Update password"
                  )}
                </Button>
              </form>
            </Form>

            <div className="flex flex-col items-center gap-2 text-sm">
              <button
                type="button"
                className="text-gray-400 hover:text-white disabled:opacity-40"
                disabled={resendCooldown > 0 || isSubmitting}
                onClick={onResend}
              >
                {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Resend code"}
              </button>
              <button
                type="button"
                className="text-gray-500 hover:text-gray-300 flex items-center gap-1"
                onClick={() => {
                  setStep("email");
                  setOtp("");
                }}
              >
                <ArrowLeft className="h-3 w-3" /> Change email
              </button>
            </div>
          </div>
        )}

        <p className="mt-8 text-center text-sm text-gray-500">
          <Link href="/login">
            <span className="text-blue-400 hover:opacity-80 cursor-pointer">Back to sign in</span>
          </Link>
        </p>
      </div>
    </div>
  );
}
