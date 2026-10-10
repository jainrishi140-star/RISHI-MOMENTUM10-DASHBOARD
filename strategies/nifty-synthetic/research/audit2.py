import numpy as np, pandas as pd, engine as E, runjoint as R
f = R.f; b = R.b; c = f["c"]
m = E.m1()
# price of the 1-min bar that STARTS when the 15m signal bar closes (i.e. execute one minute late)
key1 = pd.Series(m.close.values, index=pd.MultiIndex.from_arrays([m.index.date, m.index.hour * 60 + m.index.minute]))
keyo = pd.Series(m.open.values, index=key1.index)
dup = key1.index.duplicated(); print("duplicate minute keys:", dup.sum()); key1 = key1[~dup]; keyo = keyo[~dup]
idx = pd.MultiIndex.from_arrays([b.day.values, b.end_min.values])
nxt_close = key1.reindex(idx).values; nxt_open = keyo.reindex(idx).values
nxt_close = np.where(np.isnan(nxt_close), c, nxt_close); nxt_open = np.where(np.isnan(nxt_open), c, nxt_open)
print("mean |next-1m-open - close| pts:", np.nanmean(np.abs(nxt_open - c)).round(2))
for lab, fl in [("fill @ signal close (Pine)", None), ("fill @ next 1m OPEN", nxt_open), ("fill @ next 1m CLOSE (1 min late)", nxt_close)]:
    for cost in (2.0, 3.0):
        R.stats(R.run(True, True, cost, fill=fl), f"{lab[:26]} c={cost}")
