import sys, itertools, time, numpy as np, pandas as pd
from multiprocessing import Pool
import engine as E, search as S

RTF = [10, 15, 30]
STS = [(10, 3.0), (14, 2.5), (20, 3.0), (14, 3.0), (20, 2.5), (30, 3.0)]
EXITS = [(0, 0, 0), (1.5, 0, 0), (2.5, 0, 0), (0, 0, 2.0), (0, 0, 3.0), (1.5, 4.0, 0), (1.5, 0, 3.0)]

def setup():
    S.TFS[:] = RTF
    S.setup.__globals__["TFS"] = RTF
    S.setup()
    for tf in RTF:
        f = S.F[tf]
        for p, m in STS:
            f[f"st{p}_{m}"] = E.supertrend(f["h"], f["l"], f["c"], p, m)[0]

def task(arg):
    tf, stp = arg
    f = S.F[tf]; c = f["c"]; st = f[f"st{stp[0]}_{stp[1]}"]
    rows = []
    for ema_f, macd_f, htf_f in itertools.product([None, "ema50", "ema100", "ema200"], [False, True],
                                                  [None, "h60_ema", "h60_st", "daily"]):
        L = st == 1; Sx = st == -1
        if ema_f: L = L & (c > f[ema_f]); Sx = Sx & (c < f[ema_f])
        if macd_f: L = L & (f["macdh"] > 0); Sx = Sx & (f["macdh"] < 0)
        if htf_f == "daily": L = L & (f["pdc"] > f["d_ema20"]); Sx = Sx & (f["pdc"] < f["d_ema20"])
        elif htf_f: L = L & (f[htf_f] == 1); Sx = Sx & (f[htf_f] == -1)
        for mode in ("fresh", "state"):
            ls, ss = (S.fresh(L), S.fresh(Sx)) if mode == "fresh" else (L, Sx)
            for es, ee in [(570, 810), (570, 870), (600, 810), (600, 870)]:
                for sl, tp, tr in EXITS:
                    res = S.evaluate(tf, ls, ss, st == -1, st == 1, sl, tp, tr, 3 if mode == "state" else 10, True, es, ee)
                    row = dict(tf=tf, st=f"{stp[0]}_{stp[1]}", ema=ema_f, macd=macd_f, htf=htf_f, mode=mode,
                               es=es, ee=ee, sl=sl, tp=tp, trail=tr)
                    for w, m in res.items():
                        for k, v in m.items(): row[f"{w}_{k}"] = v
                    rows.append(row)
    return rows

if __name__ == "__main__":
    t0 = time.time(); setup(); print("setup", time.time() - t0, flush=True)
    rows = []
    with Pool(4) as p:
        for ch in p.imap_unordered(task, [(tf, s) for tf in RTF for s in STS]):
            rows += ch; print(len(rows), time.time() - t0, flush=True)
    pd.DataFrame(rows).to_pickle(f"{E.SCR}/data/res_refine.pkl"); print("done", len(rows))
