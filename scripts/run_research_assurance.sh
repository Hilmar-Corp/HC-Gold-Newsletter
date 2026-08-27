#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

python -m py_compile     newsletter_digital_gold.py     scripts/verify_research_snapshot.py     scripts/build_publication_manifest.py

python -m ruff check     newsletter_digital_gold.py     scripts     tests

python -m pytest -q

python scripts/verify_research_snapshot.py

python scripts/build_publication_manifest.py     --verify

echo "RESEARCH_ASSURANCE_PASS"
