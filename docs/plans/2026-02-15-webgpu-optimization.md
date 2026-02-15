# WebGPU 效能優化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 消除 `webgpu-renderer.ts` 中的三個主要渲染瓶頸：Trail N 個 draw call 批量化為 1 個、移除 render loop 的 debug logging、預分配 CPU buffer 消除每幀 GC。

**Architecture:** 所有修改集中在 `frontend/src/lib/webgpu-renderer.ts`（2404 行），不改動其他檔案。Fix 1 使用 WebGPU primitive restart index（`stripIndexFormat: 'uint32'` + 哨兵值 `0xFFFFFFFF`）將 N 個 draw call 合併為 1 個 `drawIndexed()`；Fix 2 直接刪除 render loop 內所有 `Math.random()` debug block；Fix 3 在 class 層級預分配 `Uint32Array`，每幀複用。

**Tech Stack:** TypeScript, WebGPU API, Vite（build）

---

## 背景知識（必讀）

**Trail 渲染的資料佈局：**
Vertex buffer 中，每個粒子 i 的軌跡點連續排列：
```
[p0_t0, p0_t1, ..., p0_tH-1,  p1_t0, ..., p1_tH-1,  ...]
 ──── particle 0 (H vertices) ──── particle 1 ────
```
每個 vertex = `(x, y, z, age)` = 16 bytes（`float32x4`）。

**Primitive Restart：**
WebGPU 的 `line-strip` topology + `stripIndexFormat: 'uint32'` 時，index buffer 中的 `0xFFFFFFFF` 會讓 GPU 自動「斷線」，開始新的 line-strip。這讓多條不相連的 line-strip 可以用一個 draw call 完成。

---

## Task 1：Trail Pipeline 加入 stripIndexFormat

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts:639-641`

### Step 1：找到 trail pipeline 的 primitive block

在 `webgpu-renderer.ts` 第 639 行附近，找到：
```typescript
      primitive: {
        topology: 'line-strip',
      },
```

### Step 2：加入 stripIndexFormat

改為：
```typescript
      primitive: {
        topology: 'line-strip',
        stripIndexFormat: 'uint32',
      },
```

### Step 3：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 4：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): add stripIndexFormat to trail pipeline for primitive restart"
```

---

## Task 2：加入 trailIndexBuffer 類別成員並在 destroy() 清理

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts:76`（成員宣告區）
- Modify: `frontend/src/lib/webgpu-renderer.ts:1670`（destroy 方法）

### Step 1：在 trailBuffer 成員宣告後加入 index buffer 成員

找到第 76 行：
```typescript
  private trailBuffer!: GPUBuffer;
```

在它**後面**新增一行：
```typescript
  private trailIndexBuffer: GPUBuffer | null = null;
```

### Step 2：在 destroy() 加入清理

找到第 1670 行：
```typescript
    if (this.trailBuffer) this.trailBuffer.destroy();
```

在它**後面**新增：
```typescript
    if (this.trailIndexBuffer) this.trailIndexBuffer.destroy();
```

### Step 3：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 4：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): add trailIndexBuffer member and cleanup"
```

---

## Task 3：buildTrailBuffer() 同時建立 index buffer

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts:1087-1133`（`buildTrailBuffer` 方法）

### Step 1：讀取目前的 buildTrailBuffer 方法

確認第 1087-1133 行的完整內容。

### Step 2：在 data 建立之後、writeBuffer 之前，加入 index buffer 的建立邏輯

在現有 `this.device.queue.writeBuffer(this.trailBuffer, 0, data);`（第 1132 行）**之後**、方法結尾 `}` **之前**，加入：

```typescript
    // 建立 primitive restart index buffer
    // 每條軌跡：historyCount 個索引 + 1 個哨兵值 0xFFFFFFFF
    const indexCount = this.particleCount * (historyCount + 1);
    const indexData = new Uint32Array(indexCount);
    for (let i = 0; i < this.particleCount; i++) {
      const base = i * (historyCount + 1);
      const vertexBase = i * historyCount;
      for (let t = 0; t < historyCount; t++) {
        indexData[base + t] = vertexBase + t;
      }
      indexData[base + historyCount] = 0xFFFFFFFF; // primitive restart sentinel
    }

    const indexBufferSize = indexData.byteLength;
    if (!this.trailIndexBuffer || this.trailIndexBuffer.size !== indexBufferSize) {
      if (this.trailIndexBuffer) this.trailIndexBuffer.destroy();
      this.trailIndexBuffer = this.device.createBuffer({
        label: 'Trail Index Buffer',
        size: indexBufferSize,
        usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST,
      });
    }
    this.device.queue.writeBuffer(this.trailIndexBuffer, 0, indexData);
```

### Step 3：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 4：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): build trail index buffer with primitive restart sentinels"
```

---

## Task 4：Trail 渲染改用單一 drawIndexed()

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts:1539-1558`（render loop 的 trail 段）

### Step 1：讀取目前的 trail render 段落（第 1539-1558 行）

確認以下結構：
```typescript
    if (this.enableTrails && this.trailBuffer && this.positionHistory.length > 1) {
      const historyCount = this.positionHistory.length;

      if (Math.random() < 0.016) {
        console.log(`🎨 Drawing trails: ...`);
      }

      renderPass.setPipeline(this.trailPipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.trailBuffer);

      // 每個粒子繪製一條 line-strip
      for (let i = 0; i < this.particleCount; i++) {
        const firstVertex = i * historyCount;
        renderPass.draw(historyCount, 1, firstVertex, 0);
      }
    } else if (Math.random() < 0.016) {
      console.log(`⚠️ Trails skipped: ...`);
    }
```

### Step 2：替換整個 trail render block

將上述整個 block（`if (this.enableTrails...` 開始到 `}` 結尾）替換為：

```typescript
    if (this.enableTrails && this.trailBuffer && this.trailIndexBuffer && this.positionHistory.length > 1) {
      const historyCount = this.positionHistory.length;
      const totalIndexCount = this.particleCount * (historyCount + 1);

      renderPass.setPipeline(this.trailPipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.trailBuffer);
      renderPass.setIndexBuffer(this.trailIndexBuffer, 'uint32');
      renderPass.drawIndexed(totalIndexCount);
    }
```

**重點**：
- `setIndexBuffer(buffer, 'uint32')` 對應 pipeline 的 `stripIndexFormat: 'uint32'`
- `drawIndexed(totalIndexCount)` 一次完成所有粒子的軌跡
- 移除所有 debug logging block

### Step 3：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 4：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): replace N trail draw calls with single drawIndexed + primitive restart"
```

---

## Task 5：移除 render loop 內所有 debug console.log

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts`（多處）

### Step 1：確認所有 render loop 內的 debug block

執行以下指令確認目標行號：
```bash
grep -n "Math.random\|🎨\|🦁\|predatorIndices\|updateParticles called\|updateParticles complete" \
  /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
```

### Step 2：逐一移除以下 debug block

**2a. 第 1389 行附近**：移除 `updateParticles` 入口的 log：
```typescript
// 刪除這行
console.log(`🔄 updateParticles called: N=${N}, positions.length=${positions.length}`);
```

**2b. 第 1449-1454 行**：移除 predator debug block：
```typescript
// 刪除這整段
const predatorIndices = Array.from(typesU32).map((t, i) => t === 3 ? i : -1).filter(i => i !== -1);
if (predatorIndices.length > 0) {
  console.log(`🦁 Found ${predatorIndices.length} predators at indices:`, predatorIndices);
  console.log('Predator positions:', predatorIndices.map(i => [positions[i*3], positions[i*3+1], positions[i*3+2]]));
}
```

**2c. 第 1489 行**：移除 `updateParticles complete` log：
```typescript
// 刪除這行
console.log(`✅ updateParticles complete: particleCount=${this.particleCount}`);
```

**2d. 第 1586 行附近**：group boundary debug block：
```typescript
// 刪除整個 if (Math.random() < 0.016) { ... } block
if (Math.random() < 0.016) {
  console.log(`✅ Drawing ${this.groupCount} group boundaries`);
}
```

**2e. 第 1609-1613 行附近**：particle draw debug：
```typescript
// 刪除整個 if block
if (Math.random() < 0.016) {
  console.log(`🎨 Drawing ${this.particleCount} particles...`);
}
```

**2f. 第 1627 行附近**：velocity vector debug：
```typescript
// 刪除整個 if block
if (Math.random() < 0.016) {
  console.log(...);
}
```

**2g. 第 1643 行附近**：group velocity arrow debug：
```typescript
// 刪除整個 if block
if (Math.random() < 0.016) {
  console.log(...);
}
```

### Step 3：確認無遺漏

```bash
grep -n "Math.random" /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
```
Expected: 無輸出（render loop 內已全部清除）。

### Step 4：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 5：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): remove all debug console.log from render loop"
```

---

## Task 6：預分配 CPU buffer 消除每幀 GC

**Files:**
- Modify: `frontend/src/lib/webgpu-renderer.ts:76`（成員宣告區）
- Modify: `frontend/src/lib/webgpu-renderer.ts:1444-1485`（updateParticles 轉換段）

### Step 1：加入預分配 buffer 的 class 成員

找到第 76 行附近的成員宣告區，在現有成員之後加入：

```typescript
  // 預分配 CPU buffer，避免每幀 GC（僅在粒子數變化時重新分配）
  private _typesU32: Uint32Array | null = null;
  private _groupLabelsU32: Uint32Array | null = null;
```

### Step 2：更新 updateParticles() 的 type buffer 段

找到第 1444-1466 行：
```typescript
    const typesU32 = new Uint32Array(N);
    for (let i = 0; i < N; i++) {
      typesU32[i] = types[i];
    }

    if (!this.typeBuffer || this.particleCount !== N) {
      ...
    }
    this.device.queue.writeBuffer(this.typeBuffer, 0, typesU32);
```

替換為：
```typescript
    // 複用預分配 buffer，僅粒子數變化時重新分配
    if (!this._typesU32 || this._typesU32.length !== N) {
      this._typesU32 = new Uint32Array(N);
    }
    for (let i = 0; i < N; i++) {
      this._typesU32[i] = types[i];
    }

    if (!this.typeBuffer || this.particleCount !== N) {
      if (this.typeBuffer) this.typeBuffer.destroy();
      this.typeBuffer = this.device.createBuffer({
        label: 'Type Buffer',
        size: this._typesU32.byteLength,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    this.device.queue.writeBuffer(this.typeBuffer, 0, this._typesU32);
```

### Step 3：更新 groupLabels buffer 段

找到第 1469-1485 行：
```typescript
    if (groupLabels) {
      const groupLabelsU32 = new Uint32Array(N);
      for (let i = 0; i < N; i++) {
        groupLabelsU32[i] = groupLabels[i];
      }

      if (!this.groupLabelBuffer || this.particleCount !== N) {
        ...
      }
      this.device.queue.writeBuffer(this.groupLabelBuffer, 0, groupLabelsU32);
    }
```

替換為：
```typescript
    if (groupLabels) {
      if (!this._groupLabelsU32 || this._groupLabelsU32.length !== N) {
        this._groupLabelsU32 = new Uint32Array(N);
      }
      for (let i = 0; i < N; i++) {
        this._groupLabelsU32[i] = groupLabels[i];
      }

      if (!this.groupLabelBuffer || this.particleCount !== N) {
        if (this.groupLabelBuffer) this.groupLabelBuffer.destroy();
        this.groupLabelBuffer = this.device.createBuffer({
          label: 'Group Label Buffer',
          size: this._groupLabelsU32.byteLength,
          usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
        });
      }
      this.device.queue.writeBuffer(this.groupLabelBuffer, 0, this._groupLabelsU32);
    }
```

### Step 4：確認 build

```bash
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -10
```
Expected: 無錯誤。

### Step 5：Commit

```bash
cd /Users/latteine/Documents/coding/alife
git add frontend/src/lib/webgpu-renderer.ts
git commit -m "perf(webgpu): pre-allocate CPU Uint32Array buffers to eliminate per-frame GC"
```

---

## 完成驗收

執行以下確認：

```bash
# 1. 確認 Math.random 已全部清除
grep -c "Math.random" /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
# Expected: 0

# 2. 確認 trailIndexBuffer 存在
grep -n "trailIndexBuffer" /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
# Expected: 至少 5 行（宣告、建立、destroy、setIndexBuffer）

# 3. 確認 drawIndexed 已使用
grep -n "drawIndexed" /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
# Expected: 至少 2 行（resource sphere + trail）

# 4. 確認無 for loop draw call
grep -n "for.*particleCount" /Users/latteine/Documents/coding/alife/frontend/src/lib/webgpu-renderer.ts
# Expected: 0 行（在 render loop 中）

# 5. Build 成功
cd /Users/latteine/Documents/coding/alife/frontend && npm run build 2>&1 | tail -5
```

---

*Created: 2026-02-15*
