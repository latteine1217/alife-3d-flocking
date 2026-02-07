# WebGPU 粒子不顯示 Debug 檢查清單

## 1. 檢查後端
```bash
# 確認後端運行
ps aux | grep "python.*server" | grep -v grep

# 查看後端日誌（如果有 nohup）
tail -f backend/server.log

# 測試後端是否能創建系統
cd backend
python -c "from simulation_manager import SimulationManager; m = SimulationManager(); print(f'N={m.system.N}')"
```

預期輸出：
```
🚀 Creating default system on startup...
✅ Created Heterogeneous system with N=100
N=100
```

## 2. 檢查 WebSocket 連接
在瀏覽器 Console (F12) 執行：
```javascript
const ws = new WebSocket('ws://localhost:8765');
ws.binaryType = 'arraybuffer';
ws.onopen = () => console.log('✅ WS connected');
ws.onmessage = (e) => console.log('📦 Data:', e.data.byteLength || e.data);
ws.send(JSON.stringify({type: 'start'}));
```

預期：
- 看到 `✅ WS connected`
- 每 ~33ms 看到 `📦 Data: 3484`（或類似大小）

## 3. 檢查前端狀態
在 React DevTools 或 Console：
```javascript
// 查看 store 狀態
useSimulationStore.getState()
```

確認：
- `isConnected: true`
- `state.N > 0`
- `state.positions.length === N * 3`

## 4. 檢查 WebGPU 初始化
Console 應該看到：
```
🚀 Initializing WebGPU renderer...
✅ GPU adapter obtained
✅ GPU device obtained
✅ Canvas context obtained
✅ WebGPU initialized successfully
```

## 5. 檢查渲染迴圈
Console 應該看到（每秒 1-2 次）：
```
🔔 Canvas3D calling updateParticles: N=100, positions.length=300
🔄 updateParticles called: N=100, positions.length=300
🎨 Drawing 100 particles (6 vertices × 100 instances = 600 total)
```

如果看到：
```
⚠️ No particles to draw (particleCount = 0)
```
→ 表示 `updateParticles` 未被呼叫或資料為空

## 6. 強制測試資料
在 Console 執行（創建假資料）：
```javascript
const store = useSimulationStore.getState();
store.setState({
  N: 10,
  step: 0,
  positions: new Float32Array([
    0, 0, 0,
    5, 5, 5,
    -5, -5, -5,
    10, 0, 0,
    0, 10, 0,
    0, 0, 10,
    -10, 0, 0,
    0, -10, 0,
    0, 0, -10,
    5, -5, 0,
  ]),
  velocities: new Float32Array(30),
  types: new Uint8Array([0,1,2,0,1,2,0,1,2,0]),
  energies: new Float32Array(10).fill(100),
  targets: new Int32Array(10).fill(-1),
  stats: { meanSpeed: 1.0, stdSpeed: 0.1, Rg: 10, polarization: 0.5, nGroups: 1 },
  resources: [],
  hasResources: false,
  hasObstacles: false,
});
```

應該立即看到 10 個粒子！

## 7. WebGPU 特定問題

### 檢查瀏覽器支援
```javascript
console.log('WebGPU supported:', !!navigator.gpu);
```

### 檢查 Canvas 大小
```javascript
const canvas = document.querySelector('canvas');
console.log(`Canvas: ${canvas.width}x${canvas.height}`);
console.log(`Client: ${canvas.clientWidth}x${canvas.clientHeight}`);
```

### 檢查 Shader 編譯
如果 shader 編譯失敗，Console 會有紅色錯誤。

## 常見原因 & 解決方案

| 症狀 | 原因 | 解決方案 |
|------|------|----------|
| "WebSocket not connected" | 後端未啟動 | `cd backend && uv run python server.py` |
| particleCount = 0 | 系統未初始化 | 點擊 "Init" 或重啟後端（已修復） |
| Canvas 黑屏 + 有粒子數 | Shader/Camera 問題 | 檢查 Console 錯誤 |
| 粒子位置全是 (0,0,0) | 模擬未執行 | 點擊 "Start" |
| FPS = 0 | WebSocket 未收到資料 | 檢查後端日誌 |

