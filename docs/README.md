# docs/

- `index.html` — the GitHub Pages test page (served from `main` / `docs`): bvmap-starlight and bvmap-koicha-starlight side by side, same view and zoom, `#zoom/lat/lng` in the URL. DECISIONS D23.
- `vendor/maplibre-gl-6.14.0/` — MapLibre GL JS 6.14.0 (BSD-3-Clause, `LICENSE.txt`), vendored from the npm package so the page has no third-party runtime dependency. Update together with `viewer/package.json`.
- `bvmap-anatomy.md` — what the bvmap tiles contain.
- `.nojekyll` — tells GitHub Pages to serve the files as they are (no Jekyll).
