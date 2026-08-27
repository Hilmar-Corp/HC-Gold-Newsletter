#!/usr/bin/env python3
"""Build or verify the controlled V4.1.1 publication manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "PUBLICATION_MANIFEST.json"
CONTROLLED_FILES = [
    "newsletter_digital_gold.py",
    "research_contract.json",
    "source_registry.json",
    "config/research_spec.json",
    "evidence/research_assurance_snapshot.json",
]
SNAPSHOT_PATH = "outputs/digital_gold_v4_1_1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_tree_sha(path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=ROOT,
        text=True,
    ).strip()


def build_payload(reference: dict | None = None) -> dict:
    reference = reference or {}
    return {
        "manifest_version": "2.0",
        "research": "Bitcoin–Gold Macro-Factor Study",
        "frozen_version": "V4.1.1",
        "controlled_snapshot": {
            "path": SNAPSHOT_PATH,
            "git_tree_sha": git_tree_sha(SNAPSHOT_PATH),
        },
        "controlled_files": {
            rel: sha256(ROOT / rel)
            for rel in CONTROLLED_FILES
        },
        "reference_results": reference.get("reference_results", {
            "primary_regression_observations": 2262,
            "primary_joint_wald": {
                "chi2": 78.36454955707579,
                "df": 3,
                "p": 6.88325332861443e-17,
            },
        }),
    }


def verify() -> None:
    published = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current = build_payload(published)
    if current != published:
        raise SystemExit(
            "PUBLICATION_MANIFEST_MISMATCH\n"
            + json.dumps({"expected": published, "current": current}, indent=2)
        )
    print("PUBLICATION_MANIFEST_PASS")


def write() -> None:
    previous = (
        json.loads(MANIFEST.read_text(encoding="utf-8"))
        if MANIFEST.exists()
        else {}
    )
    payload = build_payload(previous)
    MANIFEST.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {MANIFEST}")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        write()


if __name__ == "__main__":
    main()
