"""chashaku/anatomy_tables.py — markdown tables for docs/bvmap-anatomy.md, from results/anatomy_*.csv"""
import csv, os
from collections import defaultdict
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
rd = lambda n: list(csv.DictReader(open(os.path.join(R, n))))
lay, fl, at = rd("anatomy_layers.csv"), rd("anatomy_flag17.csv"), rd("anatomy_attrs.csv")

print("## 層 × ズーム: 地物数(5範囲合計) / 1枚あたり中央の目安=合計÷枚数\n")
agg = defaultdict(lambda: [0, 0, 0, 0])
for r in lay:
    a = agg[(r["layer"], int(r["z"]))]
    a[0] += int(r["tiles"]); a[1] += int(r["features"]); a[2] += int(r["vertices"]); a[3] += int(r["layer_bytes_raw"])
layers = sorted({k[0] for k in agg})
print("| 層 | z13 | z14 | z15 | z16 |\n|---|---|---|---|---|")
for l in layers:
    cells = []
    for z in (13, 14, 15, 16):
        a = agg.get((l, z))
        cells.append("–" if not a else f"{a[1]:,}地物 / {a[0]}枚")
    print(f"| {l} | " + " | ".join(cells) + " |")

print("\n## z16 の vt_flag17 分布(5範囲合計、地物数)\n")
f = defaultdict(lambda: defaultdict(int))
for r in fl:
    if int(r["z"]) == 16:
        f[r["layer"]][r["flag17"]] += int(r["features"])
print("| 層 | flag17 なし(キー無し) | 0 | 1 | 2 | 地物にキーが無い |\n|---|---|---|---|---|---|")
for l in sorted(f):
    d = f[l]
    if set(d) == {"n/a"}:
        print(f"| {l} | {d['n/a']:,} | – | – | – | – |")
    else:
        print(f"| {l} | – | {d.get('0',0):,} | {d.get('1',0):,} | {d.get('2',0):,} | {d.get('none',0):,} |")

print("\n## flag17 キーが現れるズーム(層ごと)\n")
zs = defaultdict(set)
for r in fl:
    if r["flag17"] != "n/a":
        zs[r["layer"]].add(int(r["z"]))
for l in sorted(zs): print(f"- {l}: z{sorted(zs[l])}")

print("\n## 属性(キー)ごとの大きさの目安: z16, 5範囲合計(生バイト)\n")
t = defaultdict(lambda: [0, 0, 0, 0])
for r in at:
    if int(r["z"]) == 16:
        a = t[(r["layer"], r["key"])]
        a[0] += int(r["features"]); a[1] += int(r["tag_bytes"]); a[2] += int(r["value_bytes"]); a[3] += int(r["key_name_bytes"])
lt = defaultdict(int)
for r in lay:
    if int(r["z"]) == 16: lt[r["layer"]] += int(r["layer_bytes_raw"])
print("| 層 | キー | 地物数 | tag(B) | value表(B) | 層全体に占める割合(属性計) |\n|---|---|---|---|---|---|")
for (l, k), a in sorted(t.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))[:24]:
    print(f"| {l} | {k} | {a[0]:,} | {a[1]:,} | {a[2]:,} | {100*(a[1]+a[2]+a[3])/lt[l]:.1f}% |")
