"""In-sample / out-of-sample robustness test on TradingView strategy trade lists.

Takes the "List of trades" CSV exports (columns: label, DATE, TYPE, PRICE, ROI, POINTS) of the
original TK TF Combined strategy and of the replica, and runs 10 IS/OOS split variations on each.
For every variation it reports, for the in-sample and out-of-sample parts: trades, ROI % per year,
average ROI per trade, win rate, profit factor and max drawdown, plus the walk-forward efficiency
(OOS ROI per year / IS ROI per year), and how many of the original's OOS trades the replica hits
on the same minute.

Usage:
    python is_oos.py <original_trades.csv> <replica_trades.csv> [--set 10|50] [--out results.csv]

--set 10 (default) runs the 10 headline designs. --set 50 runs 50 time-period designs:
15 forward anchored splits, 15 backward anchored splits, 10 walk-forward configurations and
10 sliding 4-year-IS / 2-year-OOS blocks, and prints a summary of the distribution.
"""
import argparse
import numpy as np
import pandas as pd

YEAR = pd.Timedelta(days=365.25)


def load_trades(path):
    d = pd.read_csv(path, encoding="utf-8-sig")
    d.columns = ["label", "date", "type", "price", "roi", "points"]
    d = d.dropna(subset=["date"])
    d["time"] = pd.to_datetime(d.date, format="%d/%m/%Y %H:%M")
    d["side"] = np.where(d.label.str.contains("long", case=False), 1, -1)
    return d.iloc[:-1].reset_index(drop=True)  # last row is the still-open trade


def metrics(trades, years):
    roi = trades.roi.values
    if len(roi) == 0:
        return dict(trades=0, roi_yr=np.nan, avg=np.nan, win=np.nan, pf=np.nan, dd=np.nan)
    wins = roi > 0
    equity = np.r_[0.0, np.cumsum(roi)]
    loss = -roi[~wins].sum()
    return dict(trades=len(roi), roi_yr=roi.sum() / years, avg=roi.mean(), win=wins.mean() * 100,
                pf=roi[wins].sum() / loss if loss else np.inf,
                dd=(np.maximum.accumulate(equity) - equity).max())


def select(trades, periods):
    mask = np.zeros(len(trades), dtype=bool)
    for a, b in periods:
        mask |= (trades.time >= a) & (trades.time < b)
    return trades[mask]


def span_years(periods):
    return sum((b - a) / YEAR for a, b in periods)


def same_minute_share(orig, rep):
    if len(orig) == 0:
        return np.nan
    keys = set(zip(rep.time, rep.side))
    return np.mean([(t, s) in keys for t, s in zip(orig.time, orig.side)]) * 100


def walk_forward(start, end, is_y, oos_y):
    windows, t = [], start
    while t + is_y * YEAR < end:
        windows.append(([(t, t + is_y * YEAR)], [(t + is_y * YEAR, min(end, t + (is_y + oos_y) * YEAR))]))
        t += oos_y * YEAR
    return windows


def variations_50(start, end):
    """50 IS/OOS time-period designs."""
    T = pd.Timestamp
    out = []
    for y in range(2011, 2026):  # A: forward anchored, IS = start..y, OOS = y..end
        out.append((f"A fwd: IS {start.year}-{y - 1} / OOS {y}-{end.year}", [(start, T(f"{y}-01-01"))],
                    [(T(f"{y}-01-01"), end)], None))
    for y in range(2011, 2026):  # B: backward anchored, IS = y..end, OOS = start..y
        out.append((f"B bwd: IS {y}-{end.year} / OOS {start.year}-{y - 1}", [(T(f"{y}-01-01"), end)],
                    [(start, T(f"{y}-01-01"))], None))
    for is_y in (2, 3, 4, 5, 6):  # C: rolling walk-forward
        for oos_y in (1, 2):
            w = walk_forward(start, end, is_y, oos_y)
            out.append((f"C walk-fwd {is_y}y IS -> {oos_y}y OOS ({len(w)} windows)",
                        [p for x in w for p in x[0]], [p for x in w for p in x[1]], w))
    for y in range(2011, 2021):  # D: sliding blocks, 4y IS then the next 2y OOS
        out.append((f"D block: IS {y}-{y + 3} / OOS {y + 4}-{y + 5}", [(T(f"{y}-01-01"), T(f"{y + 4}-01-01"))],
                    [(T(f"{y + 4}-01-01"), min(end, T(f"{y + 6}-01-01")))], None))
    return out


def variations(start, end):
    """10 IS/OOS designs as (name, is_periods, oos_periods, walk_forward_windows or None)."""
    T = pd.Timestamp
    span = end - start
    cut = lambda f: start + span * f
    out = []
    for f in (0.5, 0.6, 0.7, 0.8):
        out.append((f"{int(f * 100)}/{int(round((1 - f) * 100))} chronological split",
                    [(start, cut(f))], [(cut(f), end)], None))
    out.append(("IS 2009-2015 / OOS 2016-2026", [(start, T("2016-01-01"))], [(T("2016-01-01"), end)], None))
    out.append(("IS 2020-2026 (replica fit period) / OOS 2009-2019",
                [(T("2020-01-01"), end)], [(start, T("2020-01-01"))], None))
    out.append(("Backward: IS 2nd half / OOS 1st half", [(cut(0.5), end)], [(start, cut(0.5))], None))
    years = range(start.year, end.year + 1)
    odd = [(max(start, T(f"{y}-01-01")), min(end, T(f"{y + 1}-01-01"))) for y in years if y % 2]
    even = [(max(start, T(f"{y}-01-01")), min(end, T(f"{y + 1}-01-01"))) for y in years if not y % 2]
    out.append(("Interleaved: IS odd years / OOS even years", odd, even, None))
    for is_y, oos_y in ((3, 1), (5, 2)):
        windows = walk_forward(start, end, is_y, oos_y)
        out.append((f"Walk-forward {is_y}y IS -> {oos_y}y OOS ({len(windows)} windows)",
                    [p for w in windows for p in w[0]], [p for w in windows for p in w[1]], windows))
    return out


def run(orig, rep, design=variations):
    start = min(orig.time.min(), rep.time.min()).normalize()
    end = max(orig.time.max(), rep.time.max()) + pd.Timedelta(minutes=1)
    rows = []
    for i, (name, is_p, oos_p, windows) in enumerate(design(start, end), 1):
        for label, tr in (("Original", orig), ("Replica", rep)):
            if windows:  # walk-forward: average the IS windows, concatenate the OOS windows
                ism = [metrics(select(tr, w[0]), span_years(w[0])) for w in windows]
                m_is = {k: np.nanmean([m[k] for m in ism]) for k in ism[0]}
                m_is["trades"] = sum(m["trades"] for m in ism)
            else:
                m_is = metrics(select(tr, is_p), span_years(is_p))
            m_oos = metrics(select(tr, oos_p), span_years(oos_p))
            rows.append({"#": i, "Variation": name, "Strategy": label,
                         "IS trades": m_is["trades"], "IS ROI/yr %": m_is["roi_yr"], "IS PF": m_is["pf"],
                         "OOS trades": m_oos["trades"], "OOS ROI/yr %": m_oos["roi_yr"],
                         "OOS avg/trade %": m_oos["avg"], "OOS win %": m_oos["win"], "OOS PF": m_oos["pf"],
                         "OOS max DD %": m_oos["dd"], "WFE %": 100 * m_oos["roi_yr"] / m_is["roi_yr"],
                         "OOS same-minute match %": same_minute_share(select(orig, oos_p), select(rep, oos_p))
                         if label == "Replica" else np.nan})
    return pd.DataFrame(rows)


def summarize(res):
    """Distribution of the OOS results over all variations, per strategy, and replica vs original."""
    lines = []
    for label in ("Original", "Replica"):
        r = res[res.Strategy == label]
        n = len(r)
        lines.append(
            f"{label}: OOS profitable {(r['OOS ROI/yr %'] > 0).sum()}/{n} | OOS PF>=1.2 {(r['OOS PF'] >= 1.2).sum()}/{n}"
            f" | OOS PF>=1.4 {(r['OOS PF'] >= 1.4).sum()}/{n} | WFE>=50% {(r['WFE %'] >= 50).sum()}/{n}"
            f" | OOS ROI/yr median {r['OOS ROI/yr %'].median():.1f} (min {r['OOS ROI/yr %'].min():.1f},"
            f" max {r['OOS ROI/yr %'].max():.1f}) | OOS PF median {r['OOS PF'].median():.2f}"
            f" (min {r['OOS PF'].min():.2f}) | WFE median {r['WFE %'].median():.0f}%"
            f" (min {r['WFE %'].min():.0f}%) | OOS max DD worst {r['OOS max DD %'].max():.1f}")
    o = res[res.Strategy == "Original"].set_index("#")
    p = res[res.Strategy == "Replica"].set_index("#")
    d_roi = (p["OOS ROI/yr %"] - o["OOS ROI/yr %"]).abs()
    d_pf = (p["OOS PF"] - o["OOS PF"]).abs()
    lines.append(f"Replica vs original OOS ROI/yr gap: median {d_roi.median():.2f}, max {d_roi.max():.2f} pts"
                 f" | OOS PF gap: median {d_pf.median():.3f}, max {d_pf.max():.3f}"
                 f" | OOS same-minute match: median {p['OOS same-minute match %'].median():.1f}%"
                 f" (min {p['OOS same-minute match %'].min():.1f}%)")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original")
    ap.add_argument("replica")
    ap.add_argument("--set", choices=["10", "50"], default="10")
    ap.add_argument("--out", help="save the full results table to this CSV")
    a = ap.parse_args()
    res = run(load_trades(a.original), load_trades(a.replica),
              variations_50 if a.set == "50" else variations)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 200)
    print(res.round(2).to_string(index=False))
    print()
    print(summarize(res))
    if a.out:
        res.round(4).to_csv(a.out, index=False)
