"""Intraday backtest engine for NIFTY synthetic futures (spot used as proxy).

Conventions (mirrored in the Pine script):
  * Indicators are computed on bar close, continuously across sessions (as TradingView does).
  * Orders fill at the CLOSE of the signal bar (Pine: process_orders_on_close=true).
  * Stops/targets are checked intrabar on subsequent bars; if both are touched in the same
    bar we assume the stop was hit first (conservative).
  * Every position is squared off at the close of the bar that ends at/after 15:15.
  * Cost is charged per round trip in index points (synthetic = 2 option legs).
"""
import numpy as np, pandas as pd
from numba import njit

SCR = "/tmp/claude-0/-home-user-RISHI-MOMENTUM10-DASHBOARD/636b87ff-ebab-5749-9ec3-2ce77c075396/scratchpad"

# ----------------------------------------------------------------------------- data
_m1 = None
def m1():
    global _m1
    if _m1 is None:
        df = pd.read_pickle(f"{SCR}/data/m1.pkl")
        mins = df.index.hour * 60 + df.index.minute
        df = df[(mins >= 555) & (mins <= 929)]  # 09:15 .. 15:29
        cnt = df.groupby(df.index.date).size()
        good = cnt[cnt >= 300].index
        df = df[np.isin(df.index.date, good)]
        _m1 = df
    return _m1

def resample(tf):
    df = m1()
    mins = df.index.hour * 60 + df.index.minute
    bucket = (mins - 555) // tf
    day = np.asarray(df.index.date)
    g = df.groupby([day, np.asarray(bucket)], sort=True)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(),
                        "low": g.low.min(), "close": g.close.last()})
    out.index = out.index.set_names(["day", "b"])
    out = out.reset_index()
    out["start_min"] = 555 + out.b * tf
    out["end_min"] = np.minimum(out.start_min + tf, 930)
    out["ts"] = pd.to_datetime(out.day.astype(str)) + pd.to_timedelta(out.start_min, unit="m")
    out["day_id"] = pd.factorize(out.day)[0]
    return out

# ----------------------------------------------------------------------------- indicators (Pine-equivalent)
@njit(cache=True)
def ema(x, n):
    out = np.empty_like(x); a = 2.0 / (n + 1)
    s = 0.0
    for i in range(len(x)):
        if i < n - 1:
            s += x[i]; out[i] = np.nan
        elif i == n - 1:
            s += x[i]; out[i] = s / n
        else:
            out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

@njit(cache=True)
def rma(x, n):
    out = np.empty_like(x); a = 1.0 / n; s = 0.0
    for i in range(len(x)):
        if i < n - 1:
            s += x[i]; out[i] = np.nan
        elif i == n - 1:
            s += x[i]; out[i] = s / n
        else:
            out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

@njit(cache=True)
def true_range(h, l, c):
    tr = np.empty_like(c); tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return tr

def atr(h, l, c, n):
    return rma(true_range(h, l, c), n)

@njit(cache=True)
def _supertrend(h, l, c, at, m):
    """Exact port of TradingView ta.supertrend. Returns dir (+1 up / -1 down, i.e. -pine_dir) and line."""
    n = len(c); dirn = np.ones(n); line = np.full(n, np.nan)
    lb_prev = 0.0; ub_prev = 0.0; st_prev = np.nan
    for i in range(n):
        src = (h[i] + l[i]) / 2
        ub = src + m * at[i]; lb = src - m * at[i]
        if np.isnan(at[i]):
            lb_prev = 0.0; ub_prev = 0.0; st_prev = np.nan; dirn[i] = -1; continue
        cp = c[i - 1] if i > 0 else c[i]
        if not (lb > lb_prev or cp < lb_prev): lb = lb_prev
        if not (ub < ub_prev or cp > ub_prev): ub = ub_prev
        if i == 0 or np.isnan(at[i - 1]):
            pdir = 1
        elif st_prev == ub_prev:
            pdir = -1 if c[i] > ub else 1
        else:
            pdir = 1 if c[i] < lb else -1
        st = lb if pdir == -1 else ub
        dirn[i] = -pdir; line[i] = st
        lb_prev = lb; ub_prev = ub; st_prev = st
    return dirn, line

def supertrend(h, l, c, n, m):
    return _supertrend(h, l, c, atr(h, l, c, n), m)

def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    g = rma(np.maximum(d, 0.0), n); ls = rma(np.maximum(-d, 0.0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + g / ls)
    r[ls == 0] = 100.0
    return r

def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    m2 = m.copy(); first = np.argmax(~np.isnan(m))
    sg = np.full_like(m, np.nan); sg[first:] = ema(m[first:], sig)
    return m, sg, m - sg

def adx(h, l, c, n=14):
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * rma(pdm, n) / tr; mdi = 100 * rma(mdm, n) / tr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    dx = np.nan_to_num(dx)
    return rma(dx, n), pdi, mdi

def htf_map(ltf, htf, values):
    """Pine idiom request.security(tf, x[1], lookahead_on): for each LTF bar take value of the
    HTF bar *preceding* the HTF bar that contains the LTF bar's start."""
    key_h = htf.day_id.values * 10000 + htf.start_min.values
    tfh = int(htf.end_min.iloc[0] - htf.start_min.iloc[0])
    hstart = 555 + ((ltf.start_min.values - 555) // tfh) * tfh
    key_l = ltf.day_id.values * 10000 + hstart
    idx = np.searchsorted(key_h, key_l)  # index of containing HTF bar
    prev = idx - 1
    out = np.full(len(ltf), np.nan)
    ok = prev >= 0
    out[ok] = values[prev[ok]]
    return out

def daily_map(ltf, values_daily):
    """values_daily indexed by day_id; returns previous completed day's value for each LTF bar."""
    d = ltf.day_id.values
    out = np.full(len(ltf), np.nan)
    ok = d >= 1
    out[ok] = values_daily[d[ok] - 1]
    return out

# ----------------------------------------------------------------------------- simulator
@njit(cache=True)
def simulate(o, h, l, c, day, entry_ok, eod, lsig, ssig, lexit, sexit,
             atrv, sl_mult, tp_mult, trail_mult, sl_long_px, sl_short_px,
             cost, max_trades, reverse):
    n = len(c)
    ei = np.empty(n, np.int64); xi = np.empty(n, np.int64)
    dr = np.empty(n, np.int64); pnl = np.empty(n); nt = 0
    pos = 0; entry = 0.0; stop = np.nan; tgt = np.nan; e_idx = -1
    trades_today = 0; cur_day = -1
    for i in range(n):
        if day[i] != cur_day:
            cur_day = day[i]; trades_today = 0
        # ---- intrabar stop/target on bars after entry
        if pos != 0 and i > e_idx:
            xp = np.nan
            if pos == 1:
                if not np.isnan(stop) and l[i] <= stop:
                    xp = min(o[i], stop)
                elif not np.isnan(tgt) and h[i] >= tgt:
                    xp = max(o[i], tgt)
            else:
                if not np.isnan(stop) and h[i] >= stop:
                    xp = max(o[i], stop)
                elif not np.isnan(tgt) and l[i] <= tgt:
                    xp = min(o[i], tgt)
            if not np.isnan(xp):
                ei[nt] = e_idx; xi[nt] = i; dr[nt] = pos
                pnl[nt] = pos * (xp - entry) - cost; nt += 1
                pos = 0
            elif trail_mult > 0 and not np.isnan(atrv[i]):
                if pos == 1:
                    ns = c[i] - trail_mult * atrv[i]
                    if np.isnan(stop) or ns > stop: stop = ns
                else:
                    ns = c[i] + trail_mult * atrv[i]
                    if np.isnan(stop) or ns < stop: stop = ns
        # ---- close-of-bar exits
        if pos != 0:
            ex = eod[i] or (pos == 1 and lexit[i]) or (pos == -1 and sexit[i])
            rev = reverse and ((pos == 1 and ssig[i]) or (pos == -1 and lsig[i]))
            if ex or rev:
                ei[nt] = e_idx; xi[nt] = i; dr[nt] = pos
                pnl[nt] = pos * (c[i] - entry) - cost; nt += 1
                pos = 0
        # ---- entries
        if pos == 0 and entry_ok[i] and not eod[i] and trades_today < max_trades:
            d = 0
            if lsig[i]: d = 1
            elif ssig[i]: d = -1
            if d != 0 and not np.isnan(atrv[i]):
                pos = d; entry = c[i]; e_idx = i; trades_today += 1
                stop = np.nan; tgt = np.nan
                if d == 1:
                    if sl_mult > 0: stop = c[i] - sl_mult * atrv[i]
                    if not np.isnan(sl_long_px[i]):
                        stop = sl_long_px[i] if np.isnan(stop) else max(stop, sl_long_px[i])
                    if tp_mult > 0: tgt = c[i] + tp_mult * atrv[i]
                else:
                    if sl_mult > 0: stop = c[i] + sl_mult * atrv[i]
                    if not np.isnan(sl_short_px[i]):
                        stop = sl_short_px[i] if np.isnan(stop) else min(stop, sl_short_px[i])
                    if tp_mult > 0: tgt = c[i] - tp_mult * atrv[i]
    if pos != 0:
        ei[nt] = e_idx; xi[nt] = n - 1; dr[nt] = pos
        pnl[nt] = pos * (c[n - 1] - entry) - cost; nt += 1
    return ei[:nt], xi[:nt], dr[:nt], pnl[:nt]

# ----------------------------------------------------------------------------- metrics
def metrics(pnl, xday, ndays_mask_days):
    """pnl per trade, xday = day_id of exit, ndays_mask_days = array of day_ids in the window."""
    if len(pnl) == 0:
        return dict(trades=0, pts=0.0, pf=0.0, win=0.0, avg=0.0, sharpe=0.0, mdd=0.0, calmar=0.0)
    days = np.asarray(ndays_mask_days)
    daily = np.zeros(len(days))
    pos = np.searchsorted(days, xday)
    np.add.at(daily, pos, pnl)
    eq = np.cumsum(daily); dd = np.max(np.maximum.accumulate(eq) - eq) if len(eq) else 0
    gp = pnl[pnl > 0].sum(); gl = -pnl[pnl < 0].sum()
    sd = daily.std()
    yrs = len(days) / 248.0
    return dict(trades=len(pnl), pts=float(pnl.sum()), pf=float(gp / gl) if gl > 0 else 99.0,
                win=float((pnl > 0).mean()), avg=float(pnl.mean()),
                sharpe=float(daily.mean() / sd * np.sqrt(248)) if sd > 0 else 0.0,
                mdd=float(dd), calmar=float(pnl.sum() / yrs / dd) if dd > 0 else 0.0)
