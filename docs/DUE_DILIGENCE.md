# Quantitative research due-diligence index

## Purpose

This document is a review map for the frozen V4.1.1 Bitcoin–Gold Macro-Factor Study. It is intended to let an investment-research, risk, model-governance or quantitative due-diligence reviewer identify the canonical assumptions, evidence and limitations without relying on editorial material.

## Canonical scope

Machine-readable research specification:

    config/research_spec.json

Research contract and explicit non-claims:

    research_contract.json

Canonical executable scope:

    config/canonical_scripts.txt

Source registry:

    source_registry.json

## Frozen evidence

Publication decision and key control values:

    evidence/research_assurance_snapshot.json

Full V4.1.1 validation state:

    outputs/digital_gold_v4_1_1/assurance/validation_v41.json

Controlled analytical snapshot:

    outputs/digital_gold_v4_1_1/

Publication identity:

    PUBLICATION_MANIFEST.json

## Primary model

The primary factor model is restricted to equities, broad USD and the US 10-year real yield. Credit, VIX, NFCI and inflation variables are deliberately outside the primary factor set.

The primary cross-asset inference is produced directly on the Bitcoin-minus-gold return spread. The joint hypothesis of an identical three-factor sensitivity vector is tested with a HAC/Newey–West Wald statistic.

Reference one-day result:

    chi2(3) = 78.36454955707579
    p       = 6.88325332861443e-17

## Temporal integrity

Bitcoin is synchronized to the actual NYSE Arca session close, including early closes. Two sessions lack an exact Binance hourly observation and are excluded without fallback.

CPI conditioning is tied to actual BLS release chronology. NFCI is explicitly ex-post and revised; it is not treated as live point-in-time information.

## Stress inference

Raw multi-session tail windows are retained for diagnostics. Publication-level stress inference uses merged episodes and one extreme anchor per episode so selected windows do not overlap.

Small episode counts remain an explicit sampling limitation.

## Reproducibility

Two levels are distinguished:

1. frozen-output verification;
2. live methodological reconstruction from currently available public sources.

The first is deterministic. The second can differ because upstream providers may revise data or interfaces.

See `REPRODUCIBILITY.md`.

## Assurance commands

    make assurance

Expected terminal state:

    RESEARCH_ASSURANCE_PASS

The assurance path compiles canonical code, runs static linting and deterministic tests, verifies the frozen research snapshot, validates repository contracts and verifies the publication manifest.

## Known limitations

- GLD is an ETF proxy, not a physical spot-gold fixing.
- Bitcoin evidence is venue-specific to Binance Spot BTCUSDT for the canonical run.
- The sample contains a limited number of independent macro cycles.
- Inflation analysis does not include market-consensus expectations and therefore does not identify CPI surprises.
- Multi-session stress estimates can have small independent-episode counts.
- NFCI is revised ex-post information.
- Statistical significance does not imply predictive power or causal identification.

## Governance interpretation

The repository is designed to support reproducibility, traceability and controlled empirical review. It does not claim independent validation, external certification, regulatory approval or endorsement by an asset manager.
