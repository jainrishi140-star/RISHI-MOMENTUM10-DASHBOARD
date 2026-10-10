"""Exact replica of the Pine execution model for the 2-module strategy."""
import numpy as np, pandas as pd
from numba import njit
import engine as E

@njit(cache=True)
def joint(o, h, l, c, day, eod, t_ok, tL, tS, tLx, tSx, o_ok, oL, oS, atr, o_tpd,
          t_sl, t_tp, o_slm, o_tpR, cost, use_t, use_o, o_max):
    n = len(c)
    out_ei = np.empty(2 * n, np.int64); out_xi = np.empty(2 * n, np.int64)
    out_dir = np.empty(2 * n, np.int64); out_mod = np.empty(2 * n, np.int64); out_p = np.empty(2 * n); k = 0
    # lot state: [dir, entry, stop, tgt, eidx]
    td = 0; te = 0.0; ts_ = 0.0; tt = 0.0; tei = 0
    od = 0; oe = 0.0; os_ = 0.0; ot = 0.0; oei = 0
    t_pend = 0; o_cnt = 0; cur = -1
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; o_cnt = 0; t_pend = 0
        # intrabar stops / targets
        if td != 0 and i > tei:
            xp = np.nan
            if td == 1:
                if l[i] <= ts_: xp = min(o[i], ts_)
                elif h[i] >= tt: xp = max(o[i], tt)
            else:
                if h[i] >= ts_: xp = max(o[i], ts_)
                elif l[i] <= tt: xp = min(o[i], tt)
            if not np.isnan(xp):
                out_ei[k] = tei; out_xi[k] = i; out_dir[k] = td; out_mod[k] = 0; out_p[k] = td * (xp - te) - cost; k += 1; td = 0
        if od != 0 and i > oei:
            xp = np.nan
            if od == 1:
                if l[i] <= os_: xp = min(o[i], os_)
                elif h[i] >= ot: xp = max(o[i], ot)
            else:
                if h[i] >= os_: xp = max(o[i], os_)
                elif l[i] <= ot: xp = min(o[i], ot)
            if not np.isnan(xp):
                out_ei[k] = oei; out_xi[k] = i; out_dir[k] = od; out_mod[k] = 1; out_p[k] = od * (xp - oe) - cost; k += 1; od = 0
        net = td + od  # position at script execution (before this bar's orders)
        # close-of-bar exits
        if td != 0 and (eod[i] or (td == 1 and tLx[i]) or (td == -1 and tSx[i])):
            out_ei[k] = tei; out_xi[k] = i; out_dir[k] = td; out_mod[k] = 0; out_p[k] = td * (c[i] - te) - cost; k += 1; td = 0
        if od != 0 and eod[i]:
            out_ei[k] = oei; out_xi[k] = i; out_dir[k] = od; out_mod[k] = 1; out_p[k] = od * (c[i] - oe) - cost; k += 1; od = 0
        if eod[i]:
            continue
        # trend entries: fresh confluence, or a signal blocked last bar (opposite position) while confluence holds
        if t_pend == 1 and not tL[i]: t_pend = 0
        if t_pend == -1 and not tS[i]: t_pend = 0
        if use_t and td == 0 and t_ok[i]:
            d = 0
            if tL[i] and (i == 0 or not tL[i - 1]): d = 1
            elif tS[i] and (i == 0 or not tS[i - 1]): d = -1
            elif t_pend != 0: d = t_pend
            if d != 0:
                if net * d < 0:
                    t_pend = d
                else:
                    td = d; te = c[i]; tei = i; t_pend = 0
                    ts_ = c[i] - d * t_sl * atr[i]; tt = c[i] + d * t_tp * atr[i]
        # ORB entries
        if use_o and od == 0 and o_ok[i] and o_cnt < o_max:
            d = 1 if oL[i] else (-1 if oS[i] else 0)
            if d != 0 and net * d >= 0:
                od = d; oe = c[i]; oei = i; o_cnt += 1
                os_ = c[i] - d * o_slm * atr[i]; ot = c[i] + d * o_tpR * o_tpd[i]
    return out_ei[:k], out_xi[:k], out_dir[:k], out_mod[:k], out_p[:k]
