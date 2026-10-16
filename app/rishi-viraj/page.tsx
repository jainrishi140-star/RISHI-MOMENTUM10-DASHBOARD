import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "20 Stocks Earnings & Price Momentum" };

const SHEET_ID = "1Ls5COhCkEEEtvFwqWvUxnwpj_NI8OwnIRuP3vK-KPkg"; // "RISHI x VIRAJ -- 19 COMMON NAMES + CASH"

export default function RishiViraj() {
  return (
    <StrategyDashboard
      currentPath="/rishi-viraj"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-rishi-viraj.json"
      overweightThreshold={0.08}
      realisedTab="Realised"
      title="20 Stocks Earnings & Price Momentum"
      rules={[
        "Book: 20 equal-weight slots (5% each) on ₹1,00,00,000, selected on earnings momentum plus price momentum.",
        "Price momentum: as per the ATH/100 EMA Avg Sharpe 20 Stock Portfolio — rank on the average of the 63/126/189/252-day Sharpe ratios (risk-free 6.5%); eligible only if the close is within 25% of its all-time high and above the 100-day EMA; top 20 ranks bought, held to rank 60.",
        "Earnings momentum: the company's quarterly profit after tax (PAT) is at an all-time high.",
        "Selection: a name qualifies when it passes both the price-momentum and the all-time-high-PAT screens. Only 19 of the 20 ranks had a match.",
        "Unmatched slot: rank 20 is held as a cash sleeve accruing 6.5% p.a. instead of a stock.",
        "Entry: frozen once at first run, whole shares only.",
        "Rebalance: weekly on Wednesday, back to equal weight.",
        "Benchmark: Nifty 500.",
      ]}
      subtitle="20 stocks selected on earnings momentum (profit after tax at an all-time high) and price momentum (ATH/100 EMA Avg Sharpe), equal-weight on ₹1,00,00,000. Only 19 of the 20 ranks had a match, so rank 20 is held as a cash sleeve instead, accruing 6.5% p.a. Stock entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
    />
  );
}
