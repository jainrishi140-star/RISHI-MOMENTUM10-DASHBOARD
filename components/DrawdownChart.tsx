"use client";

import { useRef, useState } from "react";
import { NavPoint } from "@/lib/portfolio";
import type { BenchmarkSeries } from "@/lib/benchmarks";
import { niceTicks } from "@/lib/chartScale";

// Running drawdown from the peak-to-date, as a % (always <= 0). Same inline-SVG
// approach as EquityCurve, sharing its date axis and hover behaviour.
function toDrawdown(series: { date: string; v: number }[]) {
  let peak = -Infinity;
  return series.map((p) => {
    const level = 1 + p.v / 100; // index level, 1 = start
    peak = Math.max(peak, level);
    return { date: p.date, v: (level / peak - 1) * 100 };
  });
}

export default function DrawdownChart({
  points,
  benchmarks = [],
  fetchedAt,
}: {
  points: NavPoint[];
  benchmarks?: BenchmarkSeries[];
  fetchedAt?: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (points.length < 1) {
    return (
      <div className="flex h-40 items-center justify-center px-4 text-center text-sm text-zinc-500 dark:text-zinc-500">
        Waiting on the first daily NAV snapshot to draw a drawdown curve.
      </div>
    );
  }

  const width = 760;
  const height = 220;
  const pad = 44;
  const padTop = 20;
  const padRight = 16;

  const t = (d: string) => Date.parse(d + "T00:00:00Z");
  const start = t(points[0].date);
  const bench = benchmarks.map((b) => ({ ...b, points: b.points.filter((p) => t(p.date) >= start) }));
  const allDates = [...points.map((p) => p.date), ...bench.flatMap((b) => b.points.map((p) => p.date))];
  const end = Math.max(...allDates.map(t));
  const xspan = end - start || 1;

  const port = toDrawdown(points.map((p) => ({ date: p.date, v: p.portfolioReturn * 100 })));
  const benchDD = bench.map((b) => ({ ...b, dd: toDrawdown(b.points.map((p) => ({ date: p.date, v: p.ret * 100 }))) }));

  const allVals = [0, ...port.map((p) => p.v), ...benchDD.flatMap((b) => b.dd.map((p) => p.v))];
  const dataMin = Math.min(...allVals);
  const valuePad = Math.max(Math.abs(dataMin) * 0.12, 0.25);
  const min = dataMin - valuePad;
  const max = 0;
  const span = max - min || 1;
  const ticks = niceTicks(min, max, 4);

  const x = (d: string) => pad + ((t(d) - start) / xspan) * (width - pad - padRight);
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad - padTop);
  const pathFor = (s: { date: string; v: number }[]) =>
    s.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.date).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const areaFor = (s: { date: string; v: number }[]) =>
    `${pathFor(s)} L${x(s[s.length - 1].date).toFixed(1)},${y(0).toFixed(1)} L${x(s[0].date).toFixed(1)},${y(0).toFixed(1)} Z`;
  const fmt = (v: number) => `${v.toFixed(2)}%`;
  const fmtDate = (d: string) =>
    new Date(t(d)).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

  const asOf = (s: { date: string; v: number }[], date: string) =>
    [...s].reverse().find((p) => p.date <= date) ?? s[0];

  const maxDD = Math.min(...port.map((p) => p.v));
  const legend = [
    { label: "Portfolio", color: "var(--series-1)", worst: maxDD },
    ...benchDD
      .filter((b) => b.dd.length)
      .map((b) => ({ label: b.label, color: b.color, worst: Math.min(...b.dd.map((p) => p.v)) })),
  ];

  const lastPortDate = port[port.length - 1].date;
  const hover = hoverIdx !== null ? port[hoverIdx] : null;
  const hoverLabel = hover
    ? hover.date === lastPortDate && fetchedAt
      ? `${fetchedAt} IST`
      : fmtDate(hover.date)
    : null;

  // Tooltip rows ranked least underwater first (closest to 0 on top).
  const hoverRows = hover
    ? [
        { key: "portfolio", label: "Portfolio", color: "#e5484d", v: hover.v },
        ...benchDD
          .filter((b) => b.dd.length)
          .map((b) => {
            const p = asOf(b.dd, hover.date);
            return p ? { key: b.key, label: b.label, color: b.color, v: p.v } : null;
          })
          .filter((r): r is { key: string; label: string; color: string; v: number } => r !== null),
      ].sort((a, b) => b.v - a.v)
    : [];

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * width;
    let nearest = 0;
    let nearestDist = Infinity;
    port.forEach((p, i) => {
      const d = Math.abs(x(p.date) - mouseX);
      if (d < nearestDist) {
        nearestDist = d;
        nearest = i;
      }
    });
    setHoverIdx(nearest);
  }

  return (
    <div>
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full cursor-crosshair"
          role="img"
          aria-label="Drawdown vs benchmarks"
          onMouseMove={handleMove}
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#e5484d" stopOpacity={0} />
              <stop offset="100%" stopColor="#e5484d" stopOpacity={0.22} />
            </linearGradient>
          </defs>

          {ticks.map((v) => (
            <g key={v}>
              <line
                x1={pad}
                y1={y(v)}
                x2={width - padRight}
                y2={y(v)}
                stroke="var(--grid-line)"
                strokeDasharray={Math.abs(v) < 1e-9 ? undefined : "4 4"}
                strokeWidth={Math.abs(v) < 1e-9 ? 1.25 : 1}
              />
              <text x={pad - 8} y={y(v)} fill="var(--text-secondary)" fontSize={10} textAnchor="end" dominantBaseline="middle">
                {fmt(v)}
              </text>
            </g>
          ))}
          <text x={pad} y={height - 6} fill="var(--text-secondary)" fontSize={10}>
            {points[0].date}
          </text>
          <text x={width - padRight} y={height - 6} fill="var(--text-secondary)" fontSize={10} textAnchor="end">
            {new Date(end).toISOString().slice(0, 10)}
          </text>

          <path d={areaFor(port)} fill="url(#ddFill)" stroke="none" />
          {benchDD.map((b) => (
            <path
              key={b.key}
              d={pathFor(b.dd)}
              fill="none"
              stroke={b.color}
              strokeWidth={1.75}
              strokeDasharray={b.dash}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
            />
          ))}
          <path
            d={pathFor(port)}
            fill="none"
            stroke="#e5484d"
            strokeWidth={2.75}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {port.length <= 30 && port.map((p) => <circle key={p.date} cx={x(p.date)} cy={y(p.v)} r={3} fill="#e5484d" />)}
          <text x={pad} y={12} fill="var(--text-secondary)" fontSize={11}>
            Drawdown from peak since {points[0].date}
          </text>

          {hover && (
            <>
              <line
                x1={x(hover.date)}
                y1={padTop}
                x2={x(hover.date)}
                y2={height - pad}
                stroke="var(--text-secondary)"
                strokeWidth={1}
                strokeDasharray="3 3"
                opacity={0.6}
              />
              <circle cx={x(hover.date)} cy={y(hover.v)} r={4} fill="#e5484d" stroke="white" strokeWidth={1.5} />
              {benchDD.map((b) => {
                const p = asOf(b.dd, hover.date);
                if (!p) return null;
                return <circle key={b.key} cx={x(hover.date)} cy={y(p.v)} r={3.5} fill={b.color} stroke="white" strokeWidth={1.25} />;
              })}
            </>
          )}
        </svg>

        {hover && (
          <div
            className="pointer-events-none absolute top-2 z-10 min-w-[9rem] rounded-lg border border-zinc-200/70 bg-white/95 p-2.5 text-xs shadow-lg backdrop-blur-sm dark:border-zinc-700/70 dark:bg-zinc-900/95"
            style={{
              left: `${Math.min(Math.max((x(hover.date) / width) * 100, 14), 86)}%`,
              transform: "translateX(-50%)",
            }}
          >
            <div className="mb-1.5 font-medium text-zinc-500 dark:text-zinc-400">{hoverLabel}</div>
            {hoverRows.map((r, i) => (
              <div key={r.key} className={`flex items-center justify-between gap-3 ${i > 0 ? "mt-1" : ""}`}>
                <span className="inline-flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
                  <span className="inline-block h-[3px] w-3 rounded" style={{ background: r.color }} />
                  {r.label}
                </span>
                <span className="font-semibold tabular-nums" style={{ color: r.color }}>
                  {fmt(r.v)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs">
        {legend.map((l) => (
          <span key={l.label} className="inline-flex items-center gap-2 text-zinc-600 dark:text-zinc-300">
            <span className="inline-block h-[3px] w-5 rounded" style={{ background: l.color }} />
            {l.label}
            <span className="font-semibold tabular-nums" style={{ color: l.color }}>
              {fmt(l.worst)} max
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
