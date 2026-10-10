"""Monte Carlo simulation on TradingView strategy trade lists (TK TF Original System vs Rishi TK TF).

Uses the per-trade ROI % of the closed trades (not compounded, like the TK TF Original System's logs) and runs:
  1. Reshuffle    : random trade order -> distribution of max drawdown and losing streaks
  2. Bootstrap    : full-length resampling with replacement -> total ROI, ROI/yr, PF, max drawdown
  3. One year     : resample one year of trades from the whole history -> yearly ROI and drawdown
  4. Recent year  : same, but drawing only from trades since --recent (default 2021-01-01)
  5. Stress       : drop --skip of the trades at random and charge --cost % per side

Usage:
    python monte_carlo.py <tk_tf_original_trades.csv> <rishi_tk_tf_trades.csv> [--runs 10000] [--seed 7]
                          [--recent 2021-01-01] [--skip 0.10] [--cost 0.02]
"""
import argparse

import numpy as np
import pandas as pd

from is_oos import load_trades

PCTS = [5, 25, 50, 75, 95]


def max_drawdown(paths):
    """Largest fall of cumulative ROI % from its running peak (starting at 0), per row."""
    eq = np.concatenate([np.zeros((paths.shape[0], 1)), np.cumsum(paths, axis=1)], axis=1)
    return (np.maximum.accumulate(eq, axis=1) - eq).max(axis=1)


def longest_losing_streak(paths):
    out = np.zeros(paths.shape[0], dtype=int)
    run = np.zeros(paths.shape[0], dtype=int)
    for j in range(paths.shape[1]):
        run = np.where(paths[:, j] <= 0, run + 1, 0)
        out = np.maximum(out, run)
    return out


def profit_factor(paths):
    win = np.where(paths > 0, paths, 0).sum(axis=1)
    loss = -np.where(paths <= 0, paths, 0).sum(axis=1)
    return np.divide(win, loss, out=np.full(len(win), np.inf), where=loss > 0)


def pct(x):
    return [np.percentile(x, p) for p in PCTS]


def simulate(roi, years, recent_roi, args, rng):
    n, runs = len(roi), args.runs
    per_year = int(round(n / years))
    res = {}

    shuffled = np.array([rng.permutation(roi) for _ in range(runs)])
    res["Reshuffle: max drawdown %"] = pct(max_drawdown(shuffled))
    res["Reshuffle: longest losing streak (trades)"] = pct(longest_losing_streak(shuffled))
    dd = max_drawdown(shuffled)
    res["Reshuffle: P(max DD > 15%) %"] = [100 * np.mean(dd > 15)] * len(PCTS)
    res["Reshuffle: P(max DD > 20%) %"] = [100 * np.mean(dd > 20)] * len(PCTS)

    boot = rng.choice(roi, size=(runs, n), replace=True)
    res["Bootstrap: total ROI %"] = pct(boot.sum(axis=1))
    res["Bootstrap: ROI per year %"] = pct(boot.sum(axis=1) / years)
    res["Bootstrap: profit factor"] = pct(profit_factor(boot))
    res["Bootstrap: max drawdown %"] = pct(max_drawdown(boot))

    for label, pool in (("One year (all history)", roi), ("One year (recent only)", recent_roi)):
        yr = rng.choice(pool, size=(runs, per_year), replace=True)
        total = yr.sum(axis=1)
        res[f"{label}: ROI %"] = pct(total)
        res[f"{label}: max drawdown %"] = pct(max_drawdown(yr))
        res[f"{label}: P(losing year) %"] = [100 * np.mean(total < 0)] * len(PCTS)
        res[f"{label}: P(year < 10%) %"] = [100 * np.mean(total < 10)] * len(PCTS)

    keep = int(round(n * (1 - args.skip)))
    stress = np.array([rng.choice(roi, size=keep, replace=False) for _ in range(runs)]) - 2 * args.cost
    res[f"Stress (skip {args.skip:.0%}, cost {args.cost}%/side): ROI per year %"] = pct(stress.sum(axis=1) / years)
    res[f"Stress (skip {args.skip:.0%}, cost {args.cost}%/side): profit factor"] = pct(profit_factor(stress))
    res[f"Stress (skip {args.skip:.0%}, cost {args.cost}%/side): max drawdown %"] = pct(max_drawdown(stress))
    return res, per_year


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original", help="TK TF Original System trade list")
    ap.add_argument("replica", help="Rishi TK TF trade list")
    ap.add_argument("--runs", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--recent", default="2021-01-01")
    ap.add_argument("--skip", type=float, default=0.10)
    ap.add_argument("--cost", type=float, default=0.02)
    ap.add_argument("--out", help="save the results table to this CSV")
    args = ap.parse_args()

    tables = []
    for label, path in (("TK TF Original", args.original), ("Rishi TK TF", args.replica)):
        tr = load_trades(path)
        years = (tr.time.max() - tr.time.min()).days / 365.25
        recent = tr[tr.time >= pd.Timestamp(args.recent)].roi.values
        res, per_year = simulate(tr.roi.values, years, recent, args, np.random.default_rng(args.seed))
        t = pd.DataFrame(res, index=[f"p{p}" for p in PCTS]).T
        t.insert(0, "Strategy", label)
        tables.append(t)
        print(f"{label}: {len(tr)} trades over {years:.2f} years, {per_year} trades per simulated year, "
              f"{len(recent)} trades since {args.recent}")
    out = pd.concat(tables).reset_index(names="Test").sort_values(["Test", "Strategy"], kind="stable")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"\n{args.runs} runs per test, percentiles p5 / p25 / p50 (median) / p75 / p95\n")
    print(out.round(2).to_string(index=False))
    if args.out:
        out.round(4).to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
