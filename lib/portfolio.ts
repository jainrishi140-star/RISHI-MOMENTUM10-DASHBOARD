// Maps raw CSV rows from each tab back onto the structure that
// BuildMomentumPortfolio_10stock.gs writes (see that file for the source of
// truth). Cell text is already formatted by Sheets on export (e.g. "₹9,630,152",
// "1.13%", "-4.82%") so most fields are rendered as-is, not re-parsed.
//
// IMPORTANT: fetched via the gviz CSV endpoint (see lib/sheet.ts), which
// silently drops blank rows. Holdings / Momentum / Rebalance / NAV are dense
// tables with no blank rows so a fixed offset is safe -- but we still locate
// the header row by content rather than a hardcoded index, since a rebuild
// can also add/remove leading rows. The Dashboard tab, by contrast, is full
// of blank spacer rows by design, so its layout is NOT safe to parse this
// way -- all dashboard-level stats below are computed from Holdings instead.

import { cell } from "./sheet";

export interface KV {
  label: string;
  value: string;
}

const SHEET_MONTHS: Record<string, string> = {
  Jan: "01", Feb: "02", Mar: "03", Apr: "04", May: "05", Jun: "06",
  Jul: "07", Aug: "08", Sep: "09", Oct: "10", Nov: "11", Dec: "12",
};

// Parses the sheet's "17-Sep-2026" Entry Date format to ISO "2026-09-17".
export function parseSheetDate(s: string): string | null {
  const m = /^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/.exec((s ?? "").trim());
  if (!m) return null;
  const mon = SHEET_MONTHS[m[2]];
  if (!mon) return null;
  return `${m[3]}-${mon}-${m[1].padStart(2, "0")}`;
}

function findRow(rows: string[][], matchFirstCell: string): number {
  return rows.findIndex((r) => (r[0] ?? "").trim() === matchFirstCell);
}

const START_CAPITAL = 10_000_000; // ₹1 Cr -- fixed forward-test parameter (BuildMomentumPortfolio_10stock.gs)

function toNumber(s: string): number {
  const cleaned = (s ?? "").replace(/[₹,%\s]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

function formatMoney(n: number): string {
  // Plain (Western) thousands grouping, matching the sheet's own
  // [$₹-en-IN]#,##0 number format as it actually renders -- not
  // Indian lakh/crore grouping, which would look inconsistent next to
  // the raw sheet strings (e.g. Holdings' "₹1,012,420") shown elsewhere
  // on this same page.
  const sign = n < 0 ? "-" : "";
  return `${sign}₹${Math.round(Math.abs(n)).toLocaleString("en-US")}`;
}

// n is a fraction (0.10 = 10%), matching how portfolioReturn etc. are computed.
function formatPct(n: number, decimals = 2): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

// Sheet weight/drift cells are already percentages as text (e.g. "10.0%"),
// so stripping "%" leaves 10.0, not the 0.10 fraction formatPct expects.
function toFraction(s: string): number {
  return toNumber(s) / 100;
}

export interface HoldingRow {
  ticker: string;
  name: string;
  entryDate: string;
  entryPrice: string;
  shares: string;
  costBasis: string;
  cmp: string;
  currentValue: string;
  unrealisedPnl: string;
  pnlPct: string;
  dayPnl: string;
  targetWt: string;
  actualWt: string;
  wtDrift: string;
  daysHeld: string;
  high52w: string;
  pctFrom52wHigh: string;
}

export function parseHoldings(rows: string[][]): { rows: HoldingRow[]; total: HoldingRow | null } {
  const headerIdx = findRow(rows, "Ticker");
  const out: HoldingRow[] = [];
  let total: HoldingRow | null = null;
  for (let r = headerIdx + 1; r < rows.length; r++) {
    const ticker = cell(rows, r, 0);
    if (!ticker) continue;
    const row: HoldingRow = {
      ticker,
      name: cell(rows, r, 1),
      entryDate: cell(rows, r, 2),
      entryPrice: cell(rows, r, 3),
      shares: cell(rows, r, 4),
      costBasis: cell(rows, r, 5),
      cmp: cell(rows, r, 6),
      currentValue: cell(rows, r, 7),
      unrealisedPnl: cell(rows, r, 8),
      pnlPct: cell(rows, r, 9),
      dayPnl: cell(rows, r, 10),
      targetWt: cell(rows, r, 11),
      actualWt: cell(rows, r, 12),
      wtDrift: cell(rows, r, 13),
      daysHeld: cell(rows, r, 14),
      high52w: cell(rows, r, 15),
      pctFrom52wHigh: cell(rows, r, 16),
    };
    if (ticker.toUpperCase() === "TOTAL") total = row;
    else out.push(row);
  }
  return { rows: out, total };
}

export interface MomentumRow {
  ticker: string;
  name: string;
  cmp: string;
  ret1m: string;
  ret3m: string;
  ret6m: string;
  ret12m: string;
  high52w: string;
  low52w: string;
  pctFrom52wHigh: string;
  pctAbove52wLow: string;
  momScore: string;
  health: string;
  rank12m: string;
}

export function parseMomentum(rows: string[][]): MomentumRow[] {
  const headerIdx = findRow(rows, "Ticker");
  const out: MomentumRow[] = [];
  for (let r = headerIdx + 1; r < rows.length; r++) {
    const ticker = cell(rows, r, 0);
    if (!ticker) continue;
    out.push({
      ticker,
      name: cell(rows, r, 1),
      cmp: cell(rows, r, 2),
      ret1m: cell(rows, r, 3),
      ret3m: cell(rows, r, 4),
      ret6m: cell(rows, r, 5),
      ret12m: cell(rows, r, 6),
      high52w: cell(rows, r, 7),
      low52w: cell(rows, r, 8),
      pctFrom52wHigh: cell(rows, r, 9),
      pctAbove52wLow: cell(rows, r, 10),
      momScore: cell(rows, r, 11),
      health: cell(rows, r, 12),
      rank12m: cell(rows, r, 13),
    });
  }
  return out;
}

export interface RebalanceRow {
  ticker: string;
  targetWt: string;
  targetValue: string;
  currentValue: string;
  driftRs: string;
  driftPct: string;
  action: string;
  sharesToTrade: string;
  estTradeValue: string;
}

export function parseRebalance(rows: string[][]): { nextDate: string; rows: RebalanceRow[] } {
  // "Next rebalance (Wed)" label sits two rows above the "Ticker" header.
  const labelIdx = rows.findIndex((r) => (r[0] ?? "").trim().startsWith("Next rebalance"));
  const nextDate = labelIdx >= 0 ? cell(rows, labelIdx, 1) : "";
  const headerIdx = findRow(rows, "Ticker");
  const out: RebalanceRow[] = [];
  for (let r = headerIdx + 1; r < rows.length; r++) {
    const ticker = cell(rows, r, 0);
    if (!ticker || ticker.toUpperCase() === "TOTAL") continue;
    out.push({
      ticker,
      targetWt: cell(rows, r, 1),
      targetValue: cell(rows, r, 2),
      currentValue: cell(rows, r, 3),
      driftRs: cell(rows, r, 4),
      driftPct: cell(rows, r, 5),
      action: cell(rows, r, 6),
      sharesToTrade: cell(rows, r, 7),
      estTradeValue: cell(rows, r, 8),
    });
  }
  return { nextDate, rows: out };
}

export interface NavPoint {
  date: string;
  nav: number;
  portfolioReturn: number;
}

// The equity curve does NOT read the sheet's own NAV tab -- that requires
// installDailySnapshot() to have been run in Apps Script (owner-only, needs
// Google account permissions we can't grant remotely). Instead
// data/nav-history.json is appended to once a day by
// .github/workflows/daily-nav-snapshot.yml, using only this repo's own
// GitHub Actions token -- no Google auth involved at all.
export function buildNavPoints(history: { date: string; nav: number }[]): NavPoint[] {
  return history
    .slice()
    .sort((a, b) => (a.date < b.date ? -1 : 1))
    .map((p) => ({ date: p.date, nav: p.nav, portfolioReturn: p.nav / START_CAPITAL - 1 }));
}

export interface DashboardData {
  nav: string;
  navRaw: number;
  totalPnl: string;
  todayPnl: string;
  portfolioReturn: string;
  portfolioReturnRaw: number;
  capitalValue: KV[];
  pnlReturn: KV[];
  riskConcentration: KV[];
  attention: KV[];
}

// Cash + current market value off the Holdings total row -- the same NAV
// math computeDashboard uses for the hero tiles, factored out so a sibling
// strategy plotted as a benchmark line (see lib/benchmarks.ts) can compute
// its own live NAV the same way, from its own Holdings tab.
export function computeLiveNav(holdings: { rows: HoldingRow[]; total: HoldingRow | null }): {
  nav: number;
  portfolioReturn: number;
} {
  const total = holdings.total;
  const costBasis = total ? toNumber(total.costBasis) : 0;
  const currentValue = total ? toNumber(total.currentValue) : 0;
  const cash = START_CAPITAL - costBasis;
  const nav = cash + currentValue;
  return { nav, portfolioReturn: nav / START_CAPITAL - 1 };
}

// Today's date in IST as YYYY-MM-DD, matching the nav-history.json date format.
export function todayIST(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

// Computed from Holdings (a stable, dense table) instead of the Dashboard
// tab's free-form layout -- see the note at the top of this file.
export function computeDashboard(
  holdings: { rows: HoldingRow[]; total: HoldingRow | null },
  rebalance: { nextDate: string; rows: RebalanceRow[] },
  momentum: MomentumRow[],
  overweightThreshold = 0.15 // 15% on the 10-stock book; the 20-stock book uses 8% (Settings!OVERWEIGHT)
): DashboardData {
  const total = holdings.total;
  const costBasis = total ? toNumber(total.costBasis) : 0;
  const currentValue = total ? toNumber(total.currentValue) : 0;
  const unrealisedPnl = total ? toNumber(total.unrealisedPnl) : 0;
  const dayPnl = total ? toNumber(total.dayPnl) : 0;

  const { nav, portfolioReturn } = computeLiveNav(holdings);
  const cash = START_CAPITAL - costBasis;
  const totalPnl = nav - START_CAPITAL;

  const weights = holdings.rows.map((h) => toFraction(h.actualWt)).filter((w) => w > 0);
  const sortedWeights = [...weights].sort((a, b) => b - a);
  const largest = sortedWeights[0] ?? 0;
  const smallest = sortedWeights[sortedWeights.length - 1] ?? 0;
  const top5 = sortedWeights.slice(0, 5).reduce((a, b) => a + b, 0);
  const maxDrift = Math.max(0, ...holdings.rows.map((h) => Math.abs(toFraction(h.wtDrift))));

  const byPnl = [...holdings.rows].sort((a, b) => toNumber(b.unrealisedPnl) - toNumber(a.unrealisedPnl));
  const best = byPnl[0]?.ticker.replace("NSE:", "") ?? "—";
  const worst = byPnl[byPnl.length - 1]?.ticker.replace("NSE:", "") ?? "—";

  const namesToRebalance = rebalance.rows.filter((r) => r.action !== "HOLD").length;
  const weakCount = momentum.filter((m) => m.health === "WEAK").length;
  const fadingCount = momentum.filter((m) => m.health === "FADING").length;
  const pricedCount = holdings.rows.filter((h) => h.cmp).length;

  const attentionNoPrice = holdings.rows.filter((h) => !h.cmp).map((h) => h.ticker.replace("NSE:", ""));
  const attentionOverweight = holdings.rows
    .filter((h) => toFraction(h.actualWt) > overweightThreshold)
    .map((h) => h.ticker.replace("NSE:", ""));
  const attentionWeak = momentum.filter((m) => m.health === "WEAK").map((m) => m.ticker.replace("NSE:", ""));

  return {
    nav: formatMoney(nav),
    navRaw: nav,
    totalPnl: formatMoney(totalPnl),
    todayPnl: formatMoney(dayPnl),
    portfolioReturn: formatPct(portfolioReturn),
    portfolioReturnRaw: portfolioReturn,
    capitalValue: [
      { label: "Starting Capital", value: formatMoney(START_CAPITAL) },
      { label: "Capital Deployed", value: formatMoney(costBasis) },
      { label: "Cash Balance", value: formatMoney(cash) },
      { label: "Current Market Value", value: formatMoney(currentValue) },
      { label: "NAV (Cash + Mkt Val)", value: formatMoney(nav) },
      { label: "Positions Priced", value: `${pricedCount} / ${holdings.rows.length}` },
    ],
    pnlReturn: [
      { label: "Unrealised P&L", value: formatMoney(unrealisedPnl) },
      { label: "Total Portfolio P&L", value: formatMoney(totalPnl) },
      { label: "Portfolio Return %", value: formatPct(portfolioReturn) },
      { label: "Today's P&L", value: formatMoney(dayPnl) },
      { label: "Best / Worst name", value: `${best}  /  ${worst}` },
    ],
    riskConcentration: [
      { label: "Largest Position %", value: formatPct(largest, 1) },
      { label: "Smallest Position %", value: formatPct(smallest, 1) },
      { label: "Top 5 Holdings %", value: formatPct(top5, 1) },
      { label: "Max Weight Drift", value: formatPct(maxDrift, 1) },
      { label: "Names to Rebalance", value: String(namesToRebalance) },
      { label: "Momentum: WEAK/FADING", value: `${weakCount} / ${fadingCount}` },
      { label: "Next Rebalance (Wed)", value: rebalance.nextDate || "—" },
    ],
    attention: [
      { label: "No price from GOOGLEFINANCE", value: attentionNoPrice.join(", ") || "None" },
      { label: `Overweight (> ${(overweightThreshold * 100).toFixed(0)}%)`, value: attentionOverweight.join(", ") || "None" },
      { label: "Momentum WEAK", value: attentionWeak.join(", ") || "None" },
    ],
  };
}
