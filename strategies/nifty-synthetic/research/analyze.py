import sys, pandas as pd, numpy as np, glob
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 30)
S="/tmp/claude-0/-home-user-RISHI-MOMENTUM10-DASHBOARD/636b87ff-ebab-5749-9ec3-2ce77c075396/scratchpad/data"
fams = sys.argv[1:] or [p.split("res_")[1][:-4] for p in glob.glob(f"{S}/res_*.pkl")]
for fam in fams:
    df = pd.read_pickle(f"{S}/res_{fam}.pkl")
    ok = (df.train_trades >= 250) & (df.val_trades >= 70)
    d = df[ok].copy()
    d["score"] = np.minimum(d.train_sharpe, d.val_sharpe)
    d = d.sort_values("score", ascending=False)
    pcols = [c for c in df.columns if not any(c.startswith(w + "_") for w in ("train", "val", "test", "last2m"))]
    show = pcols + ["train_trades", "train_pts", "train_sharpe", "train_pf", "val_pts", "val_sharpe", "val_pf",
                    "test_trades", "test_pts", "test_sharpe", "test_pf", "test_mdd", "last2m_pts", "last2m_trades"]
    print(f"===== {fam}: {len(df)} combos, {ok.sum()} eligible; score>1: {(d.score>1).sum()}; "
          f"of those test_sharpe>0: {((d.score>1)&(d.test_sharpe>0)).sum()}")
    print(d[show].head(25).round(2).to_string(index=False))
