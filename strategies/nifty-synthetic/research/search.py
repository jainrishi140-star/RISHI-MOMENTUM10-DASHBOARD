"""Grid search across indicator families / timeframes. Writes results to results_<family>.pkl"""
import sys, itertools, time, numpy as np, pandas as pd
from multiprocessing import Pool
import engine as E

COST = 2.0
TRAIN = ("2015-01-01", "2021-12-31"); VAL = ("2022-01-01", "2023-12-31"); TEST = ("2024-01-01", "2025-12-31")
TFS = [3, 5, 15, 30, 60]

F = {}  # tf -> features dict

def build(tf):
    b = E.resample(tf)
    o, h, l, c = (b[k].values.astype(np.float64) for k in ("open", "high", "low", "close"))
    f = dict(bars=b, o=o, h=h, l=l, c=c, day=b.day_id.values, smin=b.start_min.values, emin=b.end_min.values)
    f["atr14"] = E.atr(h, l, c, 14)
    for n in (9, 20, 50, 100, 200):
        f[f"ema{n}"] = E.ema(c, n)
    for p, m in [(7, 2.0), (10, 2.0), (10, 3.0), (14, 2.5), (10, 1.5), (20, 3.0)]:
        f[f"st{p}_{m}"] = E.supertrend(h, l, c, p, m)[0]
    f["rsi14"] = E.rsi(c, 14); f["rsi2"] = E.rsi(c, 2); f["rsi7"] = E.rsi(c, 7)
    f["macdh"] = E.macd(c)[2]
    f["adx"], f["pdi"], f["mdi"] = E.adx(h, l, c, 14)
    sma20 = pd.Series(c).rolling(20).mean().values; sd20 = pd.Series(c).rolling(20).std(ddof=0).values
    f["bbm"], f["bbu"], f["bbl"] = sma20, sma20 + 2 * sd20, sma20 - 2 * sd20
    # ribbon alignment
    r = [E.ema(c, n) for n in (8, 13, 21, 34, 55)]
    f["rib_up"] = (r[0] > r[1]) & (r[1] > r[2]) & (r[2] > r[3]) & (r[3] > r[4])
    f["rib_dn"] = (r[0] < r[1]) & (r[1] < r[2]) & (r[2] < r[3]) & (r[3] < r[4])
    # daily features (previous completed day)
    d = b.groupby("day_id").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"), o=("open", "first"))
    dc = d.c.values.astype(float)
    f["pdh"] = E.daily_map(b, d.h.values); f["pdl"] = E.daily_map(b, d.l.values); f["pdc"] = E.daily_map(b, dc)
    f["d_ema20"] = E.daily_map(b, E.ema(dc, 20)); f["d_ema50"] = E.daily_map(b, E.ema(dc, 50))
    f["d_atr"] = E.daily_map(b, E.atr(d.h.values.astype(float), d.l.values.astype(float), dc, 14))
    f["dopen"] = d.o.values[b.day_id.values]
    return f

def add_htf(f, tf):
    b = f["bars"]
    for htf in (15, 60):
        if htf <= tf:
            continue
        hb = HB[htf]
        h, l, c = hb.high.values.astype(float), hb.low.values.astype(float), hb.close.values.astype(float)
        f[f"h{htf}_st"] = E.htf_map(b, hb, E.supertrend(h, l, c, 10, 3.0)[0])
        f[f"h{htf}_ema"] = E.htf_map(b, hb, (c > E.ema(c, 50)).astype(float) * 2 - 1)

def orb(f, tf, mins):
    m = E.m1()
    mm = m.index.hour * 60 + m.index.minute
    sub = m[mm < 555 + mins]
    g = sub.groupby(sub.index.date)
    hi, lo = g.high.max(), g.low.min()
    b = f["bars"]
    days = pd.Index(b.day.values)
    H = hi.reindex(days).values; L = lo.reindex(days).values
    ready = b.start_min.values >= 555 + mins
    H = np.where(ready, H, np.nan); L = np.where(ready, L, np.nan)
    return H, L

def shift(x):
    y = np.empty_like(x); y[0] = False if x.dtype == bool else np.nan; y[1:] = x[:-1]; return y

def fresh(cond):
    return cond & ~shift(cond)

WIN = {}

def evaluate(tf, lsig, ssig, lexit, sexit, sl, tp, trail, maxt, rev, es=570, ee=870,
           sl_lp=None, sl_sp=None, atrkey="atr14"):
    f = F[tf]
    n = len(f["c"])
    entry_ok = (f["smin"] >= es) & (f["emin"] <= ee)
    eod = f["emin"] >= 915
    nanarr = np.full(n, np.nan)
    ei, xi, dr, pnl = E.simulate(f["o"], f["h"], f["l"], f["c"], f["day"], entry_ok, eod,
                                lsig, ssig, lexit, sexit, f[atrkey], sl, tp, trail,
                                nanarr if sl_lp is None else sl_lp, nanarr if sl_sp is None else sl_sp,
                                COST, maxt, rev)
    xday = f["day"][xi]
    out = {}
    for name, (a, z) in WIN.items():
        da = WIN_DAYS[name]
        msk = (xday >= da[0]) & (xday <= da[-1])
        out[name] = E.metrics(pnl[msk], xday[msk], da)
    return out

# ----------------------------------------------------------------------------- families
def fam_supertrend(tfs):
    for tf in tfs:
        f = F[tf]
        for stk in [k for k in f if k.startswith("st")]:
            st = f[stk]
            for ema_f, rsi_f, macd_f, adx_f, htf_f in itertools.product(
                    [None, "ema50", "ema200"], [False, True], [False, True], [0, 20],
                    [None] + [k for k in f if k.endswith("_st") or k.endswith("_ema")] + ["daily"]):
                L = st == 1; S = st == -1
                if ema_f: L = L & (f["c"] > f[ema_f]); S = S & (f["c"] < f[ema_f])
                if rsi_f: L = L & (f["rsi14"] > 50); S = S & (f["rsi14"] < 50)
                if macd_f: L = L & (f["macdh"] > 0); S = S & (f["macdh"] < 0)
                if adx_f: L = L & (f["adx"] > adx_f); S = S & (f["adx"] > adx_f)
                if htf_f == "daily": L = L & (f["pdc"] > f["d_ema20"]); S = S & (f["pdc"] < f["d_ema20"])
                elif htf_f: L = L & (f[htf_f] == 1); S = S & (f[htf_f] == -1)
                lsig, ssig = fresh(L), fresh(S)
                for sl, tp in [(0, 0), (1.5, 0), (1.5, 3.0), (2.5, 0), (1.0, 2.0)]:
                    yield (dict(fam="ST", tf=tf, st=stk, ema=ema_f, rsi=rsi_f, macd=macd_f, adx=adx_f,
                                htf=htf_f, sl=sl, tp=tp),
                           (tf, lsig, ssig, st == -1, st == 1, sl, tp, 0.0, 10, True))

def fam_emacross(tfs):
    for tf in tfs:
        f = F[tf]; c = f["c"]
        for fa, sa in [(5, 13), (9, 21), (13, 34), (20, 50), (9, 50)]:
            ef, es_ = E.ema(c, fa), E.ema(c, sa)
            up = ef > es_
            for rib, rsi_f, htf_f, adx_f in itertools.product([False, True], [False, True],
                    [None] + [k for k in f if k.endswith("_st")] + ["daily"], [0, 20]):
                L = up.copy(); S = ~up
                if rib: L &= f["rib_up"]; S &= f["rib_dn"]
                if rsi_f: L &= f["rsi14"] > 55; S &= f["rsi14"] < 45
                if adx_f: L &= f["adx"] > adx_f; S &= f["adx"] > adx_f
                if htf_f == "daily": L &= f["pdc"] > f["d_ema20"]; S &= f["pdc"] < f["d_ema20"]
                elif htf_f: L &= f[htf_f] == 1; S &= f[htf_f] == -1
                lsig, ssig = fresh(L), fresh(S)
                for sl, tp, tr in [(0, 0, 0), (1.5, 0, 0), (1.5, 3.0, 0), (0, 0, 2.0), (2.0, 4.0, 0)]:
                    yield (dict(fam="EMAX", tf=tf, fast=fa, slow=sa, rib=rib, rsi=rsi_f, htf=htf_f, adx=adx_f,
                                sl=sl, tp=tp, trail=tr),
                           (tf, lsig, ssig, ~up, up, sl, tp, tr, 10, True))

def fam_orb(tfs):
    for tf in tfs:
        if tf not in F: continue
        f = F[tf]; c = f["c"]
        for mins in [15, 30, 45, 60]:
            if mins < tf: continue
            H, L_ = orb(f, tf, mins)
            width = H - L_
            for flt, wmax, ee, maxt in itertools.product(
                    [None, "daily", "ema50", "h60_st", "vwapish"], [0, 0.6], [690, 780, 870], [1, 2]):
                Lc = (c > H) & (shift(c) <= shift(H) if True else True)
                Sc = (c < L_) & (shift(c) >= shift(L_))
                if flt == "daily": Lc &= f["pdc"] > f["d_ema20"]; Sc &= f["pdc"] < f["d_ema20"]
                elif flt == "vwapish": Lc &= c > f["dopen"]; Sc &= c < f["dopen"]
                elif flt and flt in f:
                    if flt.endswith("_st"): Lc &= f[flt] == 1; Sc &= f[flt] == -1
                    else: Lc &= c > f[flt]; Sc &= c < f[flt]
                elif flt: continue
                if wmax: ok = width < wmax * f["d_atr"]; Lc &= ok; Sc &= ok
                nf = np.zeros(len(c), bool)
                for stop_mode, tp in itertools.product(["range", "mid", "atr1.5"], [0, 1.0, 2.0, 3.0]):
                    if stop_mode == "range": slp, ssp, sl = L_, H, 0
                    elif stop_mode == "mid": slp, ssp, sl = (H + L_) / 2, (H + L_) / 2, 0
                    else: slp, ssp, sl = None, None, 1.5
                    # tp as R-multiple of OR width -> convert to ATR multiple approx not possible; use width
                    yield (dict(fam="ORB", tf=tf, mins=mins, flt=flt, wmax=wmax, ee=ee, maxt=maxt,
                                stop=stop_mode, tpR=tp),
                           ("ORB", tf, Lc, Sc, nf, nf, sl, tp, maxt, ee, slp, ssp, width))

def fam_pdhl(tfs):
    for tf in tfs:
        f = F[tf]; c = f["c"]
        for flt, ee, maxt, buf in itertools.product([None, "daily", "h60_st", "ema50"], [780, 870], [1, 2], [0.0, 0.1]):
            H = f["pdh"] + buf * f["d_atr"]; L_ = f["pdl"] - buf * f["d_atr"]
            Lc = (c > H) & (shift(c) <= shift(H)); Sc = (c < L_) & (shift(c) >= shift(L_))
            if flt == "daily": Lc &= f["pdc"] > f["d_ema20"]; Sc &= f["pdc"] < f["d_ema20"]
            elif flt == "ema50": Lc &= c > f["ema50"]; Sc &= c < f["ema50"]
            elif flt: Lc &= f[flt] == 1; Sc &= f[flt] == -1
            nf = np.zeros(len(c), bool)
            for sl, tp, tr in [(1.0, 0, 0), (1.5, 0, 0), (1.5, 3.0, 0), (1.0, 3.0, 0), (0, 0, 2.0), (1.0, 0, 1.5)]:
                yield (dict(fam="PDHL", tf=tf, flt=flt, ee=ee, maxt=maxt, buf=buf, sl=sl, tp=tp, trail=tr),
                       (tf, Lc, Sc, nf, nf, sl, tp, tr, maxt, True, 570, ee))

def fam_meanrev(tfs):
    for tf in tfs:
        f = F[tf]; c = f["c"]
        for rk, lo, adxmax, bb in itertools.product(["rsi2", "rsi7", "rsi14"], [10, 20, 30], [0, 20, 25], [False, True]):
            if rk == "rsi14" and lo < 20: continue
            if rk == "rsi2" and lo > 20: continue
            L = f[rk] < lo; S = f[rk] > 100 - lo
            if bb: L &= c < f["bbl"]; S &= c > f["bbu"]
            if adxmax: L &= f["adx"] < adxmax; S &= f["adx"] < adxmax
            lsig, ssig = fresh(L), fresh(S)
            for ex in ["mid", "rsi50"]:
                lx = c > f["bbm"] if ex == "mid" else f[rk] > 50
                sx = c < f["bbm"] if ex == "mid" else f[rk] < 50
                for sl in [1.0, 2.0, 3.0]:
                    yield (dict(fam="MR", tf=tf, rk=rk, lo=lo, adxmax=adxmax, bb=bb, ex=ex, sl=sl),
                           (tf, lsig, ssig, lx, sx, sl, 0.0, 0.0, 5, False))

def run_job(job):
    params, a = job
    if a[0] == "ORB":
        _, tf, Lc, Sc, nf, _, sl, tpR, maxt, ee, slp, ssp, width = a
        # implement R-multiple target via custom atr array: use width as "atr" with tp multiple
        f = F[tf]
        key = f"__w{tf}"
        F[tf][key] = width  # same for given mins within this process
        if sl > 0:
            res = evaluate(tf, Lc, Sc, nf, nf, 0.0, tpR, 0.0, maxt, False, 570, ee,
                           sl_lp=f["c"] - 1.5 * f["atr14"], sl_sp=f["c"] + 1.5 * f["atr14"], atrkey=key)
        else:
            res = evaluate(tf, Lc, Sc, nf, nf, 0.0, tpR, 0.0, maxt, False, 570, ee,
                           sl_lp=slp, sl_sp=ssp, atrkey=key)
    elif len(a) == 12:
        tf, L, S, lx, sx, sl, tp, tr, maxt, rev, es, ee = a
        res = evaluate(tf, L, S, lx, sx, sl, tp, tr, maxt, rev, es, ee)
    else:
        tf, L, S, lx, sx, sl, tp, tr, maxt, rev = a
        res = evaluate(tf, L, S, lx, sx, sl, tp, tr, maxt, rev)
    row = dict(params)
    for w, m in res.items():
        for k, v in m.items():
            row[f"{w}_{k}"] = v
    return row

def task(arg):
    fam, tf = arg
    gen = dict(st=fam_supertrend, ema=fam_emacross, orb=fam_orb, pdhl=fam_pdhl, mr=fam_meanrev)[fam]
    return [run_job(j) for j in gen([tf])]

def setup():
    global HB, WIN_DAYS
    days = E.resample(60)[["day", "day_id"]].drop_duplicates()
    dd = pd.to_datetime(days.day.astype(str))
    WIN.update(train=TRAIN, val=VAL, test=TEST, last2m=("2025-05-26", "2025-07-31"))
    WIN_DAYS = {k: days.day_id.values[(dd >= a) & (dd <= z)] for k, (a, z) in WIN.items()}
    HB = {t: E.resample(t) for t in (15, 60)}
    for tf in TFS + [1]:
        F[tf] = build(tf); add_htf(F[tf], tf)

if __name__ == "__main__":
    fam = sys.argv[1]
    t0 = time.time(); setup(); print("setup", time.time() - t0, flush=True)
    gen = dict(st=fam_supertrend, ema=fam_emacross, orb=fam_orb, pdhl=fam_pdhl, mr=fam_meanrev)[fam]
    tfs = dict(st=TFS, ema=TFS, orb=[1, 3, 5, 15], pdhl=[3, 5, 15], mr=[3, 5, 15])[fam]
    rows = []
    with Pool(4) as p:
        for chunk in p.imap_unordered(task, [(fam, tf) for tf in sorted(tfs)]):
            rows += chunk
            print(len(rows), time.time() - t0, flush=True)
    df = pd.DataFrame(rows)
    df.to_pickle(f"{E.SCR}/data/res_{fam}.pkl")
    print("done", len(df), time.time() - t0)
