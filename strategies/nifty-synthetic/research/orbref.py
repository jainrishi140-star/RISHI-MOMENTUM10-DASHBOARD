import itertools, time, numpy as np, pandas as pd
from multiprocessing import Pool
import engine as E, search as S

OTF = [5, 15]
def setup():
    S.TFS[:] = [5, 15, 60]
    S.setup()
    for tf in OTF:
        f = S.F[tf]; b = f["bars"]
        d = b.groupby("day_id").agg(c=("close", "last")); dc = d.c.values.astype(float)
        for n in (10, 50):
            f[f"d_ema{n}"] = E.daily_map(b, E.ema(dc, n))
        f["st15"] = E.supertrend(f["h"], f["l"], f["c"], 10, 3.0)[0]

def task(arg):
    tf, mins = arg
    f = S.F[tf]; c = f["c"]; n = len(c)
    H0, L0 = S.orb(f, tf, mins); width = H0 - L0
    rows = []
    biases = {"none": (np.ones(n, bool), np.ones(n, bool))}
    for k in ("d_ema10", "d_ema20", "d_ema50"):
        biases[k] = (f["pdc"] > f[k], f["pdc"] < f[k])
    biases["h60_st"] = (f["h60_st"] == 1, f["h60_st"] == -1)
    biases["d20+h60"] = (biases["d_ema20"][0] & biases["h60_st"][0], biases["d_ema20"][1] & biases["h60_st"][1])
    biases["d20+ema200"] = (biases["d_ema20"][0] & (c > f["ema200"]), biases["d_ema20"][1] & (c < f["ema200"]))
    for buf in (0.0, 0.05):
        H = H0 + buf * f["d_atr"]; L_ = L0 - buf * f["d_atr"]
        brk_l = (c > H) & (S.shift(c) <= S.shift(H)); brk_s = (c < L_) & (S.shift(c) >= S.shift(L_))
        for bname, (bl, bs) in biases.items():
            Lc = brk_l & bl; Sc = brk_s & bs
            for ee, maxt, stop, tpR, stx in itertools.product([780, 840, 870], [1, 2], ["range", "mid", "atr1.5", "atr2"],
                                                               [0, 2.0, 3.0], [False, True]):
                if stop == "range": slp, ssp = L0, H0
                elif stop == "mid": slp = ssp = (H0 + L0) / 2
                else:
                    m = float(stop[3:]); slp, ssp = c - m * f["atr14"], c + m * f["atr14"]
                f["__w"] = width
                lx = f["st15"] == -1 if stx else np.zeros(n, bool)
                sx = f["st15"] == 1 if stx else np.zeros(n, bool)
                res = S.evaluate(tf, Lc, Sc, lx, sx, 0.0, tpR, 0.0, maxt, False, 570, ee, sl_lp=slp, sl_sp=ssp, atrkey="__w")
                row = dict(tf=tf, mins=mins, buf=buf, bias=bname, ee=ee, maxt=maxt, stop=stop, tpR=tpR, stx=stx)
                for w, mm in res.items():
                    for k, v in mm.items(): row[f"{w}_{k}"] = v
                rows.append(row)
    return rows

if __name__ == "__main__":
    t0 = time.time(); setup(); print("setup", time.time() - t0, flush=True)
    rows = []
    with Pool(4) as p:
        for ch in p.imap_unordered(task, [(tf, m) for tf in OTF for m in (45, 60, 75, 90)]):
            rows += ch; print(len(rows), time.time() - t0, flush=True)
    pd.DataFrame(rows).to_pickle(f"{E.SCR}/data/res_orbref.pkl"); print("done", len(rows))
