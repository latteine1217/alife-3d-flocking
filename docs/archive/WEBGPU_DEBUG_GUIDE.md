# WebGPU 初始化問題診斷指南

## 問題症狀

前端顯示「⏳ Initializing WebGPU...」但一直卡住。

---

## 診斷步驟

### Step 1: 檢查瀏覽器支援

**打開瀏覽器 Console (F12)**，查看是否有錯誤訊息：

```javascript
// 快速檢查
console.log('WebGPU supported:', !!navigator.gpu);
```

**預期結果**：
- Chrome 113+: `true`
- Edge 113+: `true`
- 其他瀏覽器: `false`

**如果為 false**：
- 升級瀏覽器到最新版本
- Chrome: `chrome://flags` 啟用 `#enable-unsafe-webgpu`

---

### Step 2: 使用診斷工具

我已經創建了一個獨立的 WebGPU 測試頁面：

```bash
# 在 frontend 目錄下
cd frontend
open webgpu-test.html
# 或使用瀏覽器直接打開 file:///path/to/frontend/webgpu-test.html
```

**這個頁面會**：
1. 檢查 WebGPU 支援
2. 請求 GPU adapter
3. 創建 device
4. 渲染一個紅色三角形

**如果三角形顯示**：WebGPU 正常工作  
**如果卡住或錯誤**：瀏覽器或 GPU 驅動問題

---

### Step 3: 檢查 Console 日誌

在主應用中，打開 Console (F12)，應該看到以下日誌：

```
📐 Canvas size: 800x600, DPR: 2
🚀 Initializing WebGPU renderer...
🔍 Requesting GPU adapter...
✅ GPU adapter obtained
🔍 Requesting GPU device...
✅ GPU device obtained
🔍 Getting WebGPU canvas context...
✅ Canvas context obtained
🎨 Canvas format: bgra8unorm
🔍 Creating shader module...
✅ Shader module created
🔍 Creating pipeline layout...
✅ Canvas3D initialized
✅ Test particles created
```

**如果卡在某一步**：記下是哪一步，並查看具體錯誤訊息。

---

## 常見問題與解決方案

### 問題 1: Canvas size 為 0x0

**錯誤訊息**：
```
📐 Canvas size: 0x0, DPR: 2
```

**原因**：Canvas 在初始化時 DOM 尚未完全渲染

**已修復**：代碼中已添加 100ms 延遲和預設尺寸 (800x600)

---

### 問題 2: GPU adapter 請求失敗

**錯誤訊息**：
```
❌ Failed to get GPU adapter
```

**可能原因**：
1. GPU 驅動過舊
2. WebGPU 被禁用
3. 虛擬機/遠端桌面環境

**解決方案**：
1. 更新 GPU 驅動
2. Chrome flags: `chrome://flags/#enable-unsafe-webgpu` 設為 Enabled
3. 在本機測試（非虛擬機）

---

### 問題 3: Shader 編譯錯誤

**錯誤訊息**：
```
GPUValidationError: ...
```

**可能原因**：WGSL 語法錯誤

**檢查方式**：
```javascript
// 在 Console 中
const shader = `/* 貼上 WGSL 代碼 */`;
const module = device.createShaderModule({ code: shader });
await module.compilationInfo(); // 查看編譯錯誤
```

---

### 問題 4: 渲染時沒有 buffer

**錯誤訊息**：
```
Cannot read properties of undefined (reading 'setVertexBuffer')
```

**原因**：在有粒子資料前就嘗試渲染

**已修復**：代碼中添加了測試粒子 (4個點)，初始化後立即可見

---

## 修復內容 (本次更新)

### 1. 添加 DOM 渲染延遲

```typescript
// 等待 DOM 完全渲染
await new Promise((resolve) => setTimeout(resolve, 100));
```

### 2. 添加預設 Canvas 尺寸

```typescript
const width = canvas.clientWidth || 800;
const height = canvas.clientHeight || 600;
```

### 3. 添加測試粒子

```typescript
// 創建 4 個測試粒子（在原點附近）
const testParticles = {
  positions: new Float32Array([
    0, 0, 0,      // 中心點（藍色）
    10, 0, 0,     // X軸（橙色）
    0, 10, 0,     // Y軸（紅色）
    0, 0, 10,     // Z軸（藍色）
  ]),
  types: new Uint8Array([0, 1, 2, 0]),
};
renderer.updateParticles(testParticles);
```

### 4. 添加詳細日誌

每個初始化步驟都會輸出日誌，方便調試。

### 5. 修復渲染循環邏輯

確保即使沒有模擬資料，也會渲染測試粒子。

---

## 預期行為

### 初始化成功後

1. **Canvas 中央區域**：黑色背景
2. **測試粒子**：4 個彩色點（連線前可見）
3. **左下角提示**：
   - 🖱️ Left drag: Rotate
   - 🖱️ Right drag: Pan
   - 🖱️ Scroll: Zoom
4. **左上角信息**：
   - Particles: 4 (測試粒子)
   - Step: 0

### 連線並 Start 後

- 粒子數量變為 N (預設 100)
- 粒子開始運動
- Statistics 面板更新

---

## 如何測試修復

### 快速測試

```bash
# 1. 重新構建前端
cd frontend
npm run build

# 2. 啟動 dev server
npm run dev

# 3. 打開瀏覽器
open http://localhost:5173

# 4. 打開 Console (F12)，查看日誌

# 5. 點擊 Connect → Start
```

### 完整測試

```bash
# 使用測試腳本（會自動啟動 backend + frontend）
./test_webgpu.sh
```

---

## 如果仍然卡住

### 收集診斷信息

1. **瀏覽器版本**：
   ```
   chrome://version
   ```

2. **GPU 信息**：
   ```
   chrome://gpu
   ```

3. **Console 完整日誌**：
   - 打開 Console (F12)
   - 右鍵 → Save as... → 保存 log

4. **測試頁面結果**：
   - 打開 `frontend/webgpu-test.html`
   - 截圖或複製日誌

### 替代方案

如果 WebGPU 無法工作，可以暫時：

1. **使用 2D Canvas**：
   - 簡單的 2D 投影
   - 無需 WebGPU

2. **使用 Three.js**：
   - 自動降級到 WebGL
   - 兼容性更好

3. **只使用 Statistics 面板**：
   - 純數據展示
   - 無視覺化

---

## 技術細節

### WebGPU 初始化流程

```
1. navigator.gpu.requestAdapter()      // 獲取 GPU adapter
2. adapter.requestDevice()             // 獲取 GPU device
3. canvas.getContext('webgpu')         // 獲取 canvas context
4. context.configure({ device, ... })  // 配置 canvas
5. createShaderModule()                // 編譯 shader
6. createRenderPipeline()              // 創建渲染管線
7. createBuffer()                      // 創建 GPU buffers
8. render loop                         // 開始渲染
```

**任何一步失敗都會卡住。**

### 關鍵 API

```typescript
// 檢查支援
if (!navigator.gpu) { /* 不支援 */ }

// 請求 adapter
const adapter = await navigator.gpu.requestAdapter();

// 請求 device
const device = await adapter.requestDevice();

// 獲取 context
const context = canvas.getContext('webgpu');

// 配置 canvas
context.configure({
  device,
  format: navigator.gpu.getPreferredCanvasFormat(),
  alphaMode: 'premultiplied',
});
```

---

## 參考資料

- [WebGPU Specification](https://gpuweb.github.io/gpuweb/)
- [Chrome WebGPU Status](https://chromestatus.com/feature/6213121689518080)
- [WebGPU Samples](https://webgpu.github.io/webgpu-samples/)
- [Can I Use WebGPU](https://caniuse.com/webgpu)

---

**Last Updated**: 2026-02-06  
**Status**: 已添加診斷工具和測試粒子
