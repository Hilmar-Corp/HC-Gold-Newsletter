#!/usr/bin/env python3
"""Fail-closed repository governance checks for the frozen research package."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_OUTPUT_TREE = "9b025b4afefbe177222f0249be3a3e8a9345321f"
EXPECTED_FACTORS = ["equity", "usd", "real_rate"]
EXPECTED_MISSING = ["2017-09-06", "2018-02-08"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_repository() -> None:
    required = [
        "README.md",
        "RESEARCH_ASSURANCE.md",
        "REPRODUCIBILITY.md",
        "DATA_PROVENANCE.md",
        "DATA_NOTICE.md",
        "research_contract.json",
        "source_registry.json",
        "config/research_spec.json",
        "config/canonical_scripts.txt",
        "evidence/research_assurance_snapshot.json",
        "PUBLICATION_MANIFEST.json",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), f"missing controlled file: {rel}"

    spec = load_json(ROOT / "config/research_spec.json")
    contract = load_json(ROOT / "research_contract.json")
    sources = load_json(ROOT / "source_registry.json")
    evidence = load_json(ROOT / "evidence/research_assurance_snapshot.json")

    assert spec["frozen_version"] == "V4.1.1"
    assert spec["status"] == "frozen"
    assert spec["primary_model"]["factors"] == EXPECTED_FACTORS
    assert contract["canonical_factor_set"] == EXPECTED_FACTORS
    assert contract["primary_hypothesis"]["reference_result"]["df"] == 3
    assert evidence["publication_decision"] == "PASS_V4_1_1_GEL"
    assert evidence["key_controls"]["btc_missing_sessions"] == EXPECTED_MISSING
    assert evidence["key_controls"]["tail_selected_windows_non_overlapping"] is True

    source_by_id = {item["id"]: item for item in sources["sources"]}
    assert source_by_id["fred_nfci"]["point_in_time_interpretation"] is False
    assert "excluded from primary model" in source_by_id["fred_nfci"]["known_limitations"]
    assert source_by_id["fred_hy_oas"]["role"] == "recent-window credit robustness"

    canonical = [
        line.strip()
        for line in (ROOT / "config/canonical_scripts.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert canonical
    for rel in canonical:
        assert (ROOT / rel).is_file(), f"canonical script missing: {rel}"

    tracked = git_output("ls-files").splitlines()
    forbidden_fragments = ("/.venv/", "/cache/", "/.env")
    for rel in tracked:
        normalized = f"/{rel}"
        assert not any(fragment in normalized for fragment in forbidden_fragments), (
            f"forbidden tracked path: {rel}"
        )

    output_tree = git_output("rev-parse", "HEAD:outputs/digital_gold_v4_1_1")
    assert output_tree == EXPECTED_OUTPUT_TREE, (
        f"frozen output tree mismatch: {output_tree} != {EXPECTED_OUTPUT_TREE}"
    )

    print("REPOSITORY_ASSURANCE_PASS")


if __name__ == "__main__":
    verify_repository()
