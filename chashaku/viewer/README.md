# chashaku/viewer

Side-by-side rendering check (DECISIONS D7). Left: bvmap converted to MLT, shown at zoom z+1. Right: koicha `hyp` tiles at zoom z,
with the GSI `std.json` style whose zoom thresholds are all shifted by -1 (symbol layers dropped, so no glyph/sprite fetches from GSI).

```bash
npm ci --ignore-scripts --prefix chashaku/viewer     # maplibre-gl 6.14.0, pmtiles 4.5.0 (exact versions in package.json)
python3 -m http.server 8765 --bind 127.0.0.1         # from the repo root; needs data/ from chashaku/run_all.sh
# open http://127.0.0.1:8765/chashaku/viewer/index.html?z=15&c=139.7671,35.6812
```
