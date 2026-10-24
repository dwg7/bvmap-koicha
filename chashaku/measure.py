"""chashaku/measure.py — build the three tile arrangements from bvmap extracts and measure MVT sizes.

Arrangements (see CLAUDE.md / DECISIONS.md D3):
  bvmap  : bvmap tiles as they are (z13-16).
  hyp    : koicha z13/z14 = 4 bvmap tiles of z+1 bundled; z15 = 4 bvmap z16 tiles bundled with
           vt_flag17=2 features and the four z17-only layers dropped; z16 = bvmap z16 with vt_flag17=0 dropped.
  contra : koicha z13/z14 as hyp; z15 = 4 bvmap z16 tiles bundled as-is (z16 + z17 content, extent x2). No z16.

Only bundling (coordinate translation, extent x2) and dropping are applied; features are never edited.
Outputs: data/variants/<area>/<variant>/<z>/<x>/<y>.mvt (raw MVT) and chashaku/results/tiles_mvt_only.csv.
"""
import csv
import gzip
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import mvt
import pmtiles_reader as pr

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "..", "data")
Z17_ONLY_LAYERS = ("RdEdg", "RdCompt", "RailTrCL", "StrctLine")
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
E = 4096


def flag17_pred(drop_value):
    """keep(layer, feat): drop features whose vt_flag17 == drop_value (features without the key are kept)."""
    cache = {}

    def keep(layer, feat):
        hit = cache.get(id(layer))
        if hit is None or hit[0] is not layer:   # keep a reference: id() is reused after GC
            fk = layer.keys.index("vt_flag17") if "vt_flag17" in layer.keys else -1
            cache[id(layer)] = hit = (layer, fk)
        fk = hit[1]
        if fk < 0:
            return True
        t = feat.tags
        for i in range(0, len(t), 2):
            if t[i] == fk:
                v = mvt.decode_value(layer.values[t[i + 1]])
                return int(v) != drop_value
        return True
    return keep


def bundle(tiles, z, x, y, src_z, transform=None):
    """Bundle bvmap tiles at src_z (= z+1) covering koicha tile (z,x,y). Returns (layers, n_children)."""
    assert src_z == z + 1
    kids = []
    for dy in (0, 1):
        for dx in (0, 1):
            t = tiles.get((src_z, 2 * x + dx, 2 * y + dy))
            if t is not None:
                layers = transform(t) if transform else t
                kids.append((layers, dx * E, dy * E))
    if not kids:
        return None, 0
    return mvt.merge_children(kids, 2 * E), len(kids)


def stats(layers):
    return (sum(len(l.features) for l in layers),
            sum(mvt.count_vertices(f.geom) for l in layers for f in l.features))


def main():
    out_rows = []
    for area in AREAS:
        src = {}
        stored = {}
        for z, x, y, b in pr.iter_tiles(os.path.join(DATA, "bvmap", area + ".pmtiles")):
            src[(z, x, y)] = mvt.decode_tile(gzip.decompress(b))
            stored[(z, x, y)] = len(b)

        def emit(variant, z, x, y, layers, nchild, stored_gz=None):
            raw = mvt.encode_tile(layers)
            d = os.path.join(DATA, "variants", area, variant, str(z), str(x))
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{y}.mvt"), "wb").write(raw)
            nf, nv = stats(layers)
            out_rows.append([area, variant, z, x, y, nchild, len(raw), len(gzip.compress(raw, 9)),
                             stored_gz if stored_gz is not None else "", nf, nv,
                             max((l.extent for l in layers), default=0)])

        # --- bvmap baseline
        for (z, x, y), layers in sorted(src.items()):
            emit("bvmap", z, x, y, layers, 1, stored[(z, x, y)])

        # --- z13/z14 (shared by hyp and contra)
        for z in (13, 14):
            parents = sorted({(x // 2, y // 2) for (zz, x, y) in src if zz == z + 1})
            for (x, y) in parents:
                layers, n = bundle(src, z, x, y, z + 1)
                for v in ("hyp", "contra"):
                    emit(v, z, x, y, layers, n)

        # --- z15
        parents15 = sorted({(x // 2, y // 2) for (zz, x, y) in src if zz == 16})
        drop_f2 = flag17_pred(2)
        for (x, y) in parents15:
            layers, n = bundle(src, 15, x, y, 16,
                               transform=lambda t: mvt.filter_layers(t, Z17_ONLY_LAYERS, drop_f2))
            emit("hyp", 15, x, y, layers, n)
            layers, n = bundle(src, 15, x, y, 16)
            emit("contra", 15, x, y, layers, n)

        # --- z16 (hyp only)
        keep_not0 = flag17_pred(0)
        for (zz, x, y), t in sorted(src.items()):
            if zz == 16:
                emit("hyp", 16, x, y, mvt.filter_layers(t, (), keep_not0), 1)
        print(area, "done", len(src), "source tiles", flush=True)

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "tiles_mvt_only.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["area", "variant", "z", "x", "y", "n_children", "mvt_raw", "mvt_gz9", "bvmap_stored_gz",
                    "features", "vertices", "extent"])
        w.writerows(out_rows)


if __name__ == "__main__":
    main()
