#!/usr/bin/env python3
"""Offline verification of the frozen Digital Gold V4.1.1 snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "outputs" / "digital_gold_v4_1_1"
ASSURANCE = SNAPSHOT / "assurance"
DATA = SNAPSHOT / "data"
TABLES = SNAPSHOT / "tables"
FIGURES = SNAPSHOT / "figures"

EXPECTED_MISSING = {"2017-09-06", "2018-02-08"}
EXPECTED_CORE = {"equity", "usd", "real_rate"}
EXPECTED_WALD = 78.36454955707579
EXPECTED_WALD_P = 6.88325332861443e-17


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_snapshot() -> None:
    validation = load_json(ASSURANCE / "validation_v41.json")
    assert validation["pass"] is True
    assert validation["core_sample_coverage_pass"] is True
    assert validation["primary_regression_n"] == 2262
    assert validation["core_return_obs"] == 2262
    assert validation["asset_return_obs"] == 2262
    assert validation["core_factor_set_exact"] is True
    assert validation["forbidden_factor_in_core"] is False

    panel = pd.read_csv(DATA / "daily_panel.csv", parse_dates=["date"])
    assert len(panel) == 2265
    assert panel["date"].is_unique
    assert panel["date"].is_monotonic_increasing
    assert (panel["btc_px"] > 0).all()
    assert (panel["gold_px"] > 0).all()

    reg = pd.read_csv(TABLES / "factor_regressions_v41.csv")
    primary = reg[
        (reg["model"] == "core")
        & (reg["sample"] == "full")
        & (reg["horizon"] == 1)
        & (~reg["winsorized"])
    ]
    assert len(primary) == 3
    assert set(primary["factor"]) == EXPECTED_CORE
    assert primary["n"].nunique() == 1
    assert int(primary["n"].iloc[0]) == 2262

    wald = pd.read_csv(TABLES / "wald_joint_tests_v41.csv")
    w = wald[
        (wald["model"] == "core")
        & (wald["sample"] == "full")
        & (wald["horizon"] == 1)
        & (~wald["winsorized"])
    ]
    assert len(w) == 1
    row = w.iloc[0]
    assert int(row["wald_df"]) == 3
    assert np.isclose(float(row["wald_chi2"]), EXPECTED_WALD, rtol=0, atol=1e-10)
    assert np.isclose(float(row["wald_p"]), EXPECTED_WALD_P, rtol=1e-10, atol=0)

    alignment = pd.read_csv(
        ASSURANCE / "btc_arcx_alignment_audit.csv",
        parse_dates=["date"],
    )
    assert bool(alignment["arcx_calendar_session"].all())
    early = alignment[alignment["is_early_close"]]
    assert len(early) == 19
    assert bool(early["btc_exact_close_available"].all())

    missing = alignment[~alignment["btc_exact_close_available"]]
    missing_dates = set(missing["date"].dt.date.astype(str))
    assert missing_dates == EXPECTED_MISSING
    assert len(missing) == 2

    cpi = pd.read_csv(
        DATA / "cpi_release_calendar.csv",
        parse_dates=["reference_month", "release_date"],
    )
    assert len(cpi) == 115
    assert cpi["reference_month"].is_unique
    assert bool(cpi["causal_release"].all())

    metadata = load_json(ASSURANCE / "data_metadata.json")
    assert "EX-POST" in metadata["nfci"].upper()

    tail = pd.read_csv(TABLES / "tail_episode_summary_v41.csv")
    assert len(tail) > 0
    assert bool(tail["non_overlapping_selected_windows"].all())
    assert int(tail["episode_count"].min()) == 5

    figure_files = sorted(FIGURES.glob("*.png"))
    assert len(figure_files) >= 10
    assert all(p.stat().st_size > 0 for p in figure_files)

    print("SNAPSHOT_VERIFICATION_PASS")


if __name__ == "__main__":
    verify_snapshot()
