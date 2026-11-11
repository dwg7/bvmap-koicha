#!/usr/bin/env python3
"""build/check_seams.py — verify build/seams.py (DECISIONS D31) on real tiles.

For sampled koicha tiles (bundles of 4 bvmap tiles) it compares the old bundling (shift only) with the seamless one:
  * area of every polygon layer inside the 2e x 2e square: old pieces are clipped to their own child square and summed (the ideal
    result); the new tiles are clipped to the whole square. They must agree (rounding slivers only).
  * line length per layer inside the square (same idea).
  * number of polygon edges that run exactly along an inner seam (x == e or y == e) — a seam line the renderer would draw.
  * attribute multiset (props) per layer must not change.
Usage: python3 -I build/check_seams.py data/bvmap/tokyo.pmtiles [more.pmtiles] --z 15 --n 40
"""
import argparse
import gzip
import math
import os
import random
import sys
from collections import Counter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "chashaku", "lib"))
sys.path.insert(0, os.path.join(ROOT, "build"))
import mvt
import pmtiles_reader as pr
import seams


def clip_box(ring, box):
    x0, y0, x1, y1 = box
    for a, S, le in ((0, x0, False), (0, x1, True), (1, y0, False), (1, y1, True)):
        if len(ring) < 3:
            return []
        ring = seams.clip_ring(ring, a, S, le)
    return ring


def clip_line_box(line, box):
    x0, y0, x1, y1 = box
    pieces = [line]
    for a, S, le in ((0, x0, False), (0, x1, True), (1, y0, False), (1, y1, True)):
        pieces = [q for p in pieces for q in seams.clip_line(p, a, S, le)]
    return pieces


def measure(layers, boxes):
    """boxes: list of (box, filter) -> polygon area2 and line length per layer inside the boxes."""
    area, length, props = Counter(), Counter(), Counter()
    for l in layers:
        for f in l.features:
            parts = seams.decode_parts(f.geom)
            for box in boxes:
                if f.type == 3:
                    for r in parts:
                        c = clip_box(r, box)
                        if len(c) >= 3:
                            area[l.name] += seams.area2(c)
                elif f.type == 2:
                    for line in parts:
                        for c in clip_line_box(line, box):
                            length[l.name] += sum(math.dist(c[i], c[i + 1]) for i in range(len(c) - 1))
    return area, length


def seam_edges(layers, e):
    n = 0
    for l in layers:
        for f in l.features:
            if f.type != 3:
                continue
            for r in seams.decode_parts(f.geom):
                for i in range(len(r)):
                    p, q = r[i], r[(i + 1) % len(r)]
                    for a in (0, 1):
                        if p[a] == e and q[a] == e and p[1 - a] != q[1 - a]:
                            n += 1
    return n


def prop_multiset(layers):
    c = Counter()
    for l in layers:
        for f in l.features:
            c[(l.name, tuple((l.keys[f.tags[i]], l.values[f.tags[i + 1]]) for i in range(0, len(f.tags), 2)))] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--z", type=int, default=15, help="koicha zoom to sample (bundles z+1 bvmap tiles)")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--tile", help="check only this koicha tile x/y")
    a = ap.parse_args()
    idx = [pr.PMTilesIndex(s) for s in a.sources]

    def look(z, x, y):
        for ix in idx:
            b = ix.get(z, x, y)
            if b is not None:
                return mvt.decode_tile(gzip.decompress(b))

    keys = set()
    for ix in idx:
        keys.update(k for k in ix.keys() if k[0] == a.z + 1)
    cands = sorted({(k[1] // 2, k[2] // 2) for k in keys})
    random.Random(a.seed).shuffle(cands)
    if a.tile:
        cands = [tuple(int(v) for v in a.tile.split("/"))]
    tot = Counter()
    worst = 0.0
    for (x, y) in cands[:a.n]:
        kids = []
        for dy in (0, 1):
            for dx in (0, 1):
                t = look(a.z + 1, 2 * x + dx, 2 * y + dy)
                if t is not None:
                    kids.append((t, dx, dy, t[0].extent))
        if len(kids) < 4:                      # edge tiles keep the buffer on the side without a neighbour (by design)
            continue
        e = kids[0][3]
        old = mvt.merge_children([(t, dx * e, dy * e) for t, dx, dy, _ in kids], 2 * e)
        new = seams.merge_seamless(kids, 2 * e)
        # ideal = each child clipped to its own square, summed
        ideal_a, ideal_l = Counter(), Counter()
        for t, dx, dy, _ in kids:
            sh = mvt.merge_children([([l], dx * e, dy * e) for l in t], 2 * e)
            aa, ll = measure(sh, [(dx * e, dy * e, dx * e + e, dy * e + e)])
            ideal_a.update(aa); ideal_l.update(ll)
        box = (0, 0, 2 * e, 2 * e)
        na, nl = measure(new, [box])
        oa, ol = measure(old, [box])
        for name in set(ideal_a) | set(na):
            ia, nn = ideal_a[name], na[name]
            rel = abs(nn - ia) / max(1, abs(ia))
            worst = max(worst, rel)
            tot[("area_ideal", name)] += ia; tot[("area_new", name)] += nn; tot[("area_old", name)] += oa[name]
            if rel > 2e-3:
                print(f"  tile {a.z}/{x}/{y} {name}: area ideal {ia} new {nn} rel {rel:.2e}")
        for name in set(ideal_l) | set(nl):
            tot[("len_ideal", name)] += ideal_l[name]; tot[("len_new", name)] += nl[name]; tot[("len_old", name)] += ol[name]
        tot["seam_edges_old"] += seam_edges(old, e)
        tot["seam_edges_new"] += seam_edges(new, e)
        tot["features_old"] += sum(len(l.features) for l in old)
        tot["features_new"] += sum(len(l.features) for l in new)
        # attributes: every old feature's props must still exist (new has <= old per props because pieces dissolve)
        po, pn = prop_multiset(old), prop_multiset(new)
        tot["props_new_not_in_old"] += sum(1 for k in pn if k not in po)
        tot["tiles"] += 1
    print("tiles checked:", tot["tiles"], " worst relative area error (any layer, any tile): %.2e" % worst)
    for name in sorted({k[1] for k in tot if isinstance(k, tuple)}):
        ia, na_, oa_ = tot[("area_ideal", name)], tot[("area_new", name)], tot[("area_old", name)]
        il, nl_, ol_ = tot[("len_ideal", name)], tot[("len_new", name)], tot[("len_old", name)]
        if ia or na_:
            print(f"  {name:10s} polygon area: ideal {ia:>14} new {na_:>14} (new/ideal {na_/max(1,ia):.5f}); old shift-only {oa_:>14} (old/ideal {oa_/max(1,ia):.5f})")
        if il or nl_:
            print(f"  {name:10s} line length : ideal {il:>14.0f} new {nl_:>14.0f} (new/ideal {nl_/max(1,il):.5f}); old {ol_:>14.0f} (old/ideal {ol_/max(1,il):.5f})")
    print("polygon edges lying on an inner seam: old", tot["seam_edges_old"], "-> new", tot["seam_edges_new"])
    print("features: old", tot["features_old"], "-> new", tot["features_new"], "; props only in new:", tot["props_new_not_in_old"])
    print("stats:", dict(seams.STATS))


if __name__ == "__main__":
    main()
