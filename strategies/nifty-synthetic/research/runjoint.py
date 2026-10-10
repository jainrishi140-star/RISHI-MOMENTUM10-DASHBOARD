import numpy as np, pandas as pd, engine as E, search as S, joint as J
pd.set_option("display.width", 250)
S.TFS[:] = [15, 60]; S.setup()
f = S.F[15]; c = f["c"]; b = f["bars"]; n = len(c)
days = pd.to_datetime(b.groupby("day_id").day.first().values.astype(str))

def build(stp=30, stm=3.0, ema_n=100, es=600, ee=870):
    st = E.supertrend(f["h"], f["l"], c, stp, stm)[0]
    e = E.ema(c, ema_n)
    L = (st == 1) & (c > e) & (f["h60_ema"] == 1); Sx = (st == -1) & (c < e) & (f["h60_ema"] == -1)
    H, L_ = S.orb(f, 15, 60)
    oL = (c > H) & (S.shift(c) <= S.shift(H)) & (f["pdc"] > f["d_ema20"])
    oS = (c < L_) & (S.shift(c) >= S.shift(L_)) & (f["pdc"] < f["d_ema20"])
    t_ok = (f["smin"] >= es) & (f["emin"] <= ee); o_ok = (f["smin"] >= 570) & (f["emin"] <= 870)
    return st, L, Sx, oL, oS, t_ok, o_ok, np.nan_to_num(H - L_)

def run(use_t=True, use_o=True, cost=2.0, **kw):
    st, L, Sx, oL, oS, t_ok, o_ok, w = build(**kw)
    eod = f["emin"] >= 915
    return J.joint(f["o"], f["h"], f["l"], c, f["day"], eod, t_ok, L, Sx, st == -1, st == 1, o_ok, oL, oS,
                   f["atr14"], w, 1.5, 4.0, 1.5, 3.0, cost, use_t, use_o, 2)

def stats(res, label):
    ei, xi, dr, md, p = res
    d = pd.Series(p).groupby(f["day"][xi]).sum().reindex(range(len(days)), fill_value=0.0); d.index = days
    eq = d.cumsum(); mdd = (eq.cummax() - eq).max()
    sh = lambda s: s.mean() / s.std() * np.sqrt(248)
    print(f"{label:28s} trades {len(p):5d} pts {p.sum():8.0f} PF {p[p>0].sum()/-p[p<0].sum():.2f} win {(p>0).mean():.1%} "
          f"sharpe {sh(d):.2f} | train {sh(d[:'2021']):.2f} val {sh(d['2022':'2023']):.2f} test {sh(d['2024':]):.2f} "
          f"| maxDD {mdd:.0f} | last2m {d['2025-05-26':].sum():.0f}")
    return d

if __name__ == "__main__":
    for cost in (2.0, 3.0):
        print(f"--- cost {cost} pts/round trip")
        stats(run(True, False, cost), "TREND only (pine model)")
        stats(run(False, True, cost), "ORB only (pine model)")
        dj = stats(run(True, True, cost), "TREND+ORB joint")
