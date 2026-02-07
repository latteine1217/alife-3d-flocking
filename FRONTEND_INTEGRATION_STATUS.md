# 前端整合狀態報告

**日期**: 2026-02-07  
**階段**: Phase 7 - WebGPU 視覺化 + WebSocket 即時通訊  
**狀態**: ✅ 架構完整，進入測試與整合階段

---

## 整體架構

```
┌─────────────────────────────────────────────────────────┐
│                     User Browser                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │           React Frontend (Vite)                  │  │
│  │  ┌─────────────┐   ┌──────────────┐   ┌──────┐  │  │
│  │  │  Zustand    │───│  WebSocket   │───│ WS   │  │  │
│  │  │  Store      │   │  Client      │   │ 8765 │  │  │
│  │  └──────┬──────┘   └──────────────┘   └──┬───┘  │  │
│  │         │                                  │      │  │
│  │         │ state                            │      │  │
│  │         ▼                                  │      │  │
│  │  ┌──────────────┐   ┌──────────────┐     │      │  │
│  │  │  Canvas3D    │───│  WebGPU      │     │      │  │
│  │  │  Component   │   │  Renderer    │     │      │  │
│  │  └──────────────┘   └──────────────┘     │      │  │
│  └──────────────────────────────────────────┼──────┘  │
└────────────────────────────────────────────┼─────────┘
                                             │
                                             │ Binary
                                             │ Protocol
                                             │
┌────────────────────────────────────────────┼─────────┐
│              Python Backend                 │         │
│  ┌─────────────────────────────────────────▼──────┐  │
│  │     WebSocket Server (asyncio)                 │  │
│  │  ┌──────────────┐   ┌──────────────────────┐  │  │
│  │  │ Simulation   │───│ Binary Serializer    │  │  │
│  │  │ Manager      │   │ (3-4 KB/frame)       │  │  │
│  │  └──────┬───────┘   └──────────────────────┘  │  │
│  └─────────┼─────────────────────────────────────┘  │
│            │                                         │
│            ▼                                         │
│  ┌─────────────────────────────────────────────┐    │
│  │  HeterogeneousFlocking3D (Taichi GPU)      │    │
│  │  - N=100 agents (Follower/Explorer/Leader) │    │
│  │  - Spatial Grid O(N) neighbor search       │    │
│  │  - Group Detection (Label Propagation)     │    │
│  │  - Resource System (foraging)              │    │
│  │  - Perception (FOV filtering)              │    │
│  │  - Navigation (goal-seeking)               │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 已完成功能 ✅

### Backend (Python + Taichi)

1. **✅ WebSocket 伺服器** (`backend/server.py`)
   - asyncio 非阻塞架構
   - 雙向通訊：JSON 命令 + 二進制狀態
   - 自動重連機制
   - 30 FPS 推送頻率

2. **✅ 模擬管理器** (`backend/simulation_manager.py`)
   - 完整的系統生命週期管理
   - 參數更新與系統重建
   - 預設配置（100 agents, 3 resources）
   - 支援 Heterogeneous / 3D / 2D 系統

3. **✅ 二進制序列化** (`backend/serializer.py`)
   - 高效協議：~3.8 KB/frame (N=100)
   - 包含：positions, velocities, types, energies, targets, group_labels
   - 統計數據：meanSpeed, Rg, polarization, nGroups
   - 資源數據：position, amount, radius, renewable
   - 群組數據：groupId, size, centroid, velocity, radius

4. **✅ 物理模擬核心** (`src/flocking_heterogeneous.py`)
   - Morse potential + Rayleigh friction + Alignment
   - Agent 類型系統（Explorer, Follower, Leader, Predator）
   - FOV 感知系統
   - 目標導向導航
   - 群組偵測（Label Propagation）
   - 覓食行為與能量管理

### Frontend (React + TypeScript + WebGPU)

1. **✅ WebSocket 客戶端** (`frontend/src/lib/websocket-client.ts`)
   - 自動重連（最多 5 次）
   - 事件回調系統（onState, onMessage, onConnect, onDisconnect）
   - FPS 統計（moving average）
   - 頻寬監控

2. **✅ 二進制反序列化** (`frontend/src/lib/deserializer.ts`)
   - 完整支援 Backend 協議
   - 資料驗證
   - 群組資料解析

3. **✅ WebGPU 渲染器** (`frontend/src/lib/webgpu-renderer.ts`)
   - Instanced rendering（粒子 = quad instances）
   - Depth buffer（正確深度排序）
   - 速度軌跡（Velocity trails, 40 frames）
   - 邊界框（Boundary box wireframe）
   - 資源球體（Resource spheres with transparency）
   - 群組邊界球體（Group boundary spheres）
   - 群組速度箭頭（Group velocity arrows）
   - 雙模式著色：
     - Type mode: FOLLOWER(blue), EXPLORER(green), LEADER(yellow), PREDATOR(red)
     - Group mode: Hash-based color per group
   - 選中群組高亮

4. **✅ 相機系統** (`frontend/src/lib/camera.ts`)
   - Orbit Camera（軌道相機）
   - 滑鼠拖曳旋轉 (LMB)
   - 滑鼠平移 (RMB)
   - 滾輪縮放
   - 重置功能

5. **✅ Zustand 狀態管理** (`frontend/src/store/simulation-store.ts`)
   - 全域狀態：SimulationState, params, isRunning, isConnected
   - Actions: connect, disconnect, toggleRunning, updateParams
   - 自動同步 WebSocket 狀態到 Store
   - FPS 與頻寬統計

6. **✅ React 組件**
   - `App.tsx`: 主應用入口，佈局管理
   - `Canvas3D.tsx`: WebGPU 渲染器整合，相機控制，渲染循環
   - `ControlPanel.tsx`: 啟動/暫停/重置控制
   - `ParamEditor.tsx`: 即時參數編輯
   - `Statistics.tsx`: 統計數據顯示
   - `GroupStatistics.tsx`: 群組統計與選擇

---

## 資料流 (Data Flow)

### 1. 初始化流程

```
User clicks "Connect"
    ↓
FlockingWebSocket.connect()
    ↓
WebSocket connected → onConnect callback
    ↓
Store.connect() → Send initial params (update_params)
    ↓
Backend: SimulationManager.create_system()
    ↓
Backend: HeterogeneousFlocking3D initialized (N=100)
    ↓
Backend: Start pushing states (30 FPS)
```

### 2. 即時渲染流程 (每幀)

```
Backend: system.step(dt=0.1)
    ↓
Backend: BinarySerializer.serialize_state()  [~3.8 KB]
    ↓
WebSocket: send(binary_data)
    ↓
Frontend: WebSocket.onmessage(event)
    ↓
Frontend: BinaryDeserializer.deserialize(buffer)
    ↓
Frontend: ws.onState(state) callback
    ↓
Frontend: Store.setState(state)
    ↓
Frontend: Canvas3D render loop (requestAnimationFrame)
    ↓
Frontend: renderer.updateParticles(positions, velocities, types, ...)
    ↓
Frontend: renderer.render(viewMatrix, projMatrix)
    ↓
WebGPU: Draw to canvas (60 FPS target)
```

### 3. 參數更新流程

```
User edits param in ParamEditor
    ↓
Store.updateParams({ beta: 2.0 })
    ↓
WebSocket: send({ type: 'update_params', payload: {...} })
    ↓
Backend: SimulationManager.update_params()
    ↓
Backend: system.create_system() (rebuild)
    ↓
Backend: Continue pushing new states
```

---

## 二進制協議規範

### Frame Structure

```
┌────────────────────────────────────────────────┐
│  Header (20 bytes)                             │
│  ┌──────────────┬──────────────┬───────────┐  │
│  │ N (uint32)   │ step (u32)   │ flags (2) │  │
│  │ 4 bytes      │ 4 bytes      │ 2 bytes   │  │
│  └──────────────┴──────────────┴───────────┘  │
│  │ reserved (10 bytes)                    │     │
│  └────────────────────────────────────────┘     │
├────────────────────────────────────────────────┤
│  Agent Data (N * 37 bytes)                     │
│  ┌──────────────────────────────────────────┐  │
│  │ positions (N * 12 bytes)                 │  │
│  │ velocities (N * 12 bytes)                │  │
│  │ types (N * 1 + padding)                  │  │
│  │ energies (N * 4 bytes)                   │  │
│  │ targets (N * 4 bytes)                    │  │
│  │ group_labels (N * 4 bytes)               │  │
│  └──────────────────────────────────────────┘  │
├────────────────────────────────────────────────┤
│  Statistics (64 bytes)                         │
│  ┌──────────────────────────────────────────┐  │
│  │ meanSpeed, stdSpeed, Rg, polarization    │  │
│  │ nGroups, reserved (28 bytes)             │  │
│  └──────────────────────────────────────────┘  │
├────────────────────────────────────────────────┤
│  Resources (optional, if hasResources=1)       │
│  ┌──────────────────────────────────────────┐  │
│  │ n_resources (uint32)                     │  │
│  │ [position(12), amount(4), radius(4),     │  │
│  │  is_renewable(1), padding(3)] × N        │  │
│  └──────────────────────────────────────────┘  │
├────────────────────────────────────────────────┤
│  Group Statistics (optional)                   │
│  ┌──────────────────────────────────────────┐  │
│  │ n_active_groups (uint32)                 │  │
│  │ [groupId(4), size(4), centroid(12),      │  │
│  │  velocity(12), radius(4)] × N            │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘

Total size (N=100): ~3864 bytes
```

---

## WebGPU Shader 管線

### Particle Rendering (Instanced Quads)

```wgsl
// Vertex Shader
@vertex
fn vs_main(
  @location(0) quad_pos: vec2f,           // Shared quad geometry
  @location(1) particle_pos: vec3f,       // Instanced: particle position
  @location(2) particle_type: u32,        // Instanced: agent type
  @location(3) group_label: u32,          // Instanced: group label (optional)
) -> VertexOutput {
  // Billboard transformation (quad always faces camera)
  // Apply view and projection matrices
}

// Fragment Shader
@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4f {
  // Type-based coloring:
  // - FOLLOWER: blue (0, 0, 1)
  // - EXPLORER: green (0, 1, 0)
  // - LEADER: yellow (1, 1, 0)
  // - PREDATOR: red (1, 0, 0)
  // OR Group-based coloring (hash-based)
}
```

### Resource Sphere Rendering (Instanced Icosphere)

```wgsl
@vertex
fn vs_main(
  @location(0) sphere_vertex: vec3f,      // Shared sphere geometry
  @location(1) sphere_normal: vec3f,
  @location(2) instance_pos: vec3f,       // Instanced: resource position
  @location(3) instance_scale: f32,       // Instanced: resource radius
  @location(4) instance_amount: f32,      // Instanced: resource amount
) -> VertexOutput

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4f {
  // Green (renewable) or Red (consumable)
  // Alpha = 0.3 (transparent)
  // Simple diffuse lighting (directional light)
}
```

---

## 檔案結構

```
alife/
├── backend/                              # Python Backend
│   ├── server.py                         # WebSocket 伺服器 (118 lines)
│   ├── simulation_manager.py             # 模擬管理器 (254 lines)
│   ├── serializer.py                     # 二進制序列化 (283 lines)
│   ├── requirements.txt                  # websockets, lz4
│   └── start_server.sh                   # 啟動腳本
│
├── frontend/                             # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── App.tsx                   # 主應用 (233 lines)
│   │   │   ├── Canvas3D.tsx              # WebGPU 渲染器整合 (598 lines)
│   │   │   ├── ControlPanel.tsx          # 控制面板
│   │   │   ├── ParamEditor.tsx           # 參數編輯器
│   │   │   ├── Statistics.tsx            # 統計顯示
│   │   │   └── GroupStatistics.tsx       # 群組統計
│   │   ├── lib/
│   │   │   ├── websocket-client.ts       # WebSocket 客戶端 (266 lines)
│   │   │   ├── deserializer.ts           # 二進制反序列化 (225 lines)
│   │   │   ├── webgpu-renderer.ts        # WebGPU 渲染器 (2800+ lines)
│   │   │   └── camera.ts                 # Orbit Camera
│   │   ├── store/
│   │   │   └── simulation-store.ts       # Zustand Store (239 lines)
│   │   └── types/
│   │       └── simulation.ts             # TypeScript 類型定義 (145 lines)
│   ├── package.json
│   └── vite.config.ts
│
└── start_fullstack.sh                    # 全棧啟動腳本 ✨ NEW
```

---

## 啟動方式

### 方式 1: 全棧一鍵啟動 (推薦)

```bash
# 同時啟動 Backend + Frontend
./start_fullstack.sh

# 輸出：
# 🔧 Backend:  ws://localhost:8765
# 🎨 Frontend: http://localhost:5173

# 停止：
# Ctrl+C 或 pkill -f 'python server.py' && pkill -f 'vite'
```

### 方式 2: 分別啟動

**Terminal 1 - Backend:**
```bash
cd backend
./start_server.sh
# 或
uv run python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# 訪問 http://localhost:5173
```

---

## 測試 Checklist

### ✅ Phase 1: Backend 獨立測試

- [x] SimulationManager 初始化 (N=100)
- [x] Serializer 二進制輸出 (~3.8 KB)
- [x] WebSocket 伺服器啟動（port 8765）

```bash
cd backend
uv run python -c "from simulation_manager import SimulationManager; m = SimulationManager(); print(f'N={m.system.N}')"
```

### 🔄 Phase 2: Frontend 獨立測試 (In Progress)

- [ ] WebGPU 初始化（瀏覽器 Console 無錯誤）
- [ ] 測試粒子渲染（手動注入模擬資料）
- [ ] 相機控制（滑鼠拖曳、滾輪縮放）
- [ ] UI 組件顯示正常

**測試方法:**
```javascript
// 瀏覽器 Console
const renderer = window.testRenderer;
const store = window.testStore;

// 注入測試資料
const testState = {
  N: 10,
  step: 0,
  positions: new Float32Array(30).fill(0),  // Random positions
  velocities: new Float32Array(30).fill(0),
  types: new Uint8Array(10).fill(0),
  // ... more fields
};

store.getState().setState(testState);
```

### 🔄 Phase 3: 全棧整合測試 (Next)

- [ ] Backend → WebSocket → Frontend 資料流
- [ ] 即時渲染（30-60 FPS）
- [ ] 參數更新（前端 → 後端）
- [ ] 控制命令（start/pause/reset）
- [ ] 群組偵測與可視化
- [ ] 資源顯示
- [ ] FPS 與頻寬監控

### 🔄 Phase 4: 效能與穩定性 (Pending)

- [ ] 長時間運行穩定性（10 分鐘無崩潰）
- [ ] FPS 達標（Frontend 60 FPS, Backend 30 FPS）
- [ ] 記憶體無洩漏（Chrome DevTools Memory profiler）
- [ ] 大規模測試（N=500, N=1000）

---

## 已知問題 & TODO

### 高優先級

1. **❗ Frontend 首次連線測試**
   - 需驗證 WebSocket 連線建立成功
   - 需驗證二進制資料正確解析
   - 需驗證 WebGPU 渲染器接收資料

2. **❗ 掠食者類型顯示**
   - Backend 已支援 PREDATOR (type=3)
   - Frontend deserializer 需確認 type=3 → RED 著色

3. **⚠️ WebGPU Shader 完整性**
   - 需檢查所有 shader code (particle, trail, resource, group)
   - 需確認是否完整（檔案被截斷在 1651 行）

### 中優先級

4. **⚙️ 動態 boxSize**
   - 目前 Canvas3D 寫死 `boxSize: 50.0`
   - 應從 `state.params.boxSize` 讀取

5. **🎨 UI/UX 改進**
   - 群組選擇互動（點擊粒子選中群組）
   - 參數預設值載入
   - 錯誤提示優化

6. **📊 更多統計資訊**
   - 每個群組的詳細統計
   - 能量分布直方圖
   - 速度分布圖

### 低優先級

7. **📝 文件完善**
   - API 文件更新
   - WebGPU Shader 註解
   - 前端組件使用說明

8. **🧪 單元測試**
   - Frontend: deserializer 測試
   - Frontend: renderer 測試（需 Mock WebGPU）

---

## 效能指標 (目標)

| 指標 | 目標 | 備註 |
|-----|-----|-----|
| **Backend FPS** | 30 FPS | WebSocket 推送頻率 |
| **Frontend FPS** | 60 FPS | WebGPU 渲染頻率 |
| **Frame Size** | ~4 KB | N=100, 含 resources + groups |
| **Bandwidth** | ~120 KB/s | 30 FPS × 4 KB |
| **Latency** | <50 ms | WebSocket 往返時間 |
| **Memory** | Stable | 無洩漏，10 分鐘運行 |

---

## 後續工作 (Phase 8+)

1. **部署優化**
   - Docker Compose 配置
   - Nginx 反向代理
   - HTTPS 支援

2. **功能擴展**
   - 即時障礙物編輯
   - 多系統切換（2D/3D/Heterogeneous）
   - 參數預設集（Presets）

3. **進階可視化**
   - 熱力圖（Heatmap）
   - 軌跡記錄與回放
   - 3D 群組凸包（Convex Hull）

4. **協作功能**
   - 多用戶同時觀看
   - 參數共享（URL 參數）

---

## 開發團隊註記

**本次整合重點**：
- ✅ Backend 已完全就緒，測試通過
- ✅ Frontend 架構完整，進入測試階段
- 🔄 下一步：啟動全棧系統，驗證 WebSocket + WebGPU 整合

**技術亮點**：
- 二進制協議高效（~4 KB/frame）
- WebGPU Instanced Rendering（高效能粒子渲染）
- Zustand + WebSocket 無縫整合
- 完整的 TypeScript 類型定義

**致謝**：
- Taichi team (GPU 加速框架)
- WebGPU community (現代圖形 API)
- React + Zustand ecosystem

---

**最後更新**: 2026-02-07  
**下次同步**: 測試完成後更新測試結果
