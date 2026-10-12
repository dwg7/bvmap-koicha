#!/usr/bin/env bash
# Extract the measurement areas (areas.tsv) from the bvmap PMTiles at z13-16 into data/bvmap/.
# Safety: never talk to GSI before a --dry-run has confirmed a small tile count (see DECISIONS D5).
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=https://cyberjapandata.gsi.go.jp/xyz/optimal_bvmap-v1/optimal_bvmap-v1.pmtiles
MAX_TILES=${MAX_TILES:-5000}
mkdir -p data/bvmap
while IFS=$'\t' read -r name bbox; do
  [ -n "$name" ] && [ -n "$bbox" ] || { echo "bad line in areas.tsv: '$name' '$bbox'" >&2; exit 1; }
  n=$(pmtiles extract "$SRC" "data/bvmap/$name.pmtiles" --bbox="$bbox" --minzoom=13 --maxzoom=16 --dry-run 2>&1 \
        | tr '\r' '\n' | sed -n 's/.*result tile entries \([0-9]*\).*/\1/p' | tail -1)
  echo "$name [$bbox]: $n tiles"
  [ -n "$n" ] && [ "$n" -le "$MAX_TILES" ] || { echo "refusing: tile count '$n' > $MAX_TILES" >&2; exit 1; }
  [ -f "data/bvmap/$name.pmtiles" ] && { echo "  already extracted, skipping"; continue; }
  pmtiles extract "$SRC" "data/bvmap/$name.pmtiles" --bbox="$bbox" --minzoom=13 --maxzoom=16 --download-threads=2 >/dev/null 2>&1
  fetched=1
done < chashaku/areas.tsv
# record provenance only when something was actually fetched (the file keeps the real fetch time)
if [ "${fetched:-0}" = 1 ]; then
  date -u +%FT%TZ > data/bvmap/FETCHED_AT.txt
  curl -sI "$SRC" | grep -i -E "last-modified|etag|content-length" > data/bvmap/source-headers.txt
fi
