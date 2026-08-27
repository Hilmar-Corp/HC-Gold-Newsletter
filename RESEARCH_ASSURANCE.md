# Research assurance

## Objective

The assurance layer verifies the traceability, numerical integrity, temporal alignment and publication contracts of the frozen research:

**L’or numérique est-il une bonne comparaison ?**

It does not certify investment performance, future behavior or an independent external review.

## Evidence levels

| Level | Meaning | Application |
|---|---|---|
| `artifact-verified` | Published files match their recorded SHA-256 hashes | code, documentation, tables, figures, data and assurance traces |
| `data-contract-verified` | The frozen dataset satisfies declared structural constraints | dates, uniqueness, positivity, sample size and factor coverage |
| `temporal-alignment-verified` | Cross-market synchronization follows the stated trading calendar | exact NYSE Arca closes, including early closes |
| `model-contract-verified` | The primary regression contains only the declared factor set | equities, dollar, real yield |
| `inference-verified` | The published primary joint test is present and numerically consistent | Wald chi-square and p-value |
| `stress-episode-verified` | Publication-level stress windows do not overlap | tail episode summary |
| `causality-contract-verified` | CPI conditioning respects release chronology | actual BLS release dates and causal-release flag |
| `code-reproducible` | The methodology can be re-executed against public sources | canonical Python runner |

## Automated controls

The offline verifier checks:

- global publication-manifest SHA-256 hashes;
- V4.1.1 validation status;
- 2,262 primary return observations;
- 100% primary core-sample coverage after asset-return availability;
- exact primary factor set: `equity`, `usd`, `real_rate`;
- absence of credit, VIX and NFCI from the primary core specification;
- one-day joint Wald statistic and degrees of freedom;
- exact ARCX session-calendar coverage;
- all 19 early closes matched to an exact Bitcoin hourly observation;
- the two explicitly documented missing Bitcoin sessions;
- CPI release-month uniqueness and causal publication ordering;
- explicit ex-post NFCI treatment;
- non-overlap of selected stress episodes;
- presence of every committed publication figure.

## Frozen reference values

Primary joint test:

```text
chi2 = 78.36454955707579
df   = 3
p    = 6.88325332861443e-17
```

Frozen missing Bitcoin sessions:

```text
2017-09-06
2018-02-08
```

Early-close sessions:

```text
19 detected
19 exact Bitcoin matches
```

## Local execution

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
bash scripts/run_research_assurance.sh
```

Expected final line:

```text
RESEARCH_ASSURANCE_PASS
```

## Continuous integration

GitHub Actions runs the offline assurance under Python 3.11, 3.12 and 3.13.

Third-party GitHub actions are pinned to immutable commit SHAs.

The public-data reproduction is deliberately manual because external providers can be unavailable or revise historical data.

## Limits

This is an internal automated assurance framework.

It verifies the consistency of the research package against declared contracts.

It must not be described as an independent audit, regulatory certification or validation of future investment outcomes.
