# build/

Builds a **regional** bvmap-koicha PMTiles (MLT) from the extracts used by chashaku (DECISIONS D9).

```bash
build/build.sh tokyo                                   # -> data/koicha/bvmap-koicha-tokyo.pmtiles (git-ignored)
python3 -I style/make_koicha_starlight.py --source-url pmtiles://http://127.0.0.1:8765/data/koicha/bvmap-koicha-tokyo.pmtiles -o data/koicha/style-local.json
python3 viewer/serve.py 8765                  # static server with Range support (from the repo root)
# http://127.0.0.1:8765/viewer/koicha.html?z=14
```

The arrangement is `hyp` (D3/D6): koicha z3-z14 bundle the bvmap z+1 tiles, z15 bundles z16 minus `vt_flag17=2` and the four
z17-only layers, z16 is bvmap z16 minus `vt_flag17=0`; z17+ is overzoom. Only bundling and dropping, no feature edits.

**Regional means** the tiles are bundled from the bvmap tiles that were extracted. At low zoom an extract holds one bvmap tile
whose bbox is larger than the area, so a koicha z3 tile is a quarter-tile (its siblings are not extracted) and the map ends at
bvmap tile edges. A nationwide build would extract everything and have no such edges.

## Hokkaido (spatial-ID cell, DECISIONS D18)

```bash
build/build.sh hokkaido      # cell 4/14/5 from build/regions.tsv: extracts bvmap z4-16 once (dry-run guarded, ~2.6GB), builds, converts to MLT
python3 build/stats_pmtiles.py data/koicha/bvmap-koicha-hokkaido.pmtiles
```
Needs ~12GB free (extract 2.5GB + mbtiles 3.9GB + PMTiles 3.2GB). A cell is nested with all lower cells, so every koicha tile at zoom >= the cell zoom is complete.

