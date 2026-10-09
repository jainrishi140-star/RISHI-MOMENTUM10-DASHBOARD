// Re-prices parsed Holdings with Yahoo Finance quotes instead of the sheet's
// GOOGLEFINANCE CMP. Shares / entry / cost / target weight still come from the
// sheet. Any ticker Yahoo can't price keeps its sheet values.

import type { HoldingRow } from "./portfolio";

type Quote = { last: number; prev: number };

async function quote(sym: string): Promise<Quote | null> {
  for (const suf of [".NS", ".BO"]) {
    try {
      const res = await fetch(
        `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym + suf)}?range=5d&interval=1d`,
        { headers: { "User-Agent": "Mozilla/5.0" }, cache: "no-store" }
      );
      if (!res.ok) continue;
      const r = (await res.json()).chart?.result?.[0];
      const ts: number[] = r?.timestamp ?? [];
      const cl: (number | null)[] = r?.indicators?.quote?.[0]?.close ?? [];
      const ist = (t: number) => new Date(t * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
      const last = r?.meta?.regularMarketPrice ?? [...cl].reverse().find((c) => c != null);
      if (!last) continue;
      // previous close = last daily close dated BEFORE the latest trading day
      // (right even before the open, when the newest bar is still yesterday's)
      const latestDay = ist(r?.meta?.regularMarketTime ?? ts.at(-1) ?? 0);
      let prev = r?.meta?.chartPreviousClose ?? last;
      for (let i = ts.length - 1; i >= 0; i--) if (cl[i] != null && ist(ts[i]) < latestDay) { prev = cl[i] as number; break; }
      return { last, prev };
    } catch {
      /* try next suffix */
    }
  }
  return null;
}

const num = (s: string) => {
  const n = Number(String(s ?? "").replace(/[₹,%\s]/g, ""));
  return Number.isFinite(n) ? n : 0;
};
const inr = (n: number, d = 2) => {
  const t = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  return `${n < 0 ? "-" : ""}₹${t}`;
};
const pct = (n: number, d = 2) => `${(n * 100).toFixed(d)}%`;

export async function repriceHoldings(h: {
  rows: HoldingRow[];
  total: HoldingRow | null;
}): Promise<{ rows: HoldingRow[]; total: HoldingRow | null }> {
  const quotes = await Promise.all(h.rows.map((r) => quote(r.ticker.replace(/^NSE:|^BOM:/, ""))));
  const rows = h.rows.map((r, i) => {
    const q = quotes[i];
    if (!q) return r;
    const shares = num(r.shares), cost = num(r.costBasis);
    const value = shares * q.last;
    const high = Math.max(num(r.high52w), q.last);
    return {
      ...r,
      cmp: inr(q.last),
      currentValue: inr(value, 0),
      unrealisedPnl: inr(value - cost, 0),
      pnlPct: pct(cost > 0 ? (value - cost) / cost : 0),
      dayPnl: inr(shares * (q.last - q.prev), 0),
      high52w: inr(high),
      pctFrom52wHigh: pct(high > 0 ? q.last / high - 1 : 0, 1),
    };
  });
  const sum = (f: (r: HoldingRow) => number) => rows.reduce((a, r) => a + f(r), 0);
  const mv = sum((r) => num(r.currentValue));
  const withWts = rows.map((r) => {
    const actual = mv > 0 ? num(r.currentValue) / mv : 0;
    return { ...r, actualWt: pct(actual, 1), wtDrift: pct(actual - num(r.targetWt) / 100, 1) };
  });
  const cost = sum((r) => num(r.costBasis));
  const total = h.total && {
    ...h.total,
    currentValue: inr(mv, 0),
    unrealisedPnl: inr(mv - cost, 0),
    pnlPct: pct(cost > 0 ? (mv - cost) / cost : 0),
    dayPnl: inr(sum((r) => num(r.dayPnl)), 0),
  };
  return { rows: withWts, total };
}
