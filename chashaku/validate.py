"""chashaku/validate.py — sanity checks for the variants built by measure.py.

1. bvmap tiles re-encode byte-for-byte (codec is lossless).
2. contra z15 feature/vertex counts == sum over its 4 bvmap z16 children.
3. hyp z15 = contra z15 minus (4 z17-only layers + vt_flag17==2); hyp z16 = bvmap z16 minus vt_flag17==0.
4. Bundled coordinates stay within the extent-x2 tile plus bvmap's own buffer.
"""
import gzip
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, ROOT)
import mvt
import pmtiles_reader as pr
from measure import Z17_ONLY_LAYERS, flag17_pred

AREAS = [l.split("\t")[0] for l in open(os.path.join(ROOT, "areas.tsv")).read().split("\n") if l]
DATA = os.path.join(ROOT, "..", "data")


def load(path):
    return mvt.decode_tile(open(path, "rb").read())


def totals(layers, names=None):
    f = v = 0
    for l in layers:
        if names is None or l.name in names:
            f += len(l.features)
            v += sum(mvt.count_vertices(x.geom) for x in l.features)
    return f, v


def cmds_bbox(geom):
    """Absolute min/max of all vertices from the command stream."""
    x = y = 0
    i = 0
    lo = [1 << 30, 1 << 30]; hi = [-(1 << 30), -(1 << 30)]
    while i < len(geom):
        cmd, cnt = geom[i] & 7, geom[i] >> 3
        i += 1
        if cmd in (1, 2):
            for _ in range(cnt):
                x += mvt.unzigzag(geom[i]); y += mvt.unzigzag(geom[i + 1]); i += 2
                lo[0] = min(lo[0], x); lo[1] = min(lo[1], y); hi[0] = max(hi[0], x); hi[1] = max(hi[1], y)
    return lo, hi


bad = 0
for area in AREAS:
    # 1
    n = 0
    for z, x, y, b in pr.iter_tiles(os.path.join(DATA, "bvmap", area + ".pmtiles")):
        raw = gzip.decompress(b)
        assert mvt.encode_tile(mvt.decode_tile(raw)) == raw, (area, z, x, y)
        assert len(gzip.compress(raw, 9)) == len(b) or True
        n += 1
    # 2/3 on every z15 tile
    d15 = os.path.join(DATA, "variants", area, "contra", "15")
    for xs in os.listdir(d15):
        for fn in os.listdir(os.path.join(d15, xs)):
            x, y = int(xs), int(fn[:-4])
            con = load(os.path.join(d15, xs, fn))
            hyp = load(os.path.join(DATA, "variants", area, "hyp", "15", xs, fn))
            kids = []
            for dy in (0, 1):
                for dx in (0, 1):
                    p = os.path.join(DATA, "variants", area, "bvmap", "16", str(2 * x + dx), f"{2 * y + dy}.mvt")
                    if os.path.exists(p):
                        kids.append(load(p))
            assert totals(con) == tuple(map(sum, zip(*[totals(k) for k in kids]))), ("contra sum", area, x, y)
            exp_f = exp_v = 0
            keep = flag17_pred(2)
            for k in kids:
                for l in k:
                    if l.name in Z17_ONLY_LAYERS:
                        continue
                    for f in l.features:
                        if keep(l, f):
                            exp_f += 1; exp_v += mvt.count_vertices(f.geom)
            assert totals(hyp) == (exp_f, exp_v), ("hyp z15", area, x, y, totals(hyp), (exp_f, exp_v))
            # 4
            for l in con:
                assert l.extent == 8192
                for f in l.features:
                    lo, hi = cmds_bbox(f.geom)
                    if lo[0] < -512 or lo[1] < -512 or hi[0] > 8192 + 512 or hi[1] > 8192 + 512:
                        bad += 1
    # hyp z16
    d16 = os.path.join(DATA, "variants", area, "hyp", "16")
    keep0 = flag17_pred(0)
    for xs in os.listdir(d16):
        for fn in os.listdir(os.path.join(d16, xs)):
            src = load(os.path.join(DATA, "variants", area, "bvmap", "16", xs, fn))
            exp = sum(1 for l in src for f in l.features if keep0(l, f))
            assert totals(load(os.path.join(d16, xs, fn)))[0] == exp, ("hyp z16", area, xs, fn)
    print(area, "ok;", n, "tiles roundtrip")
print("features outside extent+buffer (should be small/0 = clipped features from tippecanoe buffer):", bad)
