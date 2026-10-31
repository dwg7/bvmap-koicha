#!/usr/bin/env bash
# Build a regional bvmap-koicha PMTiles (MLT) :  build/build.sh tokyo        (bbox region of chashaku/areas.tsv, z3-16)
#                                                build/build.sh hokkaido     (spatial-ID cell of build/regions.tsv, z4-16)
# Needs: pmtiles, tools/mlt-0.4.3/mlt (tools/fetch-mlt.sh). Talks to GSI only after a --dry-run tile-count check (DECISIONS D5).
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=https://cyberjapandata.gsi.go.jp/xyz/optimal_bvmap-v1/optimal_bvmap-v1.pmtiles
area=${1:?usage: build/build.sh <area> [roads]}
variant=${2:-}                      # "roads": keep the true-width road layers in z15 (prototype, DECISIONS D26)
suffix=${variant:+-$variant}; xflag=${variant:+--$variant}
cell=$(awk -F'\t' -v a="$area" '$1==a && $0 !~ /^#/ {print $2}' build/regions.tsv)
[ -x tools/mlt-0.4.3/mlt ] || tools/fetch-mlt.sh
if [ -n "$cell" ]; then
  # spatial-ID cell: extract bvmap z4-16 inside the cell bbox once (the cell is nested, so every koicha tile >= its zoom is complete)
  bbox=$(python3 -I -c "
import math,sys
z,x,y=map(int,'$cell'.split('/')); n=2**z
lon=lambda v:v/n*360-180; lat=lambda v:math.degrees(math.atan(math.sinh(math.pi*(1-2*v/n))))
print('%.6f,%.6f,%.6f,%.6f'%(lon(x),lat(y+1),lon(x+1),lat(y)))")
  src=data/bvmap/$area.pmtiles
  if [ ! -f "$src" ]; then
    MAX_TILES=${MAX_TILES:-800000}
    n=$(pmtiles extract "$SRC" "$src.tmp" --bbox="$bbox" --minzoom=4 --maxzoom=16 --dry-run 2>&1 | tr '\r' '\n' | sed -n 's/.*result tile entries \([0-9]*\).*/\1/p' | tail -1)
    echo "$area cell $cell [$bbox] z4-16: $n tiles"
    [ -n "$n" ] && [ "$n" -le "$MAX_TILES" ] || { echo "refusing: tile count '$n' > $MAX_TILES" >&2; exit 1; }
    pmtiles extract "$SRC" "$src.tmp" --bbox="$bbox" --minzoom=4 --maxzoom=16 --download-threads=2 >/dev/null 2>&1
    mv "$src.tmp" "$src"; date -u +%FT%TZ > "data/bvmap/$area.FETCHED_AT.txt"
  fi
  python3 -I build/build_koicha.py "$area" --cell "$cell" --source "$src" $xflag
else
bbox=$(awk -F'\t' -v a="$area" '$1==a {print $2}' chashaku/areas.tsv)
[ -n "$bbox" ] || { echo "unknown area: $area" >&2; exit 1; }
MAX_TILES=${MAX_TILES:-5000}
chashaku/fetch.sh                                            # z13-16 of all areas (skips existing extracts)
low=data/bvmap/$area-z4-13.pmtiles
if [ ! -f "$low" ]; then                                     # z4-13 of this area (a few dozen tiles)
  n=$(pmtiles extract "$SRC" "$low" --bbox="$bbox" --minzoom=4 --maxzoom=13 --dry-run 2>&1 | tr '\r' '\n' | sed -n 's/.*result tile entries \([0-9]*\).*/\1/p' | tail -1)
  echo "$area z4-13: $n tiles"
  [ -n "$n" ] && [ "$n" -le "$MAX_TILES" ] || { echo "refusing: tile count '$n' > $MAX_TILES" >&2; exit 1; }
  pmtiles extract "$SRC" "$low" --bbox="$bbox" --minzoom=4 --maxzoom=13 --download-threads=2 >/dev/null 2>&1
  date -u +%FT%TZ > "data/bvmap/$area-z4-13.FETCHED_AT.txt"
fi
python3 -I build/build_koicha.py "$area" $xflag               # -> data/koicha/bvmap-koicha-<area>[-roads].mvt.mbtiles
fi
rm -f "data/koicha/bvmap-koicha-$area$suffix.pmtiles"
tools/mlt-0.4.3/mlt convert --verify "data/koicha/bvmap-koicha-$area$suffix.mvt.mbtiles" "data/koicha/bvmap-koicha-$area$suffix.pmtiles"
pmtiles edit "data/koicha/bvmap-koicha-$area$suffix.pmtiles" --metadata="data/koicha/bvmap-koicha-$area$suffix.metadata.json"
ls -la "data/koicha/bvmap-koicha-$area$suffix.pmtiles"
