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
      realisedTab="Realised"
      hideMonitorTables
      title="STAR RSI SHARPE — Forward Test"
      rules={[
        "Signals: weekly Wilder RSI(50) on Friday closes; rank = 252-day Sharpe ratio (risk-free 6.5%), which needs a full 252 valid days.",
        "Universe: RSI-scanner drilldown names, screened to drop any name with more than 20 circuit-locked days in the last year.",
        "Buy: RSI > 55, valid Sharpe, not quarantined, not already held, rank ≤ 20. Hold: rank 21–40. Sell: RSI < 50, rank > 40, or quarantined.",
        "Quarantine: any one-day move above 40% bars the stock for 252 trading days and forces a sale.",
        "Sizing: 20 equal-weight slots (equity/20); unfilled slots stay in cash; no leverage.",
        "Timing: stock decisions on the first Friday of each month, fills at the next session's close.",
        "Cash call (independent, weekly): Smallcap 100 index Supertrend(4,3) on weekly bars; close below the line moves the whole book to 100% cash (earning 6.5% p.a.) until it turns green.",
        "23-Oct-2026: all 20 stocks exited at live price; whole book parked in NSE:LIQUIDCASE (Zerodha Nifty 1D Rate Liquid ETF, ~6% p.a.) until re-entry.",
      ]}
      subtitle="20-stock, equal-weight book on ₹1,00,00,000. Universe = RSI-scanner drilldown names, ranked by 252-day Sharpe, screened to drop any name with >20 circuit-locked days in the last year. Entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
      siblingStrategies={[
        {
          key: "mom10",
          label: "ATH/100 EMA Avg Sharpe 10",
          navHistoryFile: "nav-history-mom10.json",
          sheetId: "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac", // "Top 10 ER MOM PORTFOLIO" -- see app/page.tsx
          color: "var(--series-5)",
        },
        {
          key: "mom20",
          label: "ATH/100 EMA Avg Sharpe 20",
          navHistoryFile: "nav-history-mom20.json",
          sheetId: "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY", // "20/60 mom portfolio" -- see app/mom20/page.tsx
          color: "var(--series-6)",
        },
      ]}
    />
  );
}
