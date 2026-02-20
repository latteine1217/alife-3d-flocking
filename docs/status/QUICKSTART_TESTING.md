# 前端整合快速測試指南

**目標**: 在 5 分鐘內啟動並驗證 WebGPU 前端整合

---

## 前置條件檢查

```bash
# 1. 檢查 uv (Backend)
uv --version

# 2. 檢查 Node.js (Frontend)
node --version  # 需要 >= 18
npm --version

# 3. 檢查瀏覽器
# Chrome >= 113 或 Edge >= 113
# 開啟 chrome://gpu 檢查 WebGPU 支援
```

---

## 快速啟動（一鍵部署）

```bash
cd /Users/latteine/Documents/coding/alife

# 方式 1: 全棧啟動（推薦）
./start_fullstack.sh

# 等待輸出：
# ✅ Full Stack Started Successfully!
# 📡 Backend:  ws://localhost:8765
# 🌐 Frontend: http://localhost:5173

# 瀏覽器訪問: http://localhost:5173
```

**如果出現權限錯誤**:
```bash
chmod +x start_fullstack.sh
chmod +x backend/start_server.sh
```

---

## 分步啟動（除錯用）

### Step 1: 啟動 Backend

```bash
# Terminal 1
cd backend
uv run python server.py

# 預期輸出：
# [Taichi] version 1.7.4, ...
# 🚀 Creating default system on startup...
# [HeterogeneousFlocking3D] Agent composition:
#   Follower: 50/100 ...
#   Explorer: 30/100 ...
#   Leader: 15/100 ...
#   Predator: 5/100 ...
# ✅ Created Heterogeneous system with N=100
# 🚀 Server started at ws://localhost:8765
# 📡 Waiting for connections...
```

**驗證**: Backend 已就緒，等待連線

### Step 2: 啟動 Frontend

```bash
# Terminal 2
cd frontend

# 首次執行需安裝依賴
npm install

# 啟動開發伺服器
npm run dev

# 預期輸出：
#   VITE v7.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: use --host to expose
```

**驗證**: Frontend 已啟動，訪問 http://localhost:5173

---

## 瀏覽器測試流程

### 1. 檢查 WebGPU 支援

訪問 `http://localhost:5173`，開啟 DevTools (F12)

**Console 應顯示**:
```
🚀 Canvas3D useEffect triggered
✅ Canvas ref obtained, proceeding with initialization
📐 Canvas size: 800x600, DPR: 2
🚀 Initializing WebGPU renderer...
🔍 Requesting GPU adapter...
✅ GPU adapter obtained
🔍 Requesting GPU device...
✅ GPU device obtained
...
✅ WebGPU initialized successfully
```

**如果出現錯誤**:
- `WebGPU not supported`: 瀏覽器版本過舊，升級至 Chrome 113+
- `Failed to get GPU adapter`: 檢查 chrome://gpu，確認 WebGPU 可用

### 2. 連接 Backend

點擊頁面上的 **"🔌 Connect"** 按鈕

**Console 應顯示**:
```
Store: Connected to server
📤 Sending initial params: {...}
🎯 System auto-initialized
```

**Backend Terminal 應顯示**:
```
✅ Client connected: ('127.0.0.1', xxxxx)
📝 Received update_params: {...}
```

**頁面變化**:
- 連接面板消失
- 出現 3D 畫布（黑色背景）
- 右側顯示控制面板和統計數據

### 3. 啟動模擬

點擊左側 **"▶ Start"** 按鈕

**Console 應顯示** (每秒一次):
```
🔵 WebSocket: Received binary data, size=3864
🔵 WebSocket: Deserialized state: N=100, positions.length=300
🔵 WebSocket: Validation passed
🔵 WebSocket: Notifying 1 callbacks
🟢 Store: onState callback triggered! N=100, positions.length=300
🔔 Canvas3D calling updateParticles: N=100, positions.length=300
🎨 Drawing 100 particles (6 vertices × 100 instances = 600 total)
```

**畫面變化**:
- 中間出現 100 個移動的彩色粒子
- 粒子顏色：
  - 🔵 藍色 = FOLLOWER (50 個)
  - 🟢 綠色 = EXPLORER (30 個)
  - 🟡 黃色 = LEADER (15 個)
  - 🔴 紅色 = PREDATOR (5 個)
- 白色線框 = 邊界盒 (50×50×50)
- 粒子留下軌跡（velocity trails）
- 綠色半透明球體 = 資源（可再生）
- 紅色半透明球體 = 資源（消耗性）

### 4. 互動測試

**相機控制**:
- 左鍵拖曳 → 旋轉視角
- 右鍵拖曳 → 平移畫面
- 滾輪 → 縮放
- 點擊 "🔄 Reset Camera" → 恢復預設視角

**渲染控制**:
- "✨ Trails" → 切換速度軌跡
- "🎭 By Type" / "🌈 By Group" → 切換著色模式
- "🔮 Boundaries" → 顯示群組邊界球體
- "➡️ Arrows" → 顯示群組速度箭頭
- "💎 Resources" → 顯示/隱藏資源球體

**統計數據** (右側面板):
```
Frame: 120
Particles: 100
Mean Speed: 1.023
Polarization: 0.156
Rg: 12.34
Groups: 3
```

### 5. 參數調整測試

展開左側 **"⚙️ Parameters"** 面板，調整參數：

1. **Alignment (beta)**: `1.0` → `2.0`
   - 點擊 "Apply"
   - Console 顯示: `📤 Sent command: update_params`
   - Backend 重建系統
   - 觀察粒子對齊度增加

2. **Noise (eta)**: `0.0` → `0.2`
   - 粒子運動變得更隨機

3. **Particle Count (N)**: `100` → `200`
   - 系統重建，粒子數量加倍

---

## 效能驗證

### 1. FPS 檢查

**Frontend FPS** (右上角 HUD):
```
Particles: 100
Step: 250
FPS: 60.0  ← 應接近 60
```

**Backend FPS** (Terminal):
每秒推送約 30 幀（看 `step` 增長速度）

### 2. 頻寬檢查

**Console 統計**:
```javascript
// 在瀏覽器 Console 執行
const ws = window.testStore.getState().ws;
const stats = ws.getStats();
console.log(`FPS: ${stats.fps.toFixed(1)}, Bandwidth: ${(stats.avgFrameSize * stats.fps / 1024).toFixed(1)} KB/s`);

// 預期輸出:
// FPS: 30.0, Bandwidth: 115.2 KB/s
```

### 3. 記憶體檢查

**Chrome DevTools → Performance Monitor**:
- JS Heap: 應穩定在 < 100 MB
- DOM Nodes: 應穩定 (無持續增長)

運行 5 分鐘，記憶體無持續增長 = 無洩漏 ✅

---

## 常見問題排查

### Q1: 頁面顯示 "WebGPU not supported"

**原因**: 瀏覽器版本過舊或 WebGPU 未啟用

**解決**:
1. 升級至 Chrome 113+ 或 Edge 113+
2. 訪問 `chrome://flags`，搜尋 "WebGPU"，確保啟用
3. 訪問 `chrome://gpu`，檢查 "WebGPU Status"

### Q2: 連接失敗 "Failed to connect"

**原因**: Backend 未啟動或 port 被佔用

**解決**:
```bash
# 檢查 Backend 是否運行
lsof -i :8765

# 如果沒有輸出，啟動 Backend
cd backend
uv run python server.py

# 如果 port 被佔用
kill -9 <PID>
```

### Q3: 畫面黑屏，無粒子顯示

**原因**: WebSocket 資料未接收或 WebGPU 渲染器錯誤

**診斷**:
```javascript
// 瀏覽器 Console
const store = window.testStore.getState();

// 檢查連線狀態
console.log('Connected:', store.isConnected);

// 檢查模擬狀態
console.log('State:', store.state);

// 檢查 FPS
console.log('FPS:', store.fps);

// 手動注入測試資料
const testState = {
  N: 1,
  step: 0,
  hasResources: false,
  hasObstacles: false,
  positions: new Float32Array([0, 0, 0]),
  velocities: new Float32Array([0, 0, 0]),
  types: new Uint8Array([0]),
  energies: new Float32Array([100]),
  targets: new Int32Array([-1]),
  groupLabels: new Int32Array([0]),
  stats: { meanSpeed: 0, stdSpeed: 0, Rg: 0, polarization: 0, nGroups: 0 },
  resources: [],
  groups: [],
};
store.setState(testState);

// 如果出現 1 個藍色粒子在中心 → WebGPU 正常，問題在 WebSocket
// 如果仍黑屏 → WebGPU 初始化失敗，檢查 Console 錯誤
```

### Q4: FPS 很低 (< 30)

**原因**: GPU 效能不足或渲染負荷過高

**優化**:
1. 減少粒子數量: N = 100 → 50
2. 關閉 Trails: 點擊 "✨ Trails" 按鈕
3. 關閉 Group Boundaries: 點擊 "🔮 Boundaries" 按鈕
4. 降低 DPR (Device Pixel Ratio):
   ```javascript
   // Console
   window.devicePixelRatio = 1;
   location.reload();
   ```

### Q5: Backend 報錯 "Import error"

**原因**: Python 模組路徑問題

**解決**:
```bash
cd backend
export PYTHONPATH=../src:../backend:$PYTHONPATH
uv run python server.py
```

或使用提供的啟動腳本（已處理路徑）:
```bash
./backend/start_server.sh
```

---

## 成功指標 ✅

**全部通過即為成功整合**:

- [ ] ✅ Backend 啟動無錯誤
- [ ] ✅ Frontend 啟動無錯誤
- [ ] ✅ WebGPU 初始化成功
- [ ] ✅ WebSocket 連接建立
- [ ] ✅ 畫面顯示 100 個移動粒子
- [ ] ✅ 粒子顏色正確（藍/綠/黃/紅）
- [ ] ✅ 相機控制順暢
- [ ] ✅ Frontend FPS ≥ 55
- [ ] ✅ Backend FPS ≈ 30
- [ ] ✅ 參數更新生效
- [ ] ✅ 無 Console 錯誤（除 LSP 類型警告）
- [ ] ✅ 運行 5 分鐘無崩潰

---

## 進階測試（可選）

### 1. 大規模測試

```bash
# 修改 backend/simulation_manager.py
# 或在前端調整 N = 500

# 檢查 FPS 是否維持 > 30 (Frontend), > 20 (Backend)
```

### 2. 網路延遲測試

```bash
# 使用 Chrome DevTools → Network → Throttling
# 模擬 3G 網路
# 檢查是否仍可流暢顯示（允許輕微延遲）
```

### 3. 多瀏覽器測試

- Chrome 113+
- Edge 113+
- 確認跨瀏覽器相容性

---

## 日誌與除錯

### Backend 日誌

```bash
# 如果使用 start_fullstack.sh
tail -f logs/backend.log

# 手動啟動時直接看 Terminal
```

### Frontend 日誌

```bash
# 如果使用 start_fullstack.sh
tail -f logs/frontend.log

# 或直接看瀏覽器 Console (F12)
```

### 詳細除錯

```bash
# Backend: 啟用 verbose logging
cd backend
DEBUG=1 uv run python server.py

# Frontend: 查看網路流量
# Chrome DevTools → Network → WS (WebSocket)
# 檢查 Binary frames (應看到每秒 ~30 個 3.8 KB 的 frames)
```

---

## 停止服務

### 使用 start_fullstack.sh 啟動的

```bash
# 按 Ctrl+C (優雅停止)

# 或強制終止
pkill -f 'python server.py'
pkill -f 'vite'
```

### 分別啟動的

```bash
# Terminal 1 (Backend): Ctrl+C
# Terminal 2 (Frontend): Ctrl+C
```

---

## 完成後檢查清單

✅ 所有測試通過  
✅ 無 Console 錯誤（除預期的 LSP 類型警告）  
✅ FPS 達標  
✅ 記憶體穩定  
✅ 可正常互動  

**恭喜！前端整合成功！🎉**

下一步：
- 效能優化（Phase 7）
- 更新 README.md（Phase 8）
- 部署指南（Phase 8）

---

**最後更新**: 2026-02-07  
**預計測試時間**: 5-10 分鐘
