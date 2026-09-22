import StrategyDashboard from "@/components/StrategyDashboard";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const metadata: Metadata = { title: "RISHI x VIRAJ — Forward Test" };

const SHEET_ID = "1Ls5COhCkEEEtvFwqWvUxnwpj_NI8OwnIRuP3vK-KPkg"; // "RISHI x VIRAJ -- 19 COMMON NAMES + CASH"

export default function RishiViraj() {
  return (
    <StrategyDashboard
      currentPath="/rishi-viraj"
      sheetId={SHEET_ID}
      navHistoryFile="nav-history-rishi-viraj.json"
      overweightThreshold={0.08}
      title="RISHI x VIRAJ — Forward Test"
      subtitle="20-slot, equal-weight book on ₹1,00,00,000. The 19 stock slots are names common to Rishi's ranked 'RISHI 20 x VIRAJ' sheet and a separate, more stringent screener sheet -- only 19 of Rishi's 20 ranks had a match, so rank 20 is held as a cash sleeve instead, accruing 6.5% p.a. Stock entry frozen once at first run, whole shares, weekly-Wednesday rebalance to equal weight, benchmarked against the Nifty 500."
    />
  );
}
