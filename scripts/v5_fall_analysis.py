#!/usr/bin/env python3
"""Fall analysis of the V5 portfolio's holdings.

usage: v5_fall_analysis.py <pit_parquet> <v5_trades.csv> <v5_nav.csv> [out_dir]

A "fall" = close-to-close decline of at least X% over N sessions (N = 1, 3, 5) on a
stock that was held for the whole window (in the portfolio at the close before the
window started AND at the close before the final day).  X in 5, 7, 8, 10, 12.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THRESH = [5, 7, 8, 10, 12]
WINDOWS = [1, 3, 5]


def md(df, floatfmt=2):
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        cells = []
        for v in r:
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else f"{v:,.{floatfmt}f}")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main(pq, trades_csv, nav_csv, out):
    px = pd.read_parquet(pq, columns=["date", "sid", "sym", "close"])
    px = px[px.close > 0]
    sym = px.drop_duplicates("sid", keep="last").set_index("sid").sym
    close = px.pivot(index="date", columns="sid", values="close").sort_index()
    dates = close.index
    T = len(dates)
    C = close.values
    col = {s: j for j, s in enumerate(close.columns)}
    didx = {d: i for i, d in enumerate(dates)}

    tr = pd.read_csv(trades_csv, parse_dates=["date"])
    tr["sgn"] = np.where(tr.side == "BUY", 1.0, -1.0)
    pos = np.zeros((T, len(col)))
    for r in tr.itertuples():
        pos[didx[r.date]:, col[r.security_id]] += r.sgn * r.qty
    pos[pos < 1e-6] = 0.0
    held = pos > 0
    nav = pd.read_csv(nav_csv, parse_dates=["date"]).set_index("date").nav.reindex(dates).values
    lastpx = pd.DataFrame(C).ffill().values

    # --- spells (buy .. flat) : avg price return
    spells = []
    for sid, g in tr.groupby("security_id"):
        j = col[sid]
        h = held[:, j]
        i = 0
        while i < T:
            if h[i]:
                k = i
                while k + 1 < T and h[k + 1]:
                    k += 1
                spells.append((sid, i, k))
                i = k + 1
            else:
                i += 1
    sp = []
    for sid, a, b in spells:
        g = tr[(tr.security_id == sid) & (tr.date >= dates[a]) & (tr.date <= dates[b] + pd.Timedelta(days=3))]
        bu = g[g.side == "BUY"]
        se = g[g.side == "SELL"]
        if len(bu) == 0 or len(se) == 0 or b == T - 1:
            continue
        sp.append(dict(sid=sid, start=a, end=b,
                       ret=(se.qty * se.price).sum() / se.qty.sum() / ((bu.qty * bu.price).sum() / bu.qty.sum()) - 1,
                       days=b - a + 1))
    sp = pd.DataFrame(sp)
    # spell id per (day, stock)
    spell_of = -np.ones((T, len(col)), int)
    for n, r in enumerate(sp.itertuples()):
        spell_of[r.start:r.end + 1, col[r.sid]] = n

    held_days = held[:-1].sum()  # stock-days exposed to a next-day move
    rows, worst_rows, ev_all = [], [], []
    yr = {}
    for n in WINDOWS:
        ret = np.full_like(C, np.nan)
        ret[n:] = C[n:] / C[:-n] - 1
        exposed = np.zeros_like(held)
        exposed[n:] = held[:-n] & held[n - 1:-1] if n > 1 else held[:-1]
        for x in THRESH:
            flag = exposed & (ret <= -x / 100)
            ti, kj = np.nonzero(flag)
            if len(ti) == 0:
                rows.append(dict(window=f"{n}d", fall=f">={x}%", flagged_days=0))
                continue
            df = pd.DataFrame(dict(t=ti, k=kj)).sort_values(["k", "t"])
            newep = (df.k.diff() != 0) | (df.t.diff() > n)
            df["ep"] = newep.cumsum()
            first = df.groupby("ep").first()  # episode start
            worst = df.assign(r=ret[df.t, df.k]).groupby("ep").apply(lambda g: g.loc[g.r.idxmin()])
            t0, k0 = worst.t.values.astype(int), worst.k.values.astype(int)
            w = pos[t0 - n, k0] * lastpx[t0 - n, k0] / nav[t0 - n]  # weight before window
            loss_nav = w * ret[t0, k0]  # portfolio hit from the fall
            f5 = np.array([C[min(t + 5, T - 1), k] / C[t, k] - 1 for t, k in zip(t0, k0)])
            f20 = np.array([C[min(t + 20, T - 1), k] / C[t, k] - 1 for t, k in zip(t0, k0)])
            s5 = np.array([not held[min(t + 5, T - 1), k] for t, k in zip(t0, k0)])
            s20 = np.array([not held[min(t + 20, T - 1), k] for t, k in zip(t0, k0)])
            sid_sp = spell_of[t0, k0]
            sret = np.where(sid_sp >= 0, sp.ret.values[np.maximum(sid_sp, 0)] if len(sp) else np.nan, np.nan)
            n_spells_hit = len(set(sid_sp[sid_sp >= 0]))
            rows.append(dict(
                window=f"{n}d", fall=f">={x}%", flagged_days=len(ti), episodes=len(t0),
                stocks=len(set(k0)), spells_hit_pct=100 * n_spells_hit / max(len(sp), 1),
                pct_holding_days=100 * len(ti) / held_days,
                per_year=len(t0) / ((dates[-1] - dates[0]).days / 365.25),
                avg_fall_pct=100 * ret[t0, k0].mean(), avg_weight_pct=100 * w.mean(),
                avg_nav_hit_pct=100 * loss_nav.mean(), worst_nav_hit_pct=100 * loss_nav.min(),
                fwd5d_pct=100 * np.nanmean(f5), fwd20d_pct=100 * np.nanmean(f20),
                rebound20d_pct=100 * np.mean(f20 > 0),
                sold_within_5d_pct=100 * s5.mean(), sold_within_20d_pct=100 * s20.mean(),
                spell_ret_after_fall_pct=100 * np.nanmean(sret) if np.isfinite(sret).any() else np.nan))
            for t, k, r_, ww in zip(t0, k0, ret[t0, k0], w):
                ev_all.append((n, x, dates[t].date(), sym.get(close.columns[k], "?"), r_ * 100, ww * 100))
            if n == 1 or x in (10, 12):
                for t in dates[t0].year:
                    yr[(f"{n}d>={x}%", t)] = yr.get((f"{n}d>={x}%", t), 0) + 1
    res = pd.DataFrame(rows)

    # base rate: same falls in ALL valid stock-days (not only held) for comparison
    base = []
    for n in WINDOWS:
        ret = np.full_like(C, np.nan)
        ret[n:] = C[n:] / C[:-n] - 1
        for x in THRESH:
            v = ~np.isnan(ret)
            base.append(dict(window=f"{n}d", fall=f">={x}%",
                             all_stocks_pct=100 * np.mean(ret[v] <= -x / 100)))
    base = pd.DataFrame(base)
    res = res.merge(base, on=["window", "fall"])
    res["held_vs_universe_x"] = res.pct_holding_days / res.all_stocks_pct
    ev = pd.DataFrame(ev_all, columns=["window", "x", "date", "symbol", "fall_pct", "weight_pct"])

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "v5_fall_summary.csv", index=False)
    ev.to_csv(out / "v5_fall_events.csv", index=False)

    # portfolio-level daily drops
    pr = pd.Series(nav, index=dates).pct_change()
    inv = pd.Series(held.any(axis=1), index=dates).shift(1, fill_value=False)
    pr = pr[inv]
    pd_rows = [dict(metric=f"portfolio down >= {x}% in a day", days=int((pr <= -x / 100).sum())) for x in (1, 2, 3, 4, 5)]
    L = []
    L.append("# V5 portfolio - fall analysis\n")
    L.append(f"Backtest {dates[0].date()} to {dates[-1].date()}; {len(sp)} completed holding spells "
             f"across {len(set(tr.security_id))} stocks; {int(held_days):,} stock-days held.\n")
    L.append("Definition: a fall of X% over N sessions = close-to-close decline >= X% on a stock held for the "
             "whole window. Episodes merge flagged days within N sessions of each other. "
             "Weight = position weight in NAV before the window; NAV hit = weight x fall.\n")
    for title, cols in [
        ("Frequency", ["window", "fall", "flagged_days", "episodes", "per_year", "stocks", "spells_hit_pct",
                       "pct_holding_days"]),
        ("Held stocks vs the whole universe", ["window", "fall", "pct_holding_days", "all_stocks_pct",
                                               "held_vs_universe_x"]),
        ("Portfolio impact", ["window", "fall", "avg_fall_pct", "avg_weight_pct", "avg_nav_hit_pct",
                              "worst_nav_hit_pct"]),
        ("What happened next", ["window", "fall", "fwd5d_pct", "fwd20d_pct", "rebound20d_pct",
                                "sold_within_5d_pct", "sold_within_20d_pct", "spell_ret_after_fall_pct"])]:
        L.append(f"## {title}\n")
        L.append(md(res[cols]) + "\n")
    L.append("## Portfolio-level daily drops (days invested)\n")
    L.append(md(pd.DataFrame(pd_rows)) + "\n")
    yrs = pd.DataFrame(yr, index=[0]).T.reset_index() if yr else pd.DataFrame()
    if len(yrs):
        yrs.columns = ["series", "year", "n"]
        L.append("## Episodes per calendar year\n")
        L.append(md(yrs.pivot(index="year", columns="series", values="n").fillna(0).astype(int).reset_index()) + "\n")
    top = ev[(ev.window == 1) & (ev.x == 12)].sort_values("fall_pct").head(15)
    L.append("## Worst single-day falls while held (>=12%)\n")
    L.append(md(top[["date", "symbol", "fall_pct", "weight_pct"]]) + "\n")
    (out / "v5_fall_analysis.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:4], sys.argv[4] if len(sys.argv) > 4 else "v5_fall_out")
