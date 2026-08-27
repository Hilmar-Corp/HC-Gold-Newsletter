#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

python newsletter_digital_gold.py     --start 2017-08-17     --end 2026-08-26     --outdir outputs/live_reproduction     --bootstrap-reps 2000
