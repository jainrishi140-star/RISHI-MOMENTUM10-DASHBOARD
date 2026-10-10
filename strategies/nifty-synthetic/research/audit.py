import numpy as np, pandas as pd, engine as E, runjoint as R, joint as J
f = R.f; b = R.b; c = f["c"]; days = R.days
ei, xi, dr, md, p = R.run(True, True, 2.0)
order = np.argsort(xi, kind="stable")
# 1) scale check vs TradingView screenshot
print("TV total 64,846,827 / (65*50) =", 64846827 / 3250, "pts ; / 65 =", 64846827 / 65)
d = pd.Series(p).groupby(f["day"][xi]).sum().reindex(range(len(days)), fill_value=0.0); d.index = days
for y in (2015,):
    s = d[str(y)]; eq = s.cumsum(); print(y, "maxDD pts", round((eq.cummax()-eq).max(),1), "-> x3250 =", round((eq.cummax()-eq).max()*3250), "INR vs 5L capital")
# 2) drawdown definitions
eqd = d.cumsum(); print("daily-close DD", round((eqd.cummax()-eqd).max(),1))
eqt = np.cumsum(p[order]); print("trade-by-trade DD", round((np.maximum.accumulate(eqt)-eqt).max(),1))
# mark-to-market per 15m bar (open P&L included, worst of bar low/high)
n = len(c); mtm = np.zeros(n); realized = np.zeros(n)
np.add.at(realized, xi, p); realized = np.cumsum(realized)
openpnl = np.zeros(n)
for a, z, dd_, pp in zip(ei, xi, dr, p):
    if z > a + 1:
        rng = np.arange(a + 1, z)
        worst = np.where(dd_ == 1, f["l"][rng], f["h"][rng])
        openpnl[rng] += dd_ * (worst - c[a])
eqm = realized + openpnl
print("intrabar mark-to-market DD (worst-case lows/highs)", round((np.maximum.accumulate(eqm)-eqm).max(),1))
