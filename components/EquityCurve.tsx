import { NavPoint } from "@/lib/portfolio";

// Lightweight inline-SVG line chart -- avoids pulling in a charting library
// for a short-history sparkline. Plots cumulative portfolio return, indexed
// to 0% at the paper-start date.
export default function EquityCurve({ points }: { points: NavPoint[] }) {
  if (points.length < 2) {
    return (
      <div className="flex h-40 items-center justify-center px-4 text-center text-sm text-zinc-500 dark:text-zinc-500">
        Waiting on tomorrow&apos;s daily NAV snapshot to draw a curve (only one data point so far).
      </div>
    );
  }

  const width = 760;
  const height = 220;
  const pad = 28;

  const port = points.map((p) => p.portfolioReturn * 100);
  const min = Math.min(0, ...port);
  const max = Math.max(0, ...port);
  const span = max - min || 1;

  const x = (i: number) => pad + (i / (points.length - 1)) * (width - pad * 2);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad * 2);

  const pathFor = (series: number[]) =>
    series.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  const zeroY = y(0);
  const last = port[port.length - 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Equity curve">
      <line x1={pad} y1={zeroY} x2={width - pad} y2={zeroY} stroke="var(--grid-line)" strokeDasharray="4 4" />
      <path d={pathFor(port)} fill="none" stroke="var(--series-1)" strokeWidth={2.5} />
      {port.map((v, i) => (
        <circle key={points[i].date} cx={x(i)} cy={y(v)} r={2.5} fill="var(--series-1)" />
      ))}
      <text x={pad} y={14} fill="var(--series-1)" fontSize={11} fontWeight={600}>
        Portfolio {last >= 0 ? "+" : ""}
        {last.toFixed(2)}% since {points[0].date}
      </text>
    </svg>
  );
}
