# Streamlit Dashboard 使用指南

## 🚀 啟動方式

### 方式 1: 使用腳本（推薦）
```bash
./run_dashboard.sh
```

### 方式 2: 直接執行
```bash
uv run streamlit run streamlit_app.py
```

啟動後會自動開啟瀏覽器，通常在 `http://localhost:8501`

---

## 📊 功能介紹

### 1. 系統類型選擇
- **2D**: 2D 平面系統
- **3D**: 基礎 3D 系統
- **Heterogeneous**: 異質性系統（支援完整功能）

### 2. 基礎參數
- **Number of Agents (N)**: 10-500 個 agents
- **Time Step (dt)**: 積分時間步長（0.001-0.1）
- **Steps per Frame**: 每幀執行的步數（影響速度）

### 3. 物理參數

#### Morse Potential（排斥-吸引力）
- **Ca**: 吸引力強度
- **Cr**: 排斥力強度
- **la**: 吸引力特徵長度
- **lr**: 排斥力特徵長度
- **rc**: 作用範圍截斷

#### Rayleigh Friction（主動速度調節）
- **alpha**: 摩擦係數
- **v0**: 目標速度

#### Alignment & Noise
- **beta**: 對齊強度
- **eta**: Vicsek noise（角度擾動）

#### Boundary & Space
- **Box Size**: 空間大小
- **Boundary Mode**: 
  - PBC (0): 週期邊界
  - Reflective (1): 反射壁面
  - Absorbing (2): 吸收壁面

### 4. 異質性配置（僅 Heterogeneous）

#### Agent Types
- **Explorer**: 高 noise、快速、弱對齊
- **Follower**: 低 noise、標準速度、強對齊
- **Leader**: 中等屬性、目標導向

比例調整：
- Explorer Ratio
- Follower Ratio
- Leader Ratio（自動計算 = 1 - Explorer - Follower）

#### Field of View (FOV)
- 啟用/禁用視野限制
- FOV 角度：30-360 度（預設 120°）

#### Goal-Seeking
- 啟用後 Leaders 會向目標點移動
- 可調整目標位置 (X, Y, Z)

#### Resources（資源系統）
- 啟用覓食行為
- 可新增多個資源點
- 支援可再生 / 不可再生資源
- 每個資源可設定位置 (X, Y, Z)

### 5. 視覺化選項
- **Show Velocity Vectors**: 顯示速度向量（黃色箭頭）
- **Show Energy Colors**: 用能量著色（僅異質性系統）

### 6. 模擬控制
- **Reset**: 重置系統
- **Start/Pause**: 開始/暫停模擬

---

## 📈 即時統計

儀表板顯示以下即時統計：

### 基礎統計
- **Step**: 模擬步數
- **FPS**: 每秒幀數（效能指標）
- **Avg Speed**: 平均速度
- **Speed Std**: 速度標準差
- **Rg**: Radius of gyration（群體尺度）
- **Polarization**: 方向一致性（0-1）

### 異質性系統額外統計
- **Avg Energy**: 平均能量
- **Min Energy**: 最低能量
- **Foraging**: 正在覓食的 agents 數量
- **Groups**: 偵測到的群組數量

---

## 🎨 視覺化說明

### 3D 視覺化（Plotly）
- **Agent 顏色**:
  - 預設：速度大小（Viridis 色階）
  - 能量模式：能量值（紅-黃-綠）
- **速度向量**: 黃色箭頭（採樣顯示，避免擁擠）
- **資源**: 半透明藍色球體
  - 外圈 = 採集範圍
  - 內圈大小 = 剩餘資源量
- **障礙物**: 灰色半透明球體

### 互動操作
- **旋轉**: 滑鼠左鍵拖曳
- **縮放**: 滾輪
- **平移**: 滑鼠右鍵拖曳
- **重置視角**: 雙擊

---

## ⚡ 效能優化建議

### 1. 調整 Steps per Frame
- **低效能裝置**: 1-2 步/幀
- **高效能裝置**: 3-5 步/幀

### 2. Agent 數量
- **流暢體驗**: N ≤ 200
- **可接受**: N ≤ 300
- **需高效能 GPU**: N > 300

### 3. 速度向量顯示
- 關閉可提升效能（尤其 N > 200）
- 自動採樣顯示（每 50 個顯示 1 個）

### 4. 資源/障礙物
- 限制數量 ≤ 5 個
- 複雜幾何體會影響渲染速度

### 5. 瀏覽器效能
- Chrome/Edge 推薦（WebGL 效能最佳）
- Firefox 可用
- Safari 可能較慢

---

## 🔧 常見問題

### Q: Dashboard 無法啟動
**A**: 確認已安裝依賴：
```bash
uv pip install streamlit plotly
```

### Q: 圖表不更新
**A**: 點擊 "Start" 按鈕開始模擬

### Q: FPS 很低
**A**: 
1. 減少 Agent 數量
2. 關閉速度向量顯示
3. 降低 Steps per Frame

### Q: 修改參數後沒反應
**A**: 系統會自動重新創建，等待幾秒鐘

### Q: 資源/障礙物看不到
**A**: 
1. 確認已啟用相關功能
2. 檢查位置是否在可視範圍內（-box_size/2 ~ box_size/2）

---

## 📝 預設配置推薦

### 配置 1: 標準 Flocking
```
System: Heterogeneous
N: 100
Explorer: 30%, Follower: 50%, Leader: 20%
beta: 1.0, eta: 0.0
Boundary: PBC
```

### 配置 2: 高 Noise 系統
```
System: Heterogeneous
N: 150
Explorer: 60%, Follower: 30%, Leader: 10%
beta: 0.5, eta: 0.2
Boundary: Reflective
```

### 配置 3: 覓食行為
```
System: Heterogeneous
N: 50
Enable Resources: Yes
Resources: 2-3 renewable
Explorer: 70%, Follower: 20%, Leader: 10%
```

### 配置 4: 目標導向
```
System: Heterogeneous
N: 80
Enable Goals: Yes
Leader: 30%
Goal Position: (10, 10, 10)
```

---

## 🎯 使用場景

### 1. 教學展示
- 即時調整參數觀察行為變化
- 視覺化集群形成過程
- 展示不同邊界條件效果

### 2. 參數探索
- 快速測試不同參數組合
- 找到最佳對齊/凝聚配置
- 觀察相變行為

### 3. 行為研究
- 異質性對集群的影響
- 覓食策略效率比較
- 目標導向 vs 自由遊走

### 4. 演算法驗證
- 視覺化驗證實作正確性
- 檢查邊界條件處理
- 除錯異常行為

---

## 🔗 相關文件

- [README.md](README.md) - 專案總覽
- [SESSION_7_SUMMARY.md](SESSION_7_SUMMARY.md) - 最新功能
- [GUIDE.md](docs/GUIDE.md) - 完整使用指南

---

## 💡 提示

1. **參數調整**: 小幅度調整觀察效果
2. **重置系統**: 大幅修改參數後建議重置
3. **效能監控**: 注意 FPS，低於 10 建議減少負載
4. **保存配置**: 記錄喜歡的參數組合
5. **實驗記錄**: 使用截圖記錄有趣的行為

---

**享受探索集群行為的樂趣！** 🐦✨
