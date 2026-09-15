// Pulls live data straight from a Google Sheet (RISHI MOMENTUM forward-test
// books -- both the 10-stock and 20-stock versions live in this one Next.js
// app now, on separate pages / sharing one Vercel deployment) on every
// request -- no cron, no cache, no copy of the data anywhere else. Whatever
// the sheet shows is what the dashboard shows, a request later.
//
// Fetched by TAB NAME via the gviz CSV endpoint, not by gid: every time
// buildPortfolio() re-runs in a sheet (OVERWRITE = true) it deletes and
// recreates every tab, which hands out fresh gids -- a gid-keyed fetch here
// would break on every rebuild. The tab name is stable across that, so
// resolve by name instead. Works for any sheet shared as "Anyone with the
// link -- Viewer", no Publish to web needed.

export const TABS = {
  dashboard: "Dashboard",
  holdings: "Holdings",
  rebalance: "Rebalance",
  momentum: "Momentum",
} as const;

function csvUrl(sheetId: string, sheetName: string): string {
  return `https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?tqx=out:csv&sheet=${encodeURIComponent(sheetName)}`;
}

// The equity curve reads from this repo's own data/nav-history-*.json files
// instead of each sheet's NAV tab -- see the note in lib/portfolio.ts.
// Fetched raw from GitHub so it's always current, independent of which
// Vercel deploy is live.
const REPO_RAW_BASE =
  "https://raw.githubusercontent.com/jainrishi140-star/RISHI-MOMENTUM10-DASHBOARD/main/data";

export async function fetchNavHistory(fileName: string): Promise<{ date: string; nav: number }[]> {
  const res = await fetch(`${REPO_RAW_BASE}/${fileName}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`NAV history fetch failed (HTTP ${res.status})`);
  return res.json();
}

// Minimal RFC4180 CSV parser -- handles quoted fields with embedded commas,
// newlines and escaped quotes, which is what Sheets emits for merged/wrapped
// cells (e.g. the README paragraphs, DataCheck details).
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
      continue;
    }
    if (c === '"') inQuotes = true;
    else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (c === "\r") {
      // skip -- \r\n line endings
    } else {
      field += c;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

export async function fetchSheetRows(sheetId: string, sheetName: string): Promise<string[][]> {
  const res = await fetch(csvUrl(sheetId, sheetName), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Sheet fetch failed (HTTP ${res.status}) for tab "${sheetName}"`);
  }
  const text = await res.text();
  // Google returns an HTML sign-in page (not CSV) if the sheet isn't
  // actually public -- surface that clearly instead of parsing garbage.
  if (text.trimStart().startsWith("<")) {
    throw new Error(
      `Tab "${sheetName}" did not return CSV -- check it is shared "Anyone with the link -- Viewer"`
    );
  }
  return parseCsv(text);
}

export function cell(rows: string[][], r: number, c: number): string {
  return (rows[r]?.[c] ?? "").trim();
}

export function isNegative(s: string): boolean {
  return s.trim().startsWith("-");
}
