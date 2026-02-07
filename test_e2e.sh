#!/bin/bash
# 端到端測試腳本
# 啟動 Backend 和 Frontend 進行測試

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║            End-to-End Test - Backend + Frontend                 ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# 檢查是否有正在運行的 backend
if lsof -i :8765 > /dev/null 2>&1; then
    echo "✅ Backend is already running on port 8765"
else
    echo "❌ Backend is not running!"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend && ./start_server.sh"
    echo ""
    exit 1
fi

# 啟動 frontend
echo "Starting frontend development server..."
echo "Open http://localhost:5173 in your browser"
echo ""
echo "Test steps:"
echo "  1. Click 'Connect' button"
echo "  2. Click 'Start' button"
echo "  3. Watch statistics update in real-time"
echo "  4. Check browser console (F12) for frame data"
echo ""

cd frontend
npm run dev
