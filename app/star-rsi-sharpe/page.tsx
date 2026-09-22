import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "STAR RSI SHARPE — Forward Test" };

const SHEET_ID = "1QDV04yw1Gb-hm0Y-K1NiDkyp-zyHm3jJQrOx-zZQTvU"; // "STAR RSI SHARPE"

export default function StarRsiSharpe() {
  return (
    <StrategyDashboard
      currentPath="/star-rsi-sharpe"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-star-rsi-sharpe.json"
      overweightThreshold={0.08}
      title="STAR RSI SHARPE — Forward Test"
      subtitle="20-stock, equal-weight book on ₹1,00,00,000. Universe = RSI-scanner drilldown names, ranked by trailing 12M Sharpe, screened to drop any name with >20 circuit-locked days in the last year. Entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
      siblingStrategies={[
        {
          key: "mom10",
          label: "MOM10 (10-stock)",
          navHistoryFile: "nav-history-mom10.json",
          sheetId: "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac", // "Top 10 ER MOM PORTFOLIO" -- see app/page.tsx
          color: "var(--series-5)",
        },
        {
          key: "mom20",
          label: "MOM20 (20-stock)",
          navHistoryFile: "nav-history-mom20.json",
          sheetId: "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY", // "20/60 mom portfolio" -- see app/mom20/page.tsx
          color: "var(--series-6)",
        },
      ]}
    />
  );
}
