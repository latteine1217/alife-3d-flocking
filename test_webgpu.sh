#!/bin/bash
# WebGPU Integration Test Script
# 
# 此腳本會：
# 1. 啟動 backend WebSocket server
# 2. 啟動 frontend dev server
# 3. 等待用戶手動測試
# 4. Ctrl+C 停止所有服務

echo "========================================="
echo "WebGPU Integration Test"
echo "========================================="
echo ""

# 檢查依賴
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' not found. Please install uv first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Error: 'npm' not found. Please install Node.js first."
    exit 1
fi

# 創建 trap 來清理子進程
trap 'echo ""; echo "🛑 Stopping all services..."; kill $(jobs -p) 2>/dev/null; exit 0' INT TERM

# 啟動 Backend
echo "🚀 Starting Backend WebSocket Server..."
cd backend
uv run python server.py &
BACKEND_PID=$!
cd ..

# 等待 backend 啟動
echo "⏳ Waiting for backend to start..."
sleep 3

# 檢查 backend 是否啟動成功
if ! ps -p $BACKEND_PID > /dev/null; then
    echo "❌ Backend failed to start!"
    exit 1
fi

echo "✅ Backend started (PID: $BACKEND_PID)"
echo ""

# 啟動 Frontend
echo "🚀 Starting Frontend Dev Server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 等待 frontend 啟動
echo "⏳ Waiting for frontend to start..."
sleep 5

echo ""
echo "========================================="
echo "✅ All services started!"
echo "========================================="
echo ""
echo "📋 Test Instructions:"
echo "1. Open browser: http://localhost:5173"
echo "2. Click '🔌 Connect' button"
echo "3. Click '▶ Start' button"
echo "4. Test camera controls:"
echo "   - Left drag: Rotate"
echo "   - Right drag: Pan"
echo "   - Scroll: Zoom"
echo "5. Check console (F12) for FPS/errors"
echo ""
echo "Expected Result:"
echo "- See colored particles (Blue/Orange/Red)"
echo "- Smooth 60 FPS rendering"
echo "- Statistics updating in real-time"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo "========================================="
echo ""

# 等待用戶按 Ctrl+C
wait
