# 視覺化展示使用指南

## 快速開始

### 1. 基本視覺化（推薦）

執行標準配置的視覺化展示：

```bash
cd /Users/latteine/Documents/coding/alife
uv run python experiments/visualize_v2.py
```

這將啟動一個互動視窗，展示：
- ✅ N=300 個粒子
- ✅ 速度著色（藍→綠→紅）
- ✅ 速度向量顯示
- ✅ PBC 邊界框
- ✅ 即時診斷資訊

### 2. 預設 Demo 展示

選擇不同的參數配置進行展示：

```bash
# Demo 1: 標準配置（推薦入門）
uv run python experiments/demo_visualizations.py --demo 1

# Demo 2: 高對齊配置（強集體運動）
uv run python experiments/demo_visualizations.py --demo 2

# Demo 3: 混亂配置（無對齊力）
uv run python experiments/demo_visualizations.py --demo 3

# Demo 4: 大規模配置（N=500）
uv run python experiments/demo_visualizations.py --demo 4

# Demo 5: 強吸引配置（緊密群體）
uv run python experiments/demo_visualizations.py --demo 5
```

---

## 互動控制

### 鍵盤快捷鍵

| 按鍵 | 功能 |
|------|------|
| `[SPACE]` | 暫停/恢復模擬 |
| `[R]` | 重置系統（隨機新種子）|
| `[I]` | 顯示/隱藏 HUD 資訊 |
| `[V]` | 切換速度向量顯示 |
| `[B]` | 切換 Box 邊界顯示 |
| `[ESC]` | 退出視覺化 |

### 相機操作

| 操作 | 功能 |
|------|------|
| `[右鍵拖曳]` | 旋轉相機視角 |
| `[滾輪]` | 縮放 |
| `[中鍵拖曳]` | 平移（部分系統）|

---

## 視覺化特性

### 1. 粒子速度著色

粒子顏色根據速度大小自動調整：

- **藍色** - 慢速（< 0.5 × v0）
- **綠色** - 中速（≈ v0）
- **紅色** - 快速（> 1.5 × v0）

### 2. 速度向量

黃色箭頭顯示每個粒子的速度方向與大小。

### 3. PBC 邊界框

半透明白色線框顯示週期邊界條件的模擬空間。

### 4. 即時診斷 HUD

每 50 步輸出一次系統狀態：

```
======================================================================
  Step: 500         Status: RUNNING
======================================================================
  System Size (N):      300
  Box Size:             50.0
  PBC Enabled:          True
----------------------------------------------------------------------
  Mean Speed:           0.9856 ± 0.1234
  Target Speed (v0):    1.0000
  Speed Error:          0.0144
----------------------------------------------------------------------
  Radius of Gyration:   12.345
  Polarization:         0.6789
----------------------------------------------------------------------
  Parameters:
    Morse:   Ca=1.50, Cr=2.00
             la=2.50, lr=0.50, rc=15.0
    Rayleigh: alpha=2.00, v0=1.00
    Alignment: beta=0.50
======================================================================
```

---

## Demo 說明

### Demo 1: 標準配置（推薦）

**參數：**
- N = 300
- beta = 0.5（中等對齊力）
- 其他參數為預設值

**預期行為：**
- 中等程度的方向對齊
- 群體保持相對緊密
- Polarization ≈ 0.4-0.6

### Demo 2: 高對齊配置

**參數：**
- N = 300
- beta = 2.0（高對齊力）

**預期行為：**
- 強烈的集體運動
- 所有粒子朝同一方向運動
- Polarization > 0.7

### Demo 3: 混亂配置

**參數：**
- N = 300
- beta = 0.0（無對齊力）

**預期行為：**
- 粒子方向混亂
- 僅有 Morse 勢能互動
- Polarization < 0.3

### Demo 4: 大規模配置

**參數：**
- N = 500（較多粒子）
- box_size = 70.0（更大空間）
- beta = 1.0

**預期行為：**
- 展示系統對大規模的處理能力
- 性能約 ~0.08 ms/step（參考）
- 複雜的集體行為模式

### Demo 5: 強吸引配置

**參數：**
- Ca = 3.0（強吸引）
- la = 5.0（長程吸引）
- alpha = 1.0（低主動能量）
- beta = 1.5

**預期行為：**
- 群體非常緊密
- Rg 較小（< box_size × 0.2）
- 高度對齊

---

## 自訂視覺化

### 修改參數

編輯 `experiments/visualize_v2.py` 的 `if __name__ == "__main__"` 區塊：

```python
params = FlockingParams(
    Ca=1.5,      # 吸引力係數
    Cr=2.0,      # 排斥力係數
    la=2.5,      # 吸引範圍
    lr=0.5,      # 排斥範圍
    rc=15.0,     # 截斷半徑
    alpha=2.0,   # Rayleigh 強度
    v0=1.0,      # 目標速度
    beta=0.5,    # 對齊力強度
    box_size=50.0,
    use_pbc=True,
)

N = 300  # 粒子數量
```

### 調整視覺化選項

```python
viz = V2EnhancedVisualizer(
    system=system,
    window_size=(1400, 1000),  # 視窗大小
    show_velocity=True,         # 顯示速度向量
    show_box=True,              # 顯示邊界框
    show_alignment_field=False, # 對齊力場（暫未實作）
)
```

### 控制模擬長度

```python
viz.run(
    steps=0,      # 0 = 無限循環，或指定步數
    dt=0.01,      # 時間步長
    log_every=100 # 診斷輸出頻率
)
```

---

## 疑難排解

### 視窗無法開啟

**可能原因：**
1. Taichi GGUI 不支援你的系統
2. 缺少圖形驅動

**解決方案：**
```bash
# 測試視覺化邏輯（無視窗）
uv run python experiments/test_viz_logic.py
```

### 性能問題（卡頓）

**解決方案：**
1. 減少粒子數量（N = 200 或更少）
2. 關閉速度向量顯示（按 `[V]`）
3. 降低 log_every 頻率

### 粒子飛出邊界

**可能原因：**
PBC 正常運作，粒子會「wrap around」到對面

**驗證方法：**
檢查所有粒子位置是否在 [0, box_size] 範圍內：

```python
x_np = system.x.to_numpy()
print(f"X range: [{x_np.min():.2f}, {x_np.max():.2f}]")
# 應該在 [0, box_size] 之間
```

---

## 效能參考

| N | 平均 FPS | ms/step | 備註 |
|---|----------|---------|------|
| 100 | 60+ | ~0.07 | 流暢 |
| 300 | 60 | ~0.08 | 推薦 |
| 500 | 50-60 | ~0.10 | 良好 |
| 1000 | 30-40 | ~0.15 | 可接受 |

*測試環境：MacBook Pro M1, Metal GPU*

---

## 進階功能（待實作）

### 1. 對齊力場可視化

在空間中採樣若干點，顯示局部平均速度向量。

### 2. 軌跡追蹤

顯示每個粒子的歷史軌跡（尾巴效果）。

### 3. 錄影功能

將視覺化過程錄製為影片。

### 4. 即時參數調整

通過 UI 滑桿即時調整物理參數。

---

## 相關檔案

- `experiments/visualize_v2.py` - 主視覺化器
- `experiments/demo_visualizations.py` - Demo 腳本
- `experiments/test_viz_logic.py` - 邏輯驗證測試
- `src/optimized_v2.py` - 模擬系統核心

## 技術報告

- `docs/OPTIMIZED_V2_REPORT.md` - V2 技術細節
- `docs/PERFORMANCE_TEST_SUMMARY.md` - 性能測試報告
