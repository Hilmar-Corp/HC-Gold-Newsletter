# Reproducibility

## Two reproducibility levels

This repository separates exact snapshot verification from live methodological reproduction.

### 1. Frozen snapshot verification

The committed publication package is the numerical reference for the research note.

Verification is offline and does not query external APIs.

Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
bash scripts/run_research_assurance.sh
```

Expected result:

```text
RESEARCH_ASSURANCE_PASS
```

This checks the committed SHA-256 manifest and the economic / data contracts documented in `RESEARCH_ASSURANCE.md`.

### 2. Live public-data reproduction

Run:

```bash
bash scripts/reproduce_live.sh
```

The script executes the V4.1.1 methodology against the current public interfaces and writes to:

```text
outputs/live_reproduction/
```

That directory is ignored by Git.

A live run is not a bit-for-bit regression test against the frozen publication package.

## Frozen command

The published methodology corresponds to:

```bash
python newsletter_digital_gold.py \
  --start 2017-08-17 \
  --end 2026-08-26 \
  --outdir outputs/live_reproduction \
  --bootstrap-reps 2000
```

The synchronized tradable-asset sample ends on the latest GLD session available in the requested period.

## Environment

Supported assurance environments:

- Python 3.11
- Python 3.12
- Python 3.13

The original local certification run was performed in a separate local environment. Cross-version CI is used for the offline assurance layer.

## Network reproducibility

The live experiment depends on public endpoints operated by Yahoo Finance, Binance, FRED and the US Bureau of Labor Statistics.

A network failure does not invalidate the committed frozen snapshot.

For this reason GitHub Actions runs the live reproduction only when manually requested through `workflow_dispatch`.

## Publication contract

The frozen snapshot must not be modified silently.

Any material research change requires:

1. a new research version;
2. regenerated outputs;
3. updated research documentation;
4. a rebuilt `PUBLICATION_MANIFEST.json`;
5. a passing offline assurance run.
