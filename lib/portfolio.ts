// Maps raw CSV rows from each tab back onto the fixed cell layout that
// BuildMomentumPortfolio_10stock.gs writes (see that file for the source of
// truth). Cell text is already formatted by Sheets on export (e.g. "₹9,630,152",
// "1.13%", "-4.82%") so most fields are rendered as-is, not re-parsed.

import { cell } from "./sheet";

export interface KV {
  label: string;
  value: string;
}

export interface DashboardData {
  title: string;
  subtitle: string;
  nav: string;
  totalPnl: string;
  todayPnl: string;
  returnVsBenchmark: string;
  capitalValue: KV[];
  pnlReturn: KV[];
  riskConcentration: KV[];
  attention: KV[];
}

export function parseDashboard(rows: string[][]): DashboardData {
  const kvBlock = (startRow: number, count: number, labelCol: number, valueCol: number): KV[] => {
    const out: KV[] = [];
    for (let i = 0; i < count; i++) {
      const label = cell(rows, startRow + i, labelCol);
      if (!label) continue;
      out.push({ label, value: cell(rows, startRow + i, valueCol) });
    }
    return out;
  };

  return {
    title: cell(rows, 0, 0),
    subtitle: cell(rows, 1, 0),
    nav: cell(rows, 4, 0),
    totalPnl: cell(rows, 4, 2),
    todayPnl: cell(rows, 4, 4),
    returnVsBenchmark: cell(rows, 4, 6),
    // Settings!B10 rows: block1 8 rows, block2 7 rows, block3 7 rows, starting sheet row 11 (0-idx 10)
    capitalValue: kvBlock(10, 8, 0, 1),
    pnlReturn: kvBlock(10, 7, 3, 4),
    riskConcentration: kvBlock(10, 7, 6, 7),
    // Attention panel: sheet rows 27-30 (0-idx 26-29), label col A(0), detail col C(2)
    attention: kvBlock(26, 4, 0, 2),
  };
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
  const out: HoldingRow[] = [];
  let total: HoldingRow | null = null;
  for (let r = 1; r < rows.length; r++) {
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
  const out: MomentumRow[] = [];
  for (let r = 1; r < rows.length; r++) {
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
  const nextDate = cell(rows, 1, 1); // B2
  const out: RebalanceRow[] = [];
  for (let r = 4; r < rows.length; r++) {
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
  benchmarkReturn: number;
}

function toNumber(s: string): number | null {
  const cleaned = s.replace(/[₹,%\s]/g, "");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function parseNav(rows: string[][]): NavPoint[] {
  const out: NavPoint[] = [];
  for (let r = 1; r < rows.length; r++) {
    const date = cell(rows, r, 0);
    const navStr = cell(rows, r, 3);
    if (!date || !navStr) continue;
    const nav = toNumber(navStr);
    if (nav === null) continue;
    out.push({
      date,
      nav,
      portfolioReturn: toNumber(cell(rows, r, 5)) ?? 0,
      benchmarkReturn: toNumber(cell(rows, r, 7)) ?? 0,
    });
  }
  return out;
}
