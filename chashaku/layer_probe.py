"""chashaku/layer_probe.py — per-layer size of the `hyp` and `contra` tiles, as a thinning guide.

Each layer is written as a single-layer MVT tile, converted with `mlt convert`, and sized. Because layers
are then encoded in isolation (no cross-layer gzip / shared state), the sum is a slight overestimate of
the real tile; use it for shares, not for absolute sizes.
Output: chashaku/results/layers_size.csv  area,variant,z,layer,tiles,features,mvt_raw,mlt_raw,mlt_gz_isolated
"""
import csv
import gzip
import os
import shutil
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import mvt

DATA = os.path.join(ROOT, "..", "data")
MLT = os.path.join(ROOT, "..", "tools", "mlt-0.4.3", "mlt")
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
probe = os.path.join(DATA, "layerprobe")
shutil.rmtree(probe, ignore_errors=True)
shutil.rmtree(os.path.join(DATA, "layerprobe_mlt"), ignore_errors=True)

meta = defaultdict(lambda: [0, 0, 0])   # (area,variant,z,layer) -> tiles, feats, mvt_raw
index = []                               # (area,variant,z,x,y,layer)
for area in AREAS:
    for variant in ("hyp", "contra"):
        base = os.path.join(DATA, "variants", area, variant)
        for z in os.listdir(base):
            for xs in os.listdir(os.path.join(base, z)):
                for fn in os.listdir(os.path.join(base, z, xs)):
                    y = fn[:-4]
                    for l in mvt.decode_tile(open(os.path.join(base, z, xs, fn), "rb").read()):
                        raw = mvt.encode_tile([l])
                        d = os.path.join(probe, area, f"{variant}__{l.name}", z, xs)
                        os.makedirs(d, exist_ok=True)
                        open(os.path.join(d, fn), "wb").write(raw)
                        m = meta[(area, variant, int(z), l.name)]
                        m[0] += 1; m[1] += len(l.features); m[2] += len(raw)
                        index.append((area, variant, z, xs, y, l.name))
for area in AREAS:
    for sub in sorted(os.listdir(os.path.join(probe, area))):
        p = subprocess.run([MLT, "convert", os.path.join(probe, area, sub), os.path.join(DATA, "layerprobe_mlt", area, sub)],
                           capture_output=True, text=True)
        if p.returncode:
            sys.exit(p.stderr[-400:])
agg = defaultdict(lambda: [0, 0])
for area, variant, z, xs, y, layer in index:
    b = open(os.path.join(DATA, "layerprobe_mlt", area, f"{variant}__{layer}", z, xs, y + ".mlt"), "rb").read()
    a = agg[(area, variant, int(z), layer)]
    a[0] += len(b); a[1] += len(gzip.compress(b, 9))
with open(os.path.join(ROOT, "results", "layers_size.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["area", "variant", "z", "layer", "tiles", "features", "mvt_raw", "mlt_raw", "mlt_gz_isolated"])
    for k in sorted(meta):
        w.writerow([*k, *meta[k], *agg[k]])
shutil.rmtree(probe, ignore_errors=True)
shutil.rmtree(os.path.join(DATA, "layerprobe_mlt"), ignore_errors=True)
print("ok")
