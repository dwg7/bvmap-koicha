# tools/

Third-party binaries used by chashaku. They are **not committed**; fetch and verify them with the scripts here.

| tool | version | source | sha256 |
|---|---|---|---|
| `mlt` (MapLibre Tile Tools, Rust) | 0.4.3 (release `rust-mlt-v0.4.3`, 2026-10-12) | https://github.com/maplibre/maplibre-tile-spec/releases/tag/rust-mlt-v0.4.3 — `mlt-aarch64-apple-darwin.tar.gz` | `c3796143381b6178b10335b1873cf36fb6b5279efcadf630bf3fa31550ba2a68` |

Other platforms: the same release has `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu` and `x86_64-pc-windows-msvc` assets
(digests are listed on the release page). `fetch-mlt.sh` only knows the macOS arm64 asset used in the first measurement.

`mlt 0.4.3` needs Rust 1.98 to build from source; the machine used for the first measurement had 1.96.1, hence the prebuilt binary.
