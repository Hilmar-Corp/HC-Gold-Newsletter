from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "outputs" / "digital_gold_v4_1_1"


def test_frozen_validation_passes() -> None:
    data = json.loads(
        (SNAPSHOT / "assurance" / "validation_v41.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["pass"] is True
    assert data["core_sample_coverage_ratio"] == 1.0
    assert data["primary_regression_n"] == 2262


def test_primary_factor_contract() -> None:
    df = pd.read_csv(SNAPSHOT / "tables" / "factor_regressions_v41.csv")
    x = df[
        (df["model"] == "core")
        & (df["sample"] == "full")
        & (df["horizon"] == 1)
        & (~df["winsorized"])
    ]
    assert set(x["factor"]) == {"equity", "usd", "real_rate"}
    assert set(x["n"]) == {2262}


def test_primary_joint_wald_contract() -> None:
    df = pd.read_csv(SNAPSHOT / "tables" / "wald_joint_tests_v41.csv")
    x = df[
        (df["model"] == "core")
        & (df["sample"] == "full")
        & (df["horizon"] == 1)
        & (~df["winsorized"])
    ]
    assert len(x) == 1
    row = x.iloc[0]
    assert int(row["wald_df"]) == 3
    assert np.isclose(row["wald_chi2"], 78.36454955707579, atol=1e-10)
    assert np.isclose(row["wald_p"], 6.88325332861443e-17, rtol=1e-10)


def test_arcx_early_close_alignment() -> None:
    df = pd.read_csv(
        SNAPSHOT / "assurance" / "btc_arcx_alignment_audit.csv"
    )
    assert df["arcx_calendar_session"].all()
    early = df[df["is_early_close"]]
    assert len(early) == 19
    assert early["btc_exact_close_available"].all()


def test_explicit_missing_btc_sessions() -> None:
    df = pd.read_csv(
        SNAPSHOT / "assurance" / "btc_missing_sessions.csv"
    )
    assert set(df["date"]) == {"2017-09-06", "2018-02-08"}
    assert len(df) == 2


def test_cpi_release_causality() -> None:
    df = pd.read_csv(SNAPSHOT / "data" / "cpi_release_calendar.csv")
    assert len(df) == 115
    assert df["reference_month"].is_unique
    assert df["causal_release"].all()


def test_nfci_is_explicitly_ex_post() -> None:
    data = json.loads(
        (SNAPSHOT / "assurance" / "data_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    assert "EX-POST" in data["nfci"].upper()


def test_tail_episode_non_overlap() -> None:
    df = pd.read_csv(
        SNAPSHOT / "tables" / "tail_episode_summary_v41.csv"
    )
    assert len(df) > 0
    assert df["non_overlapping_selected_windows"].all()
    assert int(df["episode_count"].min()) == 5


def test_frozen_daily_panel_contract() -> None:
    df = pd.read_csv(
        SNAPSHOT / "data" / "daily_panel.csv",
        parse_dates=["date"],
    )
    assert len(df) == 2265
    assert df["date"].is_unique
    assert df["date"].is_monotonic_increasing
    assert (df["btc_px"] > 0).all()
    assert (df["gold_px"] > 0).all()


def test_publication_figures_exist() -> None:
    figures = sorted((SNAPSHOT / "figures").glob("*.png"))
    assert len(figures) >= 10
    assert all(path.stat().st_size > 0 for path in figures)
