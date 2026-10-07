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

## Rishi TK TF Robust (trend-gated shorts)

`robustness_research.py` tested 90 variations of Rishi TK TF Every-Candle on its 2009-2026
trade log (2,324 trades). Each variation is decided only from what is known at the entry. Each
was scored on the full period, in-sample 2009-2017 and out-of-sample 2018-2026, at 0, 0.02% and
0.05% cost per side.

**The rule kept.** BUY signals are traded as before. A SELL signal is shorted only when price is
at or below its 30-day trend average (the time-weighted average of the signal prices over the
last 30 calendar days). Above the average, the long is closed and the strategy stays flat until
the next BUY.

Why it works: Indian equities trend up over time. The 736 shorts taken against an uptrend
made +13.7% in total over 17.6 years (0.02% a trade) and won only 27.6% of the time. They are
where most of the whipsaws happen. The 426 shorts kept, taken in downtrends, average 0.20% a
trade and still protect 2011, 2015 and 2020.

| 2009-2026, 1x size | Every-Candle | Robust | Every-Candle, 0.02%/side | Robust, 0.02%/side |
|---|---|---|---|---|
| Trades | 2,324 | 1,588 | 2,324 | 1,588 |
| CAGR (compounded) | 26.32% | 25.63% | 19.83% | **21.19%** |
| Max DD (compounded) | 12.27% | **10.07%** | 14.70% | **11.04%** |
| Total ROI / ROI per year | 436.8% / 24.8% | 423.1% / 24.0% | 343.8% / 19.5% | **359.6% / 20.4%** |
| Max DD on ROI | 12.78% | **10.50%** | 15.58% | **11.58%** |
| Profit factor | 1.65 | **1.92** | 1.47 | **1.71** |
| Avg ROI / trade | 0.188% | **0.266%** | 0.148% | **0.226%** |
| Worst year | +0.94% | **+2.60%** | −3.18% | **−0.40%** |
| Out of sample 2018-26: CAGR / DD | 23.9% / 10.5% | 24.3% / 10.1% | 17.4% / 12.7% | **19.8% / 11.0%** |
| Risk-matched (same DD as Every-Candle): size / CAGR | 1x / 26.3% | **1.23x / 32.0%** | 1x / 19.8% | **1.35x / 29.0%** |

At 0.05% per side, CAGR is 10.7% for Every-Candle and 14.8% for Robust, with drawdowns of 22.1%
and 12.5%.

**Robustness of the rule**
- **Lookback:** chosen on 2009-2017 only. Every lookback from 20 to 150 days lowers the drawdown,
  and 30-50 and 100 days give almost the same result.
- **Walk-forward:** the lookback was re-chosen each January from earlier data only. Over
  2012-2026 at 0.02% cost this gives 17.8% CAGR / 12.9% DD, against 16.4% / 14.7% for
  Every-Candle.
- **Rolling 3-year windows:** better return per unit of drawdown in 13 of 16 windows with no
  costs, and 15 of 16 at 0.02%.
- **Year-block bootstrap (5,000 runs):**
  - Lower drawdown: 91.7% of runs with no costs, 99.6% at 0.02%.
  - Better return per unit of drawdown: 86.0% with no costs, 98.6% at 0.02%.
  - Higher final equity: 34.5% with no costs, 80.3% at 0.02%.
- **Monte Carlo, random trade order:** median / 95th-percentile max drawdown falls from
  16.8 / 24.1% to 13.2 / 19.1% with no costs, and from 20.7 / 29.7% to 15.6 / 22.6% at 0.02%.
- **Costs:** the rule takes 32% fewer trades, so it gains more the higher the costs.

**Rejected, because they lost return or did not hold up out of sample**

| Idea | Best result at 0.02% / side (Every-Candle: CAGR 19.8%, DD 14.7%) |
|---|---|
| Chop filter: efficiency ratio of recent signal prices | CAGR 17.7%, DD 12.9%; most settings much worse |
| Chop filter: skip after many signals in a few days | CAGR 19.7%, DD 15.4%; most settings much worse |
| Chop filter: skip after a losing streak | CAGR 13.0%, DD 18.4% |
| Equity-curve filter (half size below its average) | CAGR 18.7%, DD 14.7% |
| Trade only with the trend on both sides | CAGR 13.3%, DD 11.2%: counter-trend longs (buying dips) are the best trades |
| Hold the long through an uptrend SELL instead of going flat | DD 13.1% at 30 days, worse at other lookbacks |
| Smaller shorts always (x0.25) or long only | Lowest DD (9.0%), but losing years 2011 and 2020 (−6.1% worst year) |
| Volatility targeting | Mostly adds leverage: CAGR 22.1%, DD 15.4% |
| Time-of-day / weekday filters | No result held in both halves |

The whipsaw losses are what the system pays to catch trends. Every filter that went flat in
choppy periods also missed the start of the next trend. The only "chop" worth removing is
shorting against an uptrend.

**Use in TradingView.** `rishi_tk_tf_robust_strategy.pine` runs on a 1m NSE:NIFTY chart with
Deep Backtesting.
- Its table shows Every-Candle and Robust side by side, from the same signals.
- The Pine version decides at the signal candle's close (the research used the next candle's
  open), so expect small differences.
- Set "Position size multiplier" to about 1.2 for the same drawdown as Every-Candle with more
  return.

```bash
python3 robustness_research.py <rishi_every_candle_trades.csv> --out robustness_results.csv
```

## Files

| File | What it is |
|------|------------|
| `rishi_tk_tf.pine` | Rishi TK TF indicator for TradingView: BUY/SELL labels, alerts, status table |
| `rishi_tk_tf_fixed_strategy.pine` | Simplest Rishi TK TF backtester for TradingView: fixed 09:45-15:15 checks built in, 1m chart only, for Deep Backtesting and trade-log export |
| `rishi_tk_tf_strategy.pine` | Rishi TK TF backtester for TradingView (Deep Backtesting), with a results table next to the TK TF Original System's figures |
| `rishi_tk_tf_robust_strategy.pine` | Rishi TK TF Robust: Every-Candle signals with trend-gated shorts, 1m chart only, table comparing it with plain Every-Candle |
| `robustness_research.py`, `robustness_results.csv` | The 90 variations tested on the Every-Candle trade log, with in-sample / out-of-sample, cost, walk-forward, bootstrap and Monte Carlo checks |
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
