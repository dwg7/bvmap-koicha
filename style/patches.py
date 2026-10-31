"""style/patches.py — bvmap-koicha specific cartographic adjustments, applied AFTER the zoom shift (DECISIONS D24).

The upstream bvmap-starlight is never edited; each patch takes the shifted style (a dict) and returns it.
`make_koicha_starlight.py --no-patches` produces the pure zoom shift (D8). Zoom values below are koicha display zooms.
"""
import copy

# --- contours (Cntr) -----------------------------------------------------------------------------------------------
# Index contour (計曲線) = vt_alti is a multiple of 50 m; the rest are intermediate contours (主曲線, 10 m or finer).
IS_INDEX = ["==", ["%", ["get", "vt_alti"], 50], 0]
INDEX_COLOR = "rgba(146,147,152,1)"
INTERMEDIATE_COLOR = "rgba(192,193,197,1)"
# line-width (px) by display zoom. Upstream: 1.4 / 0.7 at every zoom >= 12 and the same grey for both.
INDEX_WIDTH = ["interpolate", ["linear"], ["zoom"], 8, 0.4, 11, 0.55, 13, 0.8, 15, 1.1, 17, 1.5, 19, 2.0]
INTERMEDIATE_WIDTH = ["interpolate", ["linear"], ["zoom"], 13, 0.25, 15, 0.4, 17, 0.6, 19, 0.9]


def contours(style):
    out = []
    for layer in style["layers"]:
        if layer.get("id") == "bvmap-等高線" and layer.get("source-layer") == "Cntr" and layer.get("type") == "line":
            base = copy.deepcopy(layer)             # keeps the upstream line-opacity (visibility by zoom and vt_code)
            inter = copy.deepcopy(base)
            inter["filter"] = ["!", IS_INDEX]
            inter["paint"]["line-color"] = INTERMEDIATE_COLOR
            inter["paint"]["line-width"] = INTERMEDIATE_WIDTH
            index = copy.deepcopy(base)
            index["id"] = "bvmap-等高線(計曲線)"
            index["filter"] = IS_INDEX
            index["paint"]["line-color"] = INDEX_COLOR
            index["paint"]["line-width"] = INDEX_WIDTH
            out += [inter, index]                    # index contours are drawn on top of the intermediate ones
        else:
            out.append(layer)
    style["layers"] = out
    return style


# --- true-width roads from z15 (DECISIONS D26) ----------------------------------------------------------------------
# Upstream (bvmap) switches from road centre lines to road edges (RdEdg, RdCompt, RailTrCL, StrctLine) at bvmap z17 = koicha z16.
# Here the switch moves one zoom up (z15), which needs the tiles built with `--roads`. Edge lines are 2-3 px wide at z16+ in the
# upstream style; at z15 a road is only ~1-2 px wide on the ground, so the lines get thinner with the zoom (x0.3 at z15, x0.6 at z16, x1 at z17).
EDGE_LAYERS = ("RdEdg", "RdCompt", "RailTrCL", "StrctLine")
CENTRE_LAYERS = ("RdCL", "RailCL")
OLD_SWITCH, NEW_SWITCH = 16, 15
WIDTH_FACTORS = [(15, 0.3), (16, 0.6), (17, 1.0)]


def _scale_width(w):
    stops = []
    for z, f in WIDTH_FACTORS:
        stops += [z, round(w * f, 3) if isinstance(w, (int, float)) else ["*", w, f]]
    return ["interpolate", ["linear"], ["zoom"], *stops]


def _move_switch(o):
    """step on zoom with a stop at OLD_SWITCH -> NEW_SWITCH"""
    if isinstance(o, list):
        out = [_move_switch(x) for x in o]
        if o and o[0] == "step" and len(o) > 2 and o[1] == ["zoom"]:
            for i in range(3, len(o), 2):
                if o[i] == OLD_SWITCH:
                    out[i] = NEW_SWITCH
        return out
    if isinstance(o, dict):
        return {k: _move_switch(v) for k, v in o.items()}
    return o


def roads(style):
    for layer in style["layers"]:
        sl = layer.get("source-layer")
        if sl in EDGE_LAYERS:
            if layer.get("minzoom") == OLD_SWITCH:
                layer["minzoom"] = NEW_SWITCH
            w = layer.get("paint", {}).get("line-width")
            if w is not None:
                layer["paint"]["line-width"] = _scale_width(w)
        elif sl in CENTRE_LAYERS:
            if layer.get("maxzoom") == OLD_SWITCH:
                layer["maxzoom"] = NEW_SWITCH
            if "filter" in layer:
                layer["filter"] = _move_switch(layer["filter"])
    return style


PATCHES = [("contours", contours)]
OPTIONAL_PATCHES = {"roads": roads}
