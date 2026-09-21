import { NavPoint } from "@/lib/portfolio";
import type { BenchmarkSeries } from "@/lib/benchmarks";

// Lightweight inline-SVG line chart -- avoids pulling in a charting library
// for a short-history chart. Plots cumulative return, indexed to 0% at the
// paper-start date, for the portfolio and each benchmark (rebased to the
// same start date). X axis is calendar time so the daily benchmark series
// and the portfolio's snapshots line up.
export default function EquityCurve({
  points,
  benchmarks = [],
}: {
  points: NavPoint[];
  benchmarks?: BenchmarkSeries[];
}) {
  if (points.length < 1) {
    return (
      <div className="flex h-40 items-center justify-center px-4 text-center text-sm text-zinc-500 dark:text-zinc-500">
        Waiting on the first daily NAV snapshot to draw a curve.
      </div>
    );
  }

  const width = 760;
  const height = 250;
  const pad = 28;
  const padTop = 30;

  const t = (d: string) => Date.parse(d + "T00:00:00Z");
  const start = t(points[0].date);
  const bench = benchmarks.map((b) => ({ ...b, points: b.points.filter((p) => t(p.date) >= start) }));
  const allDates = [...points.map((p) => p.date), ...bench.flatMap((b) => b.points.map((p) => p.date))];
  const end = Math.max(...allDates.map(t));
  const xspan = end - start || 1;

  const port = points.map((p) => ({ date: p.date, v: p.portfolioReturn * 100 }));
  const allVals = [0, ...port.map((p) => p.v), ...bench.flatMap((b) => b.points.map((p) => p.ret * 100))];
  const min = Math.min(...allVals);
  const max = Math.max(...allVals);
  const span = max - min || 1;

  const x = (d: string) => pad + ((t(d) - start) / xspan) * (width - pad * 2);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad - padTop);
  const pathFor = (s: { date: string; v: number }[]) =>
    s.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.date).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const fmt = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

  const zeroY = y(0);
  const legend = [
    { label: "Portfolio", color: "var(--series-1)", last: port[port.length - 1].v },
    ...bench
      .filter((b) => b.points.length)
      .map((b) => ({ label: b.label, color: b.color, last: b.points[b.points.length - 1].ret * 100 })),
  ];

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Equity curve vs benchmarks">
        <line x1={pad} y1={zeroY} x2={width - pad} y2={zeroY} stroke="var(--grid-line)" strokeDasharray="4 4" />
        <text x={pad} y={height - 8} fill="var(--text-secondary)" fontSize={10}>
          {points[0].date}
        </text>
        <text x={width - pad} y={height - 8} fill="var(--text-secondary)" fontSize={10} textAnchor="end">
          {new Date(end).toISOString().slice(0, 10)}
        </text>
        {bench.map((b) => {
          const s = b.points.map((p) => ({ date: p.date, v: p.ret * 100 }));
          return (
            <path
              key={b.key}
              d={pathFor(s)}
              fill="none"
              stroke={b.color}
              strokeWidth={1.75}
              strokeDasharray={b.dash}
              opacity={0.9}
            />
          );
        })}
        <path d={pathFor(port)} fill="none" stroke="var(--series-1)" strokeWidth={2.75} />
        {port.map((p) => (
          <circle key={p.date} cx={x(p.date)} cy={y(p.v)} r={3} fill="var(--series-1)" />
        ))}
        <text x={pad} y={14} fill="var(--text-secondary)" fontSize={11}>
          Cumulative return since {points[0].date}
        </text>
      </svg>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs">
        {legend.map((l) => (
          <span key={l.label} className="inline-flex items-center gap-2 text-zinc-600 dark:text-zinc-300">
            <span className="inline-block h-[3px] w-5 rounded" style={{ background: l.color }} />
            {l.label}
            <span className="font-semibold tabular-nums" style={{ color: l.color }}>
              {fmt(l.last)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
