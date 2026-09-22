// Appends today's NAV to each strategy's data/nav-history-*.json, computed
// from that sheet's Holdings tab -- the same way lib/portfolio.ts does it.
// Run daily by .github/workflows/daily-nav-snapshot.yml (no Google Apps
// Script dependency, no Google account permissions needed).

import fs from "node:fs/promises";

const START_CAPITAL = 10_000_000;

const STRATEGIES = [
  {
    name: "mom10",
    sheetId: "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac", // Top 10 ER MOM PORTFOLIO
    historyPath: new URL("../data/nav-history-mom10.json", import.meta.url),
  },
  {
    name: "mom20",
    sheetId: "1yU6YSzZcyAHlhH-4aFlrVNaiDOcT5afdvar1yuAaQCY", // 20/60 mom portfolio
    historyPath: new URL("../data/nav-history-mom20.json", import.meta.url),
  },
  {
    name: "star-rsi-sharpe",
    sheetId: "1QDV04yw1Gb-hm0Y-K1NiDkyp-zyHm3jJQrOx-zZQTvU", // STAR RSI SHARPE
    historyPath: new URL("../data/nav-history-star-rsi-sharpe.json", import.meta.url),
  },
  {
    name: "rishi-viraj",
    sheetId: "1Ls5COhCkEEEtvFwqWvUxnwpj_NI8OwnIRuP3vK-KPkg", // RISHI x VIRAJ -- 19 COMMON NAMES + CASH
    historyPath: new URL("../data/nav-history-rishi-viraj.json", import.meta.url),
  },
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
      continue;
    }
    if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c === "\r") { /* skip */ }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function toNumber(s) {
  const cleaned = (s ?? "").replace(/[₹,%\s]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

async function fetchHoldingsTotal(sheetId) {
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?tqx=out:csv&sheet=Holdings`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Holdings fetch failed: HTTP ${res.status}`);
  const rows = parseCsv(await res.text());
  const headerIdx = rows.findIndex((r) => (r[0] ?? "").trim() === "Ticker");
  const totalRow = rows.slice(headerIdx + 1).find((r) => (r[0] ?? "").trim().toUpperCase() === "TOTAL");
  if (!totalRow) throw new Error("Could not find TOTAL row in Holdings");
  return {
    costBasis: toNumber(totalRow[5]),
    currentValue: toNumber(totalRow[7]),
  };
}

async function snapshotOne(strategy) {
  const { costBasis, currentValue } = await fetchHoldingsTotal(strategy.sheetId);
  const cash = START_CAPITAL - costBasis;
  const nav = cash + currentValue;

  // IST calendar date, not UTC -- the snapshot represents end-of-trading-day India time.
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date()); // YYYY-MM-DD

  let history = [];
  try {
    history = JSON.parse(await fs.readFile(strategy.historyPath, "utf8"));
  } catch {
    history = [];
  }

  const idx = history.findIndex((p) => p.date === today);
  const point = { date: today, nav };
  if (idx >= 0) history[idx] = point;
  else history.push(point);
  history.sort((a, b) => (a.date < b.date ? -1 : 1));

  await fs.writeFile(strategy.historyPath, JSON.stringify(history, null, 2) + "\n");
  console.log(`[${strategy.name}] Snapshot ${today}: NAV ${nav.toFixed(2)} (${history.length} points total)`);
}

async function main() {
  for (const strategy of STRATEGIES) {
    await snapshotOne(strategy);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
