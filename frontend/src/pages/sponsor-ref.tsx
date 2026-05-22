import { useEffect } from "react";
import { useRoute, useLocation } from "wouter";
import { Loader2 } from "lucide-react";

/**
 * Public short link handler: /ref/ALEE24 → /register?ref=ALEE24
 * Matches production URLs like s24tx.com/ref/ALEE24
 */
export default function SponsorRefRedirect() {
  const [, params] = useRoute("/ref/:slug");
  const [, setLocation] = useLocation();
  const slug = params?.slug?.trim();

  useEffect(() => {
    if (!slug) return;
    setLocation(`/register?ref=${encodeURIComponent(slug.toUpperCase())}`);
  }, [slug, setLocation]);

  return (
    <div className="flex h-dvh w-full items-center justify-center bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
