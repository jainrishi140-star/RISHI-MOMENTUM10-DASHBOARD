"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Re-fetches the (server-rendered, no-store) dashboard every minute so Yahoo
// prices, hero tiles and the live equity-curve point move without a manual
// reload. Skips ticks while the tab is hidden and refreshes on return.
export default function AutoRefresh({ intervalMs = 60 * 1000 }: { intervalMs?: number }) {
  const router = useRouter();

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") router.refresh();
    };
    const id = setInterval(tick, intervalMs);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [router, intervalMs]);

  return null;
}
