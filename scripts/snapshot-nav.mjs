// Appends today's NAV to data/nav-history.json, computed from the Holdings
// tab of the Google Sheet -- the same way lib/portfolio.ts does it. Run
// daily by .github/workflows/daily-nav-snapshot.yml (no Google Apps Script
// dependency, no Google account permissions needed).

const SHEET_ID = "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac";
const START_CAPITAL = 10_000_000;
const HISTORY_PATH = new URL("../data/nav-history.json", import.meta.url);

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

async function fetchHoldingsTotal() {
  const url = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Holdings`;
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

async function main() {
  const { costBasis, currentValue } = await fetchHoldingsTotal();
  const cash = START_CAPITAL - costBasis;
  const nav = cash + currentValue;

  // IST calendar date, not UTC -- the snapshot represents end-of-trading-day India time.
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date()); // YYYY-MM-DD

  let history = [];
  try {
    const raw = await import("node:fs/promises").then((fs) => fs.readFile(HISTORY_PATH, "utf8"));
    history = JSON.parse(raw);
  } catch {
    history = [];
  }

  const idx = history.findIndex((p) => p.date === today);
  const point = { date: today, nav };
  if (idx >= 0) history[idx] = point;
  else history.push(point);
  history.sort((a, b) => (a.date < b.date ? -1 : 1));

  const fs = await import("node:fs/promises");
  await fs.writeFile(HISTORY_PATH, JSON.stringify(history, null, 2) + "\n");
  console.log(`Snapshot ${today}: NAV ${nav.toFixed(2)} (${history.length} points total)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
