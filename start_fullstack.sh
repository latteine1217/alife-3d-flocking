#!/usr/bin/env bash
# Full Stack 啟動腳本：Backend + Frontend
# 使用說明：
# 1. 啟動後端 WebSocket 伺服器（ws://localhost:8765）
# 2. 啟動前端開發伺服器（http://localhost:5173）
# 3. 前端會自動連接後端並即時顯示模擬結果

set -e

cd "$(dirname "$0")"

echo "==================================="
echo "🚀 Full Stack Flocking Simulation"
echo "==================================="
echo ""

# 檢查依賴
echo "📦 Checking dependencies..."
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' not found. Please install uv first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Error: 'npm' not found. Please install Node.js and npm first."
    exit 1
fi

# 安裝前端依賴（如果需要）
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# 創建 log 目錄
mkdir -p logs

# 啟動 Backend（背景執行）
echo ""
echo "🔧 Starting Backend WebSocket Server..."
cd backend
uv run python server.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "   Backend PID: $BACKEND_PID"
echo "   Backend URL: ws://localhost:8765"
echo "   Backend logs: logs/backend.log"

# 等待 Backend 啟動
echo "   Waiting for backend to start..."
sleep 3

# 檢查 Backend 是否正常運行
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start! Check logs/backend.log"
    exit 1
fi

# 啟動 Frontend（背景執行）
echo ""
echo "🎨 Starting Frontend Dev Server..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend PID: $FRONTEND_PID"
echo "   Frontend URL: http://localhost:5173"
echo "   Frontend logs: logs/frontend.log"

# 等待 Frontend 啟動
echo "   Waiting for frontend to start..."
sleep 3

# 檢查 Frontend 是否正常運行
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend failed to start! Check logs/frontend.log"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 成功啟動
echo ""
echo "==================================="
echo "✅ Full Stack Started Successfully!"
echo "==================================="
echo ""
echo "📡 Backend:  ws://localhost:8765"
echo "🌐 Frontend: http://localhost:5173"
echo ""
echo "📋 To view logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 To stop all services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Or run: pkill -f 'python server.py' && pkill -f 'vite'"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# 設定清理函數
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ All services stopped"
    exit 0
}

# 註冊清理函數
trap cleanup SIGINT SIGTERM

# 保持腳本運行
wait
