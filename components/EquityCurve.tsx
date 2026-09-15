import { NavPoint } from "@/lib/portfolio";

// Lightweight inline-SVG line chart -- avoids pulling in a charting library
// for what is, for now, a short-history sparkline. Plots cumulative
// portfolio return vs the Nifty 500 benchmark return, both indexed to 0% at
// the first recorded day.
export default function EquityCurve({ points }: { points: NavPoint[] }) {
  if (points.length < 2) {
    return (
      <div className="flex h-40 items-center justify-center px-4 text-center text-sm text-zinc-500 dark:text-zinc-500">
        <span>
          Run <code className="mx-1 rounded bg-zinc-800 px-1.5 py-0.5 text-xs">installDailySnapshot()</code>
          in the sheet to start recording the equity curve.
        </span>
      </div>
    );
  }

  const width = 760;
  const height = 220;
  const pad = 28;

  const port = points.map((p) => p.portfolioReturn * 100);
  const bench = points.map((p) => p.benchmarkReturn * 100);
  const all = [...port, ...bench];
  const min = Math.min(0, ...all);
  const max = Math.max(0, ...all);
  const span = max - min || 1;

  const x = (i: number) => pad + (i / (points.length - 1)) * (width - pad * 2);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad * 2);

  const pathFor = (series: number[]) =>
    series.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  const zeroY = y(0);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Equity curve">
      <line x1={pad} y1={zeroY} x2={width - pad} y2={zeroY} stroke="var(--grid-line)" strokeDasharray="4 4" />
      <path d={pathFor(bench)} fill="none" stroke="var(--series-2)" strokeWidth={2} />
      <path d={pathFor(port)} fill="none" stroke="var(--series-1)" strokeWidth={2.5} />
      <text x={pad} y={14} fill="var(--series-1)" fontSize={11} fontWeight={600}>
        Portfolio {port[port.length - 1].toFixed(1)}%
      </text>
      <text x={pad + 160} y={14} fill="var(--series-2)" fontSize={11} fontWeight={600}>
        Nifty 500 {bench[bench.length - 1].toFixed(1)}%
      </text>
    </svg>
  );
}
