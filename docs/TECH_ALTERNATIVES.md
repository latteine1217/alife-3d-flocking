# 技術方案比較：Dashboard 替代方案

**日期**: 2026-02-06  
**情境**: 效能優化 + 公開發布

---

## 目標與限制

### 需求
1. **效能**: N=500 時 FPS > 30
2. **跨平台**: Windows/macOS/Linux
3. **易分享**: 適合公開發布
4. **維護性**: 長期可維護

### 現狀
- Streamlit: N=100 時 35 FPS（可接受）
- Streamlit: N=500 時 <15 FPS（不可接受）
- Taichi GGUI: N=1000 時 60+ FPS（優秀，但需要本地安裝）

---

## 方案對比

### 1. Taichi GGUI (Native) ⭐ 推薦

**技術棧**: Python + Taichi + GGUI (OpenGL/Metal/Vulkan)

**優點**:
- ✅ 效能最佳 (60+ FPS @ N=1000)
- ✅ 已實作完成 (`experiments/demo_*.py`)
- ✅ 跨平台 (macOS/Linux/Windows)
- ✅ 零額外開發時間
- ✅ 直接 GPU 渲染（無 Python → WebGL 開銷）

**缺點**:
- ❌ 需要本地安裝 Python + Taichi
- ❌ 無法用瀏覽器直接存取
- ❌ 分享需要打包（PyInstaller/Nuitka）

**適用情境**:
- 科學計算工具
- 本地實驗與研究
- 論文配圖與影片製作
- 需要最高效能的情境

**打包方式**:
```bash
# 使用 PyInstaller 打包成單一執行檔
uv run pyinstaller --onefile experiments/demo_heterogeneous.py
# 產生 dist/demo_heterogeneous（~50 MB）
```

**實際效能** (Apple M1 Pro):
```
N=100:  120 FPS
N=500:  60 FPS
N=1000: 40 FPS
N=2000: 20 FPS
```

---

### 2. Streamlit (現有) ✅ 保留作為輔助

**技術棧**: Python + Streamlit + Plotly

**優點**:
- ✅ 已完成實作
- ✅ 易於部署（Streamlit Cloud）
- ✅ 非技術人員友善
- ✅ 參數調整直觀

**缺點**:
- ❌ 效能受限 (FPS ~35 @ N=100)
- ❌ 無法處理大規模模擬 (N>200)
- ❌ Plotly 渲染開銷大

**適用情境**:
- 線上 Demo（GitHub Pages）
- 非技術人員快速試用
- 參數探索與調整
- 論文補充材料

**保留理由**:
- 無需重寫，作為「輕量級入口」
- 用於教學與展示
- 用於參數配置匯出（未來可整合到 GGUI）

---

### 3. React + TypeScript + WebGPU 🚀 高效能 Web

**技術棧**: React + TypeScript + WebGPU + WebSocket

**架構**:
```
┌─────────────────────────────────────┐
│  Frontend (Browser)                 │
│  ┌─────────────────────────────┐   │
│  │ React UI (TypeScript)       │   │
│  │  - 參數控制                  │   │
│  │  - 統計顯示                  │   │
│  └─────────────┬───────────────┘   │
│                ↓                    │
│  ┌─────────────────────────────┐   │
│  │ WebGPU Renderer             │   │
│  │  - GPU 粒子系統              │   │
│  │  - 60 FPS @ N=500           │   │
│  └─────────────┬───────────────┘   │
└────────────────┼───────────────────┘
                 ↓ WebSocket (Binary)
┌────────────────┼───────────────────┐
│  Backend (Python)                  │
│  ┌─────────────┴───────────────┐   │
│  │ Taichi Physics Engine        │   │
│  │  - 計算位置/速度              │   │
│  │  - 每幀傳輸 Float32Array     │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**優點**:
- ✅ 高效能 (50+ FPS @ N=500)
- ✅ 瀏覽器直接存取
- ✅ 跨平台（任何現代瀏覽器）
- ✅ 易於分享（URL）
- ✅ 現代開發體驗（熱重載、型別安全）

**缺點**:
- ❌ 需要 2-3 週開發
- ❌ 需要學習 WebGPU API
- ❌ 瀏覽器相容性（Chrome 113+, Safari 18+）

**開發時間估計**:
- Week 1: WebSocket 通訊 + 資料序列化
- Week 2: WebGPU 粒子渲染系統
- Week 3: React UI + 整合測試

**技術細節**:

```typescript
// types.ts
interface SimulationState {
  positions: Float32Array;   // N * 3
  velocities: Float32Array;  // N * 3
  types: Uint8Array;         // N
  energies: Float32Array;    // N
  resources: ResourceData[];
}

// webgpu-renderer.ts
class ParticleRenderer {
  private device: GPUDevice;
  private pipeline: GPURenderPipeline;
  private positionBuffer: GPUBuffer;
  
  async init() {
    const adapter = await navigator.gpu.requestAdapter();
    this.device = await adapter.requestDevice();
    
    // 建立 Render Pipeline
    this.pipeline = this.device.createRenderPipeline({
      vertex: {
        module: this.device.createShaderModule({
          code: vertexShaderCode  // WGSL
        }),
        entryPoint: "vs_main",
      },
      fragment: {
        module: this.device.createShaderModule({
          code: fragmentShaderCode
        }),
        entryPoint: "fs_main",
      },
      // ... 更多配置
    });
  }
  
  updatePositions(data: Float32Array) {
    this.device.queue.writeBuffer(
      this.positionBuffer,
      0,
      data.buffer
    );
  }
  
  render(viewMatrix: mat4) {
    // GPU 渲染粒子
  }
}

// websocket-client.ts
class SimulationClient {
  private ws: WebSocket;
  
  connect(url: string) {
    this.ws = new WebSocket(url);
    this.ws.binaryType = "arraybuffer";
    
    this.ws.onmessage = (event) => {
      const buffer = event.data as ArrayBuffer;
      const state = this.deserialize(buffer);
      this.onUpdate(state);
    };
  }
  
  private deserialize(buffer: ArrayBuffer): SimulationState {
    // 解析二進位資料
    const view = new DataView(buffer);
    const N = view.getUint32(0);
    const positions = new Float32Array(buffer, 4, N * 3);
    // ...
    return { positions, velocities, types, energies };
  }
}

// App.tsx
function App() {
  const [params, setParams] = useState<SimParams>(defaultParams);
  const rendererRef = useRef<ParticleRenderer>();
  
  useEffect(() => {
    const renderer = new ParticleRenderer();
    renderer.init().then(() => {
      rendererRef.current = renderer;
      
      const client = new SimulationClient();
      client.connect("ws://localhost:8765");
      client.onUpdate = (state) => {
        renderer.updatePositions(state.positions);
        renderer.render(viewMatrix);
      };
    });
  }, []);
  
  return (
    <div className="app">
      <Sidebar params={params} onChange={setParams} />
      <canvas ref={canvasRef} />
      <Statistics data={currentState} />
    </div>
  );
}
```

**資料傳輸優化**:
```python
# backend/websocket_server.py
import asyncio
import websockets
import struct

class SimulationServer:
    async def handle_client(self, websocket):
        while True:
            # 執行一幀模擬
            self.system.step(0.05)
            
            # 序列化資料（高效二進位格式）
            x_np = self.system.x.to_numpy()  # (N, 3)
            v_np = self.system.v.to_numpy()
            
            # 打包: [N (4 bytes)] + [positions (N*3*4)] + [velocities (N*3*4)]
            data = struct.pack('I', self.N) + x_np.tobytes() + v_np.tobytes()
            
            await websocket.send(data)
            await asyncio.sleep(0.016)  # ~60 FPS
```

**預期效能**:
```
N=100:  60 FPS
N=500:  50 FPS
N=1000: 30 FPS
```

---

### 4. Swift + Metal ❌ 不推薦

**技術棧**: Swift + SwiftUI + Metal

**優點**:
- ✅ 效能最佳 (70+ FPS @ N=1000)
- ✅ macOS 原生整合
- ✅ Metal API 功能強大

**缺點**:
- ❌ **只支援 macOS**（失去 80% 使用者）
- ❌ 需要學習 Swift + Metal（學習曲線陡峭）
- ❌ Python ↔ Swift 橋接複雜
- ❌ 需要 Apple Developer Account ($99/年)
- ❌ 需要公證（Notarization）流程
- ❌ 難以維護（兩套語言）

**唯一適用情境**:
- 你已經是 Swift/Metal 專家
- 專案**只針對** macOS
- 需要深度整合 macOS 系統功能

**不推薦理由**:
> 投資報酬率過低。開發 4-6 週，卻只能服務 macOS 使用者。
> Taichi GGUI 已經提供接近的效能，且跨平台。

---

### 5. Electron + React + WebGL

**技術棧**: Electron + React + Three.js

**優點**:
- ✅ 桌面應用外觀
- ✅ 跨平台（打包後）
- ✅ 熟悉的 Web 技術

**缺點**:
- ❌ Electron 打包體積大（~150 MB）
- ❌ 效能不如 WebGPU
- ❌ 記憶體佔用高
- ❌ 使用者安裝門檻

**結論**: 
> 不如直接用 WebGPU（效能更好）或 GGUI（體積更小）

---

## 推薦策略：混合方案

### Phase 1: 現在立即可用 ✅

**主力工具**: Taichi GGUI
```bash
# 高效能本地實驗
uv run python experiments/demo_heterogeneous.py
```

**輔助工具**: Streamlit
```bash
# 輕量級線上展示
./run_dashboard.sh
```

**優點**:
- 零額外開發
- 滿足 90% 使用情境
- 效能與易用性兼顧

---

### Phase 2: 如果需要高效能 Web (2-3 週後)

**實作**: React + TypeScript + WebGPU

**觸發條件**:
- Streamlit 效能真的不夠用
- 需要大量線上分享
- 想學習 WebGPU 技術

**開發里程碑**:
```
Week 1: 
  - [ ] WebSocket 通訊建立
  - [ ] 二進位資料序列化
  - [ ] 基本 WebGPU 渲染

Week 2:
  - [ ] GPU 粒子系統
  - [ ] 相機控制（OrbitControls）
  - [ ] 資源/障礙物渲染

Week 3:
  - [ ] React UI 整合
  - [ ] 參數控制面板
  - [ ] 統計資訊顯示
  - [ ] 效能優化
```

---

## 決策流程圖

```
開始
  │
  ├─ 只有自己/實驗室使用？
  │   └─ YES → Taichi GGUI ⭐ (已完成)
  │
  ├─ 需要線上展示給非技術人員？
  │   └─ YES → Streamlit ✅ (已完成)
  │
  ├─ N > 200 且需要高 FPS？
  │   └─ YES → 考慮 WebGPU 🚀 (2-3 週開發)
  │
  └─ 只在 macOS 使用且你會 Swift？
      └─ YES → 考慮 Swift + Metal
      └─ NO  → 不要選 Swift
```

---

## 技術選型檢查清單

在選擇新技術前，問自己：

### 效能需求
- [ ] Streamlit (35 FPS @ N=100) 真的不夠用嗎？
- [ ] 需要支援 N > 500 的模擬嗎？
- [ ] 目標使用者真的在乎 FPS 嗎？

### 開發成本
- [ ] 願意投入 2-4 週開發時間嗎？
- [ ] 需要學習新技術嗎（WebGPU/Swift）？
- [ ] 團隊有前端開發經驗嗎？

### 使用情境
- [ ] 主要使用者在哪個平台？(macOS/Windows/Linux/Web)
- [ ] 需要頻繁分享給他人嗎？
- [ ] 使用者願意安裝軟體嗎？

### 長期維護
- [ ] 誰來維護前端程式碼？
- [ ] 會有新功能需求嗎？
- [ ] 依賴的技術穩定嗎？（WebGPU 仍在發展中）

---

## 總結建議

### 立即行動（0 成本）
1. ✅ **手動測試 Streamlit Dashboard**
2. ✅ **確認實際效能是否滿足需求**
3. ✅ **使用 Taichi GGUI 製作論文圖表**

### 如果 Streamlit 不夠用（2-3 週投資）
1. 🚀 **選擇 React + TypeScript + WebGPU**
2. 📊 **預期效能提升 2-3 倍**
3. 🌐 **獲得跨平台高效能 Web 應用**

### 不建議（除非特殊情況）
1. ❌ Swift + Metal（平台限制太大）
2. ❌ Electron（效能無優勢）
3. ❌ Unity/Unreal（開發成本過高）

---

## 參考資源

### WebGPU 學習
- [WebGPU Fundamentals](https://webgpufundamentals.org/)
- [WebGPU Samples](https://webgpu.github.io/webgpu-samples/)
- [Learn WGSL](https://google.github.io/tour-of-wgsl/)

### React + WebGPU 範例
- [react-webgpu](https://github.com/visgl/react-webgpu)
- [WebGPU Particles](https://github.com/gnikoloff/webgpu-particles)

### Taichi GGUI 文件
- [GGUI System](https://docs.taichi-lang.org/docs/ggui)
- [Particle System Example](https://github.com/taichi-dev/taichi/blob/master/python/taichi/examples/simulation/sph_gpu.py)

---

**最後更新**: 2026-02-06  
**建議有效期**: 6 個月（WebGPU 技術快速發展中）
