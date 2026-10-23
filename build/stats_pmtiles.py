#!/usr/bin/env python3
"""build/stats_pmtiles.py <file.pmtiles> — per-zoom tile-size statistics (stored bytes; median / p95 / max, nearest-rank) and the worst tiles."""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chashaku", "lib"))
import pmtiles_reader as pr
ix = pr.PMTilesIndex(sys.argv[1])
by = {}
for (z, x, y), (off, ln) in ix.index.items():
    by.setdefault(z, []).append((ln, x, y))
nr = lambda v, p: v[max(0, math.ceil(p * len(v)) - 1)]
print("| z | 枚数 | 合計 (MB) | 中央値 (KB) | p95 (KB) | 最大 (KB) | 最大のタイル |\n|---|---|---|---|---|---|---|")
allt = []
for z in sorted(by):
    v = sorted(by[z]); sizes = [a for a, _, _ in v]; allt += [(a, z, x, y) for a, x, y in v[-5:]]
    w = v[-1]
    print(f"| {z} | {len(v):,} | {sum(sizes)/1e6:.1f} | {nr(sizes,.5)/1024:.1f} | {nr(sizes,.95)/1024:.1f} | {sizes[-1]/1024:.1f} | {z}/{w[1]}/{w[2]} |")
tot = sum(a for v in by.values() for a, _, _ in v)
print(f"\n全体: {sum(len(v) for v in by.values()):,} 枚(ディレクトリ展開後)、{tot/1e9:.2f}GB(重複排除前の合計。ファイルは {os.path.getsize(sys.argv[1])/1e9:.2f}GB)")
print("\n最悪の 8 枚:"); 
for a, z, x, y in sorted(allt, reverse=True)[:8]: print(f"  {z}/{x}/{y}  {a/1024:.1f} KB")
