#!/usr/bin/env bash
# Fetch mlt 0.4.3 (macOS arm64) from the official maplibre-tile-spec release and verify its sha256.
set -euo pipefail
cd "$(dirname "$0")"
VER=0.4.3
ASSET=mlt-aarch64-apple-darwin.tar.gz
SHA=c3796143381b6178b10335b1873cf36fb6b5279efcadf630bf3fa31550ba2a68
tmp=$(mktemp -d)
curl -sL -o "$tmp/$ASSET" "https://github.com/maplibre/maplibre-tile-spec/releases/download/rust-mlt-v$VER/$ASSET"
echo "$SHA  $tmp/$ASSET" | shasum -a 256 -c -
mkdir -p "mlt-$VER"
tar -xzf "$tmp/$ASSET" -C "mlt-$VER"
xattr -d com.apple.quarantine "mlt-$VER/mlt" 2>/dev/null || true
"mlt-$VER/mlt" --version
