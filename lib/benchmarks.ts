// Benchmarks drawn on every equity curve, rebased to 0% at each strategy's
// own start date. Raw levels/NAVs live in data/benchmarks.json, refreshed by
// scripts/snapshot-benchmarks.mjs (daily GitHub Action).

const REPO_RAW_BASE =
  "https://raw.githubusercontent.com/jainrishi140-star/RISHI-MOMENTUM10-DASHBOARD/main/data";

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

export async function fetchBenchmarks(startDate: string | undefined): Promise<BenchmarkSeries[]> {
  if (!startDate) return [];
  const res = await fetch(`${REPO_RAW_BASE}/benchmarks.json`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Benchmarks fetch failed (HTTP ${res.status})`);
  const raw: Record<string, { date: string; value: number }[]> = await res.json();
  return DEFS.map((d) => {
    const s = (raw[d.key] ?? []).slice().sort((a, b) => (a.date < b.date ? -1 : 1));
    // Base = last close on or before the strategy start date (else first available).
    const base = [...s].reverse().find((p) => p.date <= startDate) ?? s[0];
    const points = base
      ? s.filter((p) => p.date >= base.date).map((p) => ({ date: p.date < startDate ? startDate : p.date, ret: p.value / base.value - 1 }))
      : [];
    // Collapse a pre-start base row and a same-day row to one point per date.
    const dedup = new Map(points.map((p) => [p.date, p]));
    return { key: d.key, label: d.label, color: d.color, dash: "dash" in d ? d.dash : undefined, points: [...dedup.values()] };
  });
}
