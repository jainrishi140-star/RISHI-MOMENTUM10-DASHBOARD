import numpy as np, pandas as pd, engine as E, search as S
pd.set_option("display.width", 250)
S.TFS[:] = [15, 60]
S.setup()
f = S.F[15]; c = f["c"]; b = f["bars"]; n = len(c)

def trend(stp=30, stm=3.0, ema_n=100, es=600, ee=870, sl=1.5, tp=4.0, tr=0.0, htf="h60_ema", cost=2.0):
    st = E.supertrend(f["h"], f["l"], c, stp, stm)[0]
    e = E.ema(c, ema_n) if ema_n else None
    L = st == 1; Sx = st == -1
    if e is not None: L &= c > e; Sx &= c < e
    if htf: L &= f[htf] == 1; Sx &= f[htf] == -1
    S.COST = cost
    entry_ok = (f["smin"] >= es) & (f["emin"] <= ee); eod = f["emin"] >= 915
    nan = np.full(n, np.nan)
    return E.simulate(f["o"], f["h"], f["l"], c, f["day"], entry_ok, eod, S.fresh(L), S.fresh(Sx), st == -1, st == 1,
                      f["atr14"], sl, tp, tr, nan, nan, cost, 10, True)

def orb60(cost=2.0):
    H, L_ = S.orb(f, 15, 60)
    Lc = (c > H) & (S.shift(c) <= S.shift(H)) & (f["pdc"] > f["d_ema20"])
    Sc = (c < L_) & (S.shift(c) >= S.shift(L_)) & (f["pdc"] < f["d_ema20"])
    entry_ok = (f["smin"] >= 570) & (f["emin"] <= 870); eod = f["emin"] >= 915
    nf = np.zeros(n, bool)
    return E.simulate(f["o"], f["h"], f["l"], c, f["day"], entry_ok, eod, Lc, Sc, nf, nf, H - L_, 0.0, 3.0, 0.0,
                      c - 1.5 * f["atr14"], c + 1.5 * f["atr14"], cost, 2, False)

days = b.groupby("day_id").day.first()
def daily(res):
    ei, xi, dr, p = res
    d = pd.Series(p).groupby(f["day"][xi]).sum()
    return d.reindex(range(len(days)), fill_value=0.0)

def report(name, res):
    ei, xi, dr, p = res
    t = pd.DataFrame(dict(entry=b.ts.values[ei], exit=b.ts.values[xi] + pd.Timedelta(minutes=15), dir=dr,
                          entry_px=c[ei], pnl=p))
    t["year"] = t.exit.dt.year
    y = t.groupby("year").agg(trades=("pnl", "size"), pts=("pnl", "sum"), win=("pnl", lambda s: (s > 0).mean()),
                              pf=("pnl", lambda s: s[s > 0].sum() / -s[s < 0].sum()))
    dd = daily(res); dd.index = pd.to_datetime(days.values.astype(str))
    eq = dd.cumsum(); mdd = (eq.cummax() - eq).max()
    y["sharpe"] = dd.groupby(dd.index.year).apply(lambda s: s.mean() / s.std() * np.sqrt(248))
    y["mdd"] = dd.groupby(dd.index.year).apply(lambda s: (s.cumsum().cummax() - s.cumsum()).max())
    print(f"\n### {name}: trades {len(p)} pts {p.sum():.0f} PF {p[p>0].sum()/-p[p<0].sum():.2f} win {(p>0).mean():.2%} "
          f"avg {p.mean():.1f} sharpe {dd.mean()/dd.std()*np.sqrt(248):.2f} maxDD {mdd:.0f}")
    print(y.round(2).to_string())
    return t, dd

if __name__ == "__main__":
    tA, dA = report("TREND 15m ST30/3 EMA100 H60EMA50 SL1.5 TP4", trend())
    tO, dO = report("ORB60 15m d_ema20", orb60())
    print("\ncorr daily", np.corrcoef(dA, dO)[0, 1])
    comb = dA + dO
    for nm, (a, z) in [("train", ("2015", "2021")), ("val", ("2022", "2023")), ("test", ("2024", "2025"))]:
        for lab, s in [("trend", dA), ("orb", dO), ("combo", comb)]:
            w = s[a:z]; print(nm, lab, f"sharpe {w.mean()/w.std()*np.sqrt(248):.2f} pts {w.sum():.0f}")
    print("\nCost sensitivity (trend):")
    for cst in (0, 1, 2, 3, 4, 5):
        p = trend(cost=cst)[3]; dd = daily(trend(cost=cst))
        print(cst, f"pts {p.sum():.0f} PF {p[p>0].sum()/-p[p<0].sum():.2f} sharpe {dd.mean()/dd.std()*np.sqrt(248):.2f}")
    print("\nST/exit neighbours (full-period sharpe | test sharpe):")
    for stp, stm in [(20, 3.0), (30, 3.0), (30, 2.5), (40, 3.0), (30, 3.5)]:
        for ema_n in (50, 100, 200):
            for sl, tp, tr in [(1.5, 4.0, 0), (1.5, 0, 3.0), (2.0, 5.0, 0)]:
                dd = daily(trend(stp, stm, ema_n, sl=sl, tp=tp, tr=tr)); dd.index = pd.to_datetime(days.values.astype(str))
                w = dd["2024":]
                print(stp, stm, ema_n, sl, tp, tr, f"{dd.mean()/dd.std()*np.sqrt(248):.2f} | {w.mean()/w.std()*np.sqrt(248):.2f}")
    tA.to_csv(f"{E.SCR}/data/trades_trend.csv", index=False)
    last = tA[tA.exit >= "2025-05-26"]
    print("\nLast 2 months trades:\n", last.round(2).to_string(index=False))
    print("last2m pts", last.pnl.sum())
