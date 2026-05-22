import { customFetch } from "@workspace/api-client-react";
import { getApiErrorMessage } from "@/lib/auth-signup";

export interface PasswordResetSentResponse {
  message: string;
  email: string;
  expires_in_minutes?: number;
  resend_cooldown_seconds?: number;
}

export interface PasswordResetConfirmResponse {
  message: string;
  email: string;
}

export async function requestPasswordReset(email: string): Promise<PasswordResetSentResponse> {
  return customFetch<PasswordResetSentResponse>("/api/auth/forgot-password/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function resendPasswordResetOtp(email: string): Promise<PasswordResetSentResponse> {
  return customFetch<PasswordResetSentResponse>("/api/auth/forgot-password/resend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(
  email: string,
  otp: string,
  password: string,
): Promise<PasswordResetConfirmResponse> {
  return customFetch<PasswordResetConfirmResponse>("/api/auth/forgot-password/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, otp, password }),
  });
}

export { getApiErrorMessage };
