# TK ALGO V1.1: in-house replica

The original TK ALGO V1.1 TradingView indicator has locked source code. Its signals were
reverse-engineered from two sources:

1. **TradingView exports** of NSE:NIFTY on the 1m, 3m, 5m and 30m charts. These include the
   original indicator's own `Slow` / `Fast` / `Combined` plot columns (+1 bullish, -1 bearish).
2. **The original's trade logs, 2009 → 2026:**

   | Log | Trades | Chart |
   |-----|--------|-------|
   | `TK_TF_slow.csv` | 3,056 | 30m signal |
   | `TK_TF_Fast.csv` | 8,179 | 1m chart |
   | `TK_TF_Combined.csv` | 2,336 | 1m chart |

   `TK_TF_Combined.csv` also includes the entry prices of the last 1,168 trades.

## What the trade logs confirmed

- **Log time = the open of the bar after the signal bar.** A Slow signal on the 09:15–09:45
  candle is logged at 09:45. A signal on the last candle of the day is logged at the next day's 09:15.
- **ROI % = return from that bar's open to the next signal's open.** This reproduces all
  1,167 Slow trades from 2020 onward to within 0.01%. The prices listed in the Combined log are
  exactly spot NIFTY's open on those bars, so the original trades on **spot** prices.
- **The Slow log is the 30m Slow series** (1,163 of 1,167 identical to the 30m export).
- **The Fast and Combined logs come from a 1m chart** (103 of 104 Fast flips identical to the 1m export).
- **The Combined rule holds across all 17 years.** Replaying the Slow and Fast logs through
  "switch only when both agree" reproduces **all 2,336** logged Combined trades exactly.

## Decoded rules (v2)

| Signal   | Timeframe | Rule |
|----------|-----------|------|
| Slow     | 30m, fixed (the same on every chart) | `sign( LEAD(HLC3) − EMA(HLC3, 63) )`, where `LEAD = 1.27·HLC3 + (1−1.27)·LEAD[1]` |
| Fast     | chart timeframe | `sign( Σ wₙ · (EMA(HLC3, n) − EMA(HLC3, 113)) )`, using the 14 fitted weights in `tk_algo.py` |
| Combined | n/a | takes a new side only when Slow and Fast agree; otherwise keeps its previous side |

**Slow.** The v1 formula ((H+L+2C)/4 vs EMA(HL2, 62)) missed mostly at the opening bars of the
session. Price momentum explained the misses, which led to the fix: Slow compares a *lead* EMA of
HLC3 against EMA(HLC3, 63). The lead EMA has a smoothing factor of 1.27, above 1, so it
overshoots price instead of lagging it.

**Fast.** No standard indicator reproduces Fast's exact flip timing. That includes EMA, SMA and
WMA pairs, DEMA, TEMA, ZLEMA, HMA, MACD, TRIX, RSI, Donchian and Supertrend. Fast is therefore
modelled as a fixed weighted mix of 14 EMAs (lengths 1–300) of HLC3. The weights were fitted
on the 30m and 5m charts only. They were then checked on the 3m and 1m charts, which the fit
never saw, and still match 99.7% of bars. That holds on every timeframe, so the weights are a
real property of the indicator rather than an overfit.

## Accuracy (v2)

Original vs replica, after 10 days of warm-up. "Exact" = the replica's signal is on the same bar
and in the same direction as the original's.

| Chart | Slow bars | Slow exact | Fast bars | Fast exact | Combined bars | Combined exact |
|-------|-----------|------------|-----------|------------|---------------|----------------|
| 30m (2020 → 2026) | 99.94% | 98.8% | 99.76% | 63.0% | 99.77% | 63.0% |
| 5m  | 99.85% | 97.0% | 99.66% | 50.9% | 99.66% | 70.9% |
| 3m  | 99.16% | 96.0% | 99.67% | 55.7% | 99.12% | 72.1% |
| 1m  | 99.84% | 96.3% | 99.63% | 54.6% | 99.83% | 88.2% |

Against the trade logs:

| Log | Overlap with price data | Exact matches |
|-----|-------------------------|---------------|
| Slow | 2020 → 2026 | 1,150 of 1,167 (98.5%) |
| Fast (1m) | Jul → Oct 2026 | 54 of 98 (55%); nearly all the rest are 1–2 bars off |
| Combined (1m) | Jul → Sep 2026 | 15 of 16 (94%) |

v1 for comparison: Slow 78% exact, Fast ~18% exact (about 60% within 2 bars).

## Backtest

Settings match the original's logs: always in the market, reverse on every signal, fill at the
open of the next bar, ROI % on spot, no costs.

| Chart / period | Signal | Trades | Sum ROI | Win % | Avg win / loss | Profit factor |
|----------------|--------|--------|---------|-------|----------------|---------------|
| 30m, 2020-01 → 2026-10 | **Original** Slow | 1,167 | 162.7% | 29.0% | 1.23% / −0.31% | 1.64 |
| 30m, 2020-01 → 2026-10 | **Replica** Slow  | 1,163 | 162.1% | 29.1% | 1.24% / −0.31% | 1.63 |
| 30m, 2020-01 → 2026-10 | Original Combined | 107 | 35.5% | 33.6% | 4.46% / −1.76% | 1.28 |
| 30m, 2020-01 → 2026-10 | Replica Combined  | 109 | 41.5% | 33.9% | 4.47% / −1.72% | 1.34 |
| 5m, 2025-09 → 2026-10  | Original Combined | 85 | 2.9% | 37.6% | 1.37% / −0.77% | 1.07 |
| 5m, 2025-09 → 2026-10  | Replica Combined  | 85 | 2.3% | 37.6% | 1.36% / −0.78% | 1.05 |
| 1m, 2026-07 → 2026-10  | Original Combined | 16 | 6.2% | 43.8% | 1.28% / −0.31% | 3.21 |
| 1m, 2026-07 → 2026-10  | Replica Combined  | 16 | 6.2% | 43.8% | 1.28% / −0.31% | 3.22 |

The original's own logs, for reference:

| Log | Trades | Sum ROI | Win % | Avg win / loss | Profit factor |
|-----|--------|---------|-------|----------------|---------------|
| Slow 2009 → 2026          | 3,056 | 443.6% | 28.5% | 1.32% / −0.32% | 1.63 |
| Fast (1m) 2009 → 2026     | 8,179 | 463.2% | 31.6% | 0.82% / −0.30% | 1.28 |
| Combined (1m) 2009 → 2026 | 2,336 | 441.3% | 31.9% | 1.50% / −0.42% | 1.65 |
| Combined (1m) 2020 → 2026 |   905 | 156.6% | 31.5% | 1.42% / −0.40% | 1.63 |

How to read this:

- The strategy loses on about 70% of trades. Its edge comes from winners being about 4× the
  size of losers.
- Costs are not included. Combined on 1m makes about 135 trades a year. At 0.02–0.03% per side
  that costs roughly 5–8% ROI a year, against the ~25% a year shown in the log.
- None of this covers the original's SL/TSL, target or option-leg (straddle/CE/PE) management.
  Those columns were empty in the exports.

## Fast timeframe lock (replica-only setting)

The original computes Fast on the chart's own timeframe. The same settings therefore give
different Fast and Combined signals on a 1m chart (104 Fast flips, 20 Jul → 6 Oct 2026) than on
a 5m chart (16) or a 30m chart (3). Slow is fixed at 30m and is identical on every chart. The
original's Fast and Combined logs come from a **1m chart**.

The replica adds a **Fast timeframe** setting, default **1 minute**. On any chart from 1m to 30m,
the Pine script reads every 1m Fast value inside each chart candle and applies the Combined rule
minute by minute. Fast and Combined then follow the 1m signals in your logs whatever chart you
open. Leave the setting empty to use the chart's timeframe, as the original does.

Combined state at each chart candle's close, compared with the **original 1m chart**
(23 Jul → 6 Oct 2026):

| Chart | Fast on chart timeframe | Fast locked to 1m |
|-------|-------------------------|-------------------|
| 3m  | 96.0% | 99.8% |
| 5m  | 93.9% | 99.8% |
| 30m | 69.7% | 99.8% |

On a higher chart a signal is shown on the candle that contains the 1m signal. A Combined flip
that reverses within the same chart candle is therefore not drawn, but the state is still correct.

In Python, pass `--fast-1m <1m export>` to `verify`, `backtest` or `checklog` to get the same lock.

## Matching the original TK TF Combined statistics

Target, from the original's Combined log on a 1m chart. Compute it with
`python3 tk_algo.py logstats TK_TF_Combined.csv [--from ...] [--to ...]`. ROI % is per trade and
not compounded. Max drawdown is the largest fall of cumulative ROI % from its peak.

| Period | Trades | Total ROI | Avg ROI / year | Avg ROI / trade | Win % | Profit factor | Max drawdown |
|--------|--------|-----------|----------------|-----------------|-------|---------------|--------------|
| 2009-02 → 2026-09 | 2,336 | 441.3% | 25.0% | 0.189% | 31.9% | 1.65 | 12.5% |
| 2020-01 → 2026-09 |   904 | 153.6% | 23.0% | 0.170% | 31.4% | 1.62 | 10.6% |

**What has been verified so far.** Fast needs 1m prices, and 1m data is only available for
Jul → Oct 2026, so the match was tested in two pieces:

1. **Slow over 2020 → 2026.** The replica's Slow (from 30m data) was combined with the
   original's Fast signals from `TK_TF_Fast.csv`. Prices at Fast signal times were rebuilt from
   the log's own ROI figures; the rebuild reproduces the original's statistics exactly when fed
   the original's own Slow log.

   | 2020-01 → 2026-09 | Trades | Total ROI | Avg/yr | Avg/trade | Win % | PF | Max DD |
   |---|---|---|---|---|---|---|---|
   | Original log                 | 904 | 153.6% | 23.0% | 0.170% | 31.4% | 1.62 | 10.6% |
   | Replica Slow + original Fast | 900 | 155.4% | 23.3% | 0.173% | 32.1% | 1.63 | 11.6% |

   894 of the 905 trades are identical.

2. **Full replica on the 1m chart, Jul → Sep 2026.** Trades and statistics are the same as the
   original indicator's own signals over that period (15 trades, ROI, PF and drawdown equal to 0.1%).

**Full-period check (2009 → 2026).** The original's log appears to be a TradingView
strategy-tester trade list from a 1m chart, so the same test is available for the replica:

1. Add `tk_replica_strategy.pine` to a **1m NSE:NIFTY** chart.
2. In the Strategy Tester, turn on **Deep Backtesting** from 2009-02-03.
3. Read the results: net profit ÷ 1,00,000 = total ROI %, max drawdown ÷ 1,00,000 = max drawdown %,
   and profit factor as shown.
4. Compare with the target table above, or export the trade list and send it back for a
   trade-by-trade comparison.

Alternatively, run `tk_algo.py backtest` on any 1m NIFTY OHLC file covering 2009 → 2026.

## Deep Backtesting result: replica vs original, 2009 → 2026

Both strategies were run with TradingView Deep Backtesting on a 1m NSE:NIFTY chart, Feb 2009 →
Sep 2026, and compared on their exported trade lists (closed trades; ROI % per trade, not compounded).

| Metric | Original TK TF Combined | Replica | Difference |
|--------|-------------------------|---------|------------|
| Closed trades | 2,330 | 2,324 | −6 |
| Total ROI | 439.87% | 436.75% | −3.12 |
| Avg ROI / year | 25.00% | 24.82% | −0.18 |
| Avg ROI / trade | 0.189% | 0.188% | −0.001 |
| Win rate | 31.89% | 31.80% | −0.09 |
| Profit factor | 1.655 | 1.649 | −0.006 |
| Max drawdown | 12.46% | 12.78% | +0.32 |
| Avg win / avg loss | 1.495% / −0.423% | 1.501% / −0.424% | |
| Net points | 42,995 | 42,996 | +2 |
| Compounded ROI | 6,196% | 6,003% | −192 |
| Compounded max drawdown | 11.99% | 12.27% | +0.28 |

Trade timing: 89.1% of the original's trades are on the same minute, 96.7% within 1 minute and
98.2% within 5 minutes. Trades driven by Slow (on the 30m marks) match 98.6% exactly. Trades driven
by Fast match 60% exactly, and nearly all the rest are 1 minute early or late. Yearly ROI agrees
within 2.3 points in every year from 2009 to 2026.

## In-sample / out-of-sample test (10 variations)

`python3 is_oos.py <original_trades.csv> <replica_trades.csv>` runs 10 IS/OOS designs on the two
Deep Backtesting trade lists (2009 → 2026). WFE = OOS ROI per year ÷ IS ROI per year.

| # | Variation | Original IS → OOS ROI/yr | Replica IS → OOS ROI/yr | OOS PF (orig / rep) | WFE (orig / rep) |
|---|-----------|--------------------------|-------------------------|---------------------|------------------|
| 1 | 50/50 chronological | 27.8 → 22.2 | 27.2 → 22.5 | 1.62 / 1.63 | 80% / 83% |
| 2 | 60/40 chronological | 27.0 → 22.0 | 26.6 → 22.2 | 1.59 / 1.60 | 82% / 84% |
| 3 | 70/30 chronological | 29.6 → 14.3 | 29.3 → 14.4 | 1.40 / 1.40 | 49% / 49% |
| 4 | 80/20 chronological | 28.2 → 12.2 | 27.9 → 12.3 | 1.38 / 1.38 | 43% / 44% |
| 5 | IS 2009-15 / OOS 2016-26 | 31.4 → 20.9 | 30.9 → 20.9 | 1.59 / 1.59 | 67% / 68% |
| 6 | IS 2020-26 (replica fit) / OOS 2009-19 | 22.9 → 26.3 | 23.1 → 25.9 | 1.68 / 1.67 | 115% / 112% |
| 7 | Backward: IS 2nd half / OOS 1st half | 22.2 → 27.8 | 22.5 → 27.2 | 1.69 / 1.67 | 125% / 121% |
| 8 | IS odd years / OOS even years | 26.1 → 23.9 | 25.8 → 23.9 | 1.62 / 1.62 | 91% / 93% |
| 9 | Walk-forward 3y → 1y (15 windows) | 24.7 → 21.1 | 24.5 → 21.1 | 1.59 / 1.59 | 86% / 86% |
| 10 | Walk-forward 5y → 2y (7 windows) | 24.2 → 21.4 | 24.0 → 21.4 | 1.61 / 1.61 | 88% / 89% |

The replica tracks the original in every variation: OOS ROI per year within 0.4 points, and OOS
profit factor within 0.01. In every OOS period, 88–90% of the original's trades are hit on the
same minute. Variation 6 is a true out-of-sample test of the replica itself, because its
parameters were fitted on 2020-2026 only. On 2009-2019 it still reproduces the original
(25.9 vs 26.3% per year, PF 1.67 vs 1.68).

Both strategies stay profitable out of sample in all 10 variations (OOS PF 1.38-1.69). The edge
is weaker in recent years, though: the last 30% of the history (about 2021 → 2026) earns
12-14% per year against 28-30% before. Note that 2026 is only up to September and is flat.

### 50 time-period variations

`python3 is_oos.py <original> <replica> --set 50 --out is_oos_50_results.csv` runs:
- 15 forward anchored splits (OOS starting 2011 … 2025)
- 15 backward anchored splits
- 10 walk-forward configurations (2-6 year IS × 1-2 year OOS)
- 10 sliding blocks (4 year IS → next 2 years OOS)

The full table is in `is_oos_50_results.csv`.

| Out-of-sample result over 50 variations | Original | Replica |
|---|---|---|
| OOS profitable | 50 / 50 | 50 / 50 |
| OOS profit factor ≥ 1.2 / ≥ 1.4 | 50 / 46 | 50 / 45 |
| Walk-forward efficiency ≥ 50% | 43 / 50 | 43 / 50 |
| OOS ROI per year: median (min - max) | 22.1% (7.5 - 46.0) | 21.9% (7.8 - 46.3) |
| OOS profit factor: median (min) | 1.62 (1.21) | 1.62 (1.22) |
| Walk-forward efficiency: median (min) | 86% (28%) | 87% (29%) |
| Worst OOS max drawdown | 12.5% | 12.8% |

Replica vs original across all 50 OOS periods: ROI per year gap median 0.24, max 1.12 points;
profit factor gap median 0.009, max 0.038; same-minute trade match median 89.2% (min 87.1%).
The 7 variations with WFE < 50% all have the out-of-sample part in 2021-2026, the weaker
recent period. Their OOS is still profitable (PF 1.21-1.49).

## Monte Carlo simulation

`python3 monte_carlo.py <original> <replica> --out monte_carlo_results.csv` runs 10,000 runs per
test on the Deep Backtesting trade lists (ROI % per trade, not compounded, seed 7). Values are the
median, with the 5th-95th percentile range in brackets. The full table is in
`monte_carlo_results.csv`.

| Test | Original | Replica |
|---|---|---|
| Reshuffled order: max drawdown | 17.9% (13.2 - 26.7) | 18.0% (13.2 - 26.7) |
| Reshuffled order: P(max DD > 15%) / > 20% | 81% / 30% | 82% / 32% |
| Reshuffled order: longest losing streak | 18 trades (14 - 24) | 18 trades (14 - 24) |
| Bootstrap 17.6 yrs: ROI per year | 24.9% (18.5 - 31.9) | 24.8% (18.2 - 31.6) |
| Bootstrap 17.6 yrs: profit factor | 1.65 (1.47 - 1.86) | 1.65 (1.47 - 1.85) |
| Bootstrap 17.6 yrs: max drawdown | 18.0% (12.7 - 27.9) | 18.1% (12.8 - 27.7) |
| One year, all history: ROI | 23.9% (−0.8 - 55.0) | 23.5% (−1.3 - 54.9) |
| One year, all history: P(loss) / P(< 10%) | 5.7% / 19.2% | 6.1% / 20.1% |
| One year, 2021+ trades only: ROI | 13.5% (−6.1 - 36.3) | 13.5% (−6.3 - 36.1) |
| One year, 2021+ trades only: P(loss) / P(< 10%) | 13.5% / 39.5% | 13.5% / 39.5% |
| Stress (skip 10% of trades, 0.02%/side cost): ROI per year | 17.8% (15.6 - 19.7) | 17.6% (15.4 - 19.5) |
| Stress: profit factor / max drawdown | 1.47 / 21.8% | 1.47 / 22.1% |

The historical max drawdown (12.5%) is at the lucky end of the simulated range. The same trades in
a random order give a median drawdown of about 18%, and 26-28% at the 95th percentile. Size
positions for a drawdown of 20-28%, not 12.5%.

## Files

- `tk_algo.py`: replica, `verify` against an export, `checklog` against an original trade log,
  and `backtest` (replica or `--original` columns), all using the original's fill convention.
- `tk_replica_strategy.pine`: the same signals as a TradingView strategy (always in the market,
  fills at the next candle's open) for Deep Backtesting against the original's statistics.
- `monte_carlo.py`: Monte Carlo simulation (reshuffle, bootstrap, one-year, stress) on two trade lists.
- `is_oos.py`: 10-variation in-sample / out-of-sample test on two TradingView trade-list exports.
- `tk_replica.pine`: TradingView Pine v6 indicator with Slow/Fast/Combined, labels, alerts and a
  status table. Signals are final at candle close; set alerts to "Once Per Bar Close".

```bash
python3 tk_algo.py verify   NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv
python3 tk_algo.py checklog NSE_NIFTY_30.csv TK_TF_slow.csv --signal Slow
python3 tk_algo.py checklog NSE_NIFTY_1.csv  TK_TF_Combined.csv --signal Combined --htf NSE_NIFTY_30.csv
python3 tk_algo.py backtest NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv --cost 0.02 --out combined_trades.csv
python3 tk_algo.py backtest NSE_NIFTY_5.csv --htf NSE_NIFTY_30.csv --fast-1m NSE_NIFTY_1.csv  # Fast locked to 1m
python3 tk_algo.py backtest NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv --original                # original's own columns
```

Pass `--htf` with a 30m export whenever the chart export is short. It gives the Slow 63-period
EMA enough history to warm up.

## Remaining gap and how to close it

Fast is the only part not reproduced exactly. About 55–63% of its flips land on the same bar
and almost all the rest are 1–2 bars off. Combined inherits only part of that error, because a
Fast flip only matters while Slow already agrees.

More 1m price history would let the Fast fit be tightened. One option is a 1m NIFTY export
going back further, ideally with the original indicator attached. Since the Fast log runs
from 2009, any extra 1m OHLC could also be scored with `checklog`.
