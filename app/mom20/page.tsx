import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "RISHI Momentum-20 — Forward Test" };

const SHEET_ID = "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY"; // "20/60 mom portfolio"

export default function Mom20() {
  return (
    <StrategyDashboard
      currentPath="/mom20"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-mom20.json"
      overweightThreshold={0.08}
      title="RISHI MOMENTUM — Forward Test"
      subtitle="20-stock, equal-weight momentum book on ₹1,00,00,000. Selection made outside this sheet; entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
    />
  );
}
