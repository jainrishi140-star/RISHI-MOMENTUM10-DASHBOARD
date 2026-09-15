import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "RISHI Momentum-10 — Forward Test" };

const SHEET_ID = "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac"; // "Top 10 ER MOM PORTFOLIO"

export default function Home() {
  return (
    <StrategyDashboard
      currentPath="/"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-mom10.json"
      overweightThreshold={0.15}
      title="RISHI MOMENTUM-10 — Forward Test"
      subtitle="10-stock, equal-weight momentum book on ₹1,00,00,000. Selection made outside this sheet; entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
    />
  );
}
