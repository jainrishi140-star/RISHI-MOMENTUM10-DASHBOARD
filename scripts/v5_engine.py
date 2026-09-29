#!/usr/bin/env python3
"""STAR RSI SHARPE 2.0 - V5 engine (see rulebook).

usage: v5_engine.py <pit_parquet> <smallcap_weekly_csv> [out_dir [atr_period mult [mode [gold_csv]]]]

Parquet columns: date, sid, sym, close (a row's presence == available price and
PIT membership).  Fractional shares, T+1 close execution, FIFO tax, cash interest.
"""
import json
import sys
from bisect import bisect_right
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

CAPITAL = 1e7
SLOTS, ENTRY_RANK, HOLD_RANK = 20, 20, 40
RF = 0.065
SHOCK, QUAR_ROWS = 0.40, 252
RSI_N, RSI_BUY, RSI_EXIT = 50, 55.0, 50.0


# ----------------------------------------------------------------- costs
def cost_rate(d, buy, stt_on=True):
    stt = (0.00125 if d < date(2013, 6, 1) else 0.001) if stt_on else 0.0
    gst = 0.18 * (0.0003 + 0.0000297 + 0.000001)
    return 0.002 + 0.0003 + 0.0000297 + 0.000001 + gst + stt + (0.00015 if buy else 0.0)


# ----------------------------------------------------------------- signals
def load_signals(pq):
    df = pd.read_parquet(pq, columns=["date", "sid", "open", "low", "close"])
    df = df[df.close > 0]
    close = df.pivot(index="date", columns="sid", values="close").sort_index()
    opn = df.pivot(index="date", columns="sid", values="open").reindex(close.index)
    low = df.pivot(index="date", columns="sid", values="low").reindex(close.index)
    dates = close.index
    ret = close / close.shift(1) - 1
    ret = ret.replace([np.inf, -np.inf], np.nan)
    mu = ret.rolling(252, min_periods=252).mean()
    sd = ret.rolling(252, min_periods=252).std(ddof=1)
    sharpe = ((mu * 252 - RF) / (sd * np.sqrt(252))).replace([np.inf, -np.inf], np.nan)
    quar = (ret.abs() > SHOCK).astype(float).rolling(QUAR_ROWS, min_periods=1).max() > 0

    # weekly closes (week = Mon..Fri; Sat/Sun sessions join the preceding Friday's week)
    wk = pd.Series([(d - timedelta(days=d.weekday()) + timedelta(days=4)) for d in dates.date],
                   index=dates)
    wclose = close.groupby(wk.values).last()
    last_sess = pd.Series(dates, index=dates).groupby(wk.values).max()
    rsi_w = pd.DataFrame(np.nan, index=wclose.index, columns=wclose.columns)
    for c in wclose.columns:
        s = wclose[c].dropna()
        if len(s) <= RSI_N:
            continue
        ch = s.diff()
        ag = ch.clip(lower=0).ewm(alpha=1 / RSI_N, adjust=False).mean()
        al = (-ch).clip(lower=0).ewm(alpha=1 / RSI_N, adjust=False).mean()
        r = 100 - 100 / (1 + ag / al)
        r[al == 0] = 100.0
        r.iloc[:RSI_N] = np.nan
        rsi_w.loc[s.index, c] = r
    rsi_w.index = pd.DatetimeIndex(last_sess.values)
    rsi = rsi_w.reindex(dates.union(rsi_w.index)).ffill().reindex(dates)
    return close, sharpe, rsi, quar, opn.values, low.values


def stock_supertrend_red(pq, index, sids, period=2, mult=1.0):
    """Daily per-stock Supertrend(period, mult) on each stock's own rows.
    Returns bool (T x N): True where the stock's close is below its Supertrend line
    (trend red) on that date.  Missing rows are False."""
    df = pd.read_parquet(pq, columns=["date", "sid", "high", "low", "close"])
    df = df[df.close > 0].sort_values(["sid", "date"])
    col = {s: j for j, s in enumerate(sids)}
    red = np.zeros((len(index), len(sids)), bool)
    for sid, g in df.groupby("sid", sort=False):
        n = len(g)
        if n <= period or sid not in col:
            continue
        h, l, c = g.high.values, g.low.values, g.close.values
        tr = np.empty(n)
        tr[0] = h[0] - l[0]
        tr[1:] = np.maximum.reduce([h[1:] - l[1:], abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])])
        atr = tr[:period].mean()
        fu = fl = 0.0
        up = True
        out = np.zeros(n, bool)
        for i in range(period - 1, n):
            if i >= period:
                atr = (atr * (period - 1) + tr[i]) / period
            hl2 = (h[i] + l[i]) / 2
            bu, bl = hl2 + mult * atr, hl2 - mult * atr
            if i == period - 1:
                fu, fl = bu, bl
            else:
                pc = c[i - 1]
                fu = bu if (bu < fu or pc > fu) else fu
                fl = bl if (bl > fl or pc < fl) else fl
                if up and c[i] < fl:
                    up = False
                elif not up and c[i] > fu:
                    up = True
            out[i] = not up
        idx = index.get_indexer(pd.DatetimeIndex(g.date.values))
        red[idx, col[sid]] = out
    return red


def _st_core(h, l, c, period, mult):
    """Supertrend on one bar series -> (red bool[n], up-trend lower band fl[n])."""
    n = len(c)
    red = np.zeros(n, bool)
    fl_out = np.full(n, np.nan)
    if n <= period:
        return red, fl_out
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])])
    atr = tr[:period].mean()
    fu = fl = 0.0
    up = True
    for i in range(period - 1, n):
        if i >= period:
            atr = (atr * (period - 1) + tr[i]) / period
        hl2 = (h[i] + l[i]) / 2
        bu, bl = hl2 + mult * atr, hl2 - mult * atr
        if i == period - 1:
            fu, fl = bu, bl
        else:
            pc = c[i - 1]
            fu = bu if (bu < fu or pc > fu) else fu
            fl = bl if (bl > fl or pc < fl) else fl
            if up and c[i] < fl:
                up = False
            elif not up and c[i] > fu:
                up = True
        red[i] = not up
        fl_out[i] = fl
    return red, fl_out


def stock_weekly_supertrend_exit(pq, index, sids, period=2, mult=1.0):
    """Per-stock WEEKLY Supertrend(period, mult) exit flag (T x N, daily).

    A held stock is flagged (sell at that day's close) when
      * the last completed weekly bar is red, or
      * its daily close is below the last completed week's up-trend line, or
      * it is the week's last session and that week's own bar closes red.
    """
    df = pd.read_parquet(pq, columns=["date", "sid", "high", "low", "close"])
    df = df[df.close > 0].sort_values(["sid", "date"])
    col = {s: j for j, s in enumerate(sids)}
    mon = (df.date - pd.to_timedelta(df.date.dt.weekday, unit="D")).values
    df = df.assign(wk=mon)
    flag = np.zeros((len(index), len(sids)), bool)
    for sid, g in df.groupby("sid", sort=False):
        if sid not in col or len(g) < 10:
            continue
        h, l, c = g.high.values, g.low.values, g.close.values
        _, inv = np.unique(g.wk.values, return_inverse=True)
        n = len(c)
        starts = np.r_[0, np.flatnonzero(np.diff(inv)) + 1]
        ends = np.r_[starts[1:] - 1, n - 1]
        red_w, fl_w = _st_core(np.maximum.reduceat(h, starts), np.minimum.reduceat(l, starts),
                               c[ends], period, mult)
        prev = inv - 1
        ok = prev >= 0
        ex = np.zeros(n, bool)
        pv = prev[ok]
        ex[ok] = red_w[pv] | (c[ok] < fl_w[pv])
        last = np.zeros(n, bool)
        last[ends] = True
        ex |= last & red_w[inv]
        flag[index.get_indexer(pd.DatetimeIndex(g.date.values)), col[sid]] = ex
    return flag


def supertrend_states(csv, period=4, mult=3.0):
    b = pd.read_csv(csv, parse_dates=["time"])
    b["fri"] = b.time.apply(lambda t: (t + timedelta(days=4 - t.weekday())).date())
    h, l, c = b.high.values, b.low.values, b.close.values
    n = len(b)
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np.full(n, np.nan)
    atr[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    hl2 = (h + l) / 2
    fu = np.full(n, np.nan)
    fl = np.full(n, np.nan)
    on = np.ones(n, bool)  # start risk-on
    for i in range(period - 1, n):
        bu, bl = hl2[i] + mult * atr[i], hl2[i] - mult * atr[i]
        if i == period - 1:
            fu[i], fl[i] = bu, bl
            continue
        fu[i] = bu if (bu < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl if (bl > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if on[i - 1]:
            on[i] = not (c[i] < fl[i])
        else:
            on[i] = c[i] > fu[i]
    return list(zip(b.fri, on))


# ----------------------------------------------------------------- tax
def fy_of(d):
    return d.year if d.month >= 4 else d.year - 1


class Tax:
    def __init__(self):
        self.st = {}  # fy -> realized ST net
        self.lt = {}
        self.st_layers = []  # [fy, remaining loss]
        self.lt_layers = []
        self.paid = 0.0
        self.tax_by_fy = {}

    def add(self, fy, term, pnl):
        d = self.st if term == "S" else self.lt
        d[fy] = d.get(fy, 0.0) + pnl

    def compute(self, fy, mutate):
        st, lt = self.st.get(fy, 0.0), self.lt.get(fy, 0.0)
        if st < 0 < lt:  # current-year ST loss vs LT gain
            x = min(-st, lt)
            st, lt = st + x, lt - x
        new_st = -st if st < 0 else 0.0
        new_lt = -lt if lt < 0 else 0.0
        st, lt = max(st, 0.0), max(lt, 0.0)
        sl = [list(x) for x in self.st_layers]
        ll = [list(x) for x in self.lt_layers]

        def eat(layers, gain):
            for L in sorted(layers):
                if gain <= 0:
                    break
                u = min(L[1], gain)
                L[1] -= u
                gain -= u
            return gain

        st = eat(sl, st)
        lt = eat(ll, lt)
        lt = eat(sl, lt)  # remaining ST loss vs LT gain
        tax = 0.2 * st + 0.125 * lt
        if mutate:
            if new_st > 0:
                sl.append([fy, new_st])
            if new_lt > 0:
                ll.append([fy, new_lt])
            self.st_layers = [x for x in sl if x[1] > 1e-9]
            self.lt_layers = [x for x in ll if x[1] > 1e-9]
        return tax


# ----------------------------------------------------------------- backtest
def run(pq, csv, out, st=(4, 3.0), mode="liquidate", sl_pct=0.05, gold_csv=None):
    """mode: liquidate (rulebook V5) | sl_none | sl_replace | sl_gold
    | st_exit | st_exit_filter (per-stock daily Supertrend(2,1) exit; freed cash idles)
    | stw_exit | stw_exit_filter (same on weekly bars).

    sl_*: on a risk-off flip nothing is sold; every holding gets a strict stop at
    (1 - sl_pct) x its close on the flip's signal date, tested against the daily low
    (filled at the stop, or at the open if it gaps below).  Risk-on cancels the stops
    and resumes the normal monthly strategy (no rebuild).  While risk-off, monthly
    decisions are suspended; sl_replace additionally buys the top-ranked new
    candidate(s) at T+1 close for each slot a stop frees (stop = 5% below entry).
    sl_gold: like sl_none, but each stop-out's proceeds are put into GOLDBEES (same
    day, no STT, same FIFO tax lots) and the gold is sold when risk-on resumes.  Only
    weekly gold bars exist, so gold is marked/traded at the latest completed weekly close.
    """
    close, sharpe, rsi, quar, OPN, LOW = load_signals(pq)
    states = supertrend_states(csv, *st)
    sl = mode.startswith("sl")
    dates = list(close.index.date)
    T, sids = len(dates), list(close.columns)
    C = close.values
    SH, RS, Q = sharpe.values, rsi.values, quar.values
    valid = ~np.isnan(C)
    last = pd.DataFrame(C).ffill().values  # latest available close
    N = len(sids)
    GOLD = -1
    if mode == "sl_gold":
        g = pd.read_csv(gold_csv, parse_dates=["time"])
        gf = [(t + timedelta(days=4 - t.weekday())).date() for t in g.time]
        gi = np.array([bisect_right(gf, d) - 1 for d in dates])
        gp = np.where(gi >= 0, g.close.values[np.maximum(gi, 0)], np.nan)
        GOLD = N
        sids.append("GOLDBEES")
        C = np.column_stack([C, gp])
        valid = ~np.isnan(C)
        last = pd.DataFrame(C).ffill().values
        OPN = np.column_stack([OPN, gp])
        LOW = np.column_stack([LOW, gp])
    sid_arr = np.array(sids[:N])
    st_red = None
    if mode.startswith("st_exit"):
        st_red = stock_supertrend_red(pq, close.index, sids)
    elif mode.startswith("stw_exit"):
        st_red = stock_weekly_supertrend_exit(pq, close.index, sids)
    # candidate mask: quarantine (+ red stock Supertrend when entry filter is on)
    Qsel = Q | st_red if mode.endswith("_filter") else Q

    # cash-call changes -> (signal friday, new_state)
    chg = []
    prev = None
    fri_dates = [s[0] for s in states]
    for f, on in states:
        if prev is not None and on != prev:
            chg.append((f, on))
        prev = on
    # state as of a date (bars with Friday <= date)
    def state_at(d):
        i = bisect_right(fri_dates, d) - 1
        return True if i < 0 else bool(states[i][1])

    def next_idx(d):  # first session strictly after date d
        return bisect_right(dates, d)

    def last_idx_le(d):
        return bisect_right(dates, d) - 1

    events = {}  # exec idx -> list of events
    red_sig = set()
    stops, stop_hits, st_exits = {}, 0, 0
    for f, on in chg:
        if f < dates[0]:
            continue
        sig = last_idx_le(f)
        ex = next_idx(f)
        if ex >= T:
            continue
        if on:
            plan = None if sl else select(sig, set(), SH, RS, Qsel, valid, sid_arr, True)
            events.setdefault(ex, []).append(("ON", plan))
        else:
            events.setdefault(ex, []).append(("OFF", None))
            red_sig.add(sig)
    # monthly decisions are generated on the fly (need holdings at signal date)
    monthly = {}
    by_month = {}
    for i, d in enumerate(dates):
        by_month.setdefault((d.year, d.month), []).append(i)
    for (y, m), idxs in by_month.items():
        d = date(y, m, 1)
        while d.weekday() != 4:
            d += timedelta(days=1)
        j = last_idx_le(d)
        if j >= 0 and dates[j].year == y and dates[j].month == m and j + 1 < T:
            monthly[j] = j + 1

    cash, hold, lots = CAPITAL, {}, {}
    pending = []
    tax = Tax()
    risk_on = state_at(dates[0])
    nav = np.zeros(T)
    taxpaid_day = np.zeros(T)
    trades = []
    notional = 0.0
    frags = []  # (pnl)
    monthly_plans = {}

    def px(i, k):
        return C[i, k] if valid[i, k] else last[i, k]

    def sell(i, k, qty, tag, price=None):
        nonlocal cash, notional
        d = dates[i]
        qty = min(qty, hold.get(k, 0.0))
        if qty <= 1e-12:
            return
        p = px(i, k) if price is None else price
        net = qty * p * (1 - cost_rate(d, False, k != GOLD))
        cash += net
        notional += qty * p
        remaining, fy = qty, fy_of(d)
        L = lots[k]
        while remaining > 1e-12 and L:
            lq, ld, lb = L[0]
            take = min(lq, remaining)
            frac = take / lq
            pnl = net * take / qty - lb * frac
            term = "L" if (d - ld).days > 365 else "S"
            tax.add(fy, term, pnl)
            frags.append(pnl)
            if take >= lq - 1e-12:
                L.pop(0)
            else:
                L[0] = [lq - take, ld, lb * (1 - frac)]
            remaining -= take
        hold[k] -= qty
        if hold[k] <= 1e-9:
            del hold[k]
            lots.pop(k, None)
        trades.append((d, sids[k], "SELL", tag, qty, p))

    def buy(i, k, budget, tag):
        nonlocal cash, notional
        d = dates[i]
        budget = min(budget, cash)
        if budget <= 1.0 or not valid[i, k]:
            return
        p = C[i, k]
        qty = budget / (p * (1 + cost_rate(d, True, k != GOLD)))
        cash -= budget
        notional += qty * p
        hold[k] = hold.get(k, 0.0) + qty
        lots.setdefault(k, []).append([qty, d, budget])
        trades.append((d, sids[k], "BUY", tag, qty, p))

    def equity(i):
        return cash + sum(q * px(i, k) for k, q in hold.items())

    first_inv = None
    for i in range(T):
        d = dates[i]
        if i > 0:
            cash *= 1 + RF * (d - dates[i - 1]).days / 365
        # monthly signal at close of i
        if i in monthly and state_at(d):
            monthly_plans.setdefault(monthly[i], []).append(
                ("MON", select(i, {k for k in hold if k != GOLD}, SH, RS, Qsel, valid[:, :N], sid_arr, False)))
        evs = events.get(i, []) + monthly_plans.get(i, [])
        kinds = [e[0] for e in evs]
        if st_red is not None:
            for k in list(hold):
                if st_red[i, k] and valid[i, k]:
                    sell(i, k, hold[k], "ST_EXIT")
                    st_exits += 1
        if sl:
            if "ON" in kinds:
                stops.clear()
            hit = 0
            cash0 = cash
            for k in list(hold):
                if k in stops and valid[i, k] and LOW[i, k] <= stops[k]:
                    sell(i, k, hold[k], "STOPLOSS", min(stops[k], OPN[i, k]))
                    del stops[k]
                    hit += 1
            stop_hits += hit
            if hit and mode == "sl_gold":
                buy(i, GOLD, cash - cash0, "GOLD")
            if hit and mode == "sl_replace":
                monthly_plans.setdefault(i + 1, []).append(
                    ("REPL", (hit, select(i, set(hold), SH, RS, Q, valid, sid_arr, False))))
        if sl and "OFF" in kinds:
            risk_on = False
            pending.clear()
        elif sl and "ON" in kinds:
            risk_on = True
            if GOLD in hold:
                sell(i, GOLD, hold[GOLD], "GOLD_EXIT")
        elif "OFF" in kinds:
            for k in list(hold):
                sell(i, k, hold[k], "RISKOFF")
            pending.clear()
            risk_on = False
        elif "ON" in kinds:
            risk_on = True
            pending.clear()
            eq = equity(i)
            plan = [e for e in evs if e[0] == "ON"][-1][1]
            for k in plan["buys"]:
                if valid[i, k]:
                    buy(i, k, eq / SLOTS, "REBUILD")
                else:
                    pending.append(k)
        elif "MON" in kinds and risk_on:
            plan = [e for e in evs if e[0] == "MON"][-1][1]
            eq = equity(i)
            target = eq / SLOTS
            for k in plan["sells"]:
                if k in hold:
                    sell(i, k, hold[k], "EXIT")
            for k in list(hold):
                v = hold[k] * px(i, k)
                if v > target * (1 + 1e-9):
                    sell(i, k, (v - target) / px(i, k), "TRIM")
            for k in plan["buys"]:
                if k in hold:
                    continue
                if valid[i, k]:
                    buy(i, k, target, "BUY")
                elif k not in pending:
                    pending.append(k)
            for k in sorted(hold, key=lambda x: sids[x]):
                v = hold[k] * px(i, k)
                if v < target * (1 - 1e-9) and valid[i, k]:
                    buy(i, k, target - v, "TOPUP")
        if sl and not risk_on:
            for e in evs:
                if e[0] == "REPL":
                    n, plan = e[1]
                    eq = equity(i)
                    for k in plan["buys"][:n]:
                        if valid[i, k] and k not in hold:
                            buy(i, k, eq / SLOTS, "REPLACE")
                            stops[k] = (1 - sl_pct) * C[i, k]
        if sl and i in red_sig:
            for k in hold:
                if k != GOLD:
                    stops[k] = (1 - sl_pct) * px(i, k)
        # retry pending buys (not on the day they were just queued)
        if risk_on and pending and not ("OFF" in kinds):
            eq = equity(i)
            for k in list(pending):
                if k in hold:
                    pending.remove(k)
                elif valid[i, k]:
                    buy(i, k, eq / SLOTS, "DELAYED")
                    pending.remove(k)
        # annual tax on last session of March
        if d.month == 3 and (i == T - 1 or dates[i + 1].month != 3):
            fy = fy_of(d)
            for _ in range(9):
                bill = tax.compute(fy, False)
                if cash >= bill - 1e-6:
                    break
                short = bill - cash
                hv = sum(q * px(i, k) for k, q in hold.items())
                if hv <= 0:
                    break
                frac = min(1.0, 1.35 * short / hv)
                for k in list(hold):
                    sell(i, k, hold[k] * frac, "TAXFUND")
            bill = tax.compute(fy, True)
            pay = min(bill, max(cash, 0.0))
            cash -= pay
            tax.paid += pay
            tax.tax_by_fy[fy] = pay
            taxpaid_day[i] = pay
        nav[i] = equity(i)
        if first_inv is None and hold:
            first_inv = i

    final_tax = tax.compute(fy_of(dates[-1]), False)
    tax.tax_by_fy["final_partial"] = final_tax
    nav_post = nav.copy()
    nav_post[-1] -= final_tax

    # ---- stats
    a = first_inv
    nv = nav_post[a:]
    tp = taxpaid_day[a:]
    adj = (nav[a + 1:] + tp[1:]) / nav[a:-1] - 1
    adj[-1] = (nav_post[-1] + tp[-1]) / nav[-2] - 1
    yrs = (dates[-1] - dates[a]).days / 365.25
    cagr = (nv[-1] / nv[0]) ** (1 / yrs) - 1
    vol = adj.std(ddof=1) * np.sqrt(252)
    rfd = 1.065 ** (1 / 252) - 1
    ex = adj - rfd
    sharpe_r = ex.mean() / adj.std(ddof=1) * np.sqrt(252)
    dd_dev = np.sqrt(np.mean(np.minimum(ex, 0) ** 2))
    sortino = ex.mean() * 252 / (dd_dev * np.sqrt(252))
    g = np.cumprod(1 + adj)
    g = np.concatenate([[1.0], g])
    mdd = (g / np.maximum.accumulate(g) - 1).min()
    ann_tn = g[-1] ** (1 / yrs) - 1
    calmar = ann_tn / abs(mdd)
    win = float(np.mean(np.array(frags) > 0)) if frags else float("nan")
    turnover = notional / nav[a:].mean() / yrs
    res = {
        "first_invested_date": str(dates[a]),
        "final_date": str(dates[-1]),
        "first_invested_nav": round(float(nav[a]), 2),
        "final_post_tax_value": round(float(nv[-1]), 2),
        "post_tax_cagr_pct": round(cagr * 100, 2),
        "volatility_pct": round(vol * 100, 2),
        "sharpe": round(sharpe_r, 2),
        "sortino": round(sortino, 2),
        "max_drawdown_pct": round(mdd * 100, 2),
        "calmar": round(calmar, 2),
        "fifo_win_rate_pct": round(win * 100, 2),
        "annualized_turnover_x": round(turnover, 2),
        "total_tax_paid": round(tax.paid, 2),
        "final_partial_year_tax": round(final_tax, 2),
        "mode": mode,
        "supertrend": list(st),
        "stop_loss_hits": stop_hits,
        "stock_supertrend_exits": st_exits,
        "trade_legs": len(trades),
        "cash_call_state_changes_in_window": sum(1 for f, _ in chg if f >= dates[0] and next_idx(f) < T),
    }
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "v5_summary.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame({"date": dates, "nav": nav, "nav_post_tax": nav_post}).to_csv(out / "v5_nav.csv", index=False)
    pd.DataFrame(trades, columns=["date", "security_id", "side", "tag", "qty", "price"]).to_csv(
        out / "v5_trades.csv", index=False)
    pd.Series({str(k): v for k, v in tax.tax_by_fy.items()}).to_csv(out / "v5_tax_by_fy.csv")
    print(json.dumps(res, indent=2))


def select(i, held, SH, RS, Q, valid, sid_arr, rebuild, hold_ids=None):
    """Fix the plan at signal index i. Returns dict(sells, buys) of column indices."""
    held = set() if rebuild else set(held)
    rsi, sh, q, v = RS[i], SH[i], Q[i], valid[i]
    forced = {k for k in held if q[k] or (not np.isnan(rsi[k]) and rsi[k] < RSI_EXIT)}
    surv = held - forced
    n = len(sh)
    cand = [k for k in range(n)
            if k not in held and v[k] and not q[k] and not np.isnan(sh[k])
            and not np.isnan(rsi[k]) and rsi[k] > RSI_BUY]
    pool = list(surv) + cand

    def key(k):
        return (np.isnan(sh[k]), -(0 if np.isnan(sh[k]) else sh[k]), sid_arr[k])

    pool.sort(key=key)
    rank = {k: r + 1 for r, k in enumerate(pool)}
    sells = set(forced) | {k for k in surv if rank[k] > HOLD_RANK}
    kept = len(surv) - (len(sells) - len(forced))
    free = SLOTS - kept
    buys = []
    for k in [k for k in pool if k in set(cand)][:50]:
        if len(buys) >= free:
            break
        if rank[k] <= ENTRY_RANK:
            buys.append(k)
    return {"sells": sorted(sells), "buys": buys}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "v5_out",
        (int(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (4, 3.0),
        sys.argv[6] if len(sys.argv) > 6 else "liquidate",
        gold_csv=sys.argv[7] if len(sys.argv) > 7 else None)
