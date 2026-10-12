#!/usr/bin/env python3
"""Rishi Robust TK TF - compare the two trend filters for gated shorts.

  A) Signal-price average : time-weighted average of the signal (flip) prices over the last N calendar
                            days (the original Robust rule, N = 30).
  B) Daily SMA            : simple moving average of the last N daily closes, using the previous
                            completed day only (no look-ahead), as in the Pine "Daily SMA" option.

A SELL is shorted only when the signal price is at or below the trend line; otherwise the long is
closed and the strategy stays flat until the next BUY. Longs are never filtered.

Inputs : the Every-Candle trade-list export (TradingView, 1m NSE:NIFTY) and an intraday NIFTY
         price export (any timeframe) from which daily closes are built. The comparison runs over
         the period covered by the price file (after the SMA warm-up).

    python3 trend_filter_compare.py every_candle_trades.csv NSE_NIFTY_30.csv --out trend_filter_results.csv
"""
import argparse

import numpy as np
import pandas as pd

from robustness_research import flip_avg, load, metrics


def daily_closes(path):
    p = pd.read_csv(path, usecols=["time", "close"])
    t = pd.to_datetime(p["time"].str.slice(0, 19))
    return p.assign(day=t.dt.normalize()).groupby("day")["close"].last()


def prev_day_sma(d, closes, n):
    """SMA of the n daily closes before the signal's day (yesterday's completed value)."""
    sma = closes.rolling(n).mean().shift(1)            # value available on each day, from earlier days
    idx = sma.index.searchsorted(d["t"].dt.normalize(), side="right") - 1
    out = np.where(idx >= 0, sma.values[np.clip(idx, 0, None)], np.nan)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trades")
    ap.add_argument("prices")
    ap.add_argument("--out", default="trend_filter_results.csv")
    a = ap.parse_args()

    d = load(a.trades)
    closes = daily_closes(a.prices)
    start = closes.index[0] + pd.Timedelta(days=120)    # leave room for the longest SMA warm-up
    side, price = d["side"].values, d["price"].values

    rules = {"No filter (Every-Candle)": np.ones(len(d))}
    for n in (20, 30, 50):
        avg = flip_avg(d, n)
        rules[f"Signal-price average {n}d"] = np.where((side < 0) & (price > avg), 0.0, 1.0)
    for n in (20, 30, 50, 100):
        sma = prev_day_sma(d, closes, n)
        rules[f"Daily SMA {n}"] = np.where((side < 0) & (price > sma), 0.0, 1.0)

    mask = (d["t"] >= start).values
    full = d["t"].dt.year.values >= 2009
    rows = []
    for name, s in rules.items():
        for cost, label in ((0.0, "before cost"), (0.0118, "after cost (synthetic, 0.0118%/side)"), (0.02, "after cost (0.02%/side)")):
            m = metrics(d, s, cost, mask)
            rows.append(dict(rule=name, costs=label, period=f"{d['t'][mask].iloc[0]:%d-%b-%Y} to {d['xt'][mask].iloc[-1]:%d-%b-%Y}",
                             shorts=int(((s != 0) & (side < 0) & mask).sum()), **m))
            if not name.startswith("Daily"):
                mf = metrics(d, s, cost, full)
                rows.append(dict(rule=name, costs=label, period="2009-2026 (full)",
                                 shorts=int(((s != 0) & (side < 0)).sum()), **mf))
    df = pd.DataFrame(rows)
    # agreement between the two 30-day filters on SELL signals in the common period
    sp = flip_avg(d, 30); sm = prev_day_sma(d, closes, 30)
    sells = (side < 0) & mask & ~np.isnan(sm)
    agree = ((price > sp) == (price > sm))[sells].mean() * 100
    print(f"Daily closes {closes.index[0]:%d-%b-%Y} to {closes.index[-1]:%d-%b-%Y}; comparison from {start:%d-%b-%Y}")
    print(f"SELL signals in the comparison period: {sells.sum()}; the 30-day filters agree on {agree:.1f}% of them")
    pd.set_option("display.width", 250)
    print(df[["rule", "costs", "period", "trades", "shorts", "roi", "cagr", "cdd", "mar", "pf", "win", "worst_yr", "loss_yrs"]].round(2).to_string(index=False))
    df.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
