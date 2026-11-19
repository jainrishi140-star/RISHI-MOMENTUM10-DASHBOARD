import pandas as pd, numpy as np, sys
S=sys.argv[1]
df=pd.read_csv(f"{S}/data/nifty1m.csv", parse_dates=['date'])
print(len(df), df.date.min(), df.date.max())
df=df.drop_duplicates('date').sort_values('date').set_index('date')
t=df.index.time
print("time range", min(t), max(t))
d=df.groupby(df.index.date).size()
print("days",len(d)); print(d.describe()); print(d[d<300].tail(20))
bad=(df.high<df[['open','close']].max(1))|(df.low>df[['open','close']].min(1))
print("bad ohlc", bad.sum())
r=df.close.pct_change().abs(); print(r.sort_values().tail(10))
df[['open','high','low','close']].to_pickle(f"{S}/data/m1.pkl")
