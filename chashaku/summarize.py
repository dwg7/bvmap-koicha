"""chashaku/summarize.py — median / p95 / max (nearest-rank) per area x variant x zoom x format.

Input : chashaku/results/tiles[_<tag>].csv       (tag from argv[1], optional)
Output: chashaku/results/summary[_<tag>].csv, and a markdown digest on stdout.
Formats: mvt_gz (MVT + gzip -9), mlt_raw (MLT only), mlt_gz (MLT + gzip -9)
"complete" = tiles whose children are all present (n_children == 4 for bundled tiles, 1 for 1:1 tiles);
edge tiles of the extract are partially bundled and therefore smaller.
"""
import csv
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
tag = sys.argv[1] if len(sys.argv) > 1 else ""
suffix = f"_{tag}" if tag else ""
rows = list(csv.DictReader(open(os.path.join(ROOT, "results", f"tiles{suffix}.csv"))))
FORMATS = {"mvt_gz": "mvt_gz9", "mlt_raw": "mlt_raw", "mlt_gz": "mlt_gz9"}
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
VARIANTS = ["bvmap", "hyp", "contra"]


def nearest_rank(sorted_vals, p):
    return sorted_vals[max(0, math.ceil(p * len(sorted_vals)) - 1)]


def expected_children(variant, z):
    return 1 if variant == "bvmap" or (variant == "hyp" and z == 16) else 4


groups = defaultdict(list)
for r in rows:
    groups[(r["area"], r["variant"], int(r["z"]))].append(r)

out = []
for (area, variant, z), rs in sorted(groups.items()):
    for fmt, col in FORMATS.items():
        for scope, sel in (("all", rs), ("complete", [r for r in rs if int(r["n_children"]) == expected_children(variant, z)])):
            if not sel:
                continue
            vals = sorted(int(r[col]) for r in sel)
            worst = max(sel, key=lambda r: int(r[col]))
            out.append([area, variant, z, fmt, scope, len(vals), sum(vals), nearest_rank(vals, .5),
                        nearest_rank(vals, .95), vals[-1], f'{worst["z"]}/{worst["x"]}/{worst["y"]}'])
with open(os.path.join(ROOT, "results", f"summary{suffix}.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["area", "variant", "z", "format", "scope", "tiles", "total_bytes", "median", "p95", "max", "max_tile"])
    w.writerows(out)

# markdown digest (scope=complete)
idx = {(o[0], o[1], o[2], o[3], o[4]): o for o in out}
for area in AREAS:
    print(f"\n### {area}\n")
    print("| z | 組み方 | 枚数(完全) | MVT+gz 中央/p95/最大 | MLT のみ 中央/p95/最大 | MLT+gz 中央/p95/最大 |")
    print("|---|---|---|---|---|---|")
    for z in (13, 14, 15, 16):
        for v in VARIANTS:
            if (area, v, z, "mvt_gz", "complete") not in idx:
                continue
            cells = []
            for fmt in FORMATS:
                o = idx[(area, v, z, fmt, "complete")]
                cells.append(f"{o[7]/1024:.1f} / {o[8]/1024:.1f} / {o[9]/1024:.1f}")
            n = idx[(area, v, z, "mvt_gz", "complete")][5]
            print(f"| {z} | {v} | {n} | " + " | ".join(cells) + " |")
