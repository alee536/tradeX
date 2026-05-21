/**
 * Django template admin lives on the backend, not in the React SPA.
 * Use full navigation (<a href>) so /admin/* is served by Django.
 */
export const ADMIN_PATHS = {
  dashboard: "/admin/",
  users: "/admin/users/",
  purchases: "/admin/purchases/",
  withdrawals: "/admin/withdrawals/",
  settings: "/admin/settings/coin/",
  sponsor: "/admin/sponsor/",
} as const;

export type AdminPathKey = keyof typeof ADMIN_PATHS;

function adminBaseUrl(): string {
  const envBase = import.meta.env.VITE_ADMIN_BASE_URL as string | undefined;
  if (envBase) {
    return envBase.replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "http://127.0.0.1:8000";
  }
  return "";
}

export function getAdminUrl(key: AdminPathKey): string {
  const path = ADMIN_PATHS[key];
  const base = adminBaseUrl();
  return base ? `${base}${path}` : path;
}
