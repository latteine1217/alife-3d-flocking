# Flocking Simulation Frontend

React + TypeScript + WebSocket 前端，連線至 Python backend 接收即時模擬資料。

## 功能

- ✅ WebSocket 即時通訊（30-60 FPS）
- ✅ 二進制資料反序列化
- ✅ Zustand 全域狀態管理
- ✅ 控制面板（Start/Pause/Reset）
- ✅ 即時統計顯示（FPS, Polarization, Rg 等）
- ✅ Agent 類型分布視覺化
- ✅ Debug Console

## 快速開始

### 1. 啟動 Backend

```bash
# 在專案根目錄
cd ../backend
./start_server.sh
```

伺服器會在 `ws://localhost:8765` 啟動。

### 2. 啟動 Frontend

```bash
# 在 frontend 目錄
npm run dev
```

瀏覽器開啟 `http://localhost:5173`

### 3. 連線與測試

1. 點擊 **「Connect」** 按鈕
2. 連線成功後，點擊 **「Start」** 啟動模擬
3. 觀察統計資料即時更新
4. 檢查瀏覽器 Console，查看每幀詳細資料

## 架構

```
frontend/
├── src/
│   ├── components/
│   │   ├── ControlPanel.tsx    # 控制按鈕
│   │   └── Statistics.tsx      # 統計顯示
│   ├── lib/
│   │   ├── websocket-client.ts # WebSocket 客戶端
│   │   └── deserializer.ts     # 二進制反序列化
│   ├── store/
│   │   └── simulation-store.ts # Zustand 狀態管理
│   ├── types/
│   │   └── simulation.ts       # TypeScript 型別定義
│   └── App.tsx                 # 主應用元件
├── package.json
└── vite.config.ts
```

## 資料流

```
Backend (Python)
   │
   │ Binary Data (30 FPS)
   │ - Header (20B)
   │ - Agents (N*33B)
   │ - Stats (64B)
   ▼
WebSocket Client (websocket-client.ts)
   │
   │ ArrayBuffer
   ▼
Binary Deserializer (deserializer.ts)
   │
   │ SimulationState
   ▼
Zustand Store (simulation-store.ts)
   │
   │ React State
   ▼
UI Components
   - ControlPanel
   - Statistics
   - Debug Console
```

## 控制命令

Frontend 發送 JSON 命令至 Backend：

```typescript
// 啟動模擬
{ type: 'start' }

// 暫停模擬
{ type: 'pause' }

// 重置模擬
{ type: 'reset' }

// 更新參數
{
  type: 'update_params',
  payload: {
    systemType: 'Heterogeneous',
    N: 100,
    Ca: 1.5,
    ...
  }
}
```

## Debug

### 查看每幀資料

打開瀏覽器 Console（F12），會看到：

```
Frame 1: N=100, Polarization=0.052
Frame 2: N=100, Polarization=0.053
...
```

### 查看 WebSocket 統計

```typescript
const { ws } = useSimulationStore();
const stats = ws?.getStats();

console.log(stats);
// {
//   framesReceived: 300,
//   bytesReceived: 1015200,
//   fps: 29.8,
//   avgFrameSize: 3384
// }
```

## 已知問題

1. **連線失敗**：確認 backend 已啟動（`ws://localhost:8765`）
2. **No data received**：點擊「Start」按鈕啟動模擬
3. **FPS 不穩定**：正常現象，受網路延遲影響

## 下一步（Week 3）

- [ ] WebGPU 渲染器（粒子系統）
- [ ] 3D 相機控制（orbit, zoom, pan）
- [ ] 參數調整面板（滑桿、輸入框）
- [ ] 資源與障礙物視覺化

## 技術棧

- **React 19** - UI 框架
- **TypeScript** - 型別安全
- **Zustand** - 狀態管理
- **Vite** - 建構工具
- **WebSocket** - 即時通訊

## 效能指標

- **連線延遲**: <50ms
- **資料接收**: 30-60 FPS
- **反序列化**: <1ms/frame
- **UI 更新**: 60 FPS (React)

---

**Status**: ✅ Week 2 Frontend 基礎完成，可接收並顯示即時資料


```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
