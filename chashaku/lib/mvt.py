"""Minimal, lossless MVT (Mapbox Vector Tile, protobuf) codec for chashaku.

Design goals:
- Round-trips bvmap tiles without touching feature contents (tag values and
  geometry command integers are kept verbatim).
- Cheap tile bundling: shifting a feature by (dx, dy) only requires rewriting
  the first MoveTo of its geometry, because geometry is delta-encoded.
"""
from dataclasses import dataclass, field


# ---- protobuf wire helpers -------------------------------------------------

def read_varint(buf, pos):
    result = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7


def write_varint(out, v):
    while v > 0x7F:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)


def varint_len(v):
    n = 1
    while v > 0x7F:
        v >>= 7
        n += 1
    return n


def iter_fields(buf):
    """Yield (field_no, wire_type, value) where value is int (varint/fixed) or bytes (len-delimited)."""
    pos, end = 0, len(buf)
    while pos < end:
        key, pos = read_varint(buf, pos)
        fno, wt = key >> 3, key & 7
        if wt == 0:
            v, pos = read_varint(buf, pos)
        elif wt == 2:
            ln, pos = read_varint(buf, pos)
            v = bytes(buf[pos:pos + ln])
            pos += ln
        elif wt == 1:
            v = bytes(buf[pos:pos + 8])
            pos += 8
        elif wt == 5:
            v = bytes(buf[pos:pos + 4])
            pos += 4
        else:
            raise ValueError(f"unsupported wire type {wt}")
        yield fno, wt, v


def unpack_varints(buf):
    out, pos = [], 0
    while pos < len(buf):
        v, pos = read_varint(buf, pos)
        out.append(v)
    return out


def zigzag(v):
    return (v << 1) ^ (v >> 63) if v < 0 else v << 1


def unzigzag(v):
    return (v >> 1) ^ -(v & 1)


# ---- model -----------------------------------------------------------------

@dataclass
class Feature:
    id: object  # int or None
    tags: list  # [key_idx, val_idx, ...] indices into the layer tables
    type: int   # 1 point, 2 line, 3 polygon
    geom: list  # command integers, verbatim


@dataclass
class Layer:
    name: str
    extent: int = 4096
    version: int = 2
    keys: list = field(default_factory=list)      # list[str]
    values: list = field(default_factory=list)    # list[bytes] raw Value messages
    features: list = field(default_factory=list)


def decode_tile(buf):
    layers = []
    for fno, _, lv in iter_fields(buf):
        if fno != 3:
            continue
        layer = Layer(name="")
        for f2, w2, v2 in iter_fields(lv):
            if f2 == 1:
                layer.name = v2.decode()
            elif f2 == 2:
                feat = Feature(None, [], 0, [])
                for f3, w3, v3 in iter_fields(v2):
                    if f3 == 1:
                        feat.id = v3
                    elif f3 == 2:
                        feat.tags = unpack_varints(v3)
                    elif f3 == 3:
                        feat.type = v3
                    elif f3 == 4:
                        feat.geom = unpack_varints(v3)
                layer.features.append(feat)
            elif f2 == 3:
                layer.keys.append(v2.decode())
            elif f2 == 4:
                layer.values.append(v2)
            elif f2 == 5:
                layer.extent = v2
            elif f2 == 15:
                layer.version = v2
        layers.append(layer)
    return layers


def _encode_feature(feat):
    # Field order mirrors tippecanoe (id, type, tags, geometry).
    out = bytearray()
    if feat.id is not None:
        write_varint(out, (1 << 3) | 0)
        write_varint(out, feat.id)
    write_varint(out, (3 << 3) | 0)
    write_varint(out, feat.type)
    if feat.tags:
        tb = bytearray()
        for t in feat.tags:
            write_varint(tb, t)
        write_varint(out, (2 << 3) | 2)
        write_varint(out, len(tb))
        out += tb
    gb = bytearray()
    for g in feat.geom:
        write_varint(gb, g)
    write_varint(out, (4 << 3) | 2)
    write_varint(out, len(gb))
    out += gb
    return out


def _len_field(out, fno, payload):
    write_varint(out, (fno << 3) | 2)
    write_varint(out, len(payload))
    out += payload


def encode_layer(layer):
    # Field order mirrors tippecanoe's output (version, name, extent, keys, values, features)
    # so that an unmodified tile re-encodes byte-for-byte.
    out = bytearray()
    write_varint(out, (15 << 3) | 0)
    write_varint(out, layer.version)
    _len_field(out, 1, layer.name.encode())
    write_varint(out, (5 << 3) | 0)
    write_varint(out, layer.extent)
    for k in layer.keys:
        _len_field(out, 3, k.encode())
    for v in layer.values:
        _len_field(out, 4, v)
    for f in layer.features:
        _len_field(out, 2, _encode_feature(f))
    return out


def encode_tile(layers):
    out = bytearray()
    for l in layers:
        if l.features:
            _len_field(out, 3, encode_layer(l))
    return bytes(out)


# ---- value / geometry helpers ---------------------------------------------

def decode_value(raw):
    """Return the python value of a raw Value message."""
    import struct
    for fno, wt, v in iter_fields(raw):
        if fno == 1:
            return v.decode()
        if fno == 2:
            return struct.unpack("<f", v)[0]
        if fno == 3:
            return struct.unpack("<d", v)[0]
        if fno in (4, 5):
            return v
        if fno == 6:
            return unzigzag(v)
        if fno == 7:
            return bool(v)
    return None


def feature_props(layer, feat):
    t = feat.tags
    return {layer.keys[t[i]]: decode_value(layer.values[t[i + 1]]) for i in range(0, len(t), 2)}


def count_vertices(geom):
    """Number of vertices (ClosePath not counted)."""
    n, i = 0, 0
    while i < len(geom):
        ci = geom[i]
        cmd, cnt = ci & 7, ci >> 3
        i += 1
        if cmd in (1, 2):
            n += cnt
            i += 2 * cnt
    return n


def shift_geom(geom, dx, dy):
    """Return geometry shifted by (dx, dy); only the first MoveTo changes (delta encoding)."""
    if not geom:
        return geom
    assert geom[0] & 7 == 1, "geometry must start with MoveTo"
    g = list(geom)
    g[1] = zigzag(unzigzag(g[1]) + dx)
    g[2] = zigzag(unzigzag(g[2]) + dy)
    return g


# ---- bundling / filtering ---------------------------------------------------

def merge_children(children, extent):
    """children: list of (layers, dx, dy) with offsets in the parent's coordinate system
    (parent extent = 2 * child extent; the caller passes dx, dy already in child units
    times child quadrant). Features are concatenated; geometry is only translated."""
    merged = {}
    order = []
    for layers, dx, dy in children:
        for l in layers:
            m = merged.get(l.name)
            if m is None:
                m = Layer(l.name, extent, l.version)
                m._kidx, m._vidx = {}, {}
                merged[l.name] = m
                order.append(l.name)
            kmap = []
            for k in l.keys:
                if k not in m._kidx:
                    m._kidx[k] = len(m.keys)
                    m.keys.append(k)
                kmap.append(m._kidx[k])
            vmap = []
            for v in l.values:
                if v not in m._vidx:
                    m._vidx[v] = len(m.values)
                    m.values.append(v)
                vmap.append(m._vidx[v])
            for f in l.features:
                tags = []
                for i in range(0, len(f.tags), 2):
                    tags.append(kmap[f.tags[i]])
                    tags.append(vmap[f.tags[i + 1]])
                m.features.append(Feature(f.id, tags, f.type, shift_geom(f.geom, dx, dy)))
    return [merged[n] for n in order]


def filter_layers(layers, drop_layers=(), feature_pred=None):
    """Drop whole layers and/or features (pred(layer, feat) -> keep?). Tables are rebuilt
    so that dropped values do not stay in the output."""
    out = []
    for l in layers:
        if l.name in drop_layers:
            continue
        kept = [f for f in l.features if feature_pred is None or feature_pred(l, f)]
        if not kept:
            continue
        n = Layer(l.name, l.extent, l.version)
        kmap, vmap = {}, {}
        for f in kept:
            tags = []
            for i in range(0, len(f.tags), 2):
                k, v = f.tags[i], f.tags[i + 1]
                if k not in kmap:
                    kmap[k] = len(n.keys)
                    n.keys.append(l.keys[k])
                if v not in vmap:
                    vmap[v] = len(n.values)
                    n.values.append(l.values[v])
                tags += [kmap[k], vmap[v]]
            n.features.append(Feature(f.id, tags, f.type, f.geom))
        out.append(n)
    return out
