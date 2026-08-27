# Data provenance

## Scope

This document records the data sources, synchronization rules and known limitations of the frozen V4.1.1 research snapshot.

The public repository does not redistribute the raw hourly Bitcoin download, Yahoo response payloads, FRED download cache or BLS HTML cache used during the local run.

It publishes the derived synchronized panel, research tables, figures and assurance traces required to inspect the published result.

## Gold

Gold exposure is represented by `GLD`.

Daily adjusted closes are retrieved from Yahoo Finance's public chart endpoint.

GLD is an investable proxy rather than the physical spot-gold fixing. The distinction is explicit and should be preserved when interpreting the results.

## Bitcoin

Bitcoin is represented by Binance Spot `BTCUSDT`.

Hourly data are downloaded from the public kline endpoint.

For each GLD trading session, Bitcoin is sampled at the exact NYSE Arca session close obtained from the `ARCX` calendar in `exchange_calendars`.

This includes early-close sessions.

The frozen alignment audit contains 19 early closes, all matched exactly.

Two sessions lack an exact hourly Bitcoin observation:

- `2017-09-06`;
- `2018-02-08`.

They are documented in `outputs/digital_gold_v4_1_1/assurance/btc_missing_sessions.csv`.

No backward or forward temporal fallback is used in V4.1.1.

## Primary macro-financial factors

| Research factor | Series | Source | Transformation |
|---|---|---|---|
| US equities | `SP500` | FRED | log return |
| Broad US dollar | `DTWEXBGS` | FRED | log return |
| US 10-year real yield | `DFII10` | FRED | change in percentage points |

Those three factors form the primary model.

## Risk aversion

`VIXCLS` is used to characterize changes in risk aversion.

Because contemporaneous equity returns and VIX changes contain strongly overlapping information, VIX is not included in the three-factor primary specification.

A separate extension orthogonalizes the VIX change to the equity return before inclusion.

## Credit

`BAA10Y` is used as the long-history credit-spread proxy.

`BAMLH0A0HYM2` is retained only as a recent-window robustness series and is explicitly prevented from shrinking the primary sample.

## Financial conditions

`NFCI` is used only as an **ex-post revised classification**.

The historical series may be revised and its FRED observation date is not treated as a point-in-time availability timestamp.

NFCI is therefore excluded from the primary factor model and from any claim that requires contemporaneous information availability.

## Inflation

The inflation block uses `CPIAUCNS`.

The CPI series is mapped to actual historical CPI release dates parsed from US Bureau of Labor Statistics calendars.

The daily inflation state used for conditioning is shifted by one traditional-market session so that the value assigned to a return observation was already available by the previous close.

The event study uses CPI publication days directly.

No market-consensus series is included. Therefore the research does not claim to measure inflation surprises.

## Frozen versus live data

The files committed under `outputs/digital_gold_v4_1_1/` document the frozen published run.

A new live reproduction may differ because:

- Yahoo may revise adjusted-price history or metadata;
- FRED series may be revised or access windows may change;
- BLS web pages may change structure;
- Binance may change API availability;
- third-party Python packages may update exchange calendars.

Exact numerical verification therefore applies to the committed frozen snapshot.

Live reproduction establishes reproducibility of the methodology against currently available public sources.
