# V5 portfolio - fall analysis

Backtest 2006-09-06 to 2026-09-04; 568 completed holding spells across 340 stocks; 50,462 stock-days held.

Definition: a fall of X% over N sessions = close-to-close decline >= X% on a stock held for the whole window. Episodes merge flagged days within N sessions of each other. Weight = position weight in NAV before the window; NAV hit = weight x fall.

## Frequency

| window | fall | flagged_days | episodes | per_year | stocks | spells_hit_pct | pct_holding_days |
|---|---|---|---|---|---|---|---|
| 1d | >=5% | 894 | 821 | 41.06 | 254 | 58.80 | 1.77 |
| 1d | >=7% | 297 | 279 | 13.95 | 143 | 30.81 | 0.59 |
| 1d | >=8% | 181 | 166 | 8.30 | 107 | 20.42 | 0.36 |
| 1d | >=10% | 67 | 62 | 3.10 | 55 | 9.68 | 0.13 |
| 1d | >=12% | 41 | 39 | 1.95 | 38 | 6.69 | 0.08 |
| 3d | >=5% | 3901 | 1915 | 95.78 | 320 | 87.15 | 7.73 |
| 3d | >=7% | 1775 | 981 | 49.06 | 271 | 67.25 | 3.52 |
| 3d | >=8% | 1211 | 692 | 34.61 | 236 | 55.81 | 2.40 |
| 3d | >=10% | 601 | 366 | 18.31 | 180 | 36.80 | 1.19 |
| 3d | >=12% | 308 | 184 | 9.20 | 113 | 21.65 | 0.61 |
| 5d | >=5% | 5690 | 1816 | 90.82 | 323 | 90.49 | 11.28 |
| 5d | >=7% | 3006 | 1152 | 57.62 | 298 | 75.70 | 5.96 |
| 5d | >=8% | 2140 | 861 | 43.06 | 267 | 64.26 | 4.24 |
| 5d | >=10% | 1115 | 488 | 24.41 | 219 | 47.89 | 2.21 |
| 5d | >=12% | 599 | 279 | 13.95 | 163 | 32.22 | 1.19 |

## Held stocks vs the whole universe

| window | fall | pct_holding_days | all_stocks_pct | held_vs_universe_x |
|---|---|---|---|---|
| 1d | >=5% | 1.77 | 2.14 | 0.83 |
| 1d | >=7% | 0.59 | 0.77 | 0.77 |
| 1d | >=8% | 0.36 | 0.49 | 0.73 |
| 1d | >=10% | 0.13 | 0.21 | 0.62 |
| 1d | >=12% | 0.08 | 0.12 | 0.70 |
| 3d | >=5% | 7.73 | 8.74 | 0.88 |
| 3d | >=7% | 3.52 | 4.23 | 0.83 |
| 3d | >=8% | 2.40 | 3.00 | 0.80 |
| 3d | >=10% | 1.19 | 1.58 | 0.75 |
| 3d | >=12% | 0.61 | 0.89 | 0.69 |
| 5d | >=5% | 11.28 | 13.44 | 0.84 |
| 5d | >=7% | 5.96 | 7.52 | 0.79 |
| 5d | >=8% | 4.24 | 5.65 | 0.75 |
| 5d | >=10% | 2.21 | 3.26 | 0.68 |
| 5d | >=12% | 1.19 | 1.95 | 0.61 |

## Portfolio impact

| window | fall | avg_fall_pct | avg_weight_pct | avg_nav_hit_pct | worst_nav_hit_pct |
|---|---|---|---|---|---|
| 1d | >=5% | -7.06 | 5.09 | -0.36 | -1.59 |
| 1d | >=7% | -9.54 | 5.14 | -0.49 | -1.59 |
| 1d | >=8% | -10.98 | 5.11 | -0.56 | -1.59 |
| 1d | >=10% | -14.44 | 5.21 | -0.75 | -1.59 |
| 1d | >=12% | -16.57 | 5.16 | -0.86 | -1.59 |
| 3d | >=5% | -8.02 | 5.09 | -0.41 | -2.43 |
| 3d | >=7% | -10.08 | 5.10 | -0.51 | -2.43 |
| 3d | >=8% | -11.16 | 5.11 | -0.57 | -2.43 |
| 3d | >=10% | -13.17 | 5.14 | -0.68 | -2.43 |
| 3d | >=12% | -15.44 | 5.13 | -0.79 | -2.43 |
| 5d | >=5% | -8.85 | 5.12 | -0.45 | -3.12 |
| 5d | >=7% | -10.59 | 5.13 | -0.54 | -3.12 |
| 5d | >=8% | -11.66 | 5.13 | -0.60 | -3.12 |
| 5d | >=10% | -13.76 | 5.15 | -0.71 | -3.12 |
| 5d | >=12% | -16.00 | 5.15 | -0.83 | -3.12 |

## What happened next

| window | fall | fwd5d_pct | fwd20d_pct | rebound20d_pct | sold_within_5d_pct | sold_within_20d_pct | spell_ret_after_fall_pct |
|---|---|---|---|---|---|---|---|
| 1d | >=5% | 2.44 | 5.86 | 61.14 | 15.59 | 35.20 | 33.58 |
| 1d | >=7% | 4.34 | 7.67 | 68.46 | 20.07 | 36.20 | 34.69 |
| 1d | >=8% | 5.45 | 7.96 | 66.27 | 26.51 | 43.98 | 34.68 |
| 1d | >=10% | 8.07 | 9.56 | 69.35 | 32.26 | 50.00 | 35.50 |
| 1d | >=12% | 10.08 | 9.56 | 71.79 | 33.33 | 53.85 | 29.14 |
| 3d | >=5% | 3.00 | 5.33 | 64.80 | 12.79 | 30.97 | 30.26 |
| 3d | >=7% | 3.57 | 6.22 | 65.14 | 16.62 | 34.25 | 28.93 |
| 3d | >=8% | 3.95 | 6.94 | 66.18 | 17.05 | 34.97 | 29.91 |
| 3d | >=10% | 4.17 | 6.56 | 63.66 | 19.67 | 37.70 | 30.61 |
| 3d | >=12% | 5.14 | 5.91 | 61.41 | 26.09 | 44.02 | 31.88 |
| 5d | >=5% | 4.04 | 6.48 | 68.56 | 13.44 | 31.77 | 29.58 |
| 5d | >=7% | 4.27 | 6.51 | 67.53 | 16.41 | 35.07 | 30.18 |
| 5d | >=8% | 4.38 | 6.59 | 67.25 | 18.00 | 36.12 | 29.49 |
| 5d | >=10% | 4.82 | 7.25 | 67.21 | 18.85 | 39.14 | 29.66 |
| 5d | >=12% | 5.54 | 7.11 | 68.46 | 23.30 | 42.29 | 29.77 |

## Number of held stocks falling on the same date

Dates on which at least one held stock met the fall test; dates_Kplus = dates on which K or more held stocks fell together.

| window | fall | dates_with_a_fall | avg_stocks_falling | max_stocks_falling | dates_2plus | dates_3plus | dates_5plus | dates_10plus |
|---|---|---|---|---|---|---|---|---|
| 1d | >=10% | 42 | 1.60 | 11 | 5 | 4 | 2 | 2 |
| 1d | >=12% | 24 | 1.71 | 9 | 4 | 2 | 2 | 0 |
| 1d | >=5% | 472 | 1.89 | 16 | 153 | 81 | 37 | 6 |
| 1d | >=7% | 175 | 1.70 | 13 | 45 | 24 | 12 | 2 |
| 1d | >=8% | 109 | 1.66 | 13 | 27 | 13 | 5 | 2 |
| 3d | >=10% | 372 | 1.62 | 19 | 111 | 40 | 14 | 4 |
| 3d | >=12% | 205 | 1.50 | 18 | 44 | 19 | 6 | 2 |
| 3d | >=5% | 1468 | 2.66 | 20 | 809 | 503 | 224 | 37 |
| 3d | >=7% | 846 | 2.10 | 19 | 368 | 197 | 81 | 10 |
| 3d | >=8% | 652 | 1.86 | 19 | 233 | 120 | 47 | 5 |
| 5d | >=10% | 613 | 1.82 | 18 | 219 | 116 | 33 | 5 |
| 5d | >=12% | 366 | 1.64 | 18 | 116 | 41 | 8 | 4 |
| 5d | >=5% | 1793 | 3.17 | 20 | 1164 | 773 | 375 | 88 |
| 5d | >=7% | 1271 | 2.37 | 20 | 629 | 357 | 162 | 23 |
| 5d | >=8% | 1017 | 2.10 | 20 | 450 | 239 | 94 | 9 |

### Dates with most stocks falling (1d >=5%)

| date | stocks_held | stocks_fallen | pct_of_portfolio | symbols |
|---|---|---|---|---|
| 2008-01-21 | 20 | 16 | 80.0 | BLUESTARCO, INDIAGLYCO, JSWSTEEL, RELINFRA, VEDL, RELIANCE, SOUTHBANK, WELCORP, RIIL, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO, LT |
| 2024-06-04 | 20 | 12 | 60.0 | RECLTD, HAL, IRFC, PRESTIGE, NTPC, BSE, PFC, SUZLON, DIXON, HUDCO, MOTILALOFS, BHEL |
| 2008-01-18 | 20 | 11 | 55.0 | INDIAGLYCO, JSWSTEEL, VEDL, RELIANCE, SOUTHBANK, WELCORP, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB |
| 2009-06-08 | 17 | 11 | 64.7 | IDEA, DSKULKARNI, NOIDATOLL, FSL, MUNJALSHOW, MCLEODRUSS, EMBDL, PFC, IIFL, NIITLTD, ORIENTPPR |
| 2021-04-12 | 20 | 11 | 55.0 | FSL, HINDCOPPER, AFFLE, CDSL, ATGL, INDIAMART, TATAELXSI, BSOFT, DIXON, APLAPOLLO, DEEPAKNTR |
| 2008-01-22 | 20 | 10 | 50.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, RELINFRA, RELIANCE, SOUTHBANK, SHRIRAMFIN, RIIL, GMDCLTD, RAJESHEXPO |
| 2008-01-24 | 20 | 9 | 45.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, RELINFRA, GMDCLTD, JINDALSTEL, ABAN, DIVISLAB, LT |
| 2009-04-16 | 17 | 9 | 52.9 | IDEA, DSKULKARNI, NOIDATOLL, FSL, MCLEODRUSS, EMBDL, IIFL, NIITLTD, ORIENTPPR |
| 2009-07-06 | 20 | 9 | 45.0 | ENGINERSIN, UNIONBANK, BANKBARODA, COROMANDEL, PFC, IIFL, ONGC, LICHSGFIN, ORIENTPPR |
| 2020-12-21 | 20 | 9 | 45.0 | LAURUSLABS, APLLTD, TATAELXSI, ESCORTS, SYNGENE, DIVISLAB, APLAPOLLO, DEEPAKNTR, GRANULES |
| 2022-01-24 | 20 | 9 | 45.0 | ADANIENT, GRASIM, LTTS, TATAPOWER, PERSISTENT, BSE, CDSL, ECLERX, DEEPAKNTR |
| 2023-09-12 | 20 | 9 | 45.0 | RECLTD, KALYANKJIL, RVNL, FACT, ZENSARTECH, PFC, NCC, FINCABLES, MAZDOCK |

### Dates with most stocks falling (1d >=10%)

| date | stocks_held | stocks_fallen | pct_of_portfolio | symbols |
|---|---|---|---|---|
| 2008-01-21 | 20 | 11 | 55.0 | INDIAGLYCO, JSWSTEEL, RELINFRA, VEDL, SOUTHBANK, WELCORP, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO |
| 2024-06-04 | 20 | 10 | 50.0 | RECLTD, HAL, IRFC, PRESTIGE, NTPC, PFC, DIXON, HUDCO, MOTILALOFS, BHEL |
| 2008-01-22 | 20 | 4 | 20.0 | INDIAGLYCO, SOUTHBANK, SHRIRAMFIN, RAJESHEXPO |
| 2024-02-12 | 20 | 3 | 15.0 | IRFC, NBCC, NLCINDIA |
| 2007-12-17 | 20 | 2 | 10.0 | JSWSTEEL, JINDALSTEL |
| 2008-01-18 | 20 | 1 | 5.0 | KOTAKBANK |
| 2008-01-24 | 20 | 1 | 5.0 | JINDALSTEL |
| 2009-04-16 | 17 | 1 | 5.9 | IIFL |
| 2009-04-22 | 17 | 1 | 5.9 | NOIDATOLL |
| 2009-04-27 | 17 | 1 | 5.9 | EMBDL |
| 2009-05-19 | 17 | 1 | 5.9 | HEROMOTOCO |
| 2009-05-26 | 17 | 1 | 5.9 | NIITLTD |

### Dates with most stocks falling (5d >=10%)

| date | stocks_held | stocks_fallen | pct_of_portfolio | symbols |
|---|---|---|---|---|
| 2008-01-22 | 20 | 18 | 90.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, ADANIENT, RELINFRA, VEDL, RELIANCE, SOUTHBANK, WELCORP, SHRIRAMFIN, RIIL, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO, USHAMART |
| 2008-01-24 | 20 | 18 | 90.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, ADANIENT, RELINFRA, VEDL, RELIANCE, SOUTHBANK, WELCORP, RIIL, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO, USHAMART, LT |
| 2008-01-21 | 20 | 16 | 80.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, RELINFRA, VEDL, RELIANCE, SOUTHBANK, WELCORP, RIIL, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO, LT |
| 2008-01-23 | 20 | 16 | 80.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, ADANIENT, RELINFRA, VEDL, RELIANCE, SOUTHBANK, RIIL, GMDCLTD, JINDALSTEL, KOTAKBANK, ABAN, DIVISLAB, RAJESHEXPO, USHAMART |
| 2008-01-25 | 20 | 11 | 55.0 | INDIAGLYCO, STCINDIA, JSWSTEEL, ADANIENT, RIIL, GMDCLTD, JINDALSTEL, ABAN, DIVISLAB, RAJESHEXPO, USHAMART |
| 2007-10-19 | 20 | 8 | 40.0 | ADANIENT, APTECHT, PRAJIND, SOUTHBANK, JINDALSTEL, CRISIL, KOTAKBANK, LT |
| 2007-11-22 | 20 | 8 | 40.0 | STCINDIA, RELINFRA, VEDL, WELCORP, GMDCLTD, ABAN, UNITDSPR, LT |
| 2023-10-25 | 20 | 8 | 40.0 | MAHABANK, RVNL, FACT, UNIONBANK, IRFC, ZENSARTECH, NCC, MAZDOCK |
| 2007-10-22 | 20 | 7 | 35.0 | JSWSTEEL, BHARTIARTL, PRAJIND, JINDALSTEL, CRISIL, KOTAKBANK, TFCILTD |
| 2018-01-31 | 20 | 7 | 35.0 | BOMDYEING, BBTC, RAIN, AVANTIFEED, VAKRANGEE, MOTILALOFS, APLAPOLLO |
| 2018-02-02 | 20 | 7 | 35.0 | BOMDYEING, BBTC, RAIN, ADANIENSOL, VAKRANGEE, APLAPOLLO, EDELWEISS |
| 2010-01-27 | 20 | 6 | 30.0 | EICHERMOT, SEAMECLTD, VEDL, MCLEODRUSS, JAYSREETEA, LICHSGFIN |

## Portfolio-level daily drops (days invested)

| metric | days |
|---|---|
| portfolio down >= 1% in a day | 338 |
| portfolio down >= 2% in a day | 110 |
| portfolio down >= 3% in a day | 42 |
| portfolio down >= 4% in a day | 24 |
| portfolio down >= 5% in a day | 9 |

## Episodes per calendar year

| year | 1d>=10% | 1d>=12% | 1d>=5% | 1d>=7% | 1d>=8% | 3d>=10% | 3d>=12% | 5d>=10% | 5d>=12% |
|---|---|---|---|---|---|---|---|---|---|
| 2007 | 2 | 1 | 42 | 18 | 8 | 33 | 22 | 34 | 22 |
| 2008 | 13 | 9 | 30 | 20 | 18 | 23 | 22 | 21 | 22 |
| 2009 | 7 | 1 | 111 | 42 | 25 | 30 | 10 | 38 | 20 |
| 2010 | 2 | 2 | 48 | 15 | 9 | 22 | 14 | 29 | 20 |
| 2011 | 1 | 0 | 19 | 7 | 4 | 7 | 4 | 10 | 7 |
| 2012 | 2 | 1 | 27 | 8 | 6 | 8 | 4 | 16 | 7 |
| 2013 | 2 | 2 | 10 | 3 | 3 | 4 | 2 | 10 | 2 |
| 2014 | 3 | 2 | 70 | 18 | 9 | 21 | 11 | 40 | 22 |
| 2015 | 0 | 0 | 34 | 8 | 2 | 11 | 3 | 21 | 8 |
| 2016 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2017 | 2 | 2 | 37 | 15 | 4 | 22 | 11 | 28 | 15 |
| 2018 | 2 | 2 | 11 | 5 | 4 | 7 | 5 | 11 | 9 |
| 2019 | 0 | 0 | 6 | 3 | 1 | 2 | 1 | 4 | 1 |
| 2020 | 2 | 1 | 46 | 10 | 5 | 17 | 9 | 20 | 13 |
| 2021 | 3 | 1 | 76 | 25 | 15 | 52 | 23 | 60 | 37 |
| 2022 | 1 | 0 | 60 | 14 | 7 | 30 | 9 | 33 | 18 |
| 2023 | 1 | 0 | 46 | 15 | 9 | 12 | 4 | 23 | 5 |
| 2024 | 18 | 15 | 94 | 37 | 29 | 45 | 22 | 61 | 34 |
| 2025 | 0 | 0 | 18 | 5 | 2 | 5 | 2 | 10 | 5 |
| 2026 | 1 | 0 | 34 | 11 | 6 | 15 | 6 | 19 | 12 |

## Worst single-day falls while held (>=12%)

| date | symbol | fall_pct | weight_pct |
|---|---|---|---|
| 2013-12-20 | MOTHERSON | -31.28 | 5.08 |
| 2008-01-21 | JINDALSTEL | -26.75 | 5.05 |
| 2024-06-04 | RECLTD | -25.19 | 5.39 |
| 2008-01-21 | VEDL | -25.02 | 4.76 |
| 2024-06-04 | PFC | -23.08 | 5.84 |
| 2024-01-11 | POLYCAB | -21.04 | 4.59 |
| 2024-06-04 | BHEL | -20.84 | 4.97 |
| 2018-02-01 | VAKRANGEE | -20.00 | 4.69 |
| 2024-06-04 | HUDCO | -19.99 | 6.19 |
| 2008-01-22 | RAJESHEXPO | -18.75 | 5.09 |
| 2010-10-06 | VIPIND | -18.18 | 5.17 |
| 2024-06-04 | HAL | -17.83 | 6.37 |
| 2008-01-21 | RELINFRA | -16.92 | 4.65 |
| 2014-11-14 | BALKRISIND | -16.55 | 4.95 |
| 2024-09-12 | GRANULES | -16.52 | 5.03 |
