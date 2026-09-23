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

// mfapi.in's upstream feed has gone stale for multi-day stretches before
// (silently stopped updating while still returning HTTP 200), so it can't be
// trusted alone. AMFI's own NAVAll.txt is the authoritative daily feed and
// is fetched every run to backfill/override whatever mfapi.in has -- if
// mfapi.in is stale, AMFI still supplies at least today's point.
async function moslNavMfapi() {
  const res = await fetch("https://api.mfapi.in/mf/153364"); // Motilal Oswal Active Momentum Fund - Direct - Growth
  if (!res.ok) throw new Error(`MOSL mfapi: HTTP ${res.status}`);
  const j = await res.json();
  return j.data.map((r) => {
    const [d, m, y] = r.date.split("-");
    return { date: `${y}-${pad(Number(m))}-${pad(Number(d))}`, value: Number(r.nav) };
  });
}

async function moslNavAmfi() {
  // amfiindia.com redirects here; hit the final host directly to avoid an
  // extra hop that occasionally times out.
  const res = await fetch("https://portal.amfiindia.com/spages/NAVAll.txt", {
    headers: { "User-Agent": "Mozilla/5.0" },
  });
  if (!res.ok) throw new Error(`MOSL AMFI: HTTP ${res.status}`);
  const text = await res.text();
  const row = text.split("\n").find((l) => l.startsWith("153364;")); // scheme code, Direct Plan - Growth
  if (!row) throw new Error("MOSL AMFI: scheme code 153364 not found in NAVAll.txt");
  const cols = row.split(";");
  const nav = Number(cols[6]);
  const [d, mon, y] = cols[7].trim().split("-");
  if (!Number.isFinite(nav) || nav <= 0) throw new Error(`MOSL AMFI: bad NAV "${cols[6]}"`);
  return [{ date: `${y}-${pad(MON[mon])}-${pad(Number(d))}`, value: nav }];
}

async function moslNav() {
  const results = await Promise.allSettled([moslNavMfapi(), moslNavAmfi()]);
  const byDate = new Map();
  for (const r of results) if (r.status === "fulfilled") for (const p of r.value) byDate.set(p.date, p);
  if (!byDate.size) throw results.find((r) => r.status === "rejected").reason;
  if (results[1].status === "rejected") console.warn(`[mosl] AMFI fallback failed: ${results[1].reason.message}`);
  return [...byDate.values()];
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
