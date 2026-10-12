"""chashaku/compare.py — derived comparisons from results/tiles.csv.

(1) mlt_gain      : MLT(+gz) / MVT+gz for the same tiles (median of per-tile ratios)
(2) same_zoom     : koicha(hyp) MLT+gz median / bvmap MVT+gz median at the same display zoom (complete tiles)
(3) view_cost     : bytes needed to cover the same ground at a display zoom, hyp vs contra (sum over tiles, MLT+gz)
Output: results/compare.csv (long format) and a markdown digest on stdout.
"""
import csv
import os
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "tiles.csv"))))
AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
by = defaultdict(list)
for r in rows:
    by[(r["area"], r["variant"], int(r["z"]))].append(r)


def complete(variant, z, rs):
    exp = 1 if variant == "bvmap" or (variant == "hyp" and z == 16) else 4
    return [r for r in rs if int(r["n_children"]) == exp]


out = []
print("### (1) MLT の効き: タイルごとの比の中央値(MLT のみ / MVT+gz,  MLT+gz / MVT+gz)\n")
print("| 範囲 | z | bvmap | hyp | contra |\n|---|---|---|---|---|")
for area in AREAS:
    for z in (13, 14, 15, 16):
        cells = []
        for v in ("bvmap", "hyp", "contra"):
            rs = by.get((area, v, z))
            if not rs:
                cells.append("–"); continue
            a = statistics.median(int(r["mlt_raw"]) / int(r["mvt_gz9"]) for r in rs)
            b = statistics.median(int(r["mlt_gz9"]) / int(r["mvt_gz9"]) for r in rs)
            out.append([area, "mlt_gain", v, z, f"{a:.3f}", f"{b:.3f}"])
            cells.append(f"{a:.2f} / {b:.2f}")
        print(f"| {area} | {z} | " + " | ".join(cells) + " |")

print("\n### (2) 同じ表示ズームでのタイルの重さ: hyp の MLT+gz 中央値 / bvmap の MVT+gz 中央値(完全タイルのみ)\n")
print("| 範囲 | z13 | z14 | z15 | z16 |\n|---|---|---|---|---|")
for area in AREAS:
    cells = []
    for z in (13, 14, 15, 16):
        h = complete("hyp", z, by[(area, "hyp", z)])
        b = complete("bvmap", z, by[(area, "bvmap", z)])
        if not h or not b:
            cells.append("–"); continue
        ratio = statistics.median(int(r["mlt_gz9"]) for r in h) / statistics.median(int(r["mvt_gz9"]) for r in b)
        out.append([area, "same_zoom", "hyp/bvmap", z, f"{ratio:.3f}", len(h)])
        cells.append(f"×{ratio:.2f} (n={len(h)})")
    print(f"| {area} | " + " | ".join(cells) + " |")

print("\n### (3) 同じ土地を覆うのに要する量(MLT+gz 合計, KB)と枚数\n")
print("| 範囲 | 表示z | hyp | contra | contra/hyp | 枚数 hyp / contra |\n|---|---|---|---|---|---|")
for area in AREAS:
    for disp in (15, 16):
        hz = by[(area, "hyp", disp)]
        cz = by[(area, "contra", 15)]
        hs = sum(int(r["mlt_gz9"]) for r in hz); cs = sum(int(r["mlt_gz9"]) for r in cz)
        out.append([area, "view_cost", f"z{disp}", disp, hs, cs])
        print(f"| {area} | {disp} | {hs/1024:.0f} | {cs/1024:.0f} | {cs/hs:.2f} | {len(hz)} / {len(cz)} |")
print("\n(アーカイブ全体: hyp = z15 + z16 の合計, contra = z15 のみ)")
print("| 範囲 | hyp z15+z16 (KB) | contra z15 (KB) | hyp/contra | bvmap z15+z16 MVT+gz (KB) |\n|---|---|---|---|---|")
for area in AREAS:
    h = sum(int(r["mlt_gz9"]) for z in (15, 16) for r in by[(area, "hyp", z)])
    c = sum(int(r["mlt_gz9"]) for r in by[(area, "contra", 15)])
    b = sum(int(r["mvt_gz9"]) for z in (15, 16) for r in by[(area, "bvmap", z)])
    out.append([area, "archive", "hyp/contra", "15+16", h, c])
    print(f"| {area} | {h/1024:.0f} | {c/1024:.0f} | {h/c:.2f} | {b/1024:.0f} |")
with open(os.path.join(ROOT, "results", "compare.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["area", "metric", "a", "b", "c", "d"]); w.writerows(out)
