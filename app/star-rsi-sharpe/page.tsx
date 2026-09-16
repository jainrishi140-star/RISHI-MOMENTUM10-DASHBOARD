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
    />
  );
}
