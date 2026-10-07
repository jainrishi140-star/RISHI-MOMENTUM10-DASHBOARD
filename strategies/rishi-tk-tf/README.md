# Rishi TK TF

**Two names, used everywhere in this folder:**

| Name | What it is |
|------|------------|
| **TK TF Original System** | The vendor's locked TradingView indicator (TK ALGO V1.1, "TK TF"). We never change it. It is only the benchmark: its exports and trade logs are the reference everything is compared with. |
| **Rishi TK TF** | Our in-house system, built by reverse-engineering the TK TF Original System. **All changes and improvements go here.** |

## How Rishi TK TF was built

The TK TF Original System's source code is locked. Its signals were reverse-engineered from:

1. **TradingView exports** of NSE:NIFTY on the 1m, 3m, 5m and 30m charts. These include the
   TK TF Original System's own `Slow` / `Fast` / `Combined` plot columns (+1 bullish, −1 bearish).
2. **The TK TF Original System's trade logs, 2009 → 2026:**

   | Log | Trades | Chart |
   |-----|--------|-------|
   | `TK_TF_slow.csv` | 3,056 | 30m signal |
   | `TK_TF_Fast.csv` | 8,179 | 1m chart |
   | `TK_TF_Combined.csv` | 2,336 | 1m chart |

What the TK TF Original System's logs confirmed:

- **Log time = the open of the bar after the signal bar.** A signal on the last candle of the day
  is logged at the next day's 09:15.
- **ROI % = return from that bar's open to the next signal's open, on spot NIFTY.** Reproduced to
  within 0.01% on every Slow trade since 2020.
- **The Fast and Combined logs come from a 1m chart.** Slow is a 30m signal.
- **The Combined rule** ("switch only when Slow and Fast agree") reproduces **all 2,336** logged
  Combined trades exactly.

## Rishi TK TF rules

| Signal   | Timeframe | Rule |
|----------|-----------|------|
| Slow     | 30m (the same on every chart) | `sign( LEAD(HLC3) − EMA(HLC3, 63) )`, where `LEAD = 1.27·HLC3 + (1−1.27)·LEAD[1]` (an EMA with smoothing factor 1.27, so it leads price) |
| Fast     | 1m (setting "Fast timeframe") | `sign( Σ wₙ · (EMA(HLC3, n) − EMA(HLC3, 113)) )`, with the 14 fitted weights in `rishi_tk_tf.py` (roughly EMA 60–100 vs EMA 140–160) |
| Combined | Fixed check times (setting, on by default) | Takes a new side only when Slow and Fast agree, otherwise keeps its side. Checked only on candles closing at **09:45, 10:15 … 15:15**. After 15:15 the next check is 09:45 the next day. |

### Rishi TK TF's own changes (not in the TK TF Original System)

| Setting | Default | What it does |
|---------|---------|--------------|
| **Check signals only at 30-min marks (09:45-15:15)** | On | Combined is checked only at 09:45, 10:15 … 15:15, twelve times a day. Slow/Fast agreement at any other time, or after 15:15, waits for the next check. Turn it off to check on every candle, which is the TK TF Original System's behaviour. |
| **Fast timeframe** | 1 minute | Fast is always calculated on 1m candles (the TK TF Original System uses the chart's timeframe), so Fast and Combined are the same on any chart from 1m to 30m. Leave empty to use the chart's timeframe. |

**Effect of the fixed check times.** This has not been backtested on Rishi TK TF over 2009-2026
yet. Run `rishi_tk_tf_strategy.pine` (setting on, the default) with Deep Backtesting on a 1m chart
and compare it with the TK TF Original System. On the 1m data available (Jul → Oct 2026) the
Python backtester gives 14 trades, +6.4% (fixed checks) against 16 trades, +6.2% (every candle).

## How closely Rishi TK TF matches the TK TF Original System

All results in this section are for Rishi TK TF with the fixed check times **off** (every
candle), which is the TK TF Original System's logic. That is the setting that tests the
reverse-engineering itself.

### Signal accuracy

Same bar = Rishi TK TF's signal is on the same bar and in the same direction as TK TF Original's.

| Chart | Slow bars | Slow same bar | Fast bars | Fast same bar | Combined bars | Combined same bar |
|-------|-----------|---------------|-----------|---------------|---------------|-------------------|
| 30m (2020 → 2026) | 99.94% | 98.8% | 99.76% | 63.0% | 99.77% | 63.0% |
| 5m  | 99.85% | 97.0% | 99.66% | 50.9% | 99.66% | 70.9% |
| 3m  | 99.16% | 96.0% | 99.67% | 55.7% | 99.12% | 72.1% |
| 1m  | 99.84% | 96.3% | 99.63% | 54.6% | 99.83% | 88.2% |

Against the TK TF Original System's logs: Slow 1,150 of 1,167 on the same candle (2020 → 2026);
Combined 15 of 16 (1m, Jul → Sep 2026).

### Deep Backtesting, 2009 → 2026 (1m NSE:NIFTY, closed trades, ROI % per trade, no costs)

| Metric | TK TF Original System | Rishi TK TF | Difference |
|--------|-----------------------|-------------|------------|
| Closed trades | 2,330 | 2,324 | −6 |
| Total ROI | 439.87% | 436.75% | −3.12 |
| Avg ROI / year | 25.00% | 24.82% | −0.18 |
| Avg ROI / trade | 0.189% | 0.188% | −0.001 |
| Win rate | 31.89% | 31.80% | −0.09 |
| Profit factor | 1.655 | 1.649 | −0.006 |
| Max drawdown | 12.46% | 12.78% | +0.32 |
| Net points | 42,995 | 42,996 | +2 |
| CAGR (compounded) | 26.54% | 26.32% | −0.22 |

Trade timing: 89.1% of TK TF Original's trades are on the same minute, 96.7% within 1 minute and
98.2% within 5 minutes. All 212 months have the same sign (profit or loss) in both, and every
year is within 2.3 ROI points. Month-by-month points are in `monthly_points_comparison.csv`.

### In-sample / out-of-sample (50 time periods)

`python3 is_oos.py <tk_tf_original_trades.csv> <rishi_tk_tf_trades.csv> --set 50 --out is_oos_50_results.csv`
runs 15 forward and 15 backward anchored splits, 10 walk-forward set-ups and 10 sliding blocks.
Use `--set 10` for the 10 headline designs.

| Out of sample, 50 periods | TK TF Original System | Rishi TK TF |
|---|---|---|
| Profitable | 50 / 50 | 50 / 50 |
| Profit factor ≥ 1.2 / ≥ 1.4 | 50 / 46 | 50 / 45 |
| ROI per year: median (min - max) | 22.1% (7.5 - 46.0) | 21.9% (7.8 - 46.3) |
| Walk-forward efficiency: median | 86% | 87% |

Rishi TK TF's parameters were fitted on 2020-2026 data only. On 2009-2019 (out of sample) it
still reproduces TK TF Original: 25.9% vs 26.3% per year, PF 1.67 vs 1.68. Both systems are
weaker since 2021, at about 12-14% per year.

### Monte Carlo (10,000 runs per test)

`python3 monte_carlo.py <tk_tf_original_trades.csv> <rishi_tk_tf_trades.csv> --out monte_carlo_results.csv`

| Median (5th - 95th percentile) | TK TF Original System | Rishi TK TF |
|---|---|---|
| Max drawdown, random trade order | 17.9% (13.2 - 26.7) | 18.0% (13.2 - 26.7) |
| ROI per year, bootstrap | 24.9% (18.5 - 31.9) | 24.8% (18.2 - 31.6) |
| One year from 2021+ trades: ROI / P(loss) | 13.5% / 13.5% | 13.5% / 13.5% |
| Stress (10% trades missed, 0.02%/side): ROI per year | 17.8% | 17.6% |

Size positions for a 20-28% drawdown, not the 12.5% seen in the backtest.

## Files

| File | What it is |
|------|------------|
| `rishi_tk_tf.pine` | Rishi TK TF indicator for TradingView: BUY/SELL labels, alerts, status table |
| `rishi_tk_tf_fixed_strategy.pine` | Simplest Rishi TK TF backtester for TradingView: fixed 09:45-15:15 checks built in, 1m chart only, for Deep Backtesting and trade-log export |
| `rishi_tk_tf_strategy.pine` | Rishi TK TF backtester for TradingView (Deep Backtesting), with a results table next to the TK TF Original System's figures |
| `rishi_tk_tf.py` | Rishi TK TF in Python: `backtest`, `verify` / `checklog` against the TK TF Original System, `logstats` of a TK TF Original log |
| `is_oos.py`, `monte_carlo.py` | In-sample / out-of-sample and Monte Carlo tests on two TradingView trade-list exports |
| `*_results.csv`, `monthly_points_comparison.csv` | Saved results of the tests above |

```bash
python3 rishi_tk_tf.py backtest NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv --cost 0.02 --out trades.csv   # fixed checks (default)
python3 rishi_tk_tf.py backtest NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv --every-candle                  # TK TF Original-style checks
python3 rishi_tk_tf.py backtest NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv --original                      # TK TF Original's exported columns
python3 rishi_tk_tf.py verify   NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv
python3 rishi_tk_tf.py checklog NSE_NIFTY_1.csv TK_TF_Combined.csv --signal Combined --htf NSE_NIFTY_30.csv
python3 rishi_tk_tf.py logstats TK_TF_Combined.csv
```

Pass `--htf` with a 30m export whenever the chart export is short; it gives the Slow 63-period EMA
enough history to settle. `verify` and `checklog` always check every candle, so they compare
like-for-like with the TK TF Original System.

Not covered: the TK TF Original System's SL/TSL, target and option-leg (straddle/CE/PE) features,
which were empty in the exports.
