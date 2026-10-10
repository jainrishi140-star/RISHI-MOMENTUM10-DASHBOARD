import numpy as np, pandas as pd, runjoint as R
f = R.f; b = R.b
ei, xi, dr, md, p = R.run(True, True, 2.0)
t = pd.DataFrame(dict(module=np.where(md == 0, "TREND", "ORB"), dir=np.where(dr == 1, "LONG", "SHORT"),
                      entry_time=b.ts.values[ei] + pd.Timedelta(minutes=15), exit_time=b.ts.values[xi] + pd.Timedelta(minutes=15),
                      entry_px=f["c"][ei], pnl_pts=p.round(2)))
t = t.sort_values("entry_time")
t["year"] = t.exit_time.dt.year
d = pd.Series(p).groupby(f["day"][xi]).sum().reindex(range(len(R.days)), fill_value=0.0); d.index = R.days
def yr(g):
    pp = g.pnl_pts.values
    dd = d[str(g.name)]; eq = dd.cumsum()
    return pd.Series(dict(trades=len(pp), pts=pp.sum(), trend_pts=g[g.module=="TREND"].pnl_pts.sum(), orb_pts=g[g.module=="ORB"].pnl_pts.sum(),
                          win=(pp > 0).mean(), pf=pp[pp > 0].sum() / -pp[pp < 0].sum(), sharpe=dd.mean() / dd.std() * np.sqrt(248),
                          maxdd=(eq.cummax() - eq).max(), rs_65=pp.sum() * 65))
y = t.groupby("year").apply(yr)
print(y.round(2).to_string())
m = d.resample("ME").sum(); print("months +ve:", (m > 0).mean().round(3), "worst month", m.min().round(0), m.idxmin().date(), "best", m.max().round(0))
print("last 6 months:", m.tail(6).round(0).to_dict())
eq = d.cumsum(); print("maxDD", (eq.cummax()-eq).max(), "at", (eq.cummax()-eq).idxmax().date())
t.drop(columns="year").to_csv(f"{R.E.SCR}/data/trades_final.csv", index=False)
pd.DataFrame(dict(date=d.index.date, daily_pts=d.values, equity_pts=eq.values)).to_csv(f"{R.E.SCR}/data/equity_final.csv", index=False)
y.to_csv(f"{R.E.SCR}/data/yearly_final.csv")
