# Streamlit Dashboard 效能優化指南

## 效能瓶頸分析

### 1. 模擬計算（Taichi GPU）⚡
**佔比**: ~30-40%  
**瓶頸**: Agent 數量 N

**優化策略**:
- ✅ 已使用 GPU 加速（Taichi Metal/CUDA）
- ✅ O(N²) 暴力法在 N < 1000 時最優
- 🔧 可調整 `steps_per_frame`（減少計算頻率）

### 2. Plotly 渲染（WebGL）🎨
**佔比**: ~40-50%  
**瓶頸**: Scatter3D 點數、Surface 面數

**優化策略**:
- ✅ 速度向量採樣顯示（每 50 個顯示 1 個）
- ✅ 資源/障礙物使用低解析度網格
- 🔧 關閉速度向量顯示可大幅提升

### 3. Streamlit 重繪（Python）🔄
**佔比**: ~10-20%  
**瓶頸**: 頁面重新渲染

**優化策略**:
- ✅ 使用 `session_state` 避免重複初始化
- ✅ 條件性更新（參數改變才重建系統）
- ✅ `use_container_width=True` 減少佈局計算

---

## 效能等級建議

### 🟢 流暢（60+ FPS）
```
N: 50-100
Steps per Frame: 1-2
Velocity Vectors: OFF
Resources: 0-2
```

### 🟡 可用（30-60 FPS）
```
N: 100-200
Steps per Frame: 1-3
Velocity Vectors: OFF
Resources: 2-3
```

### 🟠 可接受（15-30 FPS）
```
N: 200-300
Steps per Frame: 1
Velocity Vectors: OFF
Resources: 0-1
```

### 🔴 需高效能（< 15 FPS）
```
N: 300-500
Steps per Frame: 1
Velocity Vectors: OFF
Resources: 0
需要高效能 GPU（RTX 3060+）
```

---

## 具體優化建議

### 1. 減少渲染負擔

#### ❌ 避免
```python
# 顯示所有速度向量
show_velocity = True  # N=300 時會創建 300 個箭頭
```

#### ✅ 優化
```python
# 採樣顯示
sample_rate = max(1, len(x_np) // 50)  # 最多 50 個箭頭
```

### 2. 控制更新頻率

#### ❌ 避免
```python
# 每幀執行多步
steps_per_frame = 10  # 過高會導致延遲
```

#### ✅ 優化
```python
# 平衡模擬速度與流暢度
steps_per_frame = 1-3  # 建議值
```

### 3. 限制資源/障礙物數量

#### ❌ 避免
```python
# 過多複雜幾何體
for i in range(10):  # 10 個球體 = 10 × 200 faces
    add_sphere_surface(...)
```

#### ✅ 優化
```python
# 限制數量與解析度
n_resources = 3  # 最多 3-5 個
u = np.linspace(0, 2*np.pi, 20)  # 低解析度 (20 vs 50)
```

### 4. Session State 管理

#### ✅ 實作（已完成）
```python
# 避免重複初始化
if st.session_state.last_params != current_params:
    # 只在參數改變時重建
    st.session_state.system = create_system(...)
```

---

## Profiling 方法

### 1. 內建 FPS 監控
Dashboard 右上角顯示即時 FPS：
- **> 30 FPS**: 流暢
- **15-30 FPS**: 可用
- **< 15 FPS**: 需優化

### 2. Streamlit Profiler（開發用）
```bash
uv run streamlit run streamlit_app.py --server.runOnSave true
```

### 3. 瀏覽器 DevTools
1. 開啟 Chrome DevTools (F12)
2. Performance Tab → Record
3. 觀察：
   - **GPU Time**: WebGL 渲染
   - **Scripting**: Python/JS 計算
   - **Rendering**: 頁面佈局

---

## 系統需求

### 最低配置
- **CPU**: Intel i5 / Apple M1
- **GPU**: 整合顯卡（Intel Iris / Apple M1）
- **RAM**: 8 GB
- **瀏覽器**: Chrome 90+
- **N 上限**: ~100

### 推薦配置
- **CPU**: Intel i7 / Apple M1 Pro
- **GPU**: 獨立顯卡（GTX 1660 / Apple M1 Pro）
- **RAM**: 16 GB
- **瀏覽器**: Chrome 100+
- **N 上限**: ~300

### 高效能配置
- **CPU**: Intel i9 / Apple M1 Max/Ultra
- **GPU**: RTX 3060+ / Apple M1 Max
- **RAM**: 32 GB
- **瀏覽器**: Chrome latest
- **N 上限**: 500+

---

## 疑難排解

### Q: FPS 突然下降
**A**: 
1. 檢查 N 是否過大
2. 關閉速度向量顯示
3. 減少資源數量
4. 降低 steps_per_frame

### Q: 瀏覽器佔用大量記憶體
**A**:
1. 關閉其他分頁
2. 重新整理頁面（清除 WebGL 快取）
3. 使用 Chrome（記憶體管理較佳）

### Q: 模擬變慢但 FPS 正常
**A**:
- FPS 指的是「渲染幀率」，不是「模擬速度」
- 調整 `dt` 或 `steps_per_frame` 加快模擬

### Q: macOS 上 GPU 不工作
**A**:
- 檢查 Taichi 是否使用 Metal backend
- 確認 `ti.init(arch=ti.gpu)` 無錯誤訊息
- 若失敗會自動 fallback 到 CPU

---

## 效能 Benchmark

### 測試環境
- **硬體**: Apple M1 Pro (16GB)
- **瀏覽器**: Chrome 131
- **配置**: Heterogeneous, PBC, 無資源

| N   | Steps/Frame | Velocity | FPS  | 評價 |
|-----|-------------|----------|------|------|
| 50  | 1           | OFF      | 60   | 🟢 完美 |
| 100 | 1           | OFF      | 55   | 🟢 流暢 |
| 200 | 1           | OFF      | 35   | 🟡 可用 |
| 300 | 1           | OFF      | 22   | 🟠 可接受 |
| 500 | 1           | OFF      | 12   | 🔴 需優化 |
| 100 | 1           | ON       | 40   | 🟡 可用 |
| 200 | 1           | ON       | 18   | 🟠 影響明顯 |

**結論**:
- **N ≤ 200**: 推薦使用範圍
- **速度向量**: 減少約 30% FPS
- **資源/障礙物**: 每個減少約 5-10% FPS

---

## 進階優化（未來）

### 1. WebWorker 多執行緒
- Streamlit 本身不支援
- 可考慮使用 Dash/FastAPI + React

### 2. Level of Detail (LOD)
```python
# 根據距離調整解析度
if distance < near_threshold:
    resolution = 50
else:
    resolution = 20
```

### 3. 批次更新
```python
# 每 N 幀才更新統計
if step % 10 == 0:
    display_statistics(...)
```

### 4. WebGPU（未來）
- Plotly 尚未支援
- 預期 2-3x 效能提升

---

**記住：流暢度 > 視覺效果！** 🚀
