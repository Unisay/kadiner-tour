#!/usr/bin/env bash
# Generate web-optimized equirectangular panoramas + thumbnails from the
# original 11904x5952 JPGs in assets/.
#
#   WEB_W    width of the web panoramas (default 4096 — universally WebGL-safe)
#   THUMB_W  width of the inspection thumbnails (default 1536)
#   THUMB_DIR where thumbnails go (default ./thumbs)
#
# Scenes are named scene01..sceneNN in the sorted order of the source files;
# the mapping is written to images/mapping.tsv.
set -euo pipefail

# Re-exec inside nix-shell if imagemagick is unavailable.
if ! command -v magick >/dev/null 2>&1; then
  exec nix-shell -p imagemagick --run "bash '$0' $*"
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/assets"
OUT="$ROOT/images"
WEB_W="${WEB_W:-4096}"
THUMB_W="${THUMB_W:-1536}"
THUMB_DIR="${THUMB_DIR:-$ROOT/thumbs}"

mkdir -p "$OUT" "$THUMB_DIR"
: > "$OUT/mapping.tsv"

n=0
for f in "$SRC"/*.jpg; do
  n=$((n+1))
  id=$(printf "scene%02d" "$n")
  printf '%s\t%s\n' "$id" "$(basename "$f")" >> "$OUT/mapping.tsv"
  echo "[$id] $(basename "$f") -> ${WEB_W}px web + ${THUMB_W}px thumb"
  magick "$f" -auto-orient \
    -resize "${WEB_W}x" -strip -quality 85 -interlace Plane -write "$OUT/$id.jpg" \
    -resize "${THUMB_W}x" -quality 80 "$THUMB_DIR/$id.jpg"
done
echo "Done: $n scenes -> $OUT (web) + $THUMB_DIR (thumbs)"
