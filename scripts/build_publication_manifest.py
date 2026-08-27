#!/usr/bin/env python3
"""Build or verify the publication SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "PUBLICATION_MANIFEST.json"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "live_reproduction",
    "reproduction",
}
EXCLUDED_FILES = {
    "PUBLICATION_MANIFEST.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if rel.name in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if rel.suffix == ".zip":
            continue
        files.append(path)
    return sorted(files)


def build_payload() -> dict:
    files = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in tracked_files()
    }
    return {
        "research": "Is “Digital Gold” a Good Comparison?",
        "hilmarcorp_research_note": "L’or numérique est-il une bonne comparaison ?",
        "frozen_version": "V4.1.1",
        "sample_request": {
            "start": "2017-08-17",
            "end": "2026-08-26",
        },
        "primary_regression_observations": 2262,
        "primary_joint_wald": {
            "chi2": 78.36454955707579,
            "df": 3,
            "p": 6.88325332861443e-17,
        },
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    current = build_payload()

    if args.verify:
        published = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if current != published:
            current_files = current.get("files", {})
            published_files = published.get("files", {})
            missing = sorted(set(published_files) - set(current_files))
            added = sorted(set(current_files) - set(published_files))
            changed = sorted(
                k
                for k in set(current_files) & set(published_files)
                if current_files[k] != published_files[k]
            )
            raise SystemExit(
                "PUBLICATION_MANIFEST_MISMATCH\n"
                f"missing={missing}\nadded={added}\nchanged={changed}"
            )
        print("PUBLICATION_MANIFEST_PASS")
        return

    MANIFEST.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {MANIFEST}")


if __name__ == "__main__":
    main()
