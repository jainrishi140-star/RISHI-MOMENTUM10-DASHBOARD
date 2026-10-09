// Re-prices all 4 dashboard books from Yahoo Finance (instead of GOOGLEFINANCE CMP in the sheets)
// and merges daily NAV points into data/nav-history-*.json. Lots/shares/cost come from each sheet's Holdings tab.
// NAV(d) = START - cost of lots entered on/before d + realised + sum(shares * Yahoo close(d)) for those lots.
// Usage: node scripts/yahoo-run-all.mjs [--write]
import fs from "node:fs/promises";
const WRITE = process.argv.includes("--write");
const START_CAPITAL = 10_000_000;
const S = [
  ["mom10", "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac"],
  ["mom20", "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY"],
  ["star-rsi-sharpe", "1QDV04yw1Gb-hm0Y-K1NiDkyp-zyHm3jJQrOx-zZQTvU"],
  ["rishi-viraj", "1Ls5COhCkEEEtvFwqWvUxnwpj_NI8OwnIRuP3vK-KPkg"],
];
const MON = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
const pad = (n) => String(n).padStart(2, "0");
const num = (s) => { const n = Number(String(s ?? "").replace(/[₹,%\s]/g, "")); return Number.isFinite(n) ? n : 0; };
function parseCsv(t) { const rows = []; let r = [], f = "", q = false;
  for (let i = 0; i < t.length; i++) { const c = t[i];
    if (q) { if (c === '"') { if (t[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; continue; }
    if (c === '"') q = true; else if (c === ",") { r.push(f); f = ""; } else if (c === "\n") { r.push(f); rows.push(r); r = []; f = ""; } else if (c !== "\r") f += c; }
  if (f.length || r.length) { r.push(f); rows.push(r); } return rows; }
const tab = async (id, name) => parseCsv(await (await fetch(`https://docs.google.com/spreadsheets/d/${id}/gviz/tq?tqx=out:csv&sheet=${name}`)).text());
const iso = (s) => { const m = /^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/.exec(s.trim()); return m ? `${m[3]}-${pad(MON[m[2]])}-${pad(+m[1])}` : null; };
const closes = {};
async function yahoo(sym) { // sym like CUPID -> CUPID.NS
  if (closes[sym]) return closes[sym];
  for (const suf of [".NS", ".BO"]) {
    const res = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym + suf)}?range=3mo&interval=1d`, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!res.ok) continue;
    const r = (await res.json()).chart?.result?.[0]; if (!r?.timestamp) continue;
    const m = new Map();
    r.timestamp.forEach((t, i) => { const c = r.indicators.quote[0].close[i]; if (c != null) m.set(new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date(t * 1000)), c); });
    return (closes[sym] = m);
  }
  throw new Error("no Yahoo data for " + sym);
}
for (const [name, id] of S) {
  const h = await tab(id, "Holdings");
  const hi = h.findIndex((r) => r[0]?.trim() === "Ticker");
  const lots = h.slice(hi + 1).filter((r) => r[0]?.trim() && r[0].trim().toUpperCase() !== "TOTAL")
    .map((r) => ({ sym: r[0].trim().replace(/^NSE:|^BOM:/, ""), entry: iso(r[2]), shares: num(r[4]), cost: num(r[5]), sheetCmp: num(r[6]) }));
  const rl = await tab(id, "Realised"); let realised = 0;
  if ((rl[0]?.[0] ?? "").trim().toUpperCase().startsWith("REALISED")) { const t = rl.find((r) => (r[0] ?? "").trim().toLowerCase().startsWith("total realised")); realised = t ? num(t[1]) : 0; }
  await Promise.all([...new Set(lots.map((l) => l.sym))].map(yahoo));
  const dates = [...new Set(lots.flatMap((l) => [...closes[l.sym].keys()]))].sort();
  const histPath = new URL(`../data/nav-history-${name}.json`, import.meta.url);
  const hist = JSON.parse(await fs.readFile(histPath, "utf8"));
  const last = hist.at(-1)?.date ?? "0000";
  const navOn = (d) => { let cash = START_CAPITAL + realised, val = 0;
    for (const l of lots) { if (l.entry && l.entry > d) continue; cash -= l.cost; const m = closes[l.sym]; let px = m.get(d); if (px == null) { const prev = [...m.keys()].filter((k) => k <= d).sort().at(-1); px = prev ? m.get(prev) : l.cost / l.shares; } val += l.shares * px; }
    return cash + val; };
  const today = dates.at(-1);
  const drift = lots.map((l) => ({ s: l.sym, sheet: l.sheetCmp, yf: closes[l.sym].get(today) })).filter((x) => Math.abs(x.yf / x.sheet - 1) > 0.01);
  const add = dates.filter((d) => d > last || d === today).map((d) => ({ date: d, nav: Math.round(navOn(d)) }));
  console.log(`[${name}] lots=${lots.length} realised=${realised} last hist=${last} ${hist.at(-1)?.nav} | Yahoo ${today} NAV=${add.at(-1)?.nav} | +${add.length} pts | >1% price diff vs sheet: ${drift.map((x) => `${x.s}(${x.sheet}->${x.yf?.toFixed(2)})`).join(", ") || "none"}`);
  if (WRITE) { const by = new Map(hist.map((p) => [p.date, p])); add.forEach((p) => by.set(p.date, p));
    await fs.writeFile(histPath, JSON.stringify([...by.values()].sort((a, b) => (a.date < b.date ? -1 : 1)), null, 2) + "\n"); }
}
