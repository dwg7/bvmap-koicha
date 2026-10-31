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


PATCHES = [("contours", contours)]
