import { useQuery } from "@tanstack/react-query";
import {
  fetchHomePublicSettings,
  type HomePublicSettings,
} from "@/lib/home-public-settings";

/** Poll interval for live admin coin rate / supply (ms). */
export const PUBLIC_COIN_SETTINGS_POLL_MS = 8_000;

export const PUBLIC_COIN_SETTINGS_QUERY_KEY = ["public-coin-settings"] as const;

/**
 * Live public settings from admin dashboard — polls automatically; no full page refresh needed.
 */
export function usePublicCoinSettings() {
  return useQuery<HomePublicSettings>({
    queryKey: PUBLIC_COIN_SETTINGS_QUERY_KEY,
    queryFn: fetchHomePublicSettings,
    staleTime: 0,
    refetchInterval: PUBLIC_COIN_SETTINGS_POLL_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    refetchOnMount: "always",
  });
}
