import { customFetch, type AuthResponse } from "@workspace/api-client-react";
import type { RegisterInput } from "@workspace/api-client-react";

export interface RegisterOtpSentResponse {
  message: string;
  email: string;
  expires_in_minutes: number;
  resend_cooldown_seconds: number;
  verification_id?: number;
}

export interface ApiErrorBody {
  error?: string;
  code?: string;
  [key: string]: unknown;
}

export function getApiErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (err && typeof err === "object" && "data" in err) {
    const data = (err as { data?: ApiErrorBody }).data;
    if (data?.error && typeof data.error === "string") {
      return data.error;
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

export async function requestSignupOtp(
  data: RegisterInput,
): Promise<RegisterOtpSentResponse> {
  return customFetch<RegisterOtpSentResponse>("/api/auth/register/request-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function verifySignupOtp(
  email: string,
  otp: string,
): Promise<AuthResponse> {
  return customFetch<AuthResponse>("/api/auth/register/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, otp }),
  });
}

export async function resendSignupOtp(email: string): Promise<RegisterOtpSentResponse> {
  return customFetch<RegisterOtpSentResponse>("/api/auth/register/resend-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}
