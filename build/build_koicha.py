#!/usr/bin/env python3
"""build/build_koicha.py — build a regional bvmap-koicha tile set (the `hyp` arrangement, DECISIONS D3/D6) as an MVT mbtiles.
Streaming: tiles are read one koicha tile at a time from the bvmap PMTiles (directory index only in memory), so it scales to ~10^6 tiles.

  koicha z<=14 : the 4 bvmap tiles of z+1 bundled (coordinates translated, extent x2)
  koicha z15   : 4 bvmap z16 tiles bundled; vt_flag17=2 features and the z17-only layers (RdEdg, RdCompt, RailTrCL, StrctLine) dropped
                 (--roads: keep those four layers in z15, so true-width roads can be drawn from z15; DECISIONS D26)
  koicha z16   : bvmap z16 with vt_flag17=0 features dropped
Only bundling and dropping; features are never edited.

Usage:
  build_koicha.py tokyo                              # z3-16 from data/bvmap/tokyo-z4-13.pmtiles + tokyo.pmtiles (chashaku/areas.tsv bbox)
  build_koicha.py hokkaido --cell 4/14/5 --source data/bvmap/hokkaido.pmtiles   # a spatial-ID cell z/x/y; minzoom = cell z
With --cell, only bvmap tiles inside the cell are used, and every koicha tile at zoom >= cell z has all its bvmap children (complete).
Output: data/koicha/bvmap-koicha-<area>.mvt.mbtiles and .metadata.json
"""
import argparse
import gzip
import json
import math
import multiprocessing as mp
import os
import sqlite3
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "chashaku", "lib"))
sys.path.insert(0, os.path.join(ROOT, "chashaku"))
import mvt
import pmtiles_reader as pr
from measure import Z17_ONLY_LAYERS, flag17_pred

D = os.path.join(ROOT, "data")
IDX = []          # PMTilesIndex objects (inherited by forked workers)
DROP2 = flag17_pred(2)
DROP_Z15_LAYERS = Z17_ONLY_LAYERS      # --roads empties this in main() before the workers are forked
DROP0 = flag17_pred(0)


def lookup(z, x, y):
    for ix in IDX:
        b = ix.get(z, x, y)
        if b is not None:
            return mvt.decode_tile(gzip.decompress(b))
    return None


def bundle(z, x, y, prep=None):
    kids = []
    for dy in (0, 1):
        for dx in (0, 1):
            t = lookup(z + 1, 2 * x + dx, 2 * y + dy)
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


def make(job):
    kind, z, x, y = job
    if kind == "b":
        L = bundle(z, x, y)
    elif kind == "f15":
        L = bundle(15, x, y, lambda t: mvt.filter_layers(t, DROP_Z15_LAYERS, DROP2))
    else:
        L = mvt.filter_layers(lookup(16, x, y), (), DROP0)
    if not L:
        return job, None, []
    return job, gzip.compress(mvt.encode_tile(L), 9), sorted({l.name for l in L})


def bbox_of(z, x, y):
    n = 2 ** z
    lon = lambda v: v / n * 360 - 180
    lat = lambda v: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * v / n))))
    return [lon(x), lat(y + 1), lon(x + 1), lat(y)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("area")
    ap.add_argument("--cell")
    ap.add_argument("--source", action="append")
    ap.add_argument("--roads", action="store_true", help="keep the z17-only road layers (RdEdg, RdCompt, ...) in z15; output name gets a -roads suffix")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    area = a.area
    global DROP_Z15_LAYERS
    if a.roads:
        DROP_Z15_LAYERS = ()
    if a.cell:
        cz, cx, cy = map(int, a.cell.split("/"))
        bbox, minzoom = bbox_of(cz, cx, cy), cz
        sources = a.source or [os.path.join(D, "bvmap", f"{area}.pmtiles")]
        where = f"spatial-ID cell {a.cell}"
    else:
        tsv = dict(l.split("\t") for l in open(os.path.join(ROOT, "chashaku", "areas.tsv")).read().split("\n") if l)
        bbox, minzoom = [float(v) for v in tsv[area].split(",")], 3
        sources = a.source or [os.path.join(D, "bvmap", f"{area}-z4-13.pmtiles"), os.path.join(D, "bvmap", f"{area}.pmtiles")]
        where = "bbox " + tsv[area]
    for s in sources:
        IDX.append(pr.PMTilesIndex(s))
    keys = set()
    for ix in IDX:
        keys.update(ix.keys())
    if a.cell:
        def inside(k):
            z, x, y = k
            return z > cz and (x >> (z - cz)) == cx and (y >> (z - cz)) == cy
        keys = {k for k in keys if inside(k)}
        for ix in IDX:                               # neighbours the bbox pulled in must not be visible to lookups
            ix.index = {k: v for k, v in ix.index.items() if k in keys}
    print(f"bvmap tiles: {len(keys):,}; zooms {min(k[0] for k in keys)}-{max(k[0] for k in keys)}; {where}", flush=True)
    jobs = []
    for z in range(minzoom, 15):
        jobs += [("b", z, x, y) for (x, y) in sorted({(k[1] // 2, k[2] // 2) for k in keys if k[0] == z + 1})]
    jobs += [("f15", 15, x, y) for (x, y) in sorted({(k[1] // 2, k[2] // 2) for k in keys if k[0] == 16})]
    jobs += [("f16", 16, k[1], k[2]) for k in sorted(keys) if k[0] == 16]
    print(f"koicha tiles to build: {len(jobs):,}", flush=True)

    os.makedirs(os.path.join(D, "koicha"), exist_ok=True)
    name = f"bvmap-koicha-{area}" + ("-roads" if a.roads else "")
    path = os.path.join(D, "koicha", f"{name}.mvt.mbtiles")
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("CREATE TABLE metadata (name TEXT, value TEXT); CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB);"
                     "CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);")
    layers, per_z, n = set(), {}, 0
    ctx = mp.get_context("fork")
    with ctx.Pool(a.workers) as pool:
        for (kind, z, x, y), data, names in pool.imap_unordered(make, jobs, chunksize=32):
            if data is None:
                continue
            db.execute("INSERT INTO tiles VALUES (?,?,?,?)", (z, x, (1 << z) - 1 - y, data))
            layers.update(names)
            per_z[z] = per_z.get(z, 0) + 1
            n += 1
            if n % 50000 == 0:
                db.commit()
                print(f"  {n:,}/{len(jobs):,}", flush=True)
    orig = pr.read_metadata(sources[-1])
    desc = f"bvmap-koicha regional tile set (hyp arrangement), {where}. Not an official GSI product."
    attribution = "国土地理院最適化ベクトルタイルを加工して作成"
    vl = [dict(l, minzoom=max(l.get("minzoom", 4) - 1, minzoom), maxzoom=16) for l in orig["vector_layers"]]
    meta = {"name": name, "format": "pbf", "type": "overlay", "version": "1", "minzoom": str(minzoom), "maxzoom": "16",
            "bounds": ",".join(f"{v:.6f}" for v in bbox), "center": f"{(bbox[0]+bbox[2])/2:.6f},{(bbox[1]+bbox[3])/2:.6f},{minzoom + 3}",
            "description": desc, "attribution": attribution, "json": json.dumps({"vector_layers": vl})}
    db.executemany("INSERT INTO metadata VALUES (?,?)", meta.items())
    db.commit()
    db.close()
    json.dump({"name": name, "description": desc, "attribution": attribution, "version": "1", "vector_layers": vl},
              open(os.path.join(D, "koicha", f"{name}.metadata.json"), "w"), ensure_ascii=False, indent=1)
    print("koicha tiles:", f"{n:,}", {z: per_z[z] for z in sorted(per_z)})
    print("wrote", path)


if __name__ == "__main__":
    main()
