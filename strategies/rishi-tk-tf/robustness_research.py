#!/usr/bin/env python3
"""Rishi TK TF - robustness research on the Every-Candle trade log.

Input : a TradingView trade-list export of Rishi TK TF with every-candle checks (1m NSE:NIFTY,
        Deep Backtesting 2009 -> 2026). Columns: [index,] signal, date (dd/mm/yyyy HH:MM), type,
        price, roi, points. The last row is the open trade and is dropped.
Output: one row per variation (and cost level) with full-period, in-sample (2009-2017) and
        out-of-sample (2018-2026) results, then robustness tests of the selected rule.

Every variation is decided only from information known at the entry: the entry price and time,
the side, and earlier trades. A skipped trade means "flat until the next signal" (its ROI is 0
and it pays no cost). A size s means the trade's ROI and cost are multiplied by s.

    python3 robustness_research.py rishi_every_candle_trades.csv --out robustness_results.csv
"""
import argparse
import itertools

import numpy as np
import pandas as pd

SPLIT = "2018-01-01"            # in-sample 2009-2017, out-of-sample 2018-2026
COSTS = (0.0, 0.02, 0.05)       # % per side
GATE_DAYS = 30                  # selected rule: trend-gated shorts, 30-day flip-price average


def load(path):
    d = pd.read_csv(path, encoding="utf-8-sig").iloc[:, -6:]
    d.columns = ["sig", "date", "type", "price", "roi", "pts"]
    d["t"] = pd.to_datetime(d["date"], format="%d/%m/%Y %H:%M")
    d["side"] = np.where(d["sig"].str.contains("long", case=False), 1, -1)
    d["xt"] = d["t"].shift(-1)
    return d.iloc[:-1].reset_index(drop=True)


def metrics(d, s, cost=0.0, mask=None):
    """Compounded CAGR / max DD at 1x, plus the simple (non-compounded) ROI figures."""
    s = np.asarray(s, float)
    r = np.where(s != 0, s * (d["roi"].values - 2 * cost), 0.0)
    taken = s != 0
    t0, t1, ex = d["t"], d["xt"], d["xt"]
    if mask is not None:
        r, taken, t0, t1, ex = r[mask], taken[mask], t0[mask], t1[mask], ex[mask]
    yrs = (t1.iloc[-1] - t0.iloc[0]).days / 365.25
    eq = np.concatenate([[1.0], np.cumprod(1 + r / 100)])
    cdd = ((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max() * 100
    cum = np.concatenate([[0.0], np.cumsum(r)])
    sdd = (np.maximum.accumulate(cum) - cum).max()
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100
    rt = r[taken]
    gl = -rt[rt < 0].sum()
    yearly = pd.Series(r).groupby(ex.dt.year.values).sum()
    return dict(cagr=cagr, cdd=cdd, mar=cagr / cdd if cdd > 0 else np.nan, roi=r.sum(),
                roi_yr=r.sum() / yrs, sdd=sdd, pf=rt[rt > 0].sum() / gl if gl > 0 else np.nan,
                trades=int(taken.sum()), avg=rt.mean() if len(rt) else 0.0,
                win=(rt > 0).mean() * 100 if len(rt) else 0.0, worst_yr=yearly.min(),
                med_yr=yearly.median(), loss_yrs=int((yearly < 0).sum()))


def flip_avg(d, days):
    """Time-weighted average of the signal (flip) prices over the last `days` calendar days,
    measured at each entry from earlier flips only. NaN until `days` of history exist."""
    p = d["price"].values
    ts = ((d["t"] - d["t"].iloc[0]).dt.total_seconds() / 86400).values
    out = np.full(len(d), np.nan)
    for i in range(1, len(d)):
        lo = ts[i] - days
        j = np.searchsorted(ts, lo, side="right") - 1
        if j < 0:
            continue
        w = np.minimum(ts[j + 1:i + 1], ts[i]) - np.maximum(ts[j:i], lo)
        out[i] = np.dot(w, p[j:i]) / w.sum()
    return out


def gate_shorts(d, days, short_size=0.0):
    """Trend-gated shorts: a short is taken only when the entry price is at or below the
    flip-price average; otherwise the short is taken at `short_size` (0 = stay flat)."""
    avg = flip_avg(d, days)
    s = np.where((d["side"].values < 0) & (d["price"].values > avg), short_size, 1.0)
    s[np.isnan(avg)] = 1.0
    return s


def variations(d, is_mask):
    n = len(d)
    p, r, side = d["price"].values, d["roi"].values, d["side"].values
    ts = ((d["t"] - d["t"].iloc[0]).dt.total_seconds() / 86400).values
    mins = (d["t"].dt.hour * 60 + d["t"].dt.minute).values
    yield "0 Baseline", "Rishi Every-Candle", np.ones(n)
    for h in (0, 0.25, 0.5, 0.75):
        yield "A Short size", f"all shorts x{h}", np.where(side < 0, h, 1.0)
    for days, h in itertools.product((20, 30, 40, 50, 60, 75, 100, 125, 150, 200, 300), (0, 0.25, 0.5)):
        yield "B Trend-gated shorts", f"short only at/below {days}d flip avg, else x{h}", gate_shorts(d, days, h)
    for days in (30, 100):
        avg = flip_avg(d, days)
        s = np.where((side < 0) & (p > avg), -1.0, 1.0)  # ignore the short, keep the long
        s[np.isnan(avg)] = 1.0
        yield "B Trend-gated shorts", f"{days}d: hold the long instead of flat", s
    for days in (50, 100, 200):
        avg = flip_avg(d, days)
        s = np.where(((side < 0) & (p > avg)) | ((side > 0) & (p <= avg)), 0.0, 1.0)
        s[np.isnan(avg)] = 1.0
        yield "C Trade only with trend (both sides)", f"{days}d flip avg", s
    absr = pd.Series(np.abs(r)).shift(1)
    for k, lo, hi in itertools.product((10, 20, 50, 100), (0.5,), (1.5, 2.0)):
        v = absr.rolling(k).mean().values
        s = np.clip(np.nanmedian(v[is_mask]) / v, lo, hi)
        s[np.isnan(v)] = 1.0
        yield "D Volatility targeting", f"last {k} trades, size {lo}-{hi}", s
    for k in (3, 5, 10, 20):
        er = np.full(n, np.nan)
        for i in range(k, n):
            er[i] = abs(p[i] - p[i - k]) / np.abs(np.diff(p[i - k:i + 1])).sum()
        for q in (0.1, 0.2, 0.3):
            th = np.nanquantile(er[is_mask], q)
            yield "E Chop filter: efficiency ratio", f"ER{k} < IS {int(q * 100)}th pct -> flat", np.where(er < th, 0.0, 1.0)
    for days, m in itertools.product((3, 5, 10), (3, 4, 5, 6, 8)):
        c = np.array([((ts >= ts[i] - days) & (ts < ts[i])).sum() for i in range(n)])
        yield "F Chop filter: signal density", f">= {m} signals in {days}d -> flat", np.where(c >= m, 0.0, 1.0)
    streak, x = [], 0
    for v in r:
        streak.append(x)
        x = x + 1 if v <= 0 else 0
    streak = np.array(streak)
    for m in (2, 3, 4, 5):
        yield "G Chop filter: loss streak", f"after {m}+ losses -> flat", np.where(streak >= m, 0.0, 1.0)
    cum = pd.Series(np.cumsum(r)).shift(1)
    for k in (10, 20, 50, 100):
        ma = cum.rolling(k).mean()
        s = np.where(cum < ma, 0.5, 1.0)
        s[np.isnan(ma.values)] = 1.0
        yield "H Equity-curve filter", f"equity < MA{k} -> x0.5", s
    dow = d["t"].dt.dayofweek.values
    yield "I Time filter", "skip 09:15 entries (gap)", np.where(mins == 555, 0.0, 1.0)
    yield "I Time filter", "skip 09:16-09:44 entries", np.where((mins > 555) & (mins < 585), 0.0, 1.0)
    yield "I Time filter", "skip entries after 15:00", np.where(mins >= 900, 0.0, 1.0)
    yield "I Time filter", "skip Tuesday entries", np.where(dow == 1, 0.0, 1.0)


def risk_matched(d, s, cost, target_dd):
    lo, hi = 0.2, 4.0
    for _ in range(40):
        lev = (lo + hi) / 2
        lo, hi = (lev, hi) if metrics(d, s * lev, cost)["cdd"] < target_dd else (lo, lev)
    return lev, metrics(d, s * lev, cost)


def robustness(d, s1, rng):
    s0 = np.ones(len(d))
    r = d["roi"].values
    years = d["t"].dt.year.values
    print(f"\n=== Robustness of the selected rule (trend-gated shorts, {GATE_DAYS}d) ===")
    g = s1 == 0
    print(f"shorts removed: {g.sum()}  their total ROI {r[g].sum():.2f}%  avg {r[g].mean():.3f}%  "
          f"| shorts kept: {((d.side < 0) & ~g).sum()}  avg {r[(d.side.values < 0) & ~g].mean():.3f}%")
    for cost in COSTS:
        y0 = pd.Series(s0 * (r - 2 * cost)).groupby(d["xt"].dt.year.values).sum()
        y1 = pd.Series(np.where(s1 != 0, s1 * (r - 2 * cost), 0)).groupby(d["xt"].dt.year.values).sum()
        print(f"cost {cost}: years rule >= baseline {(y1 >= y0).sum()}/{len(y0)}")
    win = {c: 0 for c in COSTS}
    tot = 0
    for y in sorted(set(years))[:-2]:
        m = np.isin(years, [y, y + 1, y + 2])
        tot += 1
        for c in COSTS:
            win[c] += metrics(d, s1, c, m)["mar"] >= metrics(d, s0, c, m)["mar"]
    print("rolling 3-year windows, rule CAGR/DD >= baseline: " + ", ".join(f"cost {c}: {win[c]}/{tot}" for c in COSTS))
    uy = np.unique(years)
    idx = {y: np.where(years == y)[0] for y in uy}
    for cost in COSTS:
        r0 = s0 * (r - 2 * cost)
        r1 = np.where(s1 != 0, s1 * (r - 2 * cost), 0)
        better = lower_dd = higher_eq = 0
        for _ in range(5000):
            ii = np.concatenate([idx[y] for y in rng.choice(uy, len(uy))])
            out = []
            for x in (r0, r1):
                eq = np.concatenate([[1.0], np.cumprod(1 + x[ii] / 100)])
                out.append((eq[-1], ((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max()))
            better += np.log(out[1][0]) / out[1][1] >= np.log(out[0][0]) / out[0][1]
            lower_dd += out[1][1] <= out[0][1]
            higher_eq += out[1][0] >= out[0][0]
        print(f"year-block bootstrap (5,000), cost {cost}: P(better return/DD) {better / 50:.1f}%  "
              f"P(lower DD) {lower_dd / 50:.1f}%  P(higher final equity) {higher_eq / 50:.1f}%")
    for cost in COSTS:
        res = []
        for s in (s0, s1):
            x = np.where(s != 0, s * (r - 2 * cost), 0)[s != 0]
            dds = []
            for _ in range(5000):
                eq = np.concatenate([[1.0], np.cumprod(1 + rng.permutation(x) / 100)])
                dds.append(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max() * 100)
            res.append(f"{np.median(dds):.1f} / {np.percentile(dds, 95):.1f}")
        print(f"Monte Carlo trade order (5,000), cost {cost}: max DD median / 95th pct  baseline {res[0]}  rule {res[1]}")
    yearsx = d["t"].dt.year.values
    picks, wf = {}, np.ones(len(d))
    grid = (20, 30, 40, 50, 60, 75, 100, 125, 150)
    gates = {k: gate_shorts(d, k) for k in grid}
    for y in range(2012, int(yearsx.max()) + 1):
        best = max(grid, key=lambda k: metrics(d, gates[k], 0.02, yearsx < y)["mar"])
        picks[y] = best
        wf[yearsx == y] = gates[best][yearsx == y]
    m = yearsx >= 2012
    print(f"walk-forward (lookback re-chosen each January on all earlier data, cost 0.02): {picks}")
    for cost in COSTS:
        a, b = metrics(d, s0, cost, m), metrics(d, wf, cost, m)
        print(f"  2012-2026 cost {cost}: baseline CAGR {a['cagr']:.2f} DD {a['cdd']:.2f} | walk-forward CAGR {b['cagr']:.2f} DD {b['cdd']:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trades", help="Rishi TK TF every-candle trade-list export (CSV)")
    ap.add_argument("--out", help="write the variation table to this CSV")
    a = ap.parse_args()
    d = load(a.trades)
    is_mask = (d["t"] < SPLIT).values
    rows = []
    for fam, name, s in variations(d, is_mask):
        for cost in COSTS:
            f, i, o = metrics(d, s, cost), metrics(d, s, cost, is_mask), metrics(d, s, cost, ~is_mask)
            rows.append(dict(family=fam, variation=name, cost_per_side=cost,
                             **{k: f[k] for k in ("trades", "cagr", "cdd", "mar", "roi", "roi_yr", "sdd", "pf", "win", "avg", "worst_yr", "med_yr", "loss_yrs")},
                             is_cagr=i["cagr"], is_cdd=i["cdd"], is_mar=i["mar"],
                             oos_cagr=o["cagr"], oos_cdd=o["cdd"], oos_mar=o["mar"]))
    df = pd.DataFrame(rows).round(3)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    cols = ["family", "variation", "trades", "cagr", "cdd", "mar", "pf", "worst_yr", "is_mar", "oos_mar"]
    for cost in COSTS:
        print(f"\n=== cost {cost}% per side (cagr / cdd = compounded CAGR and max DD at 1x; mar = cagr / cdd) ===")
        print(df[df.cost_per_side == cost][cols].to_string(index=False))
    if a.out:
        df.to_csv(a.out, index=False)
    s0, s1 = np.ones(len(d)), gate_shorts(d, GATE_DAYS)
    print("\n=== Risk-matched: size scaled so compounded max DD equals the baseline's ===")
    for cost in COSTS:
        bdd = metrics(d, s0, cost)["cdd"]
        lev, m = risk_matched(d, s1, cost, bdd)
        print(f"cost {cost}: baseline CAGR {metrics(d, s0, cost)['cagr']:.2f} DD {bdd:.2f} | rule x{lev:.2f}: CAGR {m['cagr']:.2f} DD {m['cdd']:.2f}")
    robustness(d, s1, np.random.default_rng(7))


if __name__ == "__main__":
    main()
