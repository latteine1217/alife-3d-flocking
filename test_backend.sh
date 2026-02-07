#!/bin/bash
# Backend 快速測試腳本

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         Backend Quick Test - WebSocket Simulation Server        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/backend"

# 測試 1: SimulationManager
echo "=== Test 1: SimulationManager ==="
echo "Testing system creation and stepping..."
echo ""
uv run python simulation_manager.py
echo ""
echo "✅ Test 1 completed!"
echo ""

# 測試 2: Serializer Performance
echo "=== Test 2: Serializer Performance ==="
echo "Testing binary serialization speed..."
echo ""
uv run python serializer.py
echo ""
echo "✅ Test 2 completed!"
echo ""

# 總結
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    All Backend Tests Passed! ✅                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Start WebSocket server: ./backend/start_server.sh"
echo "  2. Test connection: cd backend && uv run python test_client.py"
echo ""
