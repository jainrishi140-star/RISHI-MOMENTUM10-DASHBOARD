// Rebuilds the stable tail of each data/nav-history-*.json from Yahoo Finance daily closes
// (NAV = 1Cr + realised - cost of held lots + shares x Yahoo close). A rebuild is only valid
// from the day AFTER the book's last entry date -- earlier days contain lots that have since
// been sold and are no longer in the Holdings tab, so those snapshots are left untouched.
// Yahoo daily bars sometimes drop a session's close (null); those are filled from the last 5m bar.
// Today's (intraday) point is dropped; the page splices a live point and the 18:05 IST cron writes the close.
// Usage: node scripts/rebuild-nav-history.mjs [--write]
import fs from "node:fs/promises";
const WRITE = process.argv.includes("--write");
const ids = {
  mom10: "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac",
  mom20: "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY",
  "star-rsi-sharpe": "1QDV04yw1Gb-hm0Y-K1NiDkyp-zyHm3jJQrOx-zZQTvU",
  "rishi-viraj": "1Ls5COhCkEEEtvFwqWvUxnwpj_NI8OwnIRuP3vK-KPkg",
};
const NL = String.fromCharCode(10);
const num = (s) => Number(String(s).replace(/[₹,%\s]/g, ""));
const MON = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
const iso = (s) => { const m = /^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/.exec(s.trim()); return m ? `${m[3]}-${String(MON[m[2]]).padStart(2, "0")}-${m[1].padStart(2, "0")}` : null; };
function csv(t) {
  const rows = []; let r = [], f = "", q = false;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (q) { if (c === '"') { if (t[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; continue; }
    if (c === '"') q = true; else if (c === ",") { r.push(f); f = ""; } else if (c === NL) { r.push(f); rows.push(r); r = []; f = ""; } else if (c !== "\r") f += c;
  }
  if (f || r.length) { r.push(f); rows.push(r); }
  return rows;
}
const sheet = async (id, tab) => csv(await (await fetch(`https://docs.google.com/spreadsheets/d/${id}/gviz/tq?tqx=out:csv&sheet=${tab}`)).text());
const istD = (t) => new Date(t * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
const H = { headers: { "User-Agent": "Mozilla/5.0" } };
const C = {};
async function closes(t) {
  if (C[t]) return C[t];
  const d = (await (await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${t}.NS?range=3mo&interval=1d`, H)).json()).chart.result[0];
  const m = new Map(); const gaps = [];
  d.timestamp.forEach((x, i) => { const c = d.indicators.quote[0].close[i]; if (c != null) m.set(istD(x), c); else gaps.push(istD(x)); });
  // fill gaps from 5m bars (last bar of that session)
  if (gaps.length) {
    const i5 = (await (await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${t}.NS?range=1mo&interval=5m`, H)).json()).chart.result[0];
    const last = new Map();
    i5.timestamp.forEach((x, i) => { const c = i5.indicators.quote[0].close[i]; if (c != null) last.set(istD(x), c); });
    for (const g of gaps) if (last.has(g)) m.set(g, last.get(g));
  }
  return (C[t] = { m, gaps });
}
for (const [name, id] of Object.entries(ids)) {
  const sh = await sheet(id, "Holdings");
  const hi = sh.findIndex((r) => r[0]?.trim() === "Ticker");
  const lots = sh.slice(hi + 1).filter((r) => r[0]?.trim() && r[0].trim().toUpperCase() !== "TOTAL")
    .map((r) => ({ t: r[0].trim().replace(/^NSE:/, ""), entry: iso(r[2]), sh: num(r[4]), cost: num(r[5]) }));
  const rl = await sheet(id, "Realised"); let realised = 0;
  if ((rl[0]?.[0] || "").toUpperCase().startsWith("REALISED")) { const t = rl.find((r) => (r[0] || "").toLowerCase().startsWith("total realised")); realised = t ? num(t[1]) : 0; }
  const cost = lots.reduce((a, l) => a + l.cost, 0);
  const fund = Math.max(0, cost - realised - 1e7);
  const path = new URL(`../data/nav-history-${name}.json`, import.meta.url);
  const hist = JSON.parse(await fs.readFile(path, "utf8"));
  const todayIst = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
  const lastEntry = lots.map((l) => l.entry).filter(Boolean).sort().at(-1) ?? "0000";
  const cl = {}; for (const l of lots) cl[l.t] = await closes(l.t);
  const dates = [...new Set(lots.flatMap((l) => [...cl[l.t].m.keys()]))].sort().filter((d) => d > lastEntry && d < todayIst);
  const by = new Map(hist.filter((p) => p.date < todayIst).map((p) => [p.date, p]));
  let maxDiff = 0, n = 0;
  for (const d of dates) {
    const priced = lots.filter((l) => cl[l.t].m.has(d)).length;
    if (priced < lots.length) { console.log(`  ${name} ${d}: only ${priced}/${lots.length} prices -- skipped`); continue; }
    const nav = Math.round(1e7 + realised - cost + lots.reduce((a, l) => a + l.sh * cl[l.t].m.get(d), 0));
    const old = by.get(d)?.nav; if (old != null) maxDiff = Math.max(maxDiff, Math.abs(old - nav));
    by.set(d, { date: d, nav }); n++;
  }
  console.log(`[${name}] rebuilt ${n} days after ${lastEntry} (max change vs stored ${Math.round(maxDiff)}); today's intraday point dropped`);
  if (WRITE) await fs.writeFile(path, JSON.stringify([...by.values()].sort((a, b) => (a.date < b.date ? -1 : 1)), null, 2) + String.fromCharCode(10));
}
