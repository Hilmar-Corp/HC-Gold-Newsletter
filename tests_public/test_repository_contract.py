from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_machine_readable_research_contract() -> None:
    spec = read_json("config/research_spec.json")
    contract = read_json("research_contract.json")
    assert spec["frozen_version"] == "V4.1.1"
    assert spec["primary_model"]["factors"] == ["equity", "usd", "real_rate"]
    assert contract["canonical_factor_set"] == ["equity", "usd", "real_rate"]
    assert "No causal identification of macro-factor effects." in contract["non_claims"]


def test_source_registry_separates_point_in_time_and_ex_post() -> None:
    registry = read_json("source_registry.json")
    sources = {row["id"]: row for row in registry["sources"]}
    assert sources["fred_nfci"]["point_in_time_interpretation"] is False
    assert sources["arcx_calendar"]["point_in_time_interpretation"] is True
    assert sources["fred_hy_oas"]["role"] == "recent-window credit robustness"


def test_frozen_assurance_snapshot() -> None:
    evidence = read_json("evidence/research_assurance_snapshot.json")
    assert evidence["publication_decision"] == "PASS_V4_1_1_GEL"
    controls = evidence["key_controls"]
    assert controls["core_sample_coverage_ratio"] == 1.0
    assert controls["primary_regression_n"] == 2262
    assert controls["arcx_early_close_exact_btc_matches"] == 19
    assert controls["tail_selected_windows_non_overlapping"] is True


def test_canonical_script_registry_resolves() -> None:
    entries = [
        line.strip()
        for line in (ROOT / "config/canonical_scripts.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert entries
    assert all((ROOT / rel).is_file() for rel in entries)
