#!/usr/bin/env python3
"""style/make_koicha_starlight.py — derive bvmap-koicha-starlight from dwg7/bvmap's bvmap-starlight (DECISIONS D8).

koicha tile zoom z carries bvmap's z+1 content (D3, `hyp`), so every zoom value in the style moves down by one:
  - layer minzoom / maxzoom                        (n -> n-1)
  - stops of ["step", ["zoom"], ...]               (n -> n-1)
  - stops of ["interpolate*", _, ["zoom"], ...]    (n -> n-1)
Nothing else in the style is changed except the source (tiles come from bvmap-koicha, MLT) and the attribution.
Usage: make_koicha_starlight.py [--source-url URL] [--minzoom N] [--no-patches] [-o OUT]
After the shift, the koicha patches of style/patches.py are applied (contours, ...); see DECISIONS D24.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patches
UPSTREAM = os.path.join(HERE, "upstream", "bvmap-starlight.json")
# Martin composite source: every regional bvmap-koicha tile set served by stars (cells are disjoint, DECISIONS D19/D20)
DEFAULT_URL = "https://stars.optgeo.org/bvmap-koicha-hokkaido,bvmap-koicha-tokyo"
ATTRIBUTION = ("国土地理院最適化ベクトルタイルを加工して作成。"
               "スプライトアイコンは国土地理院最適化ベクトルタイルの原本を改変(グレースケール化)して使用。"
               "改変者: dwg7/bvmap、dwg7/bvmap-koicha。国土地理院コンテンツ利用規約に基づく。"
               "国土地理院の公式な製品ではありません。")
stats = {"step": 0, "interpolate": 0, "minzoom": 0, "maxzoom": 0}


def shift_expr(o):
    if isinstance(o, list):
        out = [shift_expr(x) for x in o]
        if o and o[0] == "step" and len(o) > 2 and o[1] == ["zoom"]:
            for i in range(3, len(o), 2):
                out[i] = o[i] - 1
            stats["step"] += 1
        elif o and isinstance(o[0], str) and o[0].startswith("interpolate") and len(o) > 3 and o[2] == ["zoom"]:
            for i in range(3, len(o), 2):
                out[i] = o[i] - 1
            stats["interpolate"] += 1
        return out
    if isinstance(o, dict):
        return {k: shift_expr(v) for k, v in o.items()}
    return o


def count_zoom_refs(o):
    if isinstance(o, list):
        return (1 if o == ["zoom"] else 0) + sum(count_zoom_refs(x) for x in o)
    if isinstance(o, dict):
        return sum(count_zoom_refs(v) for v in o.values())
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-url", default=DEFAULT_URL)
    ap.add_argument("--no-patches", action="store_true", help="only shift the zoom values (D8); skip the koicha cartographic patches (D24)")
    ap.add_argument("--minzoom", type=int, default=3, help="source minzoom (3 for the tokyo set; 4 for the hokkaido cell set)")
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "bvmap-koicha-starlight.json"))
    a = ap.parse_args()
    up = json.load(open(UPSTREAM))
    s = copy.deepcopy(up)
    # every ["zoom"] must sit directly in a step/interpolate we know how to shift
    total_refs = count_zoom_refs(up["layers"])
    s["layers"] = []
    for l in up["layers"]:
        l = shift_expr(l)
        for k in ("minzoom", "maxzoom"):
            if k in l:
                l[k] -= 1
                stats[k] += 1
        s["layers"].append(l)
    assert stats["step"] + stats["interpolate"] == total_refs, "unhandled ['zoom'] usage"
    assert count_zoom_refs(s["layers"]) == total_refs
    s["name"] = "bvmap-koicha-starlight (bvmap-starlight with zoom values shifted by -1 for bvmap-koicha tiles)"
    src = s["sources"]["bvmap"]
    s["sources"]["bvmap"] = {
        "type": "vector", "url": a.source_url, "encoding": "mlt", "minzoom": a.minzoom, "maxzoom": 16,
        "attribution": ATTRIBUTION,
    }
    s["metadata"] = {"derived-from": "dwg7/bvmap style/bvmap-starlight.json @ 9068c809beeecaec2a97366f8e1a6e210459eacd",
                     "zoom-shift": -1, "generator": "dwg7/bvmap-koicha style/make_koicha_starlight.py"}
    if not a.no_patches:
        for name, fn in patches.PATCHES:
            s = fn(s)
        s["metadata"]["patches"] = [n for n, _ in patches.PATCHES]
    with open(a.out, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {a.out}: layers={len(s['layers'])} {stats}")


if __name__ == "__main__":
    main()
