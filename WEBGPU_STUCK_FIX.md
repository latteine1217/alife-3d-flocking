# WebGPU 初始化卡住 - 快速修復指南

## 問題

前端顯示「⏳ Initializing WebGPU...」一直不消失，但 Console 日誌顯示初始化已完成。

---

## 根本原因

這是 **React 狀態更新** 的問題，不是 WebGPU 的問題。可能原因：

1. **瀏覽器緩存**：舊的 JavaScript 被緩存
2. **React StrictMode**：開發模式下會執行兩次 useEffect，導致狀態混亂
3. **狀態更新延遲**：`setIsInitializing(false)` 沒有觸發重新渲染

---

## 立即解決方案

### 方法 1: 硬性刷新（最快）

```
1. 打開瀏覽器 (http://localhost:5173)
2. 按 Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows/Linux)
3. 這會清除緩存並重新載入
```

### 方法 2: 清除瀏覽器緩存

```
1. 打開 DevTools (F12)
2. 右鍵點擊刷新按鈕
3. 選擇「清空緩存並硬性重新載入」
```

### 方法 3: 使用隱私模式

```
1. 打開無痕/隱私視窗 (Cmd+Shift+N)
2. 訪問 http://localhost:5173
3. 這樣不會有任何緩存
```

### 方法 4: 重新啟動 dev server

```bash
# 停止當前的 dev server (Ctrl+C)
cd frontend
rm -rf node_modules/.vite  # 清除 Vite 緩存
npm run dev
```

---

## 已實施的修復

### 1. 移除 React StrictMode

**檔案**: `frontend/src/main.tsx`

```typescript
// 之前（會導致雙重初始化）
<StrictMode>
  <App />
</StrictMode>

// 現在（單次初始化）
<App />
```

### 2. 添加狀態監聽日誌

**檔案**: `frontend/src/components/Canvas3D.tsx`

```typescript
useEffect(() => {
  console.log('🔔 isInitializing changed to:', isInitializing);
}, [isInitializing]);
```

**預期 Console 輸出**：
```
🚀 useEffect triggered
... (初始化步驟)
✅ Canvas3D initialized
🔔 isInitializing changed to: false  ← 這一行很關鍵！
```

**如果沒有這一行**：狀態沒更新，需要硬性刷新。

### 3. 添加「刷新頁面」按鈕

**如果卡住**，現在可以直接點擊「🔄 Refresh Page」按鈕。

---

## 診斷步驟

### Step 1: 檢查 Console 日誌

打開 Console (F12)，查找以下關鍵日誌：

```
✅ Canvas3D initialized           ← 初始化完成
🔔 isInitializing changed to: false  ← 狀態更新
```

**Case A**: 兩行都有 → 硬性刷新即可解決  
**Case B**: 只有第一行 → React 狀態更新失敗，繼續下一步  
**Case C**: 都沒有 → WebGPU 初始化失敗，查看錯誤訊息

### Step 2: 檢查 React 渲染

在 Console 中輸入：

```javascript
// 檢查組件狀態
console.log('Current state:', {
  isInitializing: document.querySelector('h3')?.textContent,
  canvasExists: !!document.querySelector('canvas'),
});
```

**預期結果**：
```javascript
{
  isInitializing: "⏳ Initializing WebGPU...",
  canvasExists: false
}
```

**如果 canvasExists 為 true**：Canvas 已經渲染，只是被遮擋了。

### Step 3: 強制狀態重置

在 Console 中輸入：

```javascript
// 嘗試強制重新渲染
window.location.reload();
```

---

## 測試新版本

```bash
# 1. 確保已重新構建
cd frontend
npm run build

# 2. 啟動 dev server
npm run dev

# 3. 打開隱私模式視窗
# Chrome: Cmd+Shift+N (Mac) / Ctrl+Shift+N (Win)
# 訪問 http://localhost:5173

# 4. 打開 Console (F12)，查看日誌

# 5. 應該會看到：
# ✅ Canvas3D initialized
# 🔔 isInitializing changed to: false
# 🎨 Rendering, isInitializing = false

# 6. UI 應該從「⏳ Initializing」變成黑色 Canvas
```

---

## 預期行為時間線

| 時間 | 狀態 | Console 日誌 |
|------|------|-------------|
| 0s   | ⏳ Initializing WebGPU... | 🚀 useEffect triggered |
| 0.1s | ⏳ Initializing WebGPU... | 📐 Canvas size: 800x600 |
| 0.2s | ⏳ Initializing WebGPU... | 🔍 Requesting GPU adapter... |
| 0.3s | ⏳ Initializing WebGPU... | ✅ GPU adapter obtained |
| 0.5s | ⏳ Initializing WebGPU... | ✅ GPU device obtained |
| 0.7s | ⏳ Initializing WebGPU... | ✅ Shader module created |
| 1.0s | ⏳ Initializing WebGPU... | ✅ Canvas3D initialized |
| 1.0s | ⏳ Initializing WebGPU... | 🔄 Setting isInitializing to false |
| **1.0s** | **✅ 黑色 Canvas 出現** | **🔔 isInitializing changed to: false** |
| 1.0s | ✅ Canvas 渲染 | ✅ Test particles created |
| 1.0s+ | ✅ 60 FPS 渲染 | (渲染循環) |

**如果卡在 1.0s 後仍顯示「⏳」**：硬性刷新（Cmd+Shift+R）

---

## 如果問題仍然存在

### 方案 A: 使用簡化版組件

我已經創建了 `Canvas3DSimple.tsx` 用於測試：

```bash
# 在 App.tsx 中臨時替換
import { Canvas3DSimple } from './components/Canvas3DSimple';
// 使用 <Canvas3DSimple /> 代替 <Canvas3D />
```

這會逐步顯示初始化進度，更容易調試。

### 方案 B: 完全重新安裝

```bash
cd frontend
rm -rf node_modules dist
npm install
npm run build
npm run dev
```

### 方案 C: 檢查瀏覽器版本

```bash
# 在 Console 中執行
console.log('Chrome version:', /Chrome\/(\d+)/.exec(navigator.userAgent)?.[1]);
```

**需要**: Chrome 113+

如果版本過舊，升級瀏覽器。

---

## 檢查清單

- [ ] 硬性刷新瀏覽器 (Cmd+Shift+R)
- [ ] Console 顯示「🔔 isInitializing changed to: false」
- [ ] 沒有紅色錯誤訊息
- [ ] 使用隱私模式測試
- [ ] 清除 Vite 緩存 (`rm -rf node_modules/.vite`)
- [ ] 重新構建 (`npm run build`)
- [ ] Chrome 版本 >= 113

---

## 成功標誌

✅ **UI 變化**: 「⏳ Initializing WebGPU...」→ 黑色 Canvas  
✅ **Console**: 顯示「🔔 isInitializing changed to: false」  
✅ **Canvas**: 左下角顯示操作提示  
✅ **Canvas**: 左上角顯示「Particles: 4」  
✅ **相機**: 可以拖曳、滾輪縮放  

---

## 聯繫信息

如果以上方法都無效，請提供：

1. **瀏覽器版本**: `chrome://version`
2. **Console 完整日誌**: 從頁面載入到卡住的所有日誌
3. **截圖**: UI 狀態 + Console
4. **是否有錯誤**: 紅色錯誤訊息

---

**Last Updated**: 2026-02-06 (修復 #2)  
**Status**: 移除 StrictMode，添加狀態監聽，添加刷新按鈕
