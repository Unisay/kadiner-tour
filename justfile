[private]
default:
    @just help

# Show available commands
help:
    @just --list

# Regenerate web panoramas (4096px) + thumbnails from assets/
images:
    bash scripts/build-images.sh

# Same, but at a custom panorama width, e.g. `just images-w 8192`
images-w width:
    WEB_W={{width}} bash scripts/build-images.sh

# Compile scenes.json -> tour.json
tour:
    python3 scripts/build-tour.py

# Build everything (images + tour)
build: images tour

# Serve the tour + authoring backend at http://localhost:8000 (Ctrl-C to stop)
serve:
    python3 scripts/serve.py 8000

# Read-only static server (no save endpoint) — to preview the published tour
serve-static:
    @echo "http://localhost:8000/"
    python3 -m http.server 8000

# Rebuild labeled contact sheets of all panoramas into thumbs/_sheet_*.jpg
sheets:
    nix-shell -p imagemagick --run 'montage thumbs/scene*.jpg -tile 2x -geometry 760x380+4+4 -label "%t" -pointsize 26 -background black -fill yellow thumbs/_sheet.jpg'
