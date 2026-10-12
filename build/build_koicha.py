#!/usr/bin/env python3
"""build/build_koicha.py — build a regional bvmap-koicha tile set (the `hyp` arrangement, DECISIONS D3/D6) as an MVT mbtiles.

  koicha z3-z14 : the 4 bvmap tiles of z+1 bundled (coordinates translated, extent x2)
  koicha z15    : 4 bvmap z16 tiles bundled; vt_flag17=2 features and the z17-only layers (RdEdg, RdCompt, RailTrCL, StrctLine) dropped
  koicha z16    : bvmap z16 with vt_flag17=0 features dropped
Only bundling and dropping; features are never edited. Tiles whose bvmap children lie outside the extracted area are
partial (bundled from the children that exist), so the result is regional (see build/README.md).
Input : data/bvmap/<area>.pmtiles (z13-16) + data/bvmap/<area>-z4-13.pmtiles (z4-13), both from `pmtiles extract`
Output: data/koicha/bvmap-koicha-<area>.mvt.mbtiles  (then `mlt convert` -> PMTiles, see build/build.sh)
"""
import gzip
import json
import os
import sqlite3
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "chashaku", "lib"))
sys.path.insert(0, os.path.join(ROOT, "chashaku"))
import mvt
import pmtiles_reader as pr
from measure import Z17_ONLY_LAYERS, flag17_pred

area = sys.argv[1]
bbox = [float(v) for v in dict(l.split("\t") for l in open(os.path.join(ROOT, "chashaku", "areas.tsv")).read().split("\n") if l)[area].split(",")]
D = os.path.join(ROOT, "data")
src = {}
for f in (f"{area}-z4-13.pmtiles", f"{area}.pmtiles"):
    for z, x, y, b in pr.iter_tiles(os.path.join(D, "bvmap", f)):
        src[(z, x, y)] = mvt.decode_tile(gzip.decompress(b))
print("bvmap tiles:", len(src), sorted({k[0] for k in src}))


def bundle(z, x, y, prep=None):
    kids = []
    for dy in (0, 1):
        for dx in (0, 1):
            t = src.get((z + 1, 2 * x + dx, 2 * y + dy))
            if t is None:
                continue
            ext = {l.extent for l in t}
            assert len(ext) == 1, ext
            e = ext.pop()
            kids.append((prep(t) if prep else t, dx * e, dy * e, e))
    if not kids:
        return None
    assert len({k[3] for k in kids}) == 1
    return mvt.merge_children([k[:3] for k in kids], 2 * kids[0][3])


out = {}
for z in range(3, 15):
    for (x, y) in sorted({(k[1] // 2, k[2] // 2) for k in src if k[0] == z + 1}):
        out[(z, x, y)] = bundle(z, x, y)
drop2 = flag17_pred(2)
for (x, y) in sorted({(k[1] // 2, k[2] // 2) for k in src if k[0] == 16}):
    out[(15, x, y)] = bundle(15, x, y, lambda t: mvt.filter_layers(t, Z17_ONLY_LAYERS, drop2))
drop0 = flag17_pred(0)
for (z, x, y), t in sorted(src.items()):
    if z == 16:
        out[(16, x, y)] = mvt.filter_layers(t, (), drop0)

os.makedirs(os.path.join(D, "koicha"), exist_ok=True)
path = os.path.join(D, "koicha", f"bvmap-koicha-{area}.mvt.mbtiles")
if os.path.exists(path):
    os.remove(path)
db = sqlite3.connect(path)
db.executescript("CREATE TABLE metadata (name TEXT, value TEXT); CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB);"
                 "CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);")
layers = {}
for (z, x, y), L in out.items():
    db.execute("INSERT INTO tiles VALUES (?,?,?,?)", (z, x, (1 << z) - 1 - y, gzip.compress(mvt.encode_tile(L), 9)))
    for l in L:
        layers.setdefault(l.name, set()).update(l.keys)
meta = {"name": f"bvmap-koicha-{area}", "format": "pbf", "type": "overlay", "version": "1",
        "minzoom": "3", "maxzoom": "16", "bounds": ",".join(map(str, bbox)),
        "center": f"{(bbox[0]+bbox[2])/2},{(bbox[1]+bbox[3])/2},14",
        "description": "bvmap-koicha regional tile set (hyp arrangement). Not an official GSI product.",
        "attribution": "国土地理院最適化ベクトルタイルを加工して作成",
        "json": json.dumps({"vector_layers": [{"id": n, "fields": {k: "String" for k in sorted(ks)}} for n, ks in sorted(layers.items())]})}
db.executemany("INSERT INTO metadata VALUES (?,?)", meta.items())
db.commit()
print("koicha tiles:", len(out), {z: sum(1 for k in out if k[0] == z) for z in range(3, 17)})
print("wrote", path)
