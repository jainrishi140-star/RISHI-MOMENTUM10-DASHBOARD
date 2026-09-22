import AutoRefresh from "@/components/AutoRefresh";
import EquityCurve from "@/components/EquityCurve";
import {
  fetchBenchmarks,
  fetchSiblingStrategies,
  priorTradingDay,
  type BenchmarkSeries,
  type SiblingStrategyDef,
} from "@/lib/benchmarks";
import Nav from "@/components/Nav";
import { fetchSheetRows, fetchNavHistory, TABS, isNegative } from "@/lib/sheet";
import {
  computeDashboard,
  parseHoldings,
  parseMomentum,
  parseRebalance,
  buildNavPoints,
  parseSheetDate,
  KV,
} from "@/lib/portfolio";

function pnlClass(s: string) {
  return isNegative(s) ? "text-red-400" : s ? "text-emerald-400" : "text-zinc-400";
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center gap-2">
      <span className="h-4 w-1 rounded-full bg-[var(--series-1)]" />
      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-300">{children}</h2>
    </div>
  );
}

function StatBlock({ title, rows }: { title: string; rows: KV[] }) {
  return (
    <section className="rounded-2xl border border-zinc-200/70 bg-white/90 p-5 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
      <div className="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{title}</div>
      <dl className="space-y-2">
        {rows.map((kv) => (
          <div key={kv.label} className="flex items-center justify-between gap-4 text-sm">
            <dt className="text-zinc-500 dark:text-zinc-400">{kv.label}</dt>
            <dd className={`font-medium tabular-nums ${pnlClass(kv.value)}`}>{kv.value || "—"}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export interface StrategyDashboardProps {
  currentPath: string;
  sheetId: string;
  navHistoryFile: string;
  overweightThreshold: number;
  title: string;
  subtitle: string;
  siblingStrategies?: SiblingStrategyDef[];
}

export default async function StrategyDashboard({
  currentPath,
  sheetId,
  navHistoryFile,
  overweightThreshold,
  title,
  subtitle,
  siblingStrategies = [],
}: StrategyDashboardProps) {
  let error: string | null = null;
  let dashboard: ReturnType<typeof computeDashboard> | null = null;
  let holdings: ReturnType<typeof parseHoldings> | null = null;
  let momentum: ReturnType<typeof parseMomentum> = [];
  let rebalance: ReturnType<typeof parseRebalance> | null = null;
  let nav: ReturnType<typeof buildNavPoints> = [];
  let benchmarks: BenchmarkSeries[] = [];
  let fetchedAt = "";

  try {
    const [holdRows, momRows, rebalRows] = await Promise.all([
      fetchSheetRows(sheetId, TABS.holdings),
      fetchSheetRows(sheetId, TABS.momentum),
      fetchSheetRows(sheetId, TABS.rebalance),
    ]);
    holdings = parseHoldings(holdRows);
    momentum = parseMomentum(momRows);
    rebalance = parseRebalance(rebalRows);
    dashboard = computeDashboard(holdings, rebalance, momentum, overweightThreshold);
    fetchedAt = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });
  } catch (e: any) {
    error = e?.message ?? String(e);
  }

  // Independent of the sheet fetch above -- a hiccup here shouldn't take
  // down the rest of the dashboard.
  try {
    nav = buildNavPoints(await fetchNavHistory(navHistoryFile));
    // A book that gets rebuilt (OVERWRITE = true) can leave behind daily
    // snapshots taken against an earlier draft of the sheet -- those predate
    // the current holdings' own Entry Date and would silently drag the
    // equity curve's anchor back to a day before the book actually existed.
    // Holdings' earliest Entry Date is ground truth for when THIS book went
    // live, so drop any snapshot older than that.
    const earliestEntry = holdings?.rows
      .map((h) => parseSheetDate(h.entryDate))
      .filter((d): d is string => d !== null)
      .sort()[0];
    if (earliestEntry) nav = nav.filter((p) => p.date >= earliestEntry);
  } catch {
    nav = [];
  }
  try {
    // First snapshot already off starting capital => anchor everything at the prior close.
    if (nav.length && Math.abs(nav[0].portfolioReturn) > 1e-9) {
      const base = await priorTradingDay(nav[0].date);
      if (base) nav = [{ date: base, nav: nav[0].nav / (1 + nav[0].portfolioReturn), portfolioReturn: 0 }, ...nav];
    }
    const [indexBenchmarks, siblings] = await Promise.all([
      fetchBenchmarks(nav[0]?.date),
      fetchSiblingStrategies(siblingStrategies, nav[0]?.date),
    ]);
    benchmarks = [...indexBenchmarks, ...siblings];
  } catch {
    benchmarks = [];
  }

  // Splice in a live point for "today", using the same Holdings-derived NAV
  // that already powers the hero tiles above (fetched fresh, no-store, on
  // every request). The daily GitHub Actions snapshot only writes one point
  // per trading day after close, so without this the curve's last point
  // would sit frozen at yesterday's close all day; this makes it move with
  // the sheet's GOOGLEFINANCE prices intraday instead. Replaces today's
  // snapshot if the Action has already run today, otherwise appends.
  if (dashboard && nav.length) {
    const todayIST = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }); // YYYY-MM-DD
    const livePoint = { date: todayIST, nav: dashboard.navRaw, portfolioReturn: dashboard.portfolioReturnRaw };
    if (nav[nav.length - 1].date === todayIST) nav = [...nav.slice(0, -1), livePoint];
    else if (todayIST > nav[nav.length - 1].date) nav = [...nav, livePoint];
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-zinc-50 font-sans dark:bg-black">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[420px] opacity-60 dark:opacity-40"
        style={{
          background:
            "radial-gradient(60% 100% at 20% 0%, color-mix(in oklab, var(--series-1) 18%, transparent), transparent 70%)," +
            "radial-gradient(50% 90% at 85% 0%, color-mix(in oklab, var(--series-2) 14%, transparent), transparent 70%)",
        }}
      />

      <main className="relative mx-auto max-w-4xl px-6 py-12">
        <AutoRefresh />
        <Nav current={currentPath} />

        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white/80 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-zinc-500 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80 dark:text-zinc-400">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            Live · reads the Google Sheet on every load
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">{title}</h1>
          <p className="mt-1.5 max-w-xl text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>
          {fetchedAt && (
            <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-600">Last fetched {fetchedAt} IST</p>
          )}
        </div>

        {error && (
          <div className="mt-6 rounded-xl border border-red-300 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
            Could not load the sheet: {error}
          </div>
        )}

        {dashboard && (
          <>
            {/* ============================= HERO ============================= */}
            <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { label: "NAV", value: dashboard.nav },
                { label: "Total P&L", value: dashboard.totalPnl },
                { label: "Today's P&L", value: dashboard.todayPnl },
                { label: "Portfolio Return", value: dashboard.portfolioReturn },
              ].map((h) => (
                <div
                  key={h.label}
                  className="rounded-2xl border border-zinc-200/70 bg-white/90 p-4 text-center shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90"
                >
                  <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                    {h.label}
                  </div>
                  <div className={`mt-1 text-lg font-bold tabular-nums sm:text-xl ${pnlClass(h.value)}`}>
                    {h.value || "—"}
                  </div>
                </div>
              ))}
            </div>

            {/* ========================= EQUITY CURVE ========================= */}
            <div className="mt-10">
              <SectionLabel>Equity Curve</SectionLabel>
              <section className="rounded-2xl border border-zinc-200/70 bg-white/90 p-6 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
                <EquityCurve points={nav} benchmarks={benchmarks} />
              </section>
            </div>

            {/* ============================ STATS ============================ */}
            <div className="mt-10">
              <SectionLabel>Portfolio Stats</SectionLabel>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatBlock title="Capital & Value" rows={dashboard.capitalValue} />
                <StatBlock title="P&L & Return" rows={dashboard.pnlReturn} />
                <StatBlock title="Risk & Concentration" rows={dashboard.riskConcentration} />
              </div>
            </div>

            {/* ========================== ATTENTION =========================== */}
            {dashboard.attention.length > 0 && (
              <div className="mt-10">
                <SectionLabel>Attention</SectionLabel>
                <section className="space-y-3 rounded-2xl border border-zinc-200/70 bg-white/90 p-5 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
                  {dashboard.attention.map((a) => (
                    <div key={a.label} className="text-sm">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">{a.label}: </span>
                      <span className={a.value === "None" || !a.value ? "text-emerald-400" : "text-red-400"}>
                        {a.value || "None"}
                      </span>
                    </div>
                  ))}
                </section>
              </div>
            )}
          </>
        )}

        {/* ============================ HOLDINGS =========================== */}
        {holdings && holdings.rows.length > 0 && (
          <div className="mt-12">
            <SectionLabel>Holdings</SectionLabel>
            <div className="overflow-x-auto rounded-2xl border border-zinc-200/70 bg-white/90 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
              <table className="w-full text-left text-sm">
                <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Ticker</th>
                    <th className="px-4 py-2.5 font-medium">Entry</th>
                    <th className="px-4 py-2.5 font-medium">Shares</th>
                    <th className="px-4 py-2.5 font-medium">CMP</th>
                    <th className="px-4 py-2.5 font-medium">Value</th>
                    <th className="px-4 py-2.5 font-medium">P&L</th>
                    <th className="px-4 py-2.5 font-medium">P&L %</th>
                    <th className="px-4 py-2.5 font-medium">Day P&L</th>
                    <th className="px-4 py-2.5 font-medium">Wt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  {holdings.rows.map((h) => (
                    <tr key={h.ticker} className="text-zinc-800 dark:text-zinc-200">
                      <td className="px-4 py-2 font-medium">{h.ticker.replace("NSE:", "")}</td>
                      <td className="px-4 py-2 tabular-nums">{h.entryPrice}</td>
                      <td className="px-4 py-2 tabular-nums">{h.shares}</td>
                      <td className="px-4 py-2 tabular-nums">{h.cmp}</td>
                      <td className="px-4 py-2 tabular-nums">{h.currentValue}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(h.unrealisedPnl)}`}>{h.unrealisedPnl}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(h.pnlPct)}`}>{h.pnlPct}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(h.dayPnl)}`}>{h.dayPnl}</td>
                      <td className="px-4 py-2 tabular-nums">{h.actualWt}</td>
                    </tr>
                  ))}
                </tbody>
                {holdings.total && (
                  <tfoot className="border-t border-zinc-200 bg-zinc-50 font-semibold dark:border-zinc-800 dark:bg-zinc-800/40">
                    <tr className="text-zinc-800 dark:text-zinc-100">
                      <td className="px-4 py-2.5">TOTAL</td>
                      <td className="px-4 py-2.5" />
                      <td className="px-4 py-2.5" />
                      <td className="px-4 py-2.5" />
                      <td className="px-4 py-2.5 tabular-nums">{holdings.total.currentValue}</td>
                      <td className={`px-4 py-2.5 tabular-nums ${pnlClass(holdings.total.unrealisedPnl)}`}>
                        {holdings.total.unrealisedPnl}
                      </td>
                      <td className="px-4 py-2.5" />
                      <td className="px-4 py-2.5" />
                      <td className="px-4 py-2.5 tabular-nums">{holdings.total.actualWt}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        )}

        {/* ============================ MOMENTUM =========================== */}
        {momentum.length > 0 && (
          <div className="mt-12">
            <SectionLabel>Momentum Monitor</SectionLabel>
            <div className="overflow-x-auto rounded-2xl border border-zinc-200/70 bg-white/90 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
              <table className="w-full text-left text-sm">
                <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Ticker</th>
                    <th className="px-4 py-2.5 font-medium">1M</th>
                    <th className="px-4 py-2.5 font-medium">3M</th>
                    <th className="px-4 py-2.5 font-medium">6M</th>
                    <th className="px-4 py-2.5 font-medium">12M</th>
                    <th className="px-4 py-2.5 font-medium">% from 52wH</th>
                    <th className="px-4 py-2.5 font-medium">Rank 12M</th>
                    <th className="px-4 py-2.5 font-medium">Health</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  {momentum.map((m) => (
                    <tr key={m.ticker} className="text-zinc-800 dark:text-zinc-200">
                      <td className="px-4 py-2 font-medium">{m.ticker.replace("NSE:", "")}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(m.ret1m)}`}>{m.ret1m}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(m.ret3m)}`}>{m.ret3m}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(m.ret6m)}`}>{m.ret6m}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(m.ret12m)}`}>{m.ret12m}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(m.pctFrom52wHigh)}`}>{m.pctFrom52wHigh}</td>
                      <td className="px-4 py-2 tabular-nums">{m.rank12m}</td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            m.health === "OK"
                              ? "text-emerald-400"
                              : m.health === "FADING"
                                ? "text-amber-400"
                                : "text-red-400"
                          }
                        >
                          {m.health}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================== REBALANCE ========================== */}
        {rebalance && rebalance.rows.length > 0 && (
          <div className="mt-12">
            <SectionLabel>Rebalance — next {rebalance.nextDate || "Wednesday"}</SectionLabel>
            <div className="overflow-x-auto rounded-2xl border border-zinc-200/70 bg-white/90 shadow-sm ring-1 ring-black/[0.02] backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-900/90">
              <table className="w-full text-left text-sm">
                <thead className="bg-zinc-50 text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Ticker</th>
                    <th className="px-4 py-2.5 font-medium">Target Value</th>
                    <th className="px-4 py-2.5 font-medium">Current Value</th>
                    <th className="px-4 py-2.5 font-medium">Drift %</th>
                    <th className="px-4 py-2.5 font-medium">Action</th>
                    <th className="px-4 py-2.5 font-medium">Shares</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  {rebalance.rows.map((r) => (
                    <tr key={r.ticker} className="text-zinc-800 dark:text-zinc-200">
                      <td className="px-4 py-2 font-medium">{r.ticker.replace("NSE:", "")}</td>
                      <td className="px-4 py-2 tabular-nums">{r.targetValue}</td>
                      <td className="px-4 py-2 tabular-nums">{r.currentValue}</td>
                      <td className={`px-4 py-2 tabular-nums ${pnlClass(r.driftPct)}`}>{r.driftPct}</td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            r.action === "BUY"
                              ? "text-emerald-400"
                              : r.action === "SELL"
                                ? "text-red-400"
                                : "text-zinc-400"
                          }
                        >
                          {r.action}
                        </span>
                      </td>
                      <td className="px-4 py-2 tabular-nums">{r.sharesToTrade}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <p className="mt-10 text-xs text-zinc-400 dark:text-zinc-600">
          Data: read live from the Google Sheet on every page load (CSV export, no auth, no
          cache) — edit the sheet after each rebalance and this page reflects it on the next
          visit. Prices in the sheet are GOOGLEFINANCE (NSE, ~20 min delayed). This is a forward
          test for research purposes, not investment advice, and does not place any trades.
        </p>
      </main>
    </div>
  );
}
