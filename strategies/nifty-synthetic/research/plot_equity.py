import sys, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
src, out = sys.argv[1], sys.argv[2]
d = pd.read_csv(src, parse_dates=["date"]).set_index("date")
eq = d.equity_pts; dd = eq - eq.cummax()
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e",
                     "xtick.color": "#52514e", "ytick.color": "#52514e"})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw=dict(height_ratios=[3, 1], hspace=0.08))
fig.patch.set_facecolor("#fcfcfb")
for a in (a1, a2):
    a.set_facecolor("#fcfcfb"); a.grid(axis="y", color="#e6e5e0", lw=0.8); a.spines[["top", "right"]].set_visible(False)
a1.plot(eq.index, eq.values, color="#2a78d6", lw=2)
for x0, lab in [("2022-01-01", "validation"), ("2024-01-01", "out-of-sample")]:
    for a in (a1, a2): a.axvline(pd.Timestamp(x0), color="#9b9a93", lw=1, ls="--")
    a1.text(pd.Timestamp(x0), eq.max() * 0.04, f" {lab} →", color="#52514e", va="bottom")
a1.text(eq.index[-1], eq.iloc[-1], f"  {eq.iloc[-1]:,.0f} pts", color="#0b0b0b", va="center")
a1.set_ylabel("Cumulative P&L (index points)")
a1.set_title("NIFTY synthetic futures · Trend + IB breakout (15m) · net of 2 pts/round trip, 1 lot per module",
             loc="left", color="#0b0b0b")
a2.fill_between(dd.index, dd.values, 0, color="#e34948", alpha=0.35, lw=0)
a2.plot(dd.index, dd.values, color="#e34948", lw=1)
a2.set_ylabel("Drawdown (pts)")
fig.savefig(out, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
