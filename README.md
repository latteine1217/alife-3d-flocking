# 3D Heterogeneous Flocking Simulation

基於物理的 2D/3D **異質性集群行為模擬系統**，使用 **Taichi** GPU 加速。

## 🎯 專案特色

### Tier 0-1: 物理與異質性 ✅
- **核心物理**：Morse potential、Rayleigh friction、Cucker-Smale alignment、Vicsek noise
- **邊界模式**：PBC / Reflective walls / Absorbing walls
- **Agent 異質性**：Explorer / Follower / Leader（不同速度、noise、對齊強度）
- **Goal-directed Behavior**：目標導向行為（PBC-aware）
- **Field of View (FOV)**：視野限制（120° 預設）

### Tier 2: Agent-Based Modeling (ABM) ✅
- **Obstacle System**：SDF-based 碰撞偵測（Sphere / Box / Cylinder）
- **Group Detection**：Label propagation clustering（空間 + 速度）
- **Resource/Foraging System**：覓食行為（可消耗 / 可再生資源）
- **Resource Competition**：FIFO 先到先得機制（多 agents 競爭同一資源） 🆕
- **Health & Weakness System**：能量影響移動速度（健康/疲勞/虛弱/瀕死） 🆕
- **Dynamic Predation**：機率性攻擊成功率（速度差/健康/群防） 🆕
- **Death & Removal**：死亡 agents 自動消失（能量耗盡/被捕食） 🆕

### Tier 3: WebGPU Frontend 🚀 (In Progress)
- **React + TypeScript**：現代化 Web 介面
- **WebSocket 即時通訊**：30-60 FPS 低延遲資料流
- **WebGPU 渲染器**：高效能 GPU 粒子系統
- **Hybrid Architecture**：Python Taichi (研究) + Web (展示)

---

## 核心物理模型

結合多種物理機制：

* **Morse potential**：短程排斥 + 長程吸引（保守力）
* **Rayleigh friction**：主動定速機制（注入/耗散能量）
* **Cucker-Smale alignment**：方向對齊力（促進集體運動）
* **Vicsek noise**：角度隨機擾動（研究 noise 對秩序的影響） 🆕
* **Multiple Boundary Modes**：PBC / Reflective walls / Absorbing walls 🆕

### 運動方程

```
dv_i/dt = (1/m) * (F_morse + F_align) + alpha * (1 - |v_i|²/v0²) * v_i + Vicsek_noise
dx_i/dt = v_i
```

### 診斷指標

1. **平均速度** `<|v|>` - 應收斂至目標速度 `v0`
2. **Radius of gyration** `Rg` - 群體緊密程度
3. **Polarization** `P = |Σv_i| / Σ|v_i|` - 方向一致性（0 = 混亂，1 = 完全對齊）

---

## 快速開始

### 安裝依賴

```bash
uv pip install taichi numpy matplotlib streamlit plotly
```

### 🎮 Streamlit 互動式 Dashboard（推薦）🆕

**最簡單的方式探索系統！**

```bash
# 啟動 Dashboard
./run_dashboard.sh

# 或
uv run streamlit run streamlit_app.py
```

功能特色：
- 🎨 **即時參數調整** - 所有物理參數可即時修改
- 📊 **Plotly 3D 互動視覺化** - 可旋轉、縮放、探索
- 🔧 **完整功能支援** - 2D/3D/異質性/覓食/障礙物/群組
- 📈 **即時統計** - FPS、能量、群組、極化度等
- 💾 **Session 管理** - 參數自動保存，無需重複設定

詳細使用指南：[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)

---

### 執行視覺化展示（命令列）

**3D 視覺化：**

```bash
# 標準配置（N=300, beta=0.5）
uv run python experiments/demo_3d.py

# 選擇預設 demo
uv run python experiments/demo_3d.py --demo 1  # 標準配置
uv run python experiments/demo_3d.py --demo 2  # 高對齊
uv run python experiments/demo_3d.py --demo 3  # 混亂狀態
uv run python experiments/demo_3d.py --demo 4  # 大規模（N=500）

# 自訂參數
uv run python experiments/demo_3d.py --N 500 --beta 1.5
```

**2D 視覺化：**

```bash
# 標準配置
uv run python experiments/demo_2d.py

# 不同預設
uv run python experiments/demo_2d.py --demo 2  # 高對齊
uv run python experiments/demo_2d.py --demo 3  # 混亂狀態
```

**2D vs 3D 比較：**

```bash
# 比較 2D 和 3D 系統的動力學差異
uv run python experiments/compare_2d_3d_fixed.py --N 100 --steps 200
```

**🆕 進階物理展示：**

```bash
# 2D: Vicsek noise、反射壁面、吸收壁面
uv run python experiments/demo_advanced_physics.py

# 3D: 球面旋轉 noise、三維邊界
uv run python experiments/demo_advanced_physics_3d.py
```

**🆕 異質性系統展示：**

```bash
# Agent 類型（Explorer/Follower/Leader）
uv run python experiments/demo_heterogeneous.py

# 障礙物系統
uv run python experiments/demo_obstacles.py

# 群組偵測
uv run python experiments/demo_group_detection.py

# 覓食行為 🆕
uv run python experiments/demo_foraging.py
```

### 進階物理參數範例

#### 2D Advanced Physics

**Vicsek Noise（角度隨機擾動）：**

```python
from flocking_2d import Flocking2D, FlockingParams

params = FlockingParams(
    beta=1.0,              # 強對齊力
    eta=0.2,               # Vicsek noise (11.5 degrees)
    boundary_mode="pbc"    # 週期邊界
)
system = Flocking2D(N=100, params=params)
```

**Reflective Walls（反射壁面）：**

```python
params = FlockingParams(
    beta=0.5,
    eta=0.0,
    boundary_mode="reflective",   # 反射邊界
    wall_stiffness=10.0,          # 壁面剛度
    box_size=30.0
)
system = Flocking2D(N=100, params=params)
```

**Absorbing Walls（吸收壁面）：**

```python
params = FlockingParams(
    beta=0.5,
    eta=0.0,
    boundary_mode="absorbing",    # 吸收邊界
    box_size=30.0
)
system = Flocking2D(N=100, params=params)
```

#### 3D Advanced Physics 🆕

**3D Vicsek Noise（球面旋轉）：**

```python
from flocking_3d import Flocking3D, FlockingParams

params = FlockingParams(
    beta=1.0,              # 強對齊力
    eta=0.2,               # 3D spherical rotation noise
    boundary_mode="pbc"    # 週期邊界
)
system = Flocking3D(N=100, params=params)

# 技術細節：使用 Rodrigues' rotation formula + Marsaglia sphere sampling
```

**3D Reflective Walls（立方體邊界）：**

```python
params = FlockingParams(
    beta=0.5,
    eta=0.0,
    boundary_mode="reflective",   # 6 個反射平面
    box_size=20.0                 # [-10, +10]³
)
system = Flocking3D(N=100, params=params)
```

**Combined Effects（Noise + Walls）：**

```python
params = FlockingParams(
    beta=1.0,                     # 對齊
    eta=0.2,                      # 3D noise
    boundary_mode="reflective",   # 限制擴散
    box_size=20.0
)
# 觀察 noise-order competition 與 boundary confinement
```

### 互動控制

- `[SPACE]` - 暫停/恢復
- `[R]` - 重置模擬（隨機種子）
- `[V]` - 切換速度向量顯示
- `[B]` - 切換邊界框顯示
- `[I]` - 顯示/隱藏 HUD 資訊
- `[RMB]` - 旋轉相機（拖曳）
- `[Scroll]` - 縮放
- `[ESC]` - 退出

---

## 專案結構

```
alife/
├── src/                               # 核心實作（模組化架構 ✨）
│   ├── agents/                        # Phase 1: Agent 類型系統
│   │   ├── __init__.py
│   │   └── types.py                   # AgentType enum, 行為參數配置
│   │
│   ├── spatial/                       # Phase 2-3: 空間結構與演算法
│   │   ├── __init__.py
│   │   ├── grid.py                    # O(N) 空間網格加速
│   │   └── group_detection.py         # Label Propagation 群體偵測
│   │
│   ├── behaviors/                     # Phase 4: 行為模組
│   │   ├── __init__.py
│   │   ├── foraging.py                # 覓食行為與能量管理 🆕 (FIFO競爭)
│   │   ├── predation.py               # 捕食行為與生死狀態 🆕 (動態攻擊率)
│   │   └── reproduction.py            # 繁殖演化系統 🚧 (設計完成，待整合)
│   │
│   ├── perception/                    # Phase 6.1 ✅: 感知模組
│   │   ├── __init__.py
│   │   └── fov.py                     # Field of View (FOV) 過濾
│   │
│   ├── navigation/                    # Phase 6.2 ✅: 導航模組
│   │   ├── __init__.py
│   │   └── goal_seeking.py            # 目標導向行為（PBC-aware）
│   │
│   ├── flocking_2d.py                 # 2D 基礎系統（O(N²)）
│   ├── flocking_3d.py                 # 3D 基礎系統（O(N²)） 🆕 (修正質量動力學)
│   ├── flocking_heterogeneous.py      # 異質性系統（整合所有模組）
│   ├── obstacles.py                   # 障礙物系統（SDF-based）
│   ├── resources.py                   # 資源系統
│   └── flocking_celllist.py           # Cell List 優化版本（實驗性）
│
├── backend/                           # 🆕 WebSocket 後端（生產就緒）
│   ├── server.py                      # WebSocket 伺服器（30 FPS）
│   ├── simulation_manager.py          # 模擬管理器
│   ├── serializer.py                  # 二進制序列化（低延遲）
│   ├── test_client.py                 # 測試客戶端
│   └── README.md                      # Backend API 文件
│
├── experiments/                       # 可執行腳本
│   ├── demo_2d.py                     # 2D 快速展示
│   ├── demo_3d.py                     # 3D 快速展示
│   ├── demo_advanced_physics.py       # 2D 進階物理展示
│   ├── demo_advanced_physics_3d.py    # 3D 進階物理展示
│   ├── demo_heterogeneous.py          # 異質性系統展示
│   ├── demo_obstacles.py              # 障礙物展示
│   ├── demo_group_detection.py        # 群組偵測展示
│   ├── demo_foraging.py               # 覓食行為展示
│   ├── visualizer_2d.py               # 2D 可視化器
│   ├── visualizer_3d.py               # 3D 可視化器
│   ├── compare_2d_3d_fixed.py         # 2D/3D 動力學比較
│   ├── demo_presets.py                # 預設參數展示
│   └── benchmark_optimized.py         # 效能測試
│
├── tests/                             # 單元測試（95+ tests ✅）
│   ├── test_physics.py                # 基礎物理測試 (13 tests)
│   ├── test_advanced_physics.py       # 2D 進階物理測試 (9 tests)
│   ├── test_advanced_physics_3d.py    # 3D 進階物理測試 (10 tests)
│   ├── test_heterogeneous.py          # 異質性測試 (12 tests)
│   ├── test_obstacles.py              # 障礙物測試 (10 tests)
│   ├── test_group_detection.py        # 群組偵測測試 (9 tests)
│   ├── test_foraging.py               # 覓食測試 (9 tests)
│   ├── test_perception.py             # Phase 6.1: FOV 測試 (7 tests)
│   └── test_navigation.py             # Phase 6.2: 導航測試 (13 tests, 1 skipped)
│
├── test_improvements.py               # 🆕 整合測試：質量動力學、排斥、健康、攻擊
├── test_death_removal.py              # 🆕 死亡消失測試
├── test_resource_competition.py       # 🆕 資源競爭測試（FIFO vs Equal）
│
├── docs/                              # 技術文件
│   ├── GUIDE.md                       # 使用指南
│   ├── PERFORMANCE.md                 # 性能測試報告
│   ├── CHANGELOG.md                   # 開發日誌
│   ├── REFACTORING_REPORT.md          # Phase 5 重構報告
│   ├── PHASE_6_PLAN.md                # ✅ Phase 6 完成報告（-7.5% 代碼）
│   ├── PHASE_6.1_REPORT.md            # Phase 6.1: PerceptionMixin 完整報告
│   ├── PHASE_6.2_REPORT.md            # Phase 6.2: NavigationMixin 完整報告
│   ├── WEBGPU_INTEGRATION_PLAN.md     # WebGPU 整合計畫
│   ├── WEBGPU_QUICKSTART.md           # WebGPU 快速開始
│   └── benchmark_result.png           # 性能測試圖
│
└── pyproject.toml                     # 專案配置
```

---

## 版本比較

| 版本 | 檔案 | 維度 | 積分器 | 複雜度 | 推薦用途 |
|------|------|------|--------|--------|----------|
| **2D** | `flocking_2d.py` | 2D | Verlet | O(N²) | **2D 生產使用（N ≤ 1000）** |
| **3D** | `flocking_3d.py` | 3D | Verlet | O(N²) | **3D 生產使用（N ≤ 1000）** |
| CellList | `flocking_celllist.py` | 3D | Verlet | O(N) | 大規模實驗（N > 5000） |

**設計原則：**
- 2D 和 3D 各自獨立，避免動態維度的複雜性
- 每個版本都經過物理模型驗證，行為一致
- 簡潔 > 抽象：兩個簡單的類別優於一個複雜的通用類別

---

## 視覺化特性

### 粒子速度著色
- **藍色** - 速度低於目標速度
- **綠色** - 接近目標速度
- **紅色** - 速度高於目標速度

### 速度向量（黃色箭頭）
顯示每個粒子的速度方向與大小

### PBC 邊界框（白色線框）
顯示週期性邊界的範圍

### 即時診斷 HUD
每 50 步輸出：
- 系統狀態（執行中/暫停）
- 平均速度 ± 標準差
- Radius of gyration
- Polarization
- 參數設定

---

## 架構設計

### 模組化架構（Phase 6 重構 ✅）

系統採用 **Mixin Pattern** 實現功能組合，符合 Taichi 的 `@ti.data_oriented` 限制：

```python
class HeterogeneousFlocking3D(
    Flocking3D,                # 基礎物理引擎（Velocity Verlet 積分）
    SpatialGridMixin,          # Phase 2: O(N) neighbor search
    GroupDetectionMixin,       # Phase 3: Label Propagation
    ForagingBehaviorMixin,     # Phase 4: 覓食 & 能量
    PredationBehaviorMixin,    # Phase 4: 捕食 & 生死
    PerceptionMixin,           # Phase 6.1 ✅: FOV 過濾
    NavigationMixin,           # Phase 6.2 ✅: 目標導向
):
    """主協調器：組合所有模組功能"""
```

#### 模組職責

| 模組 | 職責 | 行數 | 狀態 |
|-----|------|------|-----|
| **agents/types.py** | Agent 類型定義與行為配置 | 54 | ✅ |
| **spatial/grid.py** | O(N) 空間網格加速結構 | 206 | ✅ |
| **spatial/group_detection.py** | Label Propagation 群體偵測 | 291 | ✅ |
| **behaviors/foraging.py** | 覓食行為與能量動態 | 380 | ✅ 🆕 (FIFO競爭) |
| **behaviors/predation.py** | 捕食行為與生死管理 | 262 | ✅ 🆕 (動態攻擊率) |
| **behaviors/reproduction.py** | 繁殖演化系統 | 227 | 🚧 (設計完成) |
| **perception/fov.py** | FOV 視野過濾（Phase 6.1） | 128 | ✅ |
| **navigation/goal_seeking.py** | 目標導向導航（Phase 6.2） | 224 | ✅ |
| **flocking_heterogeneous.py** | 主協調器（整合所有模組） | 753 | ✅ |

#### 重構成果

**Phase 5 → Phase 6 累積成效**：
- **主檔案縮減**：1230 → 753 lines (-38.8%)
- **方法數減少**：47 → 14 methods (-70.2%)
- **模組化代碼**：1289 lines（8 個獨立模組）
- **測試覆蓋**：新增 494 lines 測試（20 tests, 100% passing）
- **可測試性**：每個模組可獨立單元測試
- **可擴展性**：新增功能只需建立新 Mixin

詳細技術報告：
- [Phase 5 重構報告](docs/REFACTORING_REPORT.md)
- [Phase 6 計畫與成果](docs/PHASE_6_PLAN.md)
- [Phase 6.1 報告](docs/PHASE_6.1_REPORT.md) - PerceptionMixin
- [Phase 6.2 報告](docs/PHASE_6.2_REPORT.md) - NavigationMixin

---

## 程式化使用

### 基本範例（3D）

```python
from src.flocking_3d import Flocking3D, FlockingParams

# 創建參數
params = FlockingParams(
    Ca=1.5, Cr=2.0, la=2.5, lr=0.5, rc=15.0,  # Morse
    alpha=2.0, v0=1.0,                         # Rayleigh
    beta=0.5,                                  # Alignment
    box_size=50.0, boundary_mode=0             # PBC
)

# 創建系統
system = Flocking3D(N=300, params=params)
system.initialize(box_size=5.0, seed=42)

# 模擬循環
for step in range(1000):
    system.step(dt=0.01)
    
    if step % 100 == 0:
        diag = system.compute_diagnostics()
        print(f"Step {step}: Rg={diag['Rg']:.2f}, P={diag['polarization']:.3f}")
```

### 異質性系統範例 🆕

```python
from src.flocking_heterogeneous import HeterogeneousFlocking3D
from src.agents.types import AgentType
from src.resources import ResourceConfig
from src.flocking_3d import FlockingParams

# 創建混合群體：20% Explorer, 70% Follower, 10% Predator
N = 100
agent_types = (
    [AgentType.EXPLORER] * 20 + 
    [AgentType.FOLLOWER] * 70 + 
    [AgentType.PREDATOR] * 10
)

params = FlockingParams(
    beta=1.0,              # 對齊強度
    eta=0.1,               # Noise level
    box_size=50.0
)

system = HeterogeneousFlocking3D(
    N=N,
    params=params,
    agent_types=agent_types,
    max_groups=16,         # 群體偵測（自動使用 Label Propagation）
    max_resources=5        # 支援覓食系統
)

system.initialize(box_size=50.0, seed=42)

# 新增可再生資源
from resources import ResourceConfig
import numpy as np

system.add_resource(ResourceConfig(
    position=np.array([0.0, 0.0, 0.0]),
    amount=100.0,
    radius=3.0,
    replenish_rate=2.0,
    max_amount=200.0
))

# 執行模擬（自動整合：物理、覓食、捕食、群體偵測）
for step in range(500):
    system.step(dt=0.05)
    
    # 查詢狀態
    groups = system.get_all_groups()           # 群體資訊
    alive_count = system.get_alive_count()     # 存活數量
    predator_count = system.get_predator_count()  # 捕食者數量
```

### 2D 範例

```python
from src.flocking_2d import Flocking2D, FlockingParams

params = FlockingParams(beta=1.0, alpha=2.0, boundary_mode=0)  # PBC
system = Flocking2D(N=200, params=params)
system.initialize(box_size=5.0, seed=42)

# 執行 100 步
system.run(steps=100, dt=0.01, log_every=20)
```

---

## 測試

執行所有測試：

```bash
# 完整測試套件（89 tests）
uv run pytest tests/ -v

# 特定測試
uv run pytest tests/test_foraging.py -v
uv run pytest tests/test_heterogeneous.py -v
uv run pytest tests/test_perception.py -v        # Phase 6.1
uv run pytest tests/test_navigation.py -v        # Phase 6.2
```

測試覆蓋：
- ✅ 基礎物理（Morse, Rayleigh, Alignment, PBC）
- ✅ 進階物理（Vicsek noise, Reflective/Absorbing walls）
- ✅ 異質性（Agent types, FOV, Goal-seeking）
- ✅ 障礙物（SDF, Collision, Dynamic obstacles）
- ✅ 群組偵測（Label propagation, PBC-aware）
- ✅ 覓食行為（Resource search, Consumption, Replenishment）
- ✅ 感知系統（FOV filtering, angle-based visibility）
- ✅ 導航系統（Goal-seeking, PBC-aware pathfinding）

---

## 參數調整指南

### 預設參數

```python
# Morse potential
Ca=1.5, Cr=2.0, la=2.5, lr=0.5, rc=15.0

# Rayleigh friction
alpha=2.0, v0=1.0

# Alignment
beta=0.5

# Space
box_size=50.0, use_pbc=True
```

### 常見問題與解決

| 現象 | 原因 | 解決方案 |
|------|------|----------|
| 塌縮成球 | 吸引過強 | ↑ `Cr` 或 ↓ `Ca` |
| 分散無法凝聚 | 排斥過強 | ↑ `Ca` 或 ↑ `la` |
| Rg 持續增長 | 主動能量過強 | ↓ `alpha` 或 ↓ `v0` |
| 對齊度低 (P < 0.5) | 對齊力太弱 | ↑ `beta` (試 0.5-2.0) |
| 數值爆炸 | 時間步長過大 | ↓ `dt` (0.005 或更小) |

### 推薦配置

**高對齊配置（強集體運動）：**
```python
FlockingParams(beta=2.0, alpha=1.5)
```

**混亂配置（低對齊）：**
```python
FlockingParams(beta=0.0, alpha=3.0)
```

**緊密群體：**
```python
FlockingParams(Ca=3.0, la=5.0, rc=20.0)
```

---

## 性能資訊

### 測試環境
- **硬體**：macOS, Metal GPU (M1/M2)
- **粒子數**：N = 100-1000

### 基準測試結果

| 系統 | N=100 | N=300 | N=500 | N=1000 |
|------|-------|-------|-------|--------|
| **flocking_3d** | 0.07 ms | 0.08 ms | 0.12 ms | 0.25 ms |
| flocking_celllist | 0.09 ms | 0.13 ms | 0.18 ms | 0.30 ms |

**結論：** 對於 N ≤ 1000，暴力法（flocking_3d）比 Cell List 更快。

詳細報告：[docs/PERFORMANCE.md](docs/PERFORMANCE.md)

---

## 文件

- [**使用指南**](docs/GUIDE.md) - 完整使用說明與範例
- [**性能報告**](docs/PERFORMANCE.md) - 性能測試與優化建議
- [**開發日誌**](docs/CHANGELOG.md) - 版本歷史與技術細節
- [**Phase 5 重構報告**](docs/REFACTORING_REPORT.md) - 模組化重構（-34% 代碼）
- [**Phase 6 計畫與成果**](docs/PHASE_6_PLAN.md) - ✅ Phase 6 完成（-7.5% 代碼）
- [**Phase 6.1 報告**](docs/PHASE_6.1_REPORT.md) - PerceptionMixin 詳細報告
- [**Phase 6.2 報告**](docs/PHASE_6.2_REPORT.md) - NavigationMixin 詳細報告
- [**WebGPU 整合計畫**](docs/WEBGPU_INTEGRATION_PLAN.md) - React + WebGPU 前端架構
- [**WebGPU 快速開始**](docs/WEBGPU_QUICKSTART.md) - 30 分鐘快速指南

### Backend API 文件

- [**Backend README**](backend/README.md) - WebSocket 伺服器使用說明

---

## 已知限制

1. **PBC 未完全穩定 Rg** - 主動能量導致群體尺度持續增長
2. **低對齊度** - 預設 beta=0.5 下 P ≈ 0.02-0.05（提高 beta 可改善）
3. **Cell List 在小規模下較慢** - 建設開銷在 N < 5000 時未被攤銷

---

## 🆕 最新改進（2026-02）

### Phase 7: 核心物理與行為系統改進 ✅

完成了 **6 項關鍵改進**，提升系統真實性與穩定性：

#### ✅ 已完成改進

1. **修正質量動力學（F=ma）** - `src/flocking_3d.py:235-384`
   - 修復：從 `a = F * inv_m` 改為正確的 `a = F / m`
   - 影響：重型 agents 加速較慢，符合物理定律

2. **軟球排斥力** - `src/flocking_3d.py:179-233`
   - 新增：`min_distance=0.8`, `repulsion_strength=10.0`
   - 效果：防止 agents 重疊或黏在一起

3. **健康/虛弱系統** - `src/behaviors/foraging.py:140-199`
   - 新增：4 級健康狀態（健康/疲勞/虛弱/瀕死）
   - 速度懲罰：100% / 85% / 60% / 30%
   - 能量閾值：>50 / 30-50 / 15-30 / <15

4. **動態攻擊成功率** - `src/behaviors/predation.py:159-237`
   - 取代：100% 固定成功率 → 動態機率計算
   - 因素：速度差（±20%）、獵物健康（+15%）、掠食者耐力（+6%）、群防（-30%）
   - 範圍：5%-95%

5. **死亡 Agent 消失** - `src/behaviors/foraging.py:266-309` + `src/behaviors/predation.py:239-262`
   - 機制：移動到遠處（1e6 單位），速度歸零
   - 觸發：能量耗盡、被捕食
   - 效果：視覺上消失，不參與物理交互

6. **資源競爭機制（FIFO）** - `src/behaviors/foraging.py:286-368`
   - 策略：先到先得（按距離排序）
   - 優勢：近距離 agents 優先獲得資源
   - 測試：`test_resource_competition.py` ✅

#### 🚧 設計完成（待整合）

7. **繁殖演化系統** - `src/behaviors/reproduction.py`
   - 觸發：能量 ≥ 90，冷卻時間已過
   - 消耗：父代 50% 能量
   - 子代：繼承父代類型、位置、30% 能量
   - 架構：預分配池（max_agents=200）
   - 狀態：Mixin 已實作，待整合到 `flocking_heterogeneous.py`

#### 📊 測試覆蓋

- ✅ `test_improvements.py` - 改進 1-4 綜合測試
- ✅ `test_death_removal.py` - 改進 5 死亡消失測試
- ✅ `test_resource_competition.py` - 改進 6 資源競爭測試

#### 📝 待辦事項

詳見專案 TODO 清單：
- [ ] 修復 Equal 模式資源消耗 bug
- [ ] 修正 `flocking_heterogeneous.py` 中 `agent_type` 欄位衝突
- [ ] 整合 ReproductionMixin 到主系統
- [ ] 撰寫繁殖演化測試

---

## 授權

MIT License

