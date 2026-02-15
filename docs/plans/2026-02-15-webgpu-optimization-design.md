# WebGPU 效能優化設計文件

**目標**：消除 N≤200 全功能開啟時的主要渲染瓶頸，不改動整體架構。

**範圍**：`frontend/src/lib/webgpu-renderer.ts`（2404 行）

---

## 問題診斷

| 問題 | 位置 | 嚴重度 |
|------|------|--------|
| Trail：N 個獨立 draw call | L1552-1555 | 高 |
| Debug console.log 散落 render loop | L1543, 1556, 1586, 1609, 1613, 1627, 1643 | 中 |
| 每幀 `new Uint32Array(N)` × 2 次 | L1444, 1470 | 中 |

---

## Fix 1：Trail Draw Call 批量化

### 現況

```typescript
for (let i = 0; i < this.particleCount; i++) {
  const firstVertex = i * historyCount;
  renderPass.draw(historyCount, 1, firstVertex, 0);  // N 個 draw call
}
```

N=200、historyCount=40 → 200 個 draw call，每個都有 GPU 狀態切換開銷。

### 設計

使用 WebGPU **primitive restart**（`stripIndexFormat: 'uint32'`）：

1. **Pipeline 修改**：在 trail pipeline 的 `primitive` block 加入 `stripIndexFormat: 'uint32'`
2. **Index buffer 建立**：`buildTrailBuffer()` 同時產生 index buffer，格式為：
   ```
   [0, 1, ..., H-1,  0xFFFFFFFF,  H, H+1, ..., 2H-1,  0xFFFFFFFF, ...]
    ─── particle 0 ── (restart)   ──── particle 1 ────  (restart)
   ```
   每條軌跡 H 個索引 + 1 個哨兵值 `0xFFFFFFFF`，GPU 遇到哨兵自動斷開 line-strip。
3. **Draw call**：替換為單次 `drawIndexed(N * (H + 1), 1, 0, 0, 0)`

### 影響

- 200 draw call → **1 draw call**
- index buffer 大小：`200 × (40 + 1) × 4 bytes = 32.8 KB`（可接受）
- Vertex buffer 結構不變（仍是 `float32x3 position + float32 age`）

---

## Fix 2：移除 Render Loop 內的 Debug Logging

### 現況

共 8 處 `Math.random() < 0.016` 判斷散落在 render loop 中，每幀：
- 觸發字串模板運算
- 可能觸發 `console.log`（字串分配 → GC）
- 即使不觸發，`Math.random()` 本身有呼叫開銷

### 設計

**直接刪除**以下所有 debug block（含外層 `if (Math.random() < ...)`）：
- L1543-1545：trail 繪製日誌
- L1556-1558：trail 跳過日誌
- L1586-1588：group boundary 日誌
- L1609-1613：particle 繪製日誌
- L1627：velocity vector 日誌
- L1643：group velocity arrow 日誌

保留初始化時的一次性 `console.log`（`init()` 方法內，非 render loop）。

---

## Fix 3：預分配 CPU Buffer 消除每幀 GC

### 現況

```typescript
// updateParticles() 每幀執行
const typesU32 = new Uint32Array(N);           // 新分配
for (let i = 0; i < N; i++) typesU32[i] = types[i];

const groupLabelsU32 = new Uint32Array(N);     // 新分配
for (let i = 0; i < N; i++) groupLabelsU32[i] = groupLabels[i];
```

N=200 → 每幀創建 2 個新 TypedArray，60FPS 下每秒 120 次 GC-tracked 分配。

### 設計

加入兩個 class 成員：
```typescript
private _typesU32: Uint32Array | null = null;
private _groupLabelsU32: Uint32Array | null = null;
```

在 `updateParticles()` 中改為：
```typescript
// 僅在粒子數變化時重新分配（罕見）
if (!this._typesU32 || this._typesU32.length !== N) {
  this._typesU32 = new Uint32Array(N);
}
for (let i = 0; i < N; i++) this._typesU32[i] = types[i];

if (!this._groupLabelsU32 || this._groupLabelsU32.length !== N) {
  this._groupLabelsU32 = new Uint32Array(N);
}
for (let i = 0; i < N; i++) this._groupLabelsU32[i] = groupLabels[i];
```

同時移除 `Array.from(typesU32).map(...)` 的 predator 偵測 debug log（L1450-1453）。

---

## 不在範圍內

- Trail buffer 的 CPU→GPU 傳輸本身（N≤200 時 128KB/frame 可接受）
- Trail history 的 compute shader 化（複雜度不成比例）
- `webgpu-renderer.ts` 的模組拆分

---

*設計日期：2026-02-15*
