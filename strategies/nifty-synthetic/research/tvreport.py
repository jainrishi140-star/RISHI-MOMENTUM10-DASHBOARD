"""TradingView-style report: same data (NSE:NIFTY spot 15m), same P&L arithmetic as the Strategy Tester:
   trade P&L = (exit - entry) * dir * 65 units - commission (1 INR/unit/side), initial capital 5,00,000."""
import numpy as np, pandas as pd, engine as E, runjoint as R
from numba import njit
f = R.f; b = R.b; c = f["c"]

@njit(cache=True)
def pine_ema(x, n):  # TradingView ta.ema: seeded with the first value
    out = np.empty_like(x); a = 2.0 / (n + 1); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

# rebuild trend/HTF EMAs with TradingView seeding to confirm it does not matter
import search as S
hb = S.HB[60]; hc = hb.close.values.astype(float)
f["h60_ema_pine"] = E.htf_map(b, hb, (hc > pine_ema(hc, 50)).astype(float) * 2 - 1)
orig_ema, orig_h = E.ema, f["h60_ema"]
E.ema = pine_ema; f["h60_ema"] = f["h60_ema_pine"]
ei, xi, dr, md, p = R.run(True, True, 2.0, tvpath=True)
E.ema = orig_ema; f["h60_ema"] = orig_h
R.stats((ei, xi, dr, md, p), "Pine-seeded EMAs")

UNITS, CAP = 65, 500000.0
order = np.argsort(xi, kind="stable")
pnl_inr = p[order] * UNITS                     # cost already = 2 pts/round trip = 1 INR/unit/side
exit_t = b.ts.values[xi[order]]
eq = CAP + np.cumsum(pnl_inr); peak = np.maximum.accumulate(np.concatenate([[CAP], eq]))[1:]
dd = peak - eq; i = dd.argmax()
def block(mask, label):
    pp = pnl_inr[mask]; e = np.cumsum(pp); pk = np.maximum.accumulate(np.concatenate([[0], e]))[1:]
    gp, gl = pp[pp > 0].sum(), -pp[pp < 0].sum()
    print(f"{label:10s} trades {len(pp):5d} | net ₹{pp.sum():>12,.0f} | profitable {np.mean(pp>0):6.2%} | PF {gp/gl:5.2f} | max DD ₹{(pk-e).max():>9,.0f}")
print("\n=== Key stats (TradingView format) NSE:NIFTY 15m, 65 units/module, ₹5,00,000 ===")
print(f"Total P&L      : ₹{pnl_inr.sum():,.0f}  (+{pnl_inr.sum()/CAP:.2%})")
print(f"Max drawdown   : ₹{dd.max():,.0f}  ({dd.max()/peak[i]:.2%} of peak equity, on {pd.Timestamp(exit_t[i]).date()})")
print(f"Profitable     : {np.mean(pnl_inr>0):.2%}  ({(pnl_inr>0).sum()}/{len(pnl_inr)})")
print(f"Profit factor  : {pnl_inr[pnl_inr>0].sum()/-pnl_inr[pnl_inr<0].sum():.3f}")
yrs = pd.DatetimeIndex(exit_t).year
for y in sorted(set(yrs)): block(yrs == y, str(y))
