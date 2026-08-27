# Is “Digital Gold” a Good Comparison?

[![Research assurance](https://github.com/Hilmar-Corp/HC-Gold-Newsletter/actions/workflows/research-ci.yml/badge.svg)](https://github.com/Hilmar-Corp/HC-Gold-Newsletter/actions/workflows/research-ci.yml)
[![Python 3.11 to 3.13](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB)](pyproject.toml)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Reproducible research experiment supporting the HilmarCorp Research note:

**L’or numérique est-il une bonne comparaison ?**

The study asks whether Bitcoin and gold exhibit sufficiently similar sensitivities to the main macro-financial risks for the “digital gold” analogy to be useful from an allocation perspective.

## Research question

Bitcoin and gold share several high-level characteristics: scarcity narratives, global tradability and an absence of issuer cash flows.

Those similarities do not imply that the two assets perform the same financial function.

The central question is therefore:

> Do Bitcoin and gold respond similarly to equity stress, the US dollar, real rates, credit stress, inflation and risk aversion?

The experiment does not attempt to determine which asset is “better”.

## Frozen research snapshot

Published research version: **V4.1.1**

Primary synchronized sample:

**17 August 2017 to 25 August 2026**

Primary factor-regression observations:

**2,262**

The frozen snapshot passed the V4.1.1 certification layer, including exact NYSE Arca close alignment, sample-coverage controls, joint Wald inference, CPI release-date causality checks, non-overlapping stress episodes and explicit treatment of NFCI as ex-post robustness information.

## Main result

The primary factor model compares Bitcoin and gold sensitivities to:

- US equities;
- the broad US dollar;
- the US 10-year real yield.

For the one-day specification:

| Factor | Bitcoin beta | Gold beta | BTC − gold | p-value |
|---|---:|---:|---:|---:|
| US equities | 0.8560 | 0.0109 | **0.8452** | **1.23e-17** |
| Broad US dollar | -0.8870 | -1.0271 | 0.1402 | 0.648 |
| US 10-year real yield | -0.0164 | -0.0574 | **0.0410** | **0.0229** |

The joint null hypothesis that Bitcoin and gold have the same three-factor sensitivity profile is rejected:

```math
\chi^2(3)=78.36,\qquad p=6.88\times10^{-17}
```

This result does not imply that the two assets never co-move. It shows that their historical macro-financial sensitivity profiles are not equivalent over the studied sample.

## Where the analogy is strongest

The broad US dollar is the principal area of similarity.

Both Bitcoin and gold display negative daily sensitivity to the dollar in the primary specification, and the difference between their estimated coefficients is not statistically distinguishable from zero.

The result is also consistent with the independent-episode analysis of large dollar declines.

## Where the analogy breaks down

The strongest divergence appears during equity and risk-aversion shocks.

For the 5% worst equity environments:

| Horizon | Independent episodes | Mean BTC return | Mean gold return | BTC − gold | 95% CI |
|---|---:|---:|---:|---:|---:|
| 1 session | 99 | -3.13% | -0.10% | -3.03% | [-4.26%; -1.93%] |
| 5 sessions | 37 | -7.30% | -0.52% | -6.78% | [-11.08%; -2.53%] |
| 20 sessions | 11 | -10.42% | -1.17% | -9.24% | [-20.01%; 2.34%] |

The 20-session estimate remains economically large but is not statistically established after the analysis is reduced to non-overlapping independent episodes.

Large VIX increases and credit-spread widening show the same broad direction: Bitcoin has historically behaved more negatively than gold during acute risk-off transitions.

## Inflation

Inflation is treated separately because a daily CPI state is not equivalent to a market inflation surprise.

The frozen study uses:

- CPI-U NSA (`CPIAUCNS`);
- actual BLS CPI release dates;
- an ex-ante daily state based on information available by the previous market close;
- a dedicated publication-day event study.

No consensus series is used, so the repository does **not** claim to measure inflation surprises.

The available sample does not establish that Bitcoin reproduces an inflation-hedging function comparable to the one traditionally associated with gold.

## Data

| Object | Proxy / series | Source |
|---|---|---|
| Gold | GLD adjusted close | Yahoo Finance chart endpoint |
| Bitcoin | BTCUSDT Spot, hourly | Binance public market-data API |
| Trading calendar | NYSE Arca (`ARCX`) | `exchange_calendars` |
| US equities | `SP500` | FRED |
| US 10-year real yield | `DFII10` | FRED |
| Broad US dollar | `DTWEXBGS` | FRED |
| Risk aversion | `VIXCLS` | FRED |
| Credit | `BAA10Y` | FRED |
| Recent HY robustness | `BAMLH0A0HYM2` | FRED |
| Financial conditions | `NFCI` | FRED / Chicago Fed, ex-post only |
| CPI | `CPIAUCNS` | FRED |
| CPI release dates | historical release calendars | US Bureau of Labor Statistics |

Bitcoin is sampled at the **actual NYSE Arca closing time for each GLD session**, including early closes.

Two Binance sessions have no exact matching BTC observation in the frozen sample:

- 6 September 2017;
- 8 February 2018.

No temporal fallback is used in the V4.1.1 frozen specification.

See [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md) for the full provenance and limitation framework.

## Methodology

The research contains five complementary layers:

1. multivariate HAC / Newey-West factor regressions;
2. direct tests of the Bitcoin-minus-gold coefficient differences;
3. joint Wald tests of the full sensitivity vector;
4. conditional and stress-tail analysis across 1, 5 and 20 sessions;
5. rolling sensitivities and leave-one-year-out robustness.

Stress-tail inference distinguishes raw overlapping windows from a publication-level summary based on non-overlapping episodes.

NFCI is explicitly retained only as a revised, ex-post robustness classification and never enters the primary factor model.

## Research assurance

The repository contains an offline assurance layer that verifies the frozen publication package without querying external APIs.

Controls include:

- SHA-256 integrity of the publication snapshot;
- exact sample and primary-regression counts;
- primary factor-set enforcement;
- joint Wald result integrity;
- NYSE Arca early-close alignment;
- explicit BTC missing-session accounting;
- CPI publication-date causality;
- NFCI ex-post labeling;
- non-overlap of the selected stress episodes;
- presence of the committed figures and tables.

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" bash scripts/run_research_assurance.sh
```

Expected terminal result:

```text
RESEARCH_ASSURANCE_PASS
```

GitHub Actions runs the offline assurance under Python 3.11, 3.12 and 3.13.

The live public-data reproduction is available manually through `workflow_dispatch`.

See [`RESEARCH_ASSURANCE.md`](RESEARCH_ASSURANCE.md).

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── research-ci.yml
├── outputs/
│   └── digital_gold_v4_1_1/
│       ├── assurance/
│       ├── data/
│       ├── figures/
│       ├── report/
│       └── tables/
├── scripts/
│   ├── build_publication_manifest.py
│   ├── reproduce_live.sh
│   ├── run_research_assurance.sh
│   └── verify_research_snapshot.py
├── tests/
│   └── test_research_assurance.py
├── DATA_PROVENANCE.md
├── LICENSE
├── NOTICE
├── PUBLICATION_MANIFEST.json
├── README.md
├── REPRODUCIBILITY.md
├── RESEARCH_ASSURANCE.md
├── newsletter_digital_gold.py
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

## Reproduction

Create an isolated environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Verify the frozen research snapshot:

```bash
bash scripts/run_research_assurance.sh
```

Re-run the methodology against current public sources:

```bash
bash scripts/reproduce_live.sh
```

A live run demonstrates methodological reproducibility. It is not expected to remain bit-for-bit identical if upstream providers revise historical data or interfaces.

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## Interpretation

The research supports a narrower conclusion than the slogan “Bitcoin is not digital gold”.

The evidence indicates that:

> The “digital gold” analogy describes some properties of Bitcoin, but it describes its historical financial behavior much less completely.

In particular, the dollar relationship is comparatively similar while equity-stress, risk-aversion and credit behavior differ materially.

## License

Original code, tests, automation and documentation are published under the Apache License 2.0.

Third-party market data remain subject to the terms and rights applicable to their respective providers.

## Disclaimer

This repository is provided for quantitative research and financial education.

It does not constitute investment advice, a recommendation, a forecast, an offer, or a solicitation to buy or sell Bitcoin, gold, an ETF, or any other financial instrument.
