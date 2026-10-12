"""chashaku/encode_mlt.py — convert every variant tile to MLT with `mlt convert --verify` and record sizes.

Reads  chashaku/results/tiles_mvt.csv + data/variants/**.mvt
Writes data/mlt/<area>/<variant>/... , chashaku/results/tiles.csv, chashaku/results/mlt_convert.log
Usage: encode_mlt.py [extra mlt convert flags...]   (e.g. --sort auto); results go to tiles_<tag>.csv if MLT_TAG is set.
"""
import csv
import gzip
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "..", "data")
MLT = os.path.join(ROOT, "..", "tools", "mlt-0.4.3", "mlt")
TAG = os.environ.get("MLT_TAG", "")
extra = sys.argv[1:]

rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "tiles_mvt.csv"))))
combos = sorted({(r["area"], r["variant"]) for r in rows})
log = open(os.path.join(ROOT, "results", f"mlt_convert{('_' + TAG) if TAG else ''}.log"), "w")
outdir = os.path.join(DATA, "mlt" + (("_" + TAG) if TAG else ""))
for area, variant in combos:
    src = os.path.join(DATA, "variants", area, variant)
    dst = os.path.join(outdir, area, variant)
    cmd = [MLT, "convert", "--verify", *extra, src, dst]
    p = subprocess.run(cmd, capture_output=True, text=True)
    log.write(f"$ {' '.join(cmd)}\nexit={p.returncode}\n{p.stdout}{p.stderr}\n")
    log.flush()
    if p.returncode != 0:
        sys.exit(f"mlt convert failed for {area}/{variant}: {p.stderr[-500:]}")

out = []
for r in rows:
    path = os.path.join(outdir, r["area"], r["variant"], r["z"], r["x"], r["y"] + ".mlt")
    b = open(path, "rb").read()
    out.append([*r.values(), len(b), len(gzip.compress(b, 9))])
hdr = list(rows[0].keys()) + ["mlt_raw", "mlt_gz9"]
with open(os.path.join(ROOT, "results", f"tiles{('_' + TAG) if TAG else ''}.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr); w.writerows(out)
print("ok", len(out), "tiles")
