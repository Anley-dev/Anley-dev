#!/bin/bash
# ============================================================
# Hawassa Call Center Navigation System — Startup Script
# ============================================================
# Run this once after every server reboot.
# Usage: ./start.sh
# ============================================================

set -e
cd "$(dirname "$0")"

echo "▶  Starting Valhalla routing engine..."
docker start hawassa-valhalla 2>/dev/null || echo "   (already running)"

echo "▶  Starting TileServer GL (offline map tiles)..."
docker start hawassa-tileserver 2>/dev/null || echo "   (already running)"

echo "▶  Starting Ollama AI engine..."
systemctl start ollama 2>/dev/null || ollama serve &>/tmp/ollama.log & 
sleep 2

echo "▶  Starting FastAPI web app on port 8080..."
# Stop any existing systemd user service or process
systemctl --user stop hawassa-web.service 2>/dev/null || true
pkill -f "web_app|uvicorn" 2>/dev/null || true
sleep 1

# Start via systemd-run so it runs persistently as a systemd background service
systemd-run --user --unit=hawassa-web python3 /home/anley/dogo/web_app.py
sleep 2

sleep 2
echo ""
echo "✅  All services started."
echo ""
echo "   🗺️  Map URL:        http://localhost:8080"
echo "   📡  API Status:    http://localhost:8080/api/status"
echo "   🧱  Tiles:         http://localhost:8081"
echo "   🛣️  Valhalla:      http://localhost:8002"
echo "   🤖  Ollama:        http://localhost:11434"
echo ""
echo "   Logs: tail -f /tmp/hawassa_webapp.log"
