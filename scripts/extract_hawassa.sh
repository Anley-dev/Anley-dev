#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../data" && pwd)"
MAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../map" && pwd)"

echo "=== Dogo Hawassa OSM Extraction Pipeline ==="

cd "$DATA_DIR"

# 1. Download Ethiopia extract if not present
if [ ! -f "ethiopia-latest.osm.pbf" ]; then
    echo "[1/3] Downloading Ethiopia OSM extract..."
    wget -c https://download.geofabrik.de/africa/ethiopia-latest.osm.pbf
else
    echo "[1/3] Ethiopia OSM extract already present."
fi

# 2. Extract Hawassa bounding box (Lake Hawassa, Piazza, Menharya, 05, University)
# Bounding box: min_lon=38.40, min_lat=7.00, max_lon=38.55, max_lat=7.12
echo "[2/3] Extracting Hawassa bounding box (38.40,7.00,38.55,7.12)..."
if command -v osmium &> /dev/null; then
    osmium extract --bbox 38.40,7.00,38.55,7.12 ethiopia-latest.osm.pbf -o hawassa.osm.pbf --overwrite
else
    echo "Warning: osmium-tool not found on PATH. Install via: sudo apt-get install osmium-tool"
    exit 1
fi

# 3. Generate offline vector tiles (.mbtiles)
echo "[3/3] Generating offline vector tiles (hawassa.mbtiles)..."
if command -v tilemaker &> /dev/null; then
    CONFIG_FILE="/usr/share/doc/tilemaker/examples/config-openmaptiles.json"
    PROCESS_FILE="/usr/share/doc/tilemaker/examples/process-openmaptiles.lua"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="/usr/share/tilemaker/config-openmaptiles.json"
        PROCESS_FILE="/usr/share/tilemaker/process-openmaptiles.lua"
    fi
    tilemaker --input hawassa.osm.pbf \
              --output "$MAP_DIR/hawassa.mbtiles" \
              --config "$CONFIG_FILE" \
              --process "$PROCESS_FILE" \
              --bbox 38.40,7.00,38.55,7.12
elif command -v planetiler &> /dev/null; then
    planetiler --osm-path=hawassa.osm.pbf --output="$MAP_DIR/hawassa.mbtiles" --bbox=38.40,7.00,38.55,7.12
else
    echo "Notice: Neither tilemaker nor planetiler binary found on PATH."
    echo "You can run tilemaker via Docker: docker run -v \"\$DATA_DIR\":/data -v \"\$MAP_DIR\":/map ghcr.io/systemed/tilemaker /data/hawassa.osm.pbf --output /map/hawassa.mbtiles"
fi

echo "Pipeline script finished."
