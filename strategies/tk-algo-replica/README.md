# TK ALGO V1.1: in-house replica

The original TK ALGO V1.1 TradingView indicator has locked source code. These signals were
reverse-engineered from TradingView CSV exports of NSE:NIFTY on the 1m, 3m, 5m and 30m charts.
Those exports include the original indicator's own `Slow`, `Fast` and `Combined` plot columns
(+1 bullish, -1 bearish, 0 warm-up), so every candidate formula could be scored bar by bar
against the real output.

## Decoded rules

| Signal   | Timeframe | Rule | Bars matched |
|----------|-----------|------|--------------|
| Slow     | 30m, fixed (the same on every chart) | `sign((H+L+2C)/4 − EMA(HL2, 62))` | 99.1% (30m, 6.7 yrs) · 99.3% (5m) · 99.7% (1m) |
| Fast     | chart timeframe | `sign(EMA(HL2, 102) − EMA(HL2, 113))` | 98.7% (30m) · 98.1% (5m) · 98.4% (3m) · 98.7% (1m) |
| Combined | n/a | takes a new side only when Slow and Fast agree; otherwise keeps its previous side | 100% when fed the original Slow and Fast columns |

End to end (replica Slow and Fast fed into the Combined rule), the replica's Combined matches the
original on 97.4–98.7% of bars.

How each rule was found:

- **Slow is a 30m signal.** On the 1m, 3m and 5m charts, Slow only ever changes on the last chart
  bar of a 30m candle (09:44 on 1m, 09:42 on 3m, 09:40 on 5m). That is exactly
  `request.security("30")` behaviour, and it is why signals arrive at 09:45, 10:15, 10:45 and so on.
  The values agree with the 30m chart's Slow 99% of the time on every chart.
- **Slow formula.** A grid search over EMA, SMA, WMA, HMA, DEMA, TEMA, RSI, CCI, MACD, Supertrend
  and Donchian rules landed on "price vs EMA(~62) on 30m". Price measured as (H+L+2C)/4 rather
  than the close gave the last +0.6% of matches.
- **Fast formula.** Fast uses chart bars. It flips about 110 times per ~21k bars on every
  timeframe, and the same EMA pair (≈102/113 on HL2) is the best fit on all four charts.
- **Combined** reproduces the original exactly from the original Slow and Fast columns, on all four charts.

## Known gap: signal timing

Bar-level agreement is high, but replica flips do not always land on the original's exact bar:

| Chart | Original Combined signals | Same bar | Within 30 min |
|-------|---------------------------|----------|---------------|
| 1m    | 18  | 67% | 78% |
| 3m    | 69  | 51% | 84% |
| 5m    | 87  | 37% | 90% |
| 30m   | 109 | 12% | 55% (within 1h) |

Most of the remaining Slow misses are tiny (median 4–5 points from the EMA). They also cluster
heavily on the 09:15 opening bar: 23% of misses, against 7.7% of all bars. That pattern points to
the original computing on a different price feed than spot, most likely **NIFTY futures
(`NSE:NIFTY1!`) or the synthetic future** (the original has a "Syn Fut" option). Price/EMA and
EMA/EMA crossovers are very sensitive to small differences in basis.

**Next step to close the gap:** export the same charts on `NSE:NIFTY1!` with the original
indicator attached, then rerun `verify`. The Pine script already has a
"Compute signals on another symbol" switch for this.

## Backtest (spot points, always in the market, reverse on each flip, no costs/slippage)

| Chart / period | Signal | Trades | Net pts | Win % | Profit factor |
|----------------|--------|--------|---------|-------|---------------|
| 30m, 2020-01 → 2026-10 | Original Combined | 107 | 4,062 | 33.6% | 1.18 |
| 30m, 2020-01 → 2026-10 | Replica Combined  | 115 | 1,782 | 29.6% | 1.07 |
| 30m, 2020-01 → 2026-10 | Original Slow     | 1,167 | 27,298 | 27.9% | 1.60 |
| 30m, 2020-01 → 2026-10 | Replica Slow      | 995 | 25,016 | 26.7% | 1.55 |
| 5m, 2025-09 → 2026-10  | Original Combined | 85 | 734 | 36.5% | 1.07 |
| 5m, 2025-09 → 2026-10  | Replica Combined  | 89 | 1,062 | 36.0% | 1.11 |

How to read this: the strategy wins on fewer than 40% of trades. Its edge comes from winners
being 2–4× the size of losers. Slow trades far more often, so costs matter a lot there. At about
2–3 points per round trip on futures, the 6.7-year Slow figure falls by roughly 2,500–3,500 points.
The exports had no data for the original's SL/TSL, TGT, strike or straddle columns, so the
original's option-leg trade management is **not** reproduced here. These results only measure
the direction signals on spot.

## Files

- `tk_algo.py`: replica, accuracy check against an export, and flip-to-flip backtest.
- `tk_replica.pine`: TradingView Pine v6 indicator (Slow/Fast/Combined, labels, alerts, status table).
  The default *Confirm Slow only on 30m close* setting avoids repainting: Slow updates on the first
  chart bar after the 30m candle closes.

```bash
# accuracy against an export that includes the original indicator's columns
python3 tk_algo.py verify   NSE_NIFTY_5.csv --htf NSE_NIFTY_30.csv
# backtest the replica, or the original's exported columns
python3 tk_algo.py backtest NSE_NIFTY_5.csv --htf NSE_NIFTY_30.csv [--original]
```

Pass `--htf` with a 30m export whenever the chart export is short. It gives the Slow 62-period
EMA enough history to warm up; without it the 30m bars are rebuilt from the chart data.
