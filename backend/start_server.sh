#!/usr/bin/env bash
# Backend WebSocket Server 啟動腳本

cd "$(dirname "$0")"

echo "=== Flocking WebSocket Server ==="
echo "Starting server at ws://localhost:8765"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uv run python server.py
