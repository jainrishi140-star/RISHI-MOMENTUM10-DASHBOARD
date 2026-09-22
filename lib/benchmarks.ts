// Benchmarks drawn on every equity curve, rebased to 0% at each strategy's
// own start date. Raw levels/NAVs live in data/benchmarks.json, refreshed by
// scripts/snapshot-benchmarks.mjs (daily GitHub Action).

const REPO_RAW_BASE =
  "https://raw.githubusercontent.com/jainrishi140-star/RISHI-MOMENTUM10-DASHBOARD/main/data";

// Last benchmark trading day strictly before `date` (Nifty 500 calendar).
export async function priorTradingDay(date: string): Promise<string | undefined> {
  const res = await fetch(`${REPO_RAW_BASE}/benchmarks.json`, { cache: "no-store" });
  if (!res.ok) return undefined;
  const raw: Record<string, { date: string }[]> = await res.json();
  return (raw.nifty500 ?? []).map((p) => p.date).filter((d) => d < date).sort().at(-1);
}

export interface BenchmarkSeries {
  key: string;
  label: string;
  color: string;
  dash?: string;
  points: { date: string; ret: number }[]; // ret is a fraction, 0 at the start date
}

const DEFS = [
  { key: "nifty500", label: "Nifty 500", color: "var(--series-2)" },
  { key: "n500mom50", label: "Nifty500 Momentum 50", color: "var(--series-3)", dash: "6 3" },
  { key: "mosl", label: "MOSL Active Momentum Fund", color: "var(--series-4)", dash: "2 3" },
] as const;

// Shared rebasing: given a raw {date, value} series and the strategy's 0%
// anchor date, base it off the last value on or before that date (else the
// series' own first value) and return points from there onward.
function rebase(
  series: { date: string; value: number }[],
  startDate: string
): { date: string; ret: number }[] {
  const s = series.slice().sort((a, b) => (a.date < b.date ? -1 : 1));
  const base = [...s].reverse().find((p) => p.date <= startDate) ?? s[0];
  if (!base) return [];
  const points = s
    .filter((p) => p.date >= base.date)
    .map((p) => ({ date: p.date < startDate ? startDate : p.date, ret: p.value / base.value - 1 }));
  // Collapse a pre-start base row and a same-day row to one point per date.
  return [...new Map(points.map((p) => [p.date, p])).values()];
}

// startDate is the 0% anchor. If the strategy's first snapshot is already off
// its starting capital (money went to work before the first snapshot), pass the
// PRIOR trading day so benchmarks are measured over the same window.
export async function fetchBenchmarks(startDate: string | undefined): Promise<BenchmarkSeries[]> {
  if (!startDate) return [];
  const res = await fetch(`${REPO_RAW_BASE}/benchmarks.json`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Benchmarks fetch failed (HTTP ${res.status})`);
  const raw: Record<string, { date: string; value: number }[]> = await res.json();
  return DEFS.map((d) => ({
    key: d.key,
    label: d.label,
    color: d.color,
    dash: "dash" in d ? d.dash : undefined,
    points: rebase(raw[d.key] ?? [], startDate),
  }));
}

export interface SiblingStrategyDef {
  key: string;
  label: string;
  navHistoryFile: string; // data/nav-history-*.json in this same repo
  color: string;
  dash?: string;
}

// Other RISHI forward-test books (e.g. MOM10, MOM20), plotted as extra lines
// on a strategy's own equity curve so you can eyeball them side by side.
// Each sibling's own NAV history is rebased to ITS ₹1 Cr start capital first
// (same as buildNavPoints), then rebased again onto the host strategy's
// startDate, exactly like an index/fund benchmark.
export async function fetchSiblingStrategies(
  defs: SiblingStrategyDef[],
  startDate: string | undefined
): Promise<BenchmarkSeries[]> {
  if (!startDate || !defs.length) return [];
  const results = await Promise.all(
    defs.map(async (d) => {
      const res = await fetch(`${REPO_RAW_BASE}/${d.navHistoryFile}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`${d.label} NAV history fetch failed (HTTP ${res.status})`);
      const history: { date: string; nav: number }[] = await res.json();
      const series = history.map((p) => ({ date: p.date, value: p.nav }));
      return { key: d.key, label: d.label, color: d.color, dash: d.dash, points: rebase(series, startDate) };
    })
  );
  return results;
}
