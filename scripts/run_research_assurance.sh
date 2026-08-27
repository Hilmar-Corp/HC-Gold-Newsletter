#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

python -m py_compile $(cat config/canonical_scripts.txt)

python -m ruff check \
    $(cat config/canonical_scripts.txt) \
    tests \
    tests_public \
    scripts

python -m pytest -q tests tests_public

python scripts/verify_research_snapshot.py
python scripts/research/verify_repository.py
python scripts/build_publication_manifest.py --verify

echo "RESEARCH_ASSURANCE_PASS"
