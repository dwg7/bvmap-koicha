"""Minimal PMTiles v3 reader (stdlib only). Yields (z, x, y, raw_tile_bytes_as_stored)."""
import gzip
import struct


def _varint(buf, pos):
    result = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7


def _decompress(data, comp):
    if comp == 2:  # gzip
        return gzip.decompress(data)
    if comp in (0, 1):
        return data
    raise ValueError(f"unsupported compression {comp}")


def _read_dir(buf):
    pos = 0
    n, pos = _varint(buf, pos)
    ids, last = [], 0
    for _ in range(n):
        d, pos = _varint(buf, pos)
        last += d
        ids.append(last)
    runs = []
    for _ in range(n):
        v, pos = _varint(buf, pos)
        runs.append(v)
    lens = []
    for _ in range(n):
        v, pos = _varint(buf, pos)
        lens.append(v)
    offs = []
    for i in range(n):
        v, pos = _varint(buf, pos)
        if v == 0 and i > 0:
            offs.append(offs[i - 1] + lens[i - 1])
        else:
            offs.append(v - 1)
    return list(zip(ids, runs, offs, lens))


def _id_to_zxy(tid):
    z = 0
    while True:
        n = (1 << z) * (1 << z)
        if tid < n:
            break
        tid -= n
        z += 1
    # Hilbert d -> xy
    x = y = 0
    t = tid
    s = 1
    while s < (1 << z):
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return z, x, y


def read_header(f):
    f.seek(0)
    h = f.read(127)
    assert h[:7] == b"PMTiles" and h[7] == 3
    u = struct.unpack("<8Q", h[8:72])
    keys = ("root_off", "root_len", "meta_off", "meta_len", "ldir_off", "ldir_len", "data_off", "data_len")
    d = dict(zip(keys, u))
    d["internal_comp"] = h[97]
    d["tile_comp"] = h[98]
    d["tile_type"] = h[99]
    d["min_zoom"], d["max_zoom"] = h[100], h[101]
    return d


def iter_tiles(path):
    """Yield (z, x, y, stored_bytes). stored_bytes are compressed per header tile_comp (gzip)."""
    with open(path, "rb") as f:
        hd = read_header(f)

        def load(off, ln):
            f.seek(off)
            return _read_dir(_decompress(f.read(ln), hd["internal_comp"]))

        stack = [load(hd["root_off"], hd["root_len"])]
        while stack:
            for tid, run, off, ln in stack.pop():
                if run == 0:
                    stack.append(load(hd["ldir_off"] + off, ln))
                else:
                    f.seek(hd["data_off"] + off)
                    data = f.read(ln)
                    for k in range(run):
                        z, x, y = _id_to_zxy(tid + k)
                        yield z, x, y, data


def read_metadata(path):
    import json
    with open(path, "rb") as f:
        hd = read_header(f)
        f.seek(hd["meta_off"])
        return json.loads(_decompress(f.read(hd["meta_len"]), hd["internal_comp"]))
