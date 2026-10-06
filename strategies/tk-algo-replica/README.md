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

## Files

- `tk_algo.py`: replica, `verify` against an export, `checklog` against an original trade log,
  and `backtest` (replica or `--original` columns), all using the original's fill convention.
- `tk_replica.pine`: TradingView Pine v6 indicator with Slow/Fast/Combined, labels, alerts and a
  status table. Signals are final at candle close; set alerts to "Once Per Bar Close".

```bash
python3 tk_algo.py verify   NSE_NIFTY_1.csv --htf NSE_NIFTY_30.csv
python3 tk_algo.py checklog NSE_NIFTY_30.csv TK_TF_slow.csv --signal Slow
python3 tk_algo.py checklog NSE_NIFTY_1.csv  TK_TF_Combined.csv --signal Combined --htf NSE_NIFTY_30.csv
python3 tk_algo.py backtest NSE_NIFTY_5.csv --htf NSE_NIFTY_30.csv [--original]
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
