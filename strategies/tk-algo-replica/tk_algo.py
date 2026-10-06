"""In-house replica of the TK ALGO V1.1 Slow / Fast / Combined signals.

Reverse-engineered from TradingView CSV exports that contain the original
indicator's plotted Slow, Fast and Combined columns (1 = bullish, -1 = bearish),
and from the original's trade logs (2009-2026).

    Slow     : 30-minute timeframe (chart independent)
               sign( LEAD(HLC3) - EMA(HLC3, 63) ), where LEAD is an EMA with
               smoothing factor 1.27 (> 1, so it leads price instead of lagging)
    Fast     : chart timeframe (or a locked lower timeframe, e.g. 1m, via --fast-1m),
               sign of a fixed weighted sum of EMA(HLC3, n) - EMA(HLC3, 113)
               (weights fitted on the 30m + 5m charts, validated on the 3m and 1m charts)
    Combined : changes only when Slow and Fast agree, otherwise holds the previous state

Trades (as in the original's logs) are taken at the open of the bar after the signal bar.

Usage:
    python tk_algo.py verify    <tv_export.csv> [--htf <30m_export.csv>] [--fast-1m <1m_export.csv>]
    python tk_algo.py backtest  <tv_export.csv> [--htf <30m_export.csv>] [--original]
    python tk_algo.py checklog  <tv_export.csv> <trade_log.csv> --signal Slow|Fast|Combined [--htf ...]
"""
import argparse
import re

import numpy as np
import pandas as pd

SLOW_TF = "30min"
SLOW_LEN = 63
SLOW_LEAD_ALPHA = 1.27
FAST_BASE_LEN = 113
FAST_LENS = [1, 5, 10, 20, 40, 60, 80, 100, 120, 140, 160, 200, 250, 300]
FAST_WEIGHTS = [0.0128, -0.0381, 0.0198, 0.1147, -0.6092, 0.5811, 1.0,
                0.4886, -0.2437, -0.7241, -0.8173, -0.1915, 0.5852, -0.1643]
SESSION_START = pd.Timedelta(minutes=15)  # NSE 30m bars are anchored at 09:15


def load(path):
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"].str[:19])
    df = df.set_index("time")
    return df[~df.index.duplicated(keep="last")]


def load_log(path):
    """Original trade log: Date (dd-mm-yyyy HH:MM, execution time), Signal, ROI %."""
    with open(path, encoding="utf-8-sig") as f:
        rows = [line.split(",")[:3] for line in f.read().splitlines()
                if re.match(r"\d\d-\d\d-\d{4} \d\d:\d\d,(Buy|Sell),", line)]
    log = pd.DataFrame(rows, columns=["time", "signal", "roi"])
    log["time"] = pd.to_datetime(log.time, format="%d-%m-%Y %H:%M")
    log["side"] = np.where(log.signal == "Buy", 1, -1)
    log["roi"] = pd.to_numeric(log.roi, errors="coerce")
    return log


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def lead(s, alpha):
    out = np.empty(len(s))
    v = s.values
    out[0] = v[0]
    for i in range(1, len(v)):
        out[i] = alpha * v[i] + (1 - alpha) * out[i - 1]
    return pd.Series(out, index=s.index)


def hlc3(df):
    return (df.high + df.low + df.close) / 3


def to_30m(df):
    bucket = (df.index - SESSION_START).floor(SLOW_TF) + SESSION_START
    g = df.groupby(bucket)
    return pd.DataFrame({"open": g.open.first(), "high": g.high.max(),
                         "low": g.low.min(), "close": g.close.last()})


def slow_signal(htf):
    """Slow state on 30m bars, indexed by 30m bar open time."""
    src = hlc3(htf)
    return np.sign(lead(src, SLOW_LEAD_ALPHA) - ema(src, SLOW_LEN))


def fast_signal(df):
    src = hlc3(df)
    base = ema(src, FAST_BASE_LEN)
    score = sum(w * (ema(src, n) - base) for n, w in zip(FAST_LENS, FAST_WEIGHTS))
    return np.sign(score)


def map_htf_to_chart(htf_sig, chart_index, bar_minutes):
    """request.security(lookahead_off) semantics: a 30m value becomes visible on
    the chart bar whose close coincides with (or passes) the 30m bar close."""
    htf_close = htf_sig.index + pd.Timedelta(SLOW_TF)
    day_end = htf_sig.index.normalize() + pd.Timedelta(hours=15, minutes=30)
    htf_close = htf_close.where(htf_close < day_end, day_end)
    s = pd.Series(htf_sig.values, index=htf_close).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    chart_close = chart_index + pd.Timedelta(minutes=bar_minutes)
    return pd.Series(s.reindex(chart_close, method="ffill").values, index=chart_index)


def combined_signal(slow, fast):
    out = np.zeros(len(slow))
    cur = 0.0
    for i, (s, f) in enumerate(zip(slow, fast)):
        if s == f and s != 0 and not np.isnan(s):
            cur = s
        out[i] = cur
    return out


def bar_minutes_of(df):
    return int(pd.Series(df.index).diff().dt.total_seconds().div(60).mode()[0])


def compute(df, htf=None, fast_df=None):
    """Slow/Fast/Combined on the chart bars of df. With fast_df (e.g. 1m bars), Fast and
    Combined are computed on fast_df's bars and each chart bar takes the value at its last
    fast_df bar, i.e. what the locked-timeframe chart shows at that moment."""
    if fast_df is not None and bar_minutes_of(fast_df) < bar_minutes_of(df):
        low = compute(fast_df, htf if htf is not None else to_30m(df))
        last_low_bar = df.index + pd.Timedelta(minutes=bar_minutes_of(df) - bar_minutes_of(fast_df))
        out = pd.DataFrame(low[["Fast", "Combined"]].reindex(last_low_bar, method="ffill").values,
                           index=df.index, columns=["Fast", "Combined"])
        out.insert(0, "Slow", compute(df, htf)["Slow"].values)
        return out
    bar_minutes = bar_minutes_of(df)
    htf = to_30m(df) if htf is None else htf[["open", "high", "low", "close"]]
    htf = htf[htf.index.time < pd.Timestamp("15:30").time()]  # drop special-session bars
    if bar_minutes >= 30:
        slow = slow_signal(df).values
    else:
        slow = map_htf_to_chart(slow_signal(htf), df.index, bar_minutes).values
    fast = fast_signal(df).values
    out = pd.DataFrame({"Slow": slow, "Fast": fast}, index=df.index)
    out["Combined"] = combined_signal(out.Slow.values, out.Fast.values)
    return out


def flips(df, state):
    """Signal events as the original logs them: (execution time = next bar open, side)."""
    s = pd.Series(np.asarray(state, dtype=float), index=df.index).replace(0, np.nan).ffill()
    f = s[(s != s.shift()) & s.shift().notna()]
    nxt = pd.Series(list(df.index[1:]) + [pd.NaT], index=df.index)
    return pd.DataFrame({"time": nxt.loc[f.index].values, "side": f.values.astype(int)}).dropna()


def verify(df, sig, warmup_days=10):
    start = df.index[0] + pd.Timedelta(days=warmup_days)
    m = (df.index >= start) & df.Combined.notna() & (df.Slow != 0)
    for col in ["Slow", "Fast", "Combined"]:
        acc = (sig.loc[m, col].values == df.loc[m, col].values).mean()
        a = flips(df[m], df.loc[m, col].values)
        r = flips(df[m], sig.loc[m, col].values)
        exact = len(a.merge(r, on=["time", "side"])) / max(len(a), 1)
        print(f"{col:9s} bars: {acc:.2%}  signals: {len(a)} original / {len(r)} replica, "
              f"exact same bar: {exact:.1%}")


def check_log(df, sig, log, col, warmup_days=10):
    start = df.index[0] + pd.Timedelta(days=warmup_days)
    r = flips(df, sig[col].values)
    r = r[r.time >= start]
    lg = log[(log.time >= start) & (log.time <= df.index[-1])]
    hit = lg.merge(r, left_on=["time", "side"], right_on=["time", "side"])
    print(f"{col}: log signals {len(lg)} | replica {len(r)} | exact matches {len(hit)} "
          f"({len(hit) / max(len(lg), 1):.1%})")


def backtest(df, sig, col="Combined"):
    """Always-in-market reversal, filled at the open of the bar after the signal
    (the original's convention). ROI % per trade, no costs."""
    ev = flips(df, sig[col].values)
    px = df.open.reindex(ev.time).values
    roi = ev.side.values[:-1] * (px[1:] / px[:-1] - 1) * 100
    pts = ev.side.values[:-1] * (px[1:] - px[:-1])
    wins = roi > 0
    print(f"{col}: {len(roi)} trades | net {pts.sum():.0f} pts | sum ROI {roi.sum():.1f}% | "
          f"win rate {wins.mean():.1%} | avg win {roi[wins].mean():.2f}% | "
          f"avg loss {roi[~wins].mean():.2f}% | profit factor {roi[wins].sum() / -roi[~wins].sum():.2f}")
    return pd.DataFrame({"entry": ev.time.values[:-1], "exit": ev.time.values[1:],
                         "side": ev.side.values[:-1], "roi": roi, "points": pts})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["verify", "backtest", "checklog"])
    ap.add_argument("csv")
    ap.add_argument("log", nargs="?", help="original trade log (checklog mode)")
    ap.add_argument("--htf", help="30m TradingView export (longer Slow EMA history)")
    ap.add_argument("--fast-1m", help="1m export: lock Fast (and Combined) to the 1m timeframe")
    ap.add_argument("--signal", default="Combined", choices=["Slow", "Fast", "Combined"])
    ap.add_argument("--original", action="store_true",
                    help="backtest the original indicator's exported columns instead of the replica")
    a = ap.parse_args()
    df = load(a.csv)
    sig = compute(df, load(a.htf) if a.htf else None, load(a.fast_1m) if a.fast_1m else None)
    if a.mode == "verify":
        verify(df, sig)
    elif a.mode == "checklog":
        check_log(df, sig, load_log(a.log), a.signal)
    else:
        df = df[df.index >= df.index[0] + pd.Timedelta(days=10)]
        sig = df[["Slow", "Fast", "Combined"]].fillna(0) if a.original else sig.loc[df.index]
        for c in ["Slow", "Fast", "Combined"]:
            backtest(df, sig, c)
