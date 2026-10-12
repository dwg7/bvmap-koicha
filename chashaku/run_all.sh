#!/usr/bin/env bash
# Reproduce the whole chashaku measurement. Fetching from GSI only happens in fetch.sh (skipped if extracts exist).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x tools/mlt-0.4.3/mlt ] || tools/fetch-mlt.sh
chashaku/fetch.sh
python3 -I chashaku/anatomy.py
python3 -I chashaku/measure.py
python3 -I chashaku/validate.py
python3 -I chashaku/encode_mlt.py
MLT_TAG=sortauto python3 -I chashaku/encode_mlt.py --sort auto
python3 -I chashaku/summarize.py > chashaku/results/summary.md
python3 -I chashaku/summarize.py sortauto > /dev/null
python3 -I chashaku/layer_probe.py
python3 -I chashaku/compare.py > chashaku/results/compare.md
python3 -I chashaku/anatomy_tables.py > chashaku/results/anatomy_tables.md
