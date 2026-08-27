# Bitcoin–Gold Macro-Factor Study

[![Research assurance](https://github.com/Hilmar-Corp/HC-Gold-Newsletter/actions/workflows/research-ci.yml/badge.svg?branch=main)](https://github.com/Hilmar-Corp/HC-Gold-Newsletter/actions/workflows/research-ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB)
![Research](https://img.shields.io/badge/research-cross--asset%20macro-2ea44f)
![Assurance](https://img.shields.io/badge/assurance-fail--closed-2ea44f)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Reproducible empirical research package for comparing Bitcoin and gold across macro-financial factors, stress environments and allocation-relevant risk states.**

This repository contains the canonical empirical pipeline, frozen analytical artifacts, validation framework and research-assurance controls for the HilmarCorp Bitcoin–Gold Macro-Factor Study.

The repository is intended as a controlled quantitative-research package rather than as the research note itself.

---

## Research question

Bitcoin is frequently described as “digital gold”.

That analogy can refer to scarcity, monetary properties or non-sovereign settlement characteristics. Those properties do not imply that Bitcoin and gold provide the same financial function inside a portfolio.

The empirical question studied here is narrower:

> Do Bitcoin and gold exhibit sufficiently similar sensitivities to major macro-financial risks for the “digital gold” analogy to be informative from an asset-allocation perspective?

The study evaluates similarity and divergence across:

- US equity risk;
- the broad US dollar;
- US real interest rates;
- acute risk-aversion shocks;
- credit stress;
- financial-condition stress;
- inflation states and CPI publication events.

The research does not attempt to determine which asset is superior.

It does not estimate an optimal Bitcoin or gold allocation.

It does not constitute a trading strategy.

---

## Research scope

### Assets

Primary Bitcoin market:

    Binance Spot BTCUSDT

Bitcoin source frequency:

    1 hour

Gold proxy:

    SPDR Gold Shares (GLD)

Gold valuation frequency:

    US market sessions

Trading calendar:

    NYSE Arca / ARCX

Requested research period:

    2017-08-17 to 2026-08-26

Frozen synchronized price observations:

    2,265

Primary regression observations:

    2,262

Frozen research version:

    V4.1.1

### Primary macro-financial factors

The canonical three-factor specification contains only:

    US equities
    broad US dollar
    US 10-year real yield

The corresponding source series are:

    SP500
    DTWEXBGS
    DFII10

Risk-aversion, credit, financial-condition and inflation variables are analyzed in separate controlled modules.

They are not allowed to reduce or contaminate the primary factor sample.

---

## Research design

The primary model estimates contemporaneous macro-financial sensitivity rather than return predictability.

For asset \(i\):

```math
r_{i,t}
=
\alpha_i
+
\beta_{i,\mathrm{EQ}} r_{\mathrm{EQ},t}
+
\beta_{i,\mathrm{USD}} r_{\mathrm{USD},t}
+
\beta_{i,\mathrm{RR}} \Delta y^{\mathrm{real}}_t
+
\varepsilon_{i,t}
```

The cross-asset comparison is performed directly through the spread:

```math
r_{\mathrm{BTC},t} - r_{\mathrm{Gold},t}
```

For each factor \(k\):

```math
\Delta\beta_k
=
\beta_{\mathrm{BTC},k}
-
\beta_{\mathrm{Gold},k}
```

The primary joint null is:

```math
H_0:
\Delta\beta_{\mathrm{EQ}}
=
\Delta\beta_{\mathrm{USD}}
=
\Delta\beta_{\mathrm{RR}}
=
0
```

The frozen one-day joint Wald test is:

```text
chi2(3) = 78.36454955707579
p       = 6.88325332861443e-17
```

The joint null of an identical three-factor sensitivity profile is rejected on the frozen sample.

This is an empirical statement about the selected sample and specification. It is not a structural theorem about either asset.

---

## Estimation conventions

The canonical analysis uses:

- logarithmic asset returns;
- logarithmic equity and dollar returns;
- changes in the 10-year real yield in percentage points;
- OLS estimation;
- HAC / Newey–West covariance estimation;
- 1-, 5- and 20-session horizons;
- direct Bitcoin-minus-gold coefficient-difference estimation;
- joint Wald tests;
- winsorized robustness specifications;
- pre/post subsamples;
- rolling sensitivity diagnostics;
- leave-one-year-out robustness.

Multi-session estimates are treated as overlapping-window estimates where applicable.

Stress analysis separately constructs non-overlapping event episodes for publication-level inference.

---

## Market-calendar construction

GLD trades on NYSE Arca while Bitcoin trades continuously.

A fixed UTC timestamp is not used.

For every GLD session, the canonical alignment uses the actual `ARCX` exchange calendar through `exchange_calendars`.

The synchronization therefore respects:

- US market holidays;
- daylight-saving transitions;
- normal closes;
- early closes;
- actual session dates.

Bitcoin is sampled exactly at the NYSE Arca session close.

The frozen alignment audit contains:

```text
19 early-close sessions
19 exact Bitcoin matches
```

Two traditional-market sessions do not contain an exact matching Binance hourly Bitcoin observation:

```text
2017-09-06
2018-02-08
```

No backward or forward temporal fallback is used in the V4.1.1 canonical specification.

The two missing sessions are explicitly recorded in:

    outputs/digital_gold_v4_1_1/assurance/btc_missing_sessions.csv

---

## Data-source registry

| Research object | Canonical proxy / series | Source |
|---|---|---|
| Bitcoin | BTCUSDT Spot | Binance public market-data API |
| Gold | GLD adjusted close | Yahoo Finance chart endpoint |
| US equities | `SP500` | FRED |
| US 10-year real yield | `DFII10` | FRED |
| Broad US dollar | `DTWEXBGS` | FRED |
| Risk aversion | `VIXCLS` | FRED |
| Long-history credit spread | `BAA10Y` | FRED |
| Recent HY robustness | `BAMLH0A0HYM2` | FRED |
| Financial conditions | `NFCI` | FRED / Chicago Fed |
| CPI | `CPIAUCNS` | FRED |
| CPI release dates | historical CPI calendars | US Bureau of Labor Statistics |
| US trading calendar | `ARCX` | `exchange_calendars` |

Third-party raw-data rights remain with the respective providers.

See:

    DATA_PROVENANCE.md

---

## Data handling policy

The canonical pipeline applies explicit research contracts.

Controls include:

- source identity checks;
- duplicate-date checks;
- monotonic-index checks;
- positive-price checks;
- finite-return checks;
- exact ARCX session alignment;
- early-close validation;
- explicit missing-session accounting;
- primary-factor coverage controls;
- primary-factor-set enforcement;
- exclusion of recent-only HY data from the core sample;
- CPI publication chronology validation;
- explicit ex-post treatment of NFCI;
- non-overlap checks for publication-level stress episodes;
- deterministic frozen-output verification.

Material contract violations fail closed.

A successful script execution is not sufficient by itself to validate the research package.

The assurance layer separately verifies the frozen publication state.

---

## Risk-aversion specification

Daily VIX changes are strongly related to contemporaneous equity moves.

For that reason, raw VIX change is not inserted directly into the canonical three-factor model.

The risk-aversion extension first orthogonalizes the VIX change to the equity return.

The residualized risk-aversion component is then used as a separate extension.

Stress-event analysis also evaluates large VIX increases directly.

This distinction is intended to reduce mechanical double-counting between equity stress and volatility stress.

---

## Credit specification

Credit is intentionally separated from the primary factor model.

Long-history credit analysis uses:

    BAA10Y

Recent high-yield robustness uses:

    BAMLH0A0HYM2

The recent HY series is allowed to operate only on its available window.

It is not allowed to shrink the canonical 2017–2026 primary sample.

The separation is enforced by the research validation layer.

---

## Inflation specification

Inflation is not represented by a forward-filled monthly series and then treated as a daily shock.

The canonical inflation module distinguishes:

1. the latest CPI state available to the market;
2. the change in published inflation between releases;
3. CPI publication-day event observations.

The CPI level is based on:

    CPIAUCNS

Historical release dates are obtained from official BLS CPI release calendars.

For daily conditioning, the inflation state is shifted so that information assigned to a return observation was available by the previous traditional-market close.

No market-consensus series is included.

The study therefore does not claim to measure:

    CPI surprise = published CPI - market consensus

Inflation-surprise conclusions are outside the evidence set of this repository.

---

## Conditional and stress analysis

The repository evaluates factor behavior through both continuous regressions and conditional distributions.

Conditional analysis uses factor quantiles rather than editorially selected market labels.

Stress conditions include:

- bottom equity-return tails;
- large VIX increases;
- high VIX levels;
- large Baa spread widening;
- recent HY spread widening;
- large dollar declines;
- large real-rate increases;
- ex-post NFCI stress states.

The raw multi-session stress windows can overlap.

For publication-level stress inference, the pipeline groups overlapping observations into episodes and retains one extreme anchor per episode.

The frozen publication-level episode table verifies:

    non_overlapping_selected_windows = true

The smallest frozen stress specification contains:

    5 independent episodes

Small-episode results must therefore be interpreted with appropriate sampling caution.

---

## NFCI treatment

NFCI is retained only as an **ex-post robustness classification**.

The historical NFCI series is revised and its FRED observation date is not interpreted as its original point-in-time market-availability date.

The canonical metadata therefore labels it explicitly as:

    EX-POST

NFCI is excluded from the primary factor model.

No point-in-time trading or forecasting claim is based on NFCI in this repository.

---

## Controlled analytical artifacts

Frozen publication outputs are stored under:

    outputs/digital_gold_v4_1_1/

The controlled snapshot is separated into:

    assurance/
    data/
    figures/
    report/
    tables/

Key analytical tables include:

    factor_regressions_v41.csv
    wald_joint_tests_v41.csv
    credit_regressions_isolated.csv
    conditional_quantiles_v4.csv
    tail_episode_summary_v41.csv
    tail_episode_details_v41.csv
    rolling_betas_v4.csv
    robustness_leave_one_year_out_v4.csv
    inflation_event_study.csv
    inflation_state_summary.csv

The README does not act as the research note.

The analytical tables and frozen report contain the controlled numerical results.

---

## Frozen evidence

The V4.1.1 publication state records:

```text
index_unique                     true
index_monotonic                  true
arcx_calendar_session_coverage   1.0
arcx_early_close_sessions        19
arcx_early_close_exact_matches   19
btc_missing_sessions_count       2
core_sample_coverage_ratio       1.0
primary_regression_n             2262
cpi_release_count                115
primary_joint_wald_df            3
primary_joint_wald_chi2          78.36454955707579
primary_joint_wald_p             6.88325332861443e-17
nfci_explicitly_ex_post          true
tail_selected_windows_non_overlap true
```

The canonical validation decision is:

    PASS_V4_1_1_GEL

The controlled validation file is:

    outputs/digital_gold_v4_1_1/assurance/validation_v41.json

---

## Research assurance

The repository uses a fail-closed assurance model for the frozen publication snapshot.

The public assurance path verifies:

- Python compilation;
- static linting;
- deterministic tests;
- frozen validation contracts;
- primary-model factor identity;
- sample counts;
- exact Wald reference values;
- ARCX early-close alignment;
- explicit missing Bitcoin sessions;
- CPI release-date causality;
- NFCI ex-post labeling;
- non-overlapping stress episodes;
- publication-figure presence;
- SHA-256 publication-manifest integrity.

Run:

```bash
make assurance
```

or:

```bash
PATH="$PWD/.venv/bin:$PATH" bash scripts/run_research_assurance.sh
```

Expected final state:

```text
RESEARCH_ASSURANCE_PASS
```

GitHub Actions runs the public assurance path on:

    Python 3.11
    Python 3.12
    Python 3.13

The assurance framework validates internal research consistency.

It is not an independent audit or external asset-manager certification.

---

## Publication manifest

Controlled file identities are recorded in:

    PUBLICATION_MANIFEST.json

The manifest contains SHA-256 identities for the frozen code, documentation, analytical tables, figures and assurance evidence included in the public package.

Any controlled-file modification invalidates the frozen snapshot until the publication manifest is intentionally rebuilt.

Verify:

```bash
python scripts/build_publication_manifest.py --verify
```

---

## Due-diligence review map

The machine-readable review layer is intentionally separate from the editorial README.

A quantitative or model-governance reviewer should begin with:

    docs/DUE_DILIGENCE.md
    research_contract.json
    config/research_spec.json
    source_registry.json
    evidence/research_assurance_snapshot.json

The canonical executable scope is registered in:

    config/canonical_scripts.txt

The controlled frozen publication identity is recorded in:

    PUBLICATION_MANIFEST.json

---

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── research-ci.yml
├── config/
│   ├── canonical_scripts.txt
│   └── research_spec.json
├── docs/
│   └── DUE_DILIGENCE.md
├── evidence/
│   └── research_assurance_snapshot.json
├── outputs/
│   └── digital_gold_v4_1_1/
│       ├── assurance/
│       ├── data/
│       ├── figures/
│       ├── report/
│       └── tables/
├── scripts/
│   ├── research/
│   │   └── verify_repository.py
│   ├── build_publication_manifest.py
│   ├── reproduce_live.sh
│   ├── run_research_assurance.sh
│   └── verify_research_snapshot.py
├── tests/
│   └── test_research_assurance.py
├── tests_public/
│   └── test_repository_contract.py
├── CITATION.cff
├── DATA_NOTICE.md
├── DATA_PROVENANCE.md
├── LICENSE
├── Makefile
├── NOTICE
├── PUBLICATION_MANIFEST.json
├── README.md
├── REPRODUCIBILITY.md
├── RESEARCH_ASSURANCE.md
├── research_contract.json
├── source_registry.json
├── newsletter_digital_gold.py
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

---

## Installation

Create an isolated environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install \
    -r requirements.txt \
    -r requirements-dev.txt
```

---

## Static assurance

Compile the controlled Python scope:

```bash
make compile
```

Run static checks:

```bash
make lint
```

---

## Tests

Run:

```bash
make test
```

The deterministic public and frozen-snapshot suites verify the empirical publication contracts, machine-readable research specification, source-role separation and repository-governance controls.

---

## Full empirical reconstruction

A live reconstruction downloads the currently available public data and reruns the methodology:

```bash
bash scripts/reproduce_live.sh
```

The canonical command is equivalent to:

```bash
python newsletter_digital_gold.py \
    --start 2017-08-17 \
    --end 2026-08-26 \
    --outdir outputs/live_reproduction \
    --bootstrap-reps 2000
```

Live outputs are excluded from the frozen publication snapshot.

See:

    REPRODUCIBILITY.md

---

## Frozen-output verification versus live reconstruction

The repository supports two different forms of reproducibility.

### Frozen-output verification

Checks the exact committed research state:

- controlled source code;
- derived synchronized data;
- analytical tables;
- figures;
- assurance evidence;
- SHA-256 identities.

This is the correct path for verifying the published numerical snapshot.

### Live methodological reconstruction

Reacquires public source data and executes the canonical methodology again.

This validates the documented process against currently available upstream data.

It is not expected to remain bit-for-bit identical if providers revise historical data, metadata, APIs or market calendars.

---

## Interpretation limits

The repository contains observational cross-asset research.

It does not establish:

- causal effects of macro variables on Bitcoin or gold;
- predictive return power;
- future hedging effectiveness;
- optimal portfolio weights;
- trading profitability;
- market timing ability;
- universal gold behavior across all gold instruments;
- universal Bitcoin behavior across all trading venues.

Results remain conditional on:

- Binance Spot BTCUSDT;
- GLD as the selected gold proxy;
- the 2017–2026 sample;
- the selected factor definitions;
- synchronization on NYSE Arca sessions;
- the selected regression and stress conventions.

Statistical significance must not be interpreted as economic predictability.

---

## Research governance

The repository is designed to preserve:

- source traceability;
- explicit analytical scope;
- deterministic data contracts;
- temporal-alignment discipline;
- separation of primary and robustness specifications;
- versioned frozen outputs;
- reproducibility;
- evidence integrity;
- fail-closed publication assurance;
- resistance to unsupported editorial claims.

The canonical research state is versioned.

A material methodological change requires:

1. a new research version;
2. regenerated analytical outputs;
3. an updated validation decision;
4. rebuilt publication evidence;
5. an updated SHA-256 publication manifest.

The repository does not claim endorsement or certification by any external asset manager, quantitative investment firm, regulator or benchmark administrator.

---

## License

Original HilmarCorp code, tests, automation and documentation are released under the Apache License 2.0.

See:

    LICENSE
    NOTICE

Third-party market data are outside the Apache-2.0 grant.

---

## Disclaimer

This repository is provided for quantitative research and financial-education purposes.

Nothing in this repository constitutes investment advice, portfolio management, a recommendation, a forecast, order execution, a solicitation or an offer to buy or sell Bitcoin, gold, GLD or any other financial instrument.

Historical observations are not indicative of future outcomes.
