import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "ATH/100 EMA Avg Sharpe 20 Stock Portfolio" };

const SHEET_ID = "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY"; // "20/60 mom portfolio"

export default function Mom20() {
  return (
    <StrategyDashboard
      currentPath="/mom20"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-mom20.json"
      overweightThreshold={0.08}
      realisedTab="Realised"
      title="ATH/100 EMA Avg Sharpe 20 Stock Portfolio"
      rules={[
        "Universe: NSE stocks (point-in-time Nifty 500 constituents).",
        "Score: average of the annualised Sharpe ratios over 63, 126, 189 and 252 trading days (risk-free 6.5%). Stocks are ranked on this average Sharpe.",
        "Eligibility filter: close within 25% of its all-time high (close ≥ 75% of the running max close) AND close above the 100-day EMA.",
        "Buy: top 20 ranked eligible stocks. Hold: a stock stays until its rank falls below 60 (20/60 band). Exit: stock drops out of the retention band, loses eligibility, or is 20% below its entry price (checked on decision dates).",
        "Sizing: 20 equal-weight slots (each 1/20 of equity), reset to equal weight at every decision date.",
        "Timing: signals at Friday close, fills at the next session's open.",
        "Cash call (independent, weekly): Smallcap 100 index Supertrend(4,3) on weekly bars; when the close is below the line the whole book moves to cash until it turns green again.",
      ]}
      subtitle="ATH/100 EMA Avg Sharpe 20 Stock Portfolio: 20-stock, equal-weight book on ₹1,00,00,000. Selection made outside this sheet; entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
    />
  );
}
