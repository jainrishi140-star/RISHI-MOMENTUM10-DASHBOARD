import pandas as pd, numpy as np, sys
pd.set_option("display.width", 250)
S="/tmp/claude-0/-home-user-RISHI-MOMENTUM10-DASHBOARD/636b87ff-ebab-5749-9ec3-2ce77c075396/scratchpad/data"
df = pd.read_pickle(f"{S}/res_{sys.argv[1]}.pkl")
df["score"] = np.minimum(df.train_sharpe, df.val_sharpe)
pcols = sys.argv[2].split(",")
df = df.fillna({c: "none" for c in pcols if df[c].dtype == object})
# neighborhood score: for each param, mean score of configs differing only in that param
base = df.set_index(pcols)
nb = []
for p in pcols:
    others = [c for c in pcols if c != p]
    g = df.groupby(others)["score"].transform("mean")
    nb.append(g.values)
df["nbhd"] = np.mean(nb, axis=0)
df["rank_score"] = 0.5 * df.score + 0.5 * df.nbhd
cols = pcols + ["score", "nbhd", "train_sharpe", "val_sharpe", "test_sharpe", "test_pts", "test_pf", "test_mdd", "last2m_pts", "train_trades"]
print(df.sort_values("rank_score", ascending=False)[cols].head(20).round(2).to_string(index=False))
