"""build/seams.py — bundle 4 bvmap tiles without the tile-buffer seams (DECISIONS D31).

bvmap tiles carry a buffer (80 units of 4096) around the tile: a feature near the border is cut at the buffer edge, and the
neighbouring tile holds an overlapping copy. In an original tile the cut is outside the visible square, so no line shows.
When 4 tiles are bundled the cut lands in the middle of the new tile: an outline appears across polygons (buildings) and lines
are drawn twice in the overlap band.

Fix: in the bundled tile, each child keeps only its own side of the seam (x <= S or x >= S, then y <= S or y >= S). Polygon pieces
that now abut along the seam are dissolved (the shared seam edges cancel); line pieces are joined at the seam; points that sit
on the other side are dropped (the neighbour has them). Features that lie entirely inside their child's own square are passed
through verbatim (fast path). Only geometry is touched; attributes are never changed.

Standard library only. Coordinates are integers in the merged tile (child coordinates + offset).
"""
from collections import defaultdict
from dataclasses import dataclass

import mvt

TOL = 16          # seam vertices of the two sides may differ by rounding of the tile clip (units)
STATS = defaultdict(int)


def _uz(v):
    return (v >> 1) ^ -(v & 1)


def _zz(v):
    return (v << 1) ^ (v >> 63) if v < 0 else v << 1


def decode_parts(geom):
    """Command integers -> list of parts (list of (x, y)). Points: one part per MoveTo. Rings are not closed."""
    parts, cur, cx, cy, i, n = [], None, 0, 0, 0, len(geom)
    while i < n:
        c = geom[i]
        cmd, k = c & 7, c >> 3
        i += 1
        if cmd == 1:
            for _ in range(k):
                cx += _uz(geom[i]); cy += _uz(geom[i + 1]); i += 2
                cur = [(cx, cy)]
                parts.append(cur)
        elif cmd == 2:
            for _ in range(k):
                cx += _uz(geom[i]); cy += _uz(geom[i + 1]); i += 2
                cur.append((cx, cy))
    return parts


def encode_parts(parts, ftype):
    out, cx, cy = [], 0, 0
    if ftype == 1:
        pts = [p for part in parts for p in part]
        out.append((len(pts) << 3) | 1)
        for x, y in pts:
            out += (_zz(x - cx), _zz(y - cy)); cx, cy = x, y
        return out
    for part in parts:
        x, y = part[0]
        out += (9, _zz(x - cx), _zz(y - cy)); cx, cy = x, y
        out.append(((len(part) - 1) << 3) | 2)
        for x, y in part[1:]:
            out += (_zz(x - cx), _zz(y - cy)); cx, cy = x, y
        if ftype == 3:
            out.append(15)
    return out


def bbox_of_geom(geom):
    """(minx, miny, maxx, maxy) of a command-integer geometry (local coordinates)."""
    x0 = y0 = 1 << 60
    x1 = y1 = -(1 << 60)
    cx = cy = i = 0
    n = len(geom)
    while i < n:
        c = geom[i]
        cmd, k = c & 7, c >> 3
        i += 1
        if cmd == 7:
            continue
        for _ in range(k):
            cx += _uz(geom[i]); cy += _uz(geom[i + 1]); i += 2
            if cx < x0: x0 = cx
            if cx > x1: x1 = cx
            if cy < y0: y0 = cy
            if cy > y1: y1 = cy
    return x0, y0, x1, y1


def area2(ring):
    s, n = 0, len(ring)
    px, py = ring[-1]
    for x, y in ring:
        s += px * y - x * py
        px, py = x, y
    return s


# ---- half-plane clipping ----------------------------------------------------

def _cross(p, q, a, S):
    """Point where segment p-q meets the line coordinate[a] == S (p, q strictly on opposite sides), rounded to integers."""
    b = 1 - a
    num = (q[b] - p[b]) * (S - p[a])
    den = q[a] - p[a]
    if den < 0:
        num, den = -num, -den
    v = p[b] + (2 * num + den) // (2 * den)
    pt = [0, 0]
    pt[a], pt[b] = S, v
    return tuple(pt)


def clip_ring(ring, a, S, keep_le):
    out = []
    prev = ring[-1]
    pin = prev[a] <= S if keep_le else prev[a] >= S
    for cur in ring:
        cin = cur[a] <= S if keep_le else cur[a] >= S
        if cin:
            if not pin:
                out.append(_cross(prev, cur, a, S))
            out.append(cur)
        elif pin:
            out.append(_cross(prev, cur, a, S))
        prev, pin = cur, cin
    return _clean(out)


def _clean(ring):
    out = []
    for p in ring:
        if not out or out[-1] != p:
            out.append(p)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _dedupe(line):
    out = []
    for p in line:
        if not out or out[-1] != p:
            out.append(p)
    return out


def clip_line(line, a, S, keep_le):
    out, cur = [], []
    inside = lambda p: p[a] <= S if keep_le else p[a] >= S
    prev, pin = line[0], inside(line[0])
    if pin:
        cur.append(prev)
    for p in line[1:]:
        cin = inside(p)
        if pin and cin:
            cur.append(p)
        elif pin and not cin:
            cur.append(_cross(prev, p, a, S)) if prev[a] != S else None
            if len(cur) > 1:
                out.append(cur)
            cur = []
        elif not pin and cin:
            cur = [] if p[a] == S else [_cross(prev, p, a, S)]
            cur.append(p)
        prev, pin = p, cin
    if len(cur) > 1:
        out.append(cur)
    return [d for d in (_dedupe(l) for l in out) if len(d) > 1]


@dataclass
class Piece:
    id: object
    props: tuple          # ((key, raw value bytes), ...)
    ftype: int
    parts: list
    col: int = 0
    row: int = 0


def clip_piece(p, a, S, keep_le):
    if p.ftype == 3:
        parts = [r for r in (clip_ring(r, a, S, keep_le) for r in p.parts) if len(r) >= 3 and area2(r) != 0]
    elif p.ftype == 2:
        parts = [l for part in p.parts for l in clip_line(part, a, S, keep_le)]
    else:
        parts = [pt for pt in p.parts if (pt[0][a] <= S if keep_le else pt[0][a] > S)]
    return Piece(p.id, p.props, p.ftype, parts, p.col, p.row) if parts else None


# ---- dissolve / join ---------------------------------------------------------

def _snap_map(lo_vals, hi_vals):
    lo = sorted(lo_vals)
    m = {}
    for v in hi_vals:
        best = None
        for u in lo:
            d = abs(u - v)
            if d <= TOL and (best is None or d < abs(best - v)):
                best = u
        if best is not None:
            m[v] = best
    return m


def _snap_rings(rings, a, S, m):
    b = 1 - a
    out = []
    for r in rings:
        nr = []
        for p in r:
            if p[a] == S and p[b] in m:
                q = [0, 0]; q[a], q[b] = S, m[p[b]]
                p = tuple(q)
            nr.append(p)
        out.append(_clean(nr))
    return out


def _seam_intervals(r, a, S):
    b = 1 - a
    out = []
    n = len(r)
    for i in range(n):
        p, q = r[i], r[(i + 1) % n]
        if p[a] == S and q[a] == S and p[b] != q[b]:
            out.append((min(p[b], q[b]), max(p[b], q[b])))
    return out


def dissolve_rings(lo_rings, hi_rings, a, S):
    """Union of pieces that abut along coordinate[a] == S. Rings are grouped into components: a low-side and a high-side ring belong
    together when their seam edges overlap. Only a component is dissolved at a time, so two unrelated neighbours (e.g. buildings
    sharing a wall) are never merged into one ring."""
    b = 1 - a
    touches = lambda r: any(p[a] == S for p in r)
    free = [r for r in lo_rings + hi_rings if not touches(r)]          # rings away from the seam stay as they are
    lo_rings = [r for r in lo_rings if touches(r)]
    hi_rings = [r for r in hi_rings if touches(r)]
    lo_v = {p[b] for r in lo_rings for p in r if p[a] == S}
    hi_v = {p[b] for r in hi_rings for p in r if p[a] == S}
    hi_rings = _snap_rings(hi_rings, a, S, _snap_map(lo_v, hi_v))
    rings = lo_rings + hi_rings
    nlo = len(lo_rings)
    iv = [_seam_intervals(r, a, S) for r in rings]
    parent = list(range(len(rings)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(nlo):
        for j in range(nlo, len(rings)):
            if any(max(u0, v0) < min(u1, v1) for u0, u1 in iv[i] for v0, v1 in iv[j]):
                parent[find(i)] = find(j)
    comps = defaultdict(list)
    for i, r in enumerate(rings):
        comps[find(i)].append(r)
    out = list(free)
    for comp in comps.values():
        out += _dissolve_component(comp, a, S)
    return out


def _dissolve_component(rings, a, S):
    import bisect
    b = 1 - a
    V = sorted({p[b] for r in rings for p in r if p[a] == S})
    seam, edges = defaultdict(int), []
    for r in rings:
        if len(r) < 3:
            continue
        n = len(r)
        for i in range(n):
            p, q = r[i], r[(i + 1) % n]
            if p == q:
                continue
            if p[a] == S and q[a] == S:
                u, w = p[b], q[b]
                lo_, hi_ = (u, w) if u < w else (w, u)
                vs = V[bisect.bisect_left(V, lo_):bisect.bisect_right(V, hi_)]
                for j in range(len(vs) - 1):
                    seam[(vs[j], vs[j + 1]) if u < w else (vs[j + 1], vs[j])] += 1
            else:
                edges.append((p, q))
    for (u, w), c in seam.items():
        net = c - seam.get((w, u), 0)
        if net > 0:
            pu, pw = [0, 0], [0, 0]
            pu[a], pu[b], pw[a], pw[b] = S, u, S, w
            edges += [(tuple(pu), tuple(pw))] * net
        elif net == 0 and c > 0 and u < w:
            STATS["seam_edges_cancelled"] += c
    out = defaultdict(list)
    for p, q in edges:
        out[p].append(q)
    res = []
    while out:
        start = next(iter(out))
        ring, cur, ok = [start], start, True
        while True:
            lst = out.get(cur)
            if not lst:
                ok = False
                break
            nxt = lst.pop()
            if not lst:
                del out[cur]
            if nxt == start:
                break
            ring.append(nxt)
            cur = nxt
        if not ok:
            STATS["open_chain_dropped"] += 1
        elif len(ring) >= 3:
            ring = _simplify_seam(ring, a, S)
            if len(ring) >= 3 and area2(ring) != 0:
                res.append(ring)
        else:
            STATS["degenerate_pair_dropped"] += 1
    return res


def _simplify_seam(ring, a, S):
    """Drop vertices in the middle of a straight run lying on the seam (left over from splitting at the other side's vertices)."""
    changed = True
    while changed and len(ring) > 3:
        changed = False
        n = len(ring)
        keep = []
        for i in range(n):
            p, q, r = ring[i - 1], ring[i], ring[(i + 1) % n]
            if p[a] == S and q[a] == S and r[a] == S and (q[1 - a] - p[1 - a]) * (r[1 - a] - q[1 - a]) > 0:
                changed = True
                continue
            keep.append(q)
        ring = keep
    return ring


def join_lines(lines, a, S):
    ends = defaultdict(list)
    for i, l in enumerate(lines):
        for w, pt in ((0, l[0]), (1, l[-1])):
            if pt[a] == S:
                ends[pt].append((i, w))
    used = [False] * len(lines)
    out = []
    for i in range(len(lines)):
        if used[i]:
            continue
        used[i] = True
        chain = list(lines[i])
        for tail in (True, False):
            while True:
                pt = chain[-1] if tail else chain[0]
                cand = [c for c in ends.get(pt, []) if not used[c[0]]]
                if pt[a] != S or len(ends.get(pt, [])) != 2 or len(cand) != 1:
                    break
                j, w = cand[0]
                used[j] = True
                nxt = lines[j]
                seq = nxt[1:] if w == 0 else nxt[::-1][1:]
                if tail:
                    chain += seq
                else:
                    chain = seq[::-1] + chain
                STATS["lines_joined"] += 1
        out.append(chain)
    return out


def _snap_lines(lines, a, S, m):
    b = 1 - a
    out = []
    for l in lines:
        l = list(l)
        for idx in (0, -1):
            p = l[idx]
            if p[a] == S and p[b] in m:
                q = [0, 0]; q[a], q[b] = S, m[p[b]]
                l[idx] = tuple(q)
        out.append(l)
    return out


def seam_pass(pieces, a, S, is_lo):
    """pieces: all slow pieces of one layer; is_lo(piece) says which side of the seam it belongs to. Returns the new piece list."""
    b = 1 - a
    clipped = []
    for p in pieces:
        c = clip_piece(p, a, S, is_lo(p))
        if c:
            clipped.append(c)
    groups = defaultdict(list)
    for p in clipped:
        groups[(p.props, p.id, p.ftype)].append(p)
    out = []
    for (props, fid, ft), g in groups.items():
        if ft == 1:
            out.append(Piece(fid, props, 1, [pt for p in g for pt in p.parts], g[0].col, g[0].row))
            continue
        lo = [part for p in g if is_lo(p) for part in p.parts]
        hi = [part for p in g if not is_lo(p) for part in p.parts]
        if ft == 3:
            parts = dissolve_rings(lo, hi, a, S)
        else:
            lo_v = {l[i][b] for l in lo for i in (0, -1) if l[i][a] == S}
            hi_v = {l[i][b] for l in hi for i in (0, -1) if l[i][a] == S}
            hi = _snap_lines(hi, a, S, _snap_map(lo_v, hi_v))
            parts = join_lines(lo + hi, a, S)
        if parts:
            out.append(Piece(fid, props, ft, parts, g[0].col, g[0].row))
    return out


# ---- ring grouping for output -------------------------------------------------

def _inside(pt, ring):
    x, y = pt
    c = False
    n = len(ring)
    px, py = ring[-1]
    for qx, qy in ring:
        if (qy > y) != (py > y) and x < (px - qx) * (y - qy) / (py - qy) + qx:
            c = not c
        px, py = qx, qy
    return c


def polygons_of(rings, exterior_positive=True):
    """Flat rings -> list of [exterior, hole, hole, ...] (MVT: exterior has positive area2 in tile coordinates)."""
    ext, holes = [], []
    for r in rings:
        (ext if (area2(r) > 0) == exterior_positive else holes).append(r)
    polys = [[e] for e in ext]
    sizes = [abs(area2(e)) for e in ext]
    for h in holes:
        best = None
        for i, e in enumerate(ext):
            if (best is None or sizes[i] < sizes[best]) and any(_inside(p, e) for p in h[:3]):
                best = i
        if best is None:
            STATS["hole_without_exterior"] += 1
            continue
        polys[best].append(h)
    return polys


# ---- the merge -----------------------------------------------------------------

def merge_seamless(kids, extent):
    """kids: list of (layers, col, row, e). Returns merged layers (extent `extent`), seams removed."""
    e = kids[0][3]
    present = {(c, r) for _, c, r, _ in kids}
    xact = {r: (0, r) in present and (1, r) in present for r in (0, 1)}
    yact = any(r == 0 for _, r in present) and any(r == 1 for _, r in present)
    merged, order, slow = {}, [], defaultdict(list)
    for layers, col, row, _ in kids:
        dx, dy = col * e, row * e
        sx = xact[row]                      # a sibling shares the x seam
        for l in layers:
            m = merged.get(l.name)
            if m is None:
                m = mvt.Layer(l.name, extent, l.version)
                m._kidx, m._vidx = {}, {}
                merged[l.name] = m
                order.append(l.name)
            kmap = []
            for k in l.keys:
                if k not in m._kidx:
                    m._kidx[k] = len(m.keys); m.keys.append(k)
                kmap.append(m._kidx[k])
            vmap = []
            for v in l.values:
                if v not in m._vidx:
                    m._vidx[v] = len(m.values); m.values.append(v)
                vmap.append(m._vidx[v])
            for f in l.features:
                x0, y0, x1, y1 = bbox_of_geom(f.geom)
                inside = True
                if sx and ((col == 0 and x1 > e) or (col == 1 and x0 < 0)):
                    inside = False
                if yact and ((row == 0 and y1 > e) or (row == 1 and y0 < 0)):
                    inside = False
                if inside:
                    tags = []
                    for i in range(0, len(f.tags), 2):
                        tags.append(kmap[f.tags[i]]); tags.append(vmap[f.tags[i + 1]])
                    m.features.append(mvt.Feature(f.id, tags, f.type, mvt.shift_geom(f.geom, dx, dy)))
                    continue
                STATS["slow_features"] += 1
                props = tuple((l.keys[f.tags[i]], l.values[f.tags[i + 1]]) for i in range(0, len(f.tags), 2))
                parts = [[(x + dx, y + dy) for x, y in part] for part in decode_parts(f.geom)]
                slow[l.name].append(Piece(f.id, props, f.type, parts, col, row))
    for name in order:
        pieces = slow.get(name)
        if not pieces:
            continue
        m = merged[name]
        for r in (0, 1):                    # pass 1: x seam, inside each row
            if xact[r]:
                row_p = [p for p in pieces if p.row == r]
                rest = [p for p in pieces if p.row != r]
                pieces = rest + seam_pass(row_p, 0, e, lambda p: p.col == 0)
        if yact:                            # pass 2: y seam
            pieces = seam_pass(pieces, 1, e, lambda p: p.row == 0)
        for p in pieces:
            groups = polygons_of(p.parts) if p.ftype == 3 else [p.parts]
            tags = []
            for k, v in p.props:
                if k not in m._kidx:
                    m._kidx[k] = len(m.keys); m.keys.append(k)
                if v not in m._vidx:
                    m._vidx[v] = len(m.values); m.values.append(v)
                tags += [m._kidx[k], m._vidx[v]]
            for parts in groups:
                m.features.append(mvt.Feature(p.id, list(tags), p.ftype, encode_parts(parts, p.ftype)))
    return [merged[n] for n in order]
