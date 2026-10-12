#!/usr/bin/env bash
# Build a regional bvmap-koicha PMTiles (MLT) for one area of chashaku/areas.tsv:  build/build.sh tokyo
# Needs: pmtiles, tools/mlt-0.4.3/mlt (tools/fetch-mlt.sh). Talks to GSI only after a --dry-run tile-count check (DECISIONS D5).
set -euo pipefail
cd "$(dirname "$0")/.."
area=${1:?usage: build/build.sh <area in chashaku/areas.tsv>}
bbox=$(awk -F'\t' -v a="$area" '$1==a {print $2}' chashaku/areas.tsv)
[ -n "$bbox" ] || { echo "unknown area: $area" >&2; exit 1; }
SRC=https://cyberjapandata.gsi.go.jp/xyz/optimal_bvmap-v1/optimal_bvmap-v1.pmtiles
MAX_TILES=${MAX_TILES:-5000}
[ -x tools/mlt-0.4.3/mlt ] || tools/fetch-mlt.sh
chashaku/fetch.sh                                            # z13-16 of all areas (skips existing extracts)
low=data/bvmap/$area-z4-13.pmtiles
if [ ! -f "$low" ]; then                                     # z4-13 of this area (a few dozen tiles)
  n=$(pmtiles extract "$SRC" "$low" --bbox="$bbox" --minzoom=4 --maxzoom=13 --dry-run 2>&1 | tr '\r' '\n' | sed -n 's/.*result tile entries \([0-9]*\).*/\1/p' | tail -1)
  echo "$area z4-13: $n tiles"
  [ -n "$n" ] && [ "$n" -le "$MAX_TILES" ] || { echo "refusing: tile count '$n' > $MAX_TILES" >&2; exit 1; }
  pmtiles extract "$SRC" "$low" --bbox="$bbox" --minzoom=4 --maxzoom=13 --download-threads=2 >/dev/null 2>&1
  date -u +%FT%TZ > "data/bvmap/$area-z4-13.FETCHED_AT.txt"
fi
python3 -I build/build_koicha.py "$area"                     # -> data/koicha/<area>.mvt.mbtiles
rm -f "data/koicha/$area.pmtiles"
tools/mlt-0.4.3/mlt convert --verify "data/koicha/$area.mvt.mbtiles" "data/koicha/$area.pmtiles"
ls -la "data/koicha/$area.pmtiles"
