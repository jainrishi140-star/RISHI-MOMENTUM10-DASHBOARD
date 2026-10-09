// ALL prices on the dashboard (CMP, value, P&L, weights, momentum returns,
// 52w stats, rebalance maths) come from Yahoo Finance. The sheets supply only
// the static book definition: tickers, entry price/date, shares, cost basis,
// target weights, realised P&L. There is NO fallback to the sheet's
// GOOGLEFINANCE numbers -- a ticker Yahoo can't price is left blank and is
// listed under "No price from Yahoo Finance".

import type { HoldingRow, MomentumRow, RebalanceRow } from "./portfolio";

export interface Mkt {
  last: number;
  prev: number; // previous trading day's close
  hi52: number;
  lo52: number;
  ret1m: number | null;
  ret3m: number | null;
  ret6m: number | null;
  ret12m: number | null;
}
export type MktMap = Map<string, Mkt | null>;

const bare = (t: string) => t.replace(/^NSE:|^BOM:|^BSE:/, "");
const ist = (t: number) => new Date(t * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

async function one(sym: string): Promise<Mkt | null> {
  for (const suf of [".NS", ".BO"]) {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await fetch(
          `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym + suf)}?range=1y&interval=1d`,
          { headers: { "User-Agent": "Mozilla/5.0" }, cache: "no-store" }
        );
        if (res.status === 404) break; // not listed under this suffix
        if (!res.ok) { await new Promise((r) => setTimeout(r, 300 * (attempt + 1))); continue; }
        const r = (await res.json()).chart?.result?.[0];
        const ts: number[] = r?.timestamp ?? [];
        const cl: (number | null)[] = r?.indicators?.quote?.[0]?.close ?? [];
        const last: number | undefined = r?.meta?.regularMarketPrice;
        if (!last || !ts.length) break;
        const latestDay = ist(r.meta.regularMarketTime ?? ts[ts.length - 1]);
        const bars = ts.map((t, i) => ({ d: ist(t), c: cl[i] })).filter((b): b is { d: string; c: number } => b.c != null);
        const prevBar = [...bars].reverse().find((b) => b.d < latestDay);
        // return vs the last close on/before (latest day - N calendar months), like EDATE back-dating
        const back = (m: number) => {
          const d = new Date(latestDay + "T00:00:00Z");
          d.setUTCMonth(d.getUTCMonth() - m);
          const key = d.toISOString().slice(0, 10);
          const b = [...bars].reverse().find((x) => x.d <= key);
          return b ? last / b.c - 1 : null;
        };
        return {
          last,
          prev: prevBar?.c ?? r.meta.chartPreviousClose ?? last,
          hi52: Math.max(r.meta.fiftyTwoWeekHigh ?? 0, last),
          lo52: Math.min(r.meta.fiftyTwoWeekLow ?? Infinity, last),
          ret1m: back(1), ret3m: back(3), ret6m: back(6), ret12m: back(12),
        };
      } catch {
        await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
      }
    }
  }
  return null;
}

export async function fetchMarket(tickers: string[]): Promise<MktMap> {
  const syms = [...new Set(tickers.map(bare).filter(Boolean))];
  const out: MktMap = new Map();
  await Promise.all(syms.map(async (s) => out.set(s, await one(s))));
  return out;
}

const num = (s: string) => {
  const n = Number(String(s ?? "").replace(/[₹,%\s]/g, ""));
  return Number.isFinite(n) ? n : 0;
};
const inr = (n: number, d = 2) => `${n < 0 ? "-" : ""}₹${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
const pct = (n: number | null, d = 2) => (n == null ? "" : `${(n * 100).toFixed(d)}%`);

export async function repriceHoldings(
  h: { rows: HoldingRow[]; total: HoldingRow | null },
  mkt?: MktMap
): Promise<{ rows: HoldingRow[]; total: HoldingRow | null }> {
  const m = mkt ?? (await fetchMarket(h.rows.map((r) => r.ticker)));
  const priced = h.rows.map((r) => {
    const q = m.get(bare(r.ticker));
    if (!q) return { ...r, cmp: "", currentValue: "", unrealisedPnl: "", pnlPct: "", dayPnl: "", high52w: "", pctFrom52wHigh: "" };
    const shares = num(r.shares), cost = num(r.costBasis), value = shares * q.last;
    return {
      ...r,
      cmp: inr(q.last),
      currentValue: inr(value, 0),
      unrealisedPnl: inr(value - cost, 0),
      pnlPct: pct(cost > 0 ? (value - cost) / cost : 0),
      dayPnl: inr(shares * (q.last - q.prev), 0),
      high52w: inr(q.hi52),
      pctFrom52wHigh: pct(q.last / q.hi52 - 1, 1),
    };
  });
  const sum = (f: (r: HoldingRow) => number) => priced.reduce((a, r) => a + f(r), 0);
  const mv = sum((r) => num(r.currentValue));
  const rows = priced.map((r) => {
    const actual = mv > 0 && r.cmp ? num(r.currentValue) / mv : 0;
    return { ...r, actualWt: r.cmp ? pct(actual, 1) : "", wtDrift: r.cmp ? pct(actual - num(r.targetWt) / 100, 1) : "" };
  });
  const cost = sum((r) => num(r.costBasis));
  const pricedCost = rows.filter((r) => r.cmp).reduce((a, r) => a + num(r.costBasis), 0);
  const total = h.total && {
    ...h.total,
    currentValue: inr(mv, 0),
    unrealisedPnl: inr(mv - pricedCost, 0),
    pnlPct: pct(pricedCost > 0 ? (mv - pricedCost) / pricedCost : 0),
    dayPnl: inr(sum((r) => num(r.dayPnl)), 0),
    costBasis: inr(cost, 0),
  };
  return { rows, total };
}

// Momentum tab: CMP, 1/3/6/12M returns, 52w stats, score, health and rank all
// recomputed from Yahoo (sheet's GOOGLEFINANCE history is not used).
export function repriceMomentum(rows: MomentumRow[], mkt: MktMap): MomentumRow[] {
  const out = rows.map((r) => {
    const q = mkt.get(bare(r.ticker));
    if (!q) {
      if (/CASH/i.test(r.health)) return r; // cash sleeve, not a stock
      return { ...r, cmp: "", ret1m: "", ret3m: "", ret6m: "", ret12m: "", high52w: "", low52w: "", pctFrom52wHigh: "", pctAbove52wLow: "", momScore: "", health: "NO DATA", rank12m: "" };
    }
    const { ret1m, ret3m, ret6m, ret12m } = q;
    const score = ret3m != null && ret6m != null && ret12m != null ? (ret3m + ret6m + ret12m) / 3 : null;
    const health = ret12m == null ? "NO DATA" : ret12m < 0 ? "WEAK" : ret1m != null && ret1m < 0 ? "FADING" : "OK";
    return {
      ...r,
      cmp: inr(q.last),
      ret1m: pct(ret1m, 1), ret3m: pct(ret3m, 1), ret6m: pct(ret6m, 1), ret12m: pct(ret12m, 1),
      high52w: inr(q.hi52), low52w: inr(q.lo52),
      pctFrom52wHigh: pct(q.last / q.hi52 - 1, 1),
      pctAbove52wLow: pct(q.last / q.lo52 - 1, 1),
      momScore: pct(score, 1),
      health,
    };
  });
  const ranked = out
    .map((r, i) => ({ i, v: mkt.get(bare(r.ticker))?.ret12m }))
    .filter((x): x is { i: number; v: number } => x.v != null)
    .sort((a, b) => b.v - a.v);
  ranked.forEach((x, k) => (out[x.i] = { ...out[x.i], rank12m: String(k + 1) }));
  return out;
}

// Rebalance tab: current value / drift / action / share counts recomputed with
// Yahoo prices (shares from Holdings). Target base = sheet base + change in the
// matched stock values, so cash-sleeve slots keep the sheet's own definition.
export function repriceRebalance<T extends { base: number; band: number; rows: RebalanceRow[] }>(
  rb: T,
  holdings: { rows: HoldingRow[] },
  mkt: MktMap
): T {
  const sharesBy = new Map<string, number>();
  for (const h of holdings.rows) sharesBy.set(bare(h.ticker), (sharesBy.get(bare(h.ticker)) ?? 0) + num(h.shares));
  const cur = (r: RebalanceRow) => {
    const q = mkt.get(bare(r.ticker)), sh = sharesBy.get(bare(r.ticker));
    return q && sh != null ? sh * q.last : null;
  };
  let delta = 0;
  for (const r of rb.rows) { const c = cur(r); if (c != null) delta += c - num(r.currentValue); }
  const base = rb.base + delta;
  const rows = rb.rows.map((r) => {
    const c = cur(r), q = mkt.get(bare(r.ticker));
    if (c == null || !q) return r.targetWt && sharesBy.has(bare(r.ticker)) ? { ...r, currentValue: "", driftRs: "", driftPct: "", action: "NO DATA", sharesToTrade: "", estTradeValue: "" } : r;
    const target = base * (num(r.targetWt) / 100);
    const drift = target - c, dp = target > 0 ? drift / target : 0;
    const action = Math.abs(dp) > rb.band ? (drift > 0 ? "BUY" : "SELL") : "HOLD";
    const sh = action === "HOLD" ? 0 : Math.round(drift / q.last);
    return {
      ...r,
      targetValue: inr(target, 0), currentValue: inr(c, 0),
      driftRs: inr(drift, 0), driftPct: pct(dp, 1),
      action, sharesToTrade: String(sh), estTradeValue: inr(sh * q.last, 0),
    };
  });
  return { ...rb, base, rows };
}
