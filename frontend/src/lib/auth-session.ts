export const AUTH_TOKEN_KEY = "24tradex_token";
export const AUTH_USER_KEY = "24tradex_user";

const PUBLIC_AUTH_PATH_SUFFIXES = [
  "/auth/login",
  "/auth/register",
  "/auth/password-reset",
  "/health",
];

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

export function getStoredAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function isPublicAuthRequest(url: string): boolean {
  const path = url.split("?")[0] ?? url;
  return PUBLIC_AUTH_PATH_SUFFIXES.some((suffix) => path.endsWith(suffix) || path.includes(suffix));
}

export function isAuthSessionError(status: number, hadBearerToken: boolean): boolean {
  return hadBearerToken && status === 401;
}

export function redirectToLoginAfterSessionExpiry(): void {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path === "/login" || path.startsWith("/register") || path.startsWith("/forgot-password")) {
    return;
  }
  const next = encodeURIComponent(`${path}${window.location.search}`);
  window.location.href = `/login?session=expired&next=${next}`;
}
