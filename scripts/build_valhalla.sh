#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROUTING_DIR="$ROOT_DIR/routing"
DATA_DIR="$ROOT_DIR/data"

echo "=== Dogo Valhalla Routing Pipeline ==="

# Clean up empty or broken valhalla.json if left over from a failed run
if [ -f "$ROUTING_DIR/valhalla.json" ] && [ ! -s "$ROUTING_DIR/valhalla.json" ]; then
  echo "Found 0-byte valhalla.json. Removing to allow clean auto-generation..."
  rm -f "$ROUTING_DIR/valhalla.json"
fi

# Ensure Hawassa extract is present in routing
cp -f "$DATA_DIR/hawassa.osm.pbf" "$ROUTING_DIR/hawassa.osm.pbf"

echo "Running GIS-OPS Valhalla container..."
docker run --rm \
  --name dogo_valhalla_build \
  -v "$ROUTING_DIR":/custom_files \
  -e build_elevation=False \
  -e build_admins=False \
  -e build_time_zones=False \
  -p 8002:8002 \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
