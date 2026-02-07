# Dashboard 快速測試指南

## 啟動 Dashboard

```bash
cd /Users/latteine/Documents/coding/alife
./run_dashboard.sh
```

**預期結果**: 瀏覽器自動開啟 `http://localhost:8501`

---

## 測試清單

### 基礎功能測試 (5 分鐘)

#### 1. 啟動測試
- [ ] Dashboard 正常啟動
- [ ] 側邊欄顯示完整
- [ ] 主面板顯示空白圖表

#### 2. 系統切換測試
- [ ] 選擇 "3D" → 觀察系統重建提示
- [ ] 選擇 "Heterogeneous" → 觀察新增的 Heterogeneity Config
- [ ] 選擇 "2D" → 觀察 2D 圖表

#### 3. 參數調整測試
- [ ] 調整 N=100
- [ ] 調整 beta=1.0
- [ ] 點擊 "Start" 按鈕
- [ ] 觀察模擬開始運行
- [ ] FPS 顯示正常（應 > 30）

#### 4. 控制按鈕測試
- [ ] "Pause" 按鈕 → 模擬暫停
- [ ] "Start" 按鈕 → 模擬繼續
- [ ] "Reset" 按鈕 → 系統重置，Step 歸零

---

### 3D 系統測試 (5 分鐘)

#### 設定
- System Type: **3D**
- N: **100**
- beta: **1.0**
- eta: **0.0**
- Show Velocity Vectors: **OFF**

#### 測試項目
- [ ] 點擊 "Start"
- [ ] Agents 以藍色點顯示
- [ ] 可旋轉 3D 圖表（滑鼠拖曳）
- [ ] 可縮放（滾輪）
- [ ] 可平移（Shift + 拖曳）
- [ ] FPS > 30
- [ ] Rg 數值合理（20-30）
- [ ] Polarization 逐漸增加（beta=1.0 會形成對齊）

#### 速度向量測試
- [ ] 開啟 "Show Velocity Vectors"
- [ ] 黃色箭頭顯示速度方向
- [ ] 箭頭數量適中（約 50 個）
- [ ] FPS 下降但仍可接受（> 20）

---

### 異質性系統測試 (10 分鐘)

#### 設定
- System Type: **Heterogeneous**
- N: **100**
- Explorer Ratio: **0.3** (30%)
- Follower Ratio: **0.5** (50%)
- Leader Ratio: **0.2** (20%, 自動計算)
- Enable FOV: **True**
- FOV Angle: **120**
- Show Energy Colors: **True**

#### 測試項目
- [ ] 點擊 "Start"
- [ ] Agents 以綠-黃-紅色顯示（能量著色）
- [ ] 統計欄顯示 5 列
- [ ] Avg Energy / Min Energy 顯示正常
- [ ] Foraging 顯示 "0/100"（無資源）
- [ ] Groups 數字逐漸變化
- [ ] FPS > 30

---

### 資源系統測試 (10 分鐘)

#### 設定
- System Type: **Heterogeneous**
- N: **100**
- Enable Resources: **True**
- Number of Resources: **2**

**Resource 1** (Consumable):
- X: **0**
- Y: **0**
- Z: **0**
- Renewable: **False**

**Resource 2** (Renewable):
- X: **10**
- Y: **10**
- Z: **10**
- Renewable: **True**

#### 測試項目
- [ ] 點擊 "Reset" 重新創建系統
- [ ] 觀察 "✅ System created" 訊息
- [ ] 點擊 "Start"
- [ ] **2 個藍色半透明球體**顯示資源位置
- [ ] Agents 逐漸靠近資源
- [ ] Foraging 數字增加（X/100）
- [ ] Avg Energy 隨時間增加（消耗資源補充能量）
- [ ] FPS > 25

---

### 目標導向測試 (10 分鐘)

#### 設定
- System Type: **Heterogeneous**
- N: **50**
- Explorer Ratio: **0.2**
- Follower Ratio: **0.5**
- Leader Ratio: **0.3**
- Enable Goals: **True**
- Goal Position: **(15, 15, 15)**

#### 測試項目
- [ ] 點擊 "Reset"
- [ ] 點擊 "Start"
- [ ] 觀察 Leaders（紅色/黃色 agents）移動向 (15, 15, 15)
- [ ] Followers 跟隨 Leaders
- [ ] Explorers 相對獨立移動
- [ ] 整體群體朝目標方向移動
- [ ] FPS > 30

---

### 效能測試 (5 分鐘)

#### Test 1: N=50 (應非常流暢)
- [ ] N=50, Show Velocity OFF
- [ ] FPS > 50 ✅

#### Test 2: N=100 (應流暢)
- [ ] N=100, Show Velocity OFF
- [ ] FPS > 35 ✅

#### Test 3: N=200 (應可用)
- [ ] N=200, Show Velocity OFF
- [ ] FPS > 20 ✅

#### Test 4: N=100 with Velocity (應稍慢)
- [ ] N=100, Show Velocity ON
- [ ] FPS > 25 ✅

#### Test 5: N=100 with 2 Resources (應流暢)
- [ ] N=100, Resources=2, Show Velocity OFF
- [ ] FPS > 30 ✅

---

## 預期問題與解決方法

### 問題 1: Dashboard 無法啟動
**症狀**: 終端機顯示錯誤訊息

**檢查**:
```bash
# 確認依賴安裝
uv pip list | grep streamlit
# 應顯示: streamlit 1.54.0

# 手動啟動
uv run streamlit run streamlit_app.py
```

### 問題 2: Taichi 初始化警告
**症狀**: 顯示 Metal backend 警告

**解決**: 正常現象，不影響功能，可忽略

### 問題 3: FPS 過低 (< 15)
**症狀**: 模擬非常卡頓

**檢查**:
1. 降低 N 值（試 N=50）
2. 關閉 "Show Velocity Vectors"
3. 關閉 "Show Energy Colors"
4. 減少 Resources 數量

### 問題 4: 資源不顯示
**症狀**: 啟用 Resources 但看不到藍色球體

**檢查**:
1. 確認 "Enable Resources" 已勾選
2. 確認點擊過 "Reset" 按鈕（需重新創建系統）
3. 調整視角（可能被遮擋）
4. 檢查資源位置是否在 box_size 範圍內

### 問題 5: 統計資訊不更新
**症狀**: Step / FPS 顯示為 0

**檢查**:
1. 確認點擊 "Start" 按鈕
2. 確認 `st.session_state.running = True`
3. 檢查瀏覽器 Console（F12）是否有錯誤

---

## 測試通過標準

### 必須通過 (Critical)
- [x] Dashboard 能啟動
- [x] 三種系統切換正常
- [x] Start/Pause/Reset 功能正常
- [x] Plotly 圖表顯示正常
- [x] 統計資訊正確顯示
- [x] FPS > 30 @ N=100

### 應該通過 (Important)
- [ ] Resources 視覺化正常
- [ ] Goal-seeking 行為正確
- [ ] 速度向量顯示正常
- [ ] 能量著色功能正常
- [ ] 參數調整即時生效

### 可選通過 (Nice-to-have)
- [ ] FPS > 50 @ N=50
- [ ] FPS > 20 @ N=200
- [ ] 長時間運行穩定（5 分鐘無崩潰）

---

## 測試完成後

### 如果所有測試通過 ✅
1. 記錄實際 FPS 數據
2. 截圖保存視覺化結果
3. 準備進入 v1.0 Release

### 如果發現問題 ❌
1. 記錄問題描述
2. 記錄重現步驟
3. 提供錯誤訊息截圖
4. 回報給開發者修正

---

## 快速重啟

如果需要重新啟動 Dashboard：

```bash
# 停止 (Ctrl+C)
^C

# 重新啟動
./run_dashboard.sh
```

---

**預計測試時間**: 30-45 分鐘  
**建議環境**: Chrome/Safari, macOS/Linux
