// Refreshes data/benchmarks.json: daily levels/NAV for the three benchmarks
// drawn on every equity curve. Idempotent -- re-fetches a window back to
// START and merges by date, so late-published closes/NAVs self-correct.
//   nifty500   -- NIFTY 500 index (niftyindices.com)
//   n500mom50  -- NIFTY500 MOMENTUM 50 index (niftyindices.com)
//   mosl       -- Motilal Oswal Active Momentum Fund, Direct Growth NAV (mfapi.in)

import fs from "node:fs/promises";

const START = "2026-08-25"; // a few days before the earliest strategy start (2026-09-02)
const OUT = new URL("../data/benchmarks.json", import.meta.url);
const MON = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
const MONTHS = Object.keys(MON);

const pad = (n) => String(n).padStart(2, "0");
const fmtNse = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${pad(d)}-${MONTHS[m - 1]}-${y}`; };
const todayIst = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());

async function niftyIndices(code, name) {
  const body = { cinfo: `{'name':'${code}','startDate':'${fmtNse(START)}','endDate':'${fmtNse(todayIst())}','indexName':'${name}'}` };
  const res = await fetch("https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString", {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8", "User-Agent": "Mozilla/5.0" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  const rows = JSON.parse(await res.text());
  return rows.map((r) => {
    const [d, m, y] = r.HistoricalDate.split(" ");
    return { date: `${y}-${pad(MON[m])}-${pad(Number(d))}`, value: Number(String(r.CLOSE).replace(/,/g, "")) };
  });
}

async function moslNav() {
  const res = await fetch("https://api.mfapi.in/mf/153364"); // Motilal Oswal Active Momentum Fund - Direct - Growth
  if (!res.ok) throw new Error(`MOSL: HTTP ${res.status}`);
  const j = await res.json();
  return j.data.map((r) => {
    const [d, m, y] = r.date.split("-");
    return { date: `${y}-${m}-${d}`, value: Number(r.nav) };
  });
}

const SOURCES = {
  nifty500: () => niftyIndices("NIFTY 500", "NIFTY 500"),
  n500mom50: () => niftyIndices("NIFTY500MOMENTM50", "NIFTY500 MOMENTUM 50"),
  mosl: moslNav,
};

async function main() {
  let store = {};
  try { store = JSON.parse(await fs.readFile(OUT, "utf8")); } catch { store = {}; }
  let failed = false;
  for (const [key, fetcher] of Object.entries(SOURCES)) {
    try {
      let raw;
      for (let attempt = 1; ; attempt++) {
        try { raw = await fetcher(); break; } catch (e) { if (attempt >= 3) throw e; await new Promise((r) => setTimeout(r, 2000)); }
      }
      const fresh = raw.filter((p) => p.date >= START && Number.isFinite(p.value) && p.value > 0);
      const byDate = new Map((store[key] ?? []).map((p) => [p.date, p]));
      for (const p of fresh) byDate.set(p.date, p);
      store[key] = [...byDate.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
      console.log(`[${key}] ${store[key].length} points, last ${store[key].at(-1)?.date}`);
    } catch (e) {
      failed = true;
      console.error(`[${key}] FAILED: ${e.message} -- keeping existing data`);
    }
  }
  await fs.writeFile(OUT, JSON.stringify(store, null, 1) + "\n");
  if (failed) process.exitCode = 1;
}
main();
