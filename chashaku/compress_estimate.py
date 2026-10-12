"""chashaku/compress_estimate.py — tile-size estimate: MLT encoder options x compression codecs (DECISIONS D16).

For every `hyp` tile of the 5 areas (data/variants/<area>/hyp/**.mvt):
  encode with `mlt convert --verify <cfg flags>` -> raw MLT, then compress with gzip -9 (zlib), brotli -q 11, zstd -19, zstd --ultra -22.
Output: chashaku/results/compress_tiles.csv (area,cfg,z,x,y,raw,gzip9,br11,zstd19,zstd22), compress_summary.csv, compress_summary.md
"""
import csv
import gzip
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "..", "data")
MLT = os.path.join(ROOT, "..", "tools", "mlt-0.4.3", "mlt")
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
CFGS = {"default": [], "no-fsst": ["--no-fsst"], "no-fastpfor": ["--no-fastpfor"],
        "no-fsst+no-fastpfor": ["--no-fsst", "--no-fastpfor"], "no-shared-dict": ["--no-shared-dict"],
        "sort-auto": ["--sort", "auto"]}
CODECS = {"gzip9": None, "br11": ["brotli", "-q", "11", "-c"], "zstd19": ["zstd", "-19", "-q", "-c"],
          "zstd22": ["zstd", "--ultra", "-22", "-q", "-c"]}


def comp(args):
    codec, b = args
    if codec == "gzip9":
        return len(gzip.compress(b, 9, mtime=0)) - 0
    return len(subprocess.run(CODECS[codec], input=b, capture_output=True, check=True).stdout)


rows = []
with ThreadPoolExecutor(8) as ex:
    for cfg, flags in CFGS.items():
        for area in AREAS:
            src = os.path.join(DATA, "variants", area, "hyp")
            dst = os.path.join(DATA, "mlt_cfg", cfg, area)
            p = subprocess.run([MLT, "convert", "--verify", *flags, src, dst], capture_output=True, text=True)
            if p.returncode:
                sys.exit(f"{cfg}/{area}: {p.stderr[-300:]}")
            files = []
            for z in os.listdir(dst):
                for xs in os.listdir(os.path.join(dst, z)):
                    for fn in os.listdir(os.path.join(dst, z, xs)):
                        files.append((z, xs, fn[:-4], open(os.path.join(dst, z, xs, fn), "rb").read()))
            res = {c: list(ex.map(comp, [(c, f[3]) for f in files])) for c in CODECS}
            for i, (z, xs, y, b) in enumerate(files):
                rows.append([area, cfg, z, xs, y, len(b)] + [res[c][i] for c in CODECS])
        print(cfg, "done", flush=True)
with open(os.path.join(ROOT, "results", "compress_tiles.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["area", "cfg", "z", "x", "y", "raw"] + list(CODECS)); w.writerows(rows)
