// Pulls live data straight from the "Top 10 ER MOM PORTFOLIO" Google Sheet
// (RISHI MOMENTUM-10 forward test) on every request -- no cron, no cache,
// no copy of the data anywhere else. Whatever the sheet shows is what the
// dashboard shows, a request later.
//
// Fetched by TAB NAME via the gviz CSV endpoint, not by gid: every time
// buildPortfolio() re-runs in the sheet (OVERWRITE = true) it deletes and
// recreates every tab, which hands out fresh gids -- a gid-keyed fetch here
// would break on every rebuild. The tab name is stable across that, so
// resolve by name instead. Works for any sheet shared as "Anyone with the
// link -- Viewer", no Publish to web needed.

const SHEET_ID = "1coh8Lbbw-K1dpZm5OPHhVtFcWZbAATGu-5-9Bt2KXac";

export const TABS = {
  dashboard: "Dashboard",
  holdings: "Holdings",
  rebalance: "Rebalance",
  momentum: "Momentum",
  nav: "NAV",
} as const;

function csvUrl(sheetName: string): string {
  return `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&sheet=${encodeURIComponent(sheetName)}`;
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

export async function fetchSheetRows(sheetName: string): Promise<string[][]> {
  const res = await fetch(csvUrl(sheetName), { cache: "no-store" });
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
