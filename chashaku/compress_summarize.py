"""chashaku/compress_summarize.py — summarize results/compress_tiles.csv -> compress_summary.csv / compress_summary.md"""
import csv, math, os
from collections import defaultdict
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
rows = list(csv.DictReader(open(os.path.join(R, "compress_tiles.csv"))))
COD = ["raw", "gzip9", "br11", "zstd19", "zstd22"]
nr = lambda v, p: sorted(v)[max(0, math.ceil(p * len(v)) - 1)]
tot = defaultdict(lambda: defaultdict(int)); by = defaultdict(list)
for r in rows:
    for c in COD:
        tot[r["cfg"]][c] += int(r[c])
    by[(r["cfg"], r["z"])].append(r)
base = tot["default"]["raw"]
out = []
md = ["### 設定 × 圧縮方式: 5範囲の `hyp` 全タイルの合計 (MB) と、default の無圧縮に対する比\n", "| 設定 | 無圧縮 | gzip -9 | brotli -11 | zstd -19 | zstd -22 |", "|---|---|---|---|---|---|"]
for cfg in tot:
    cells = [f"{tot[cfg][c]/1e6:.2f} ({tot[cfg][c]/base:.3f})" for c in COD]
    md.append(f"| {cfg} | " + " | ".join(cells) + " |")
    for c in COD:
        out.append([cfg, "all", c, tot[cfg][c], round(tot[cfg][c] / base, 4)])
md += ["", "### z13 のタイル(最悪のタイルが出るズーム): 中央値 / 最大 (KB)\n", "| 設定 | 無圧縮 | gzip -9 | brotli -11 | zstd -19 |", "|---|---|---|---|---|"]
for cfg in tot:
    rs = by[(cfg, "13")]
    cells = []
    for c in ("raw", "gzip9", "br11", "zstd19"):
        v = [int(r[c]) for r in rs]
        cells.append(f"{nr(v,.5)/1024:.1f} / {max(v)/1024:.1f}")
    md.append(f"| {cfg} | " + " | ".join(cells) + " |")
with open(os.path.join(R, "compress_summary.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["cfg", "scope", "codec", "total_bytes", "ratio_vs_default_raw"]); w.writerows(out)
open(os.path.join(R, "compress_summary.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md)); print(len(rows), "rows")
