#!/usr/bin/env python3
"""build/pack_compressed.py — re-pack an MLT MVT-less mbtiles into a PMTiles with a chosen tile compression.

Usage: pack_compressed.py <in.mlt.mbtiles> <out.pmtiles> {gzip,brotli,zstd}
Each tile is compressed with the codec, written to a temp mbtiles, converted by `pmtiles convert` (which stores tiles verbatim), and
the PMTiles header (tile compression byte 98, tile type byte 99 = 6/MLT) is patched. Directory entries stay valid (lengths are of the stored bytes).
"""
import gzip
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

src, dst, codec = sys.argv[1:4]
COMP = {"gzip": 2, "brotli": 3, "zstd": 4}[codec]
CMD = {"brotli": ["brotli", "-q", "11", "-c"], "zstd": ["zstd", "-19", "-q", "-c"]}


def pack(b):
    return gzip.compress(b, 9, mtime=0) if codec == "gzip" else subprocess.run(CMD[codec], input=b, capture_output=True, check=True).stdout


tmp = tempfile.mkdtemp()
t = os.path.join(tmp, "t.mbtiles")
shutil.copy(src, t)
db = sqlite3.connect(t)
rows = db.execute("select zoom_level,tile_column,tile_row,tile_data from tiles").fetchall()
for z, x, y, d in rows:
    db.execute("update tiles set tile_data=? where zoom_level=? and tile_column=? and tile_row=?", (pack(d), z, x, y))
db.commit(); db.close()
if os.path.exists(dst):
    os.remove(dst)
subprocess.run(["pmtiles", "convert", t, dst], check=True, capture_output=True)
with open(dst, "r+b") as f:
    f.seek(98); f.write(bytes([COMP, 6]))
shutil.rmtree(tmp)
print("wrote", dst, os.path.getsize(dst))
