"""chashaku/anatomy.py — tile-content statistics for bvmap tiles (z13-16 extracts + a few low-zoom tiles).

Outputs (chashaku/results/):
  anatomy_layers.csv   area,z,layer,tiles,features,vertices,layer_bytes_raw
  anatomy_flag17.csv   area,z,layer,flag17,features,vertices   (flag17 = 'none' when the key is absent)
  anatomy_attrs.csv    area,z,layer,key,features,tag_bytes,value_bytes,key_name_bytes
  anatomy_extent.csv   z,extent,version,layers,tiles
  anatomy_lowzoom.csv  z,layer,features,vertices   (tokyo center tile per zoom, z4-12)
"""
import csv
import glob
import gzip
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import mvt
import pmtiles_reader as pr

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "..", "data", "bvmap")
OUT = os.path.join(ROOT, "results")
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]


def flag_of(layer, feat, fk):
    if fk is None:
        return "n/a"          # layer has no vt_flag17 key at all
    t = feat.tags
    for i in range(0, len(t), 2):
        if t[i] == fk:
            v = mvt.decode_value(layer.values[t[i + 1]])
            return str(int(v)) if isinstance(v, (int, float)) else str(v)
    return "none"             # layer has the key, this feature does not


def main():
    lay = defaultdict(lambda: [0, 0, 0, 0])      # (area,z,layer) -> tiles,features,verts,bytes
    fl = defaultdict(lambda: [0, 0])             # (area,z,layer,flag) -> feats, verts
    at = defaultdict(lambda: [0, 0, 0, 0])       # (area,z,layer,key) -> feats, tagB, valB, keyB
    ex = defaultdict(int)
    for area in AREAS:
        for z, x, y, b in pr.iter_tiles(os.path.join(DATA, area + ".pmtiles")):
            for l in mvt.decode_tile(gzip.decompress(b)):
                fk = l.keys.index("vt_flag17") if "vt_flag17" in l.keys else None
                k = (area, z, l.name)
                lay[k][0] += 1
                lay[k][1] += len(l.features)
                lay[k][3] += len(mvt.encode_layer(l))
                ex[(z, l.extent, l.version, l.name)] += 1
                used = defaultdict(set)
                for f in l.features:
                    nv = mvt.count_vertices(f.geom)
                    lay[k][2] += nv
                    fv = fl[(area, z, l.name, flag_of(l, f, fk))]
                    fv[0] += 1
                    fv[1] += nv
                    for i in range(0, len(f.tags), 2):
                        key = l.keys[f.tags[i]]
                        a = at[(area, z, l.name, key)]
                        a[0] += 1
                        a[1] += mvt.varint_len(f.tags[i]) + mvt.varint_len(f.tags[i + 1])
                        used[key].add(f.tags[i + 1])
                for key, vs in used.items():
                    a = at[(area, z, l.name, key)]
                    a[2] += sum(1 + mvt.varint_len(len(l.values[v])) + len(l.values[v]) for v in vs)
                    a[3] += 1 + 1 + len(key.encode())
    with open(os.path.join(OUT, "anatomy_layers.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["area", "z", "layer", "tiles", "features", "vertices", "layer_bytes_raw"])
        for k in sorted(lay): w.writerow([*k, *lay[k]])
    with open(os.path.join(OUT, "anatomy_flag17.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["area", "z", "layer", "flag17", "features", "vertices"])
        for k in sorted(fl): w.writerow([*k, *fl[k]])
    with open(os.path.join(OUT, "anatomy_attrs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["area", "z", "layer", "key", "features", "tag_bytes", "value_bytes", "key_name_bytes"])
        for k in sorted(at): w.writerow([*k, *at[k]])
    agg = defaultdict(lambda: [0, 0])
    for (z, e, v, name), n in ex.items():
        agg[(z, e, v)][0] += 1; agg[(z, e, v)][1] += n
    with open(os.path.join(OUT, "anatomy_extent.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["z", "extent", "version", "distinct_layers", "layer_instances"])
        for k in sorted(agg): w.writerow([*k, *agg[k]])
    rows = []
    for p in sorted(glob.glob(os.path.join(DATA, "lowzoom", "*.mvt.gz")), key=lambda s: int(os.path.basename(s).split("_")[1])):
        z = int(os.path.basename(p).split("_")[1])
        for l in mvt.decode_tile(gzip.decompress(open(p, "rb").read())):
            rows.append([z, l.extent, l.name, len(l.features), sum(mvt.count_vertices(f.geom) for f in l.features)])
    with open(os.path.join(OUT, "anatomy_lowzoom.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["z", "extent", "layer", "features", "vertices"]); w.writerows(rows)


if __name__ == "__main__":
    main()
