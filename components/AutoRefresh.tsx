"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Re-fetches the (server-rendered, no-store) dashboard on an interval so the
// live-spliced equity curve point and hero tiles move intraday without the
// user having to manually reload the tab.
export default function AutoRefresh({ intervalMs = 15 * 60 * 1000 }: { intervalMs?: number }) {
  const router = useRouter();

  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);

  return null;
}
