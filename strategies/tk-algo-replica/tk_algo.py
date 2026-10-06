"""In-house replica of the TK ALGO V1.1 Slow / Fast / Combined signals.

Reverse-engineered from TradingView CSV exports that contain the original
indicator's plotted Slow, Fast and Combined columns (1 = bullish, -1 = bearish).

    Slow     : 30-minute timeframe, (H+L+2C)/4 vs EMA(HL2, 62)   (chart independent)
    Fast     : chart timeframe,     EMA(HL2, 102) vs EMA(HL2, 113)
    Combined : changes only when Slow and Fast agree, otherwise holds the previous state

Usage:
    python tk_algo.py verify   <tv_export.csv> [--htf <30m_export.csv>]
    python tk_algo.py backtest <tv_export.csv> [--htf <30m_export.csv>] [--original]
"""
import argparse

import numpy as np
import pandas as pd

SLOW_TF = "30min"
SLOW_LEN = 62
FAST_LEN = 102
FAST_SLOW_LEN = 113
SESSION_START = pd.Timedelta(minutes=15)  # NSE 30m bars are anchored at 09:15


def load(path):
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"].str[:19])
    return df.set_index("time")


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def to_30m(df):
    bucket = (df.index - SESSION_START).floor(SLOW_TF) + SESSION_START
    g = df.groupby(bucket)
    return pd.DataFrame({"open": g.open.first(), "high": g.high.max(),
                         "low": g.low.min(), "close": g.close.last()})


def slow_signal(htf):
    """Slow state on 30m bars, indexed by 30m bar open time."""
    fast_src = (htf.high + htf.low + 2 * htf.close) / 4
    base = ema((htf.high + htf.low) / 2, SLOW_LEN)
    return np.sign(fast_src - base)


def fast_signal(df):
    hl2 = (df.high + df.low) / 2
    return np.sign(ema(hl2, FAST_LEN) - ema(hl2, FAST_SLOW_LEN))


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


def compute(df, htf=None):
    bar_minutes = int(pd.Series(df.index).diff().dt.total_seconds().div(60).mode()[0])
    htf = to_30m(df) if htf is None else htf[["open", "high", "low", "close"]]
    if bar_minutes >= 30:
        slow = slow_signal(df).values
    else:
        slow = map_htf_to_chart(slow_signal(htf), df.index, bar_minutes).values
    fast = fast_signal(df).values
    out = pd.DataFrame({"Slow": slow, "Fast": fast}, index=df.index)
    out["Combined"] = combined_signal(out.Slow.values, out.Fast.values)
    return out


def verify(df, sig, warmup_days=10):
    start = df.index[0] + pd.Timedelta(days=warmup_days)
    m = (df.index >= start) & df.Combined.notna() & (df.Slow != 0)
    for col in ["Slow", "Fast", "Combined"]:
        acc = (sig.loc[m, col].values == df.loc[m, col].values).mean()
        print(f"{col:9s} match: {acc:.2%}  ({m.sum()} bars)")


def backtest(df, sig, col="Combined"):
    """Always-in-market reversal on spot: enter on the close of the bar where the
    signal flips, exit/reverse on the next flip. Points per trade, no costs."""
    s = pd.Series(sig[col].values, index=df.index)
    flips = s[(s != s.shift()) & (s != 0)].iloc[1:]
    px = df.close.loc[flips.index].values
    side = flips.values
    pts = side[:-1] * (px[1:] - px[:-1])
    trades = pd.DataFrame({"entry": flips.index[:-1], "exit": flips.index[1:],
                           "side": side[:-1], "points": pts})
    wins = trades.points > 0
    print(f"{col}: {len(trades)} trades | net {pts.sum():.0f} pts | win rate {wins.mean():.1%} | "
          f"avg win {trades.points[wins].mean():.1f} | avg loss {trades.points[~wins].mean():.1f} | "
          f"profit factor {trades.points[wins].sum() / -trades.points[~wins].sum():.2f}")
    return trades


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["verify", "backtest"])
    ap.add_argument("csv")
    ap.add_argument("--htf", help="30m TradingView export (longer Slow EMA history)")
    ap.add_argument("--original", action="store_true",
                    help="backtest the original indicator's exported columns instead of the replica")
    a = ap.parse_args()
    df = load(a.csv)
    sig = compute(df, load(a.htf) if a.htf else None)
    if a.mode == "verify":
        verify(df, sig)
    else:
        df = df[df.index >= df.index[0] + pd.Timedelta(days=10)]
        sig = df[["Slow", "Fast", "Combined"]].fillna(0) if a.original else sig.loc[df.index]
        for c in ["Slow", "Fast", "Combined"]:
            backtest(df, sig, c)
