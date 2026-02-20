# 3D Heterogeneous Flocking Simulation

基於物理的 2D/3D 異質性集群行為模擬系統，使用 Taichi GPU 加速。

---

## 近期累積變更（依 `git diff`）

- 文件重整：大量根目錄說明文件已整理至 `docs/archive/`、`docs/reports/`、`docs/status/`、`docs/plans/`
- 測試體系擴充：目前可收集測試為 **103** 項（含 `tests/grid/` 與 `tests/integration/`）
- 行為模組更新：`foraging` / `predation` / `reproduction` 與主協調器邏輯持續整合
- 前端與序列化調整：`frontend/` 與 `backend/serializer.py` 已同步更新

---

## 核心特色

### 物理引擎
- **核心物理**：Morse potential、Rayleigh friction、Cucker-Smale alignment、Vicsek noise
- **邊界模式**：PBC（週期性邊界）/ Reflective walls（反射壁面）/ Absorbing walls（吸收壁面）
- **數值積分**：Velocity Verlet（二階精度，能量守恆）

### Agent-Based Modeling (ABM)
- **Agent 異質性**：Explorer / Follower / Leader / Predator（不同速度、noise、對齊強度）
- **感知系統**：Field of View (FOV) 過濾（可調視野角度）
- **導航系統**：目標導向行為（PBC-aware pathfinding）
- **覓食行為**：能量管理、可消耗/可再生資源、FIFO 資源競爭
- **捕食系統**：動態攻擊成功率（速度差、健康狀態、群防效應）
- **健康系統**：4 級健康狀態（健康/疲勞/虛弱/瀕死），影響移動速度
- **生死機制**：能量耗盡或被捕食後自動消失
- **群體偵測**：Label propagation clustering（空間 + 速度）
- **障礙物系統**：SDF-based 碰撞偵測（Sphere / Box / Cylinder）

### 架構設計
- **模組化架構**：Mixin Pattern 組合功能（8 個獨立模組）
- **空間加速**：O(N) 空間網格（Cell List）
- **測試覆蓋**：103 個測試案例（以 `pytest --collect-only` 為準）

### WebGPU Frontend (In Progress)
- **React + TypeScript**：現代化 Web 介面
- **WebSocket 即時通訊**：30 FPS 低延遲資料流
- **WebGPU 渲染器**：GPU 粒子系統
- **族群動態儀表板**：8 張即時圖表（各類型數量、飢餓率、Lotka-Volterra 比、群組數、系統能量）

### 實驗設定檔系統
- **YAML 設定檔**：`configs/` 目錄，三個內建預設（`default`、`predator_heavy`、`foraging_only`）
- **可驗證載入**：ratio 總和超過 1.0 時立即報錯
- **CLI 整合**：`--config` 啟動參數動態切換實驗場景

---

## 快速開始

### 安裝依賴

```bash
uv pip install taichi numpy matplotlib
```

### 執行視覺化展示

```bash
# 3D 標準配置（N=300, beta=0.5）
uv run python experiments/demo_3d.py

# 2D 標準配置
uv run python experiments/demo_2d.py

# 異質性系統展示（Agent 類型、覓食、捕食）
uv run python experiments/demo_heterogeneous.py
uv run python experiments/demo_foraging.py

# 進階物理展示（Vicsek noise、反射壁面、吸收壁面）
uv run python experiments/demo_advanced_physics.py       # 2D
uv run python experiments/demo_advanced_physics_3d.py    # 3D

# 障礙物與群組偵測
uv run python experiments/demo_obstacles.py
uv run python experiments/demo_group_detection.py
```

### 互動控制

- `[SPACE]` - 暫停/恢復
- `[R]` - 重置模擬
- `[V]` - 切換速度向量顯示
- `[B]` - 切換邊界框顯示
- `[I]` - 顯示/隱藏 HUD 資訊
- `[RMB + 拖曳]` - 旋轉相機
- `[Scroll]` - 縮放
- `[ESC]` - 退出

---

## 核心物理模型

### 運動方程

```
dv_i/dt = (1/m) * (F_morse + F_align + F_repulsion) + alpha * (1 - |v_i|²/v0²) * v_i + Vicsek_noise
dx_i/dt = v_i
```

**組成要素**：
- **Morse potential**：短程排斥 + 長程吸引
- **Cucker-Smale alignment**：速度對齊力
- **Soft-sphere repulsion**：防止 agents 重疊
- **Rayleigh friction**：主動定速機制
- **Vicsek noise**：角度隨機擾動（可選）

### 診斷指標

- **平均速度** `<|v|>` - 應收斂至目標速度 `v0`
- **Radius of gyration** `Rg` - 群體緊密程度
- **Polarization** `P = |Σv_i| / Σ|v_i|` - 方向一致性（0 = 混亂，1 = 完全對齊）

---

## 專案架構

### 模組化設計（Mixin Pattern）

```python
class HeterogeneousFlocking3D(
    Flocking3D,                # 基礎物理引擎（Velocity Verlet）
    SpatialGridMixin,          # O(N) 空間網格加速
    GroupDetectionMixin,       # Label Propagation 群體偵測
    ForagingBehaviorMixin,     # 覓食行為與能量管理
    PredationBehaviorMixin,    # 捕食行為與生死機制
    PerceptionMixin,           # FOV 視野過濾
    NavigationMixin,           # 目標導向導航
):
    """主協調器：組合所有模組功能"""
```

### 核心模組

| 模組 | 職責 | 行數 | 狀態 |
|-----|------|------|-----|
| `flocking_3d.py` | 基礎物理引擎 | ~500 | ✅ |
| `flocking_heterogeneous.py` | 主協調器 | 753 | ✅ |
| `agents/types.py` | Agent 類型定義 | 54 | ✅ |
| `spatial/grid.py` | O(N) 空間網格 | 206 | ✅ |
| `spatial/group_detection.py` | 群體偵測 | 291 | ✅ |
| `behaviors/foraging.py` | 覓食與能量 | 380 | ✅ |
| `behaviors/predation.py` | 捕食與生死 | 262 | ✅ |
| `behaviors/reproduction.py` | 繁殖演化 | 227 | 🚧 |
| `perception/fov.py` | FOV 過濾 | 128 | ✅ |
| `navigation/goal_seeking.py` | 目標導向 | 224 | ✅ |
| `resources.py` | 資源系統 | 246 | ✅ |
| `obstacles.py` | SDF 碰撞偵測 | ~220 | ✅ |

### 目錄結構

```
alife/
├── src/                     # 核心實作
│   ├── agents/              # Agent 類型系統
│   ├── spatial/             # 空間結構與群體偵測
│   ├── behaviors/           # 行為模組（覓食、捕食、繁殖）
│   ├── perception/          # 感知系統（FOV）
│   ├── navigation/          # 導航系統（目標導向）
│   ├── flocking_2d.py       # 2D 基礎系統
│   ├── flocking_3d.py       # 3D 基礎系統
│   ├── flocking_heterogeneous.py  # 異質性系統（整合所有模組）
│   ├── resources.py         # 資源系統
│   └── obstacles.py         # 障礙物系統
│
├── backend/                 # WebSocket 後端（30 FPS）
│   ├── server.py
│   ├── simulation_manager.py
│   └── serializer.py
│
├── experiments/             # 可執行腳本
│   ├── demo_3d.py
│   ├── demo_heterogeneous.py
│   ├── demo_foraging.py
│   └── ...
│
├── configs/                 # YAML 實驗設定檔
│   ├── default.yaml         # 平衡生態系統（預設）
│   ├── predator_heavy.yaml  # 高捕食者密度
│   └── foraging_only.yaml   # 純覓食（無捕食者）
│
├── tests/                   # 測試（目前 103 tests）
│   ├── test_physics.py
│   ├── test_foraging.py
│   ├── test_heterogeneous.py
│   ├── test_config.py       # YAML 設定檔測試（7 tests）
│   └── ...
│
└── docs/                    # 技術文件
    ├── GUIDE.md             # 使用指南
    ├── AGENTS.md            # 開發者指南
    ├── CHANGELOG.md         # 版本歷史
    └── ...
```

---

## 程式化使用

### 基本範例（3D）

```python
from src.flocking_3d import Flocking3D, FlockingParams

# 創建系統
params = FlockingParams(
    Ca=1.5, Cr=2.0, la=2.5, lr=0.5, rc=15.0,  # Morse
    alpha=2.0, v0=1.0,                         # Rayleigh
    beta=0.5,                                  # Alignment
    box_size=50.0, boundary_mode="pbc"         # PBC
)

system = Flocking3D(N=300, params=params)
system.initialize(box_size=5.0, seed=42)

# 執行模擬
for step in range(1000):
    system.step(dt=0.01)
    if step % 100 == 0:
        diag = system.compute_diagnostics()
        print(f"Step {step}: Rg={diag['Rg']:.2f}, P={diag['polarization']:.3f}")
```

### 異質性系統範例

```python
from src.flocking_heterogeneous import HeterogeneousFlocking3D
from src.agents.types import AgentType
from src.flocking_3d import FlockingParams

# 創建混合群體
N = 100
agent_types = (
    [AgentType.EXPLORER] * 20 +
    [AgentType.FOLLOWER] * 70 +
    [AgentType.PREDATOR] * 10
)

params = FlockingParams(beta=1.0, eta=0.1, box_size=50.0)

system = HeterogeneousFlocking3D(
    N=N, params=params, agent_types=agent_types,
    max_groups=16, max_resources=5
)

system.initialize(box_size=50.0, seed=42)

# 執行模擬
for step in range(500):
    system.step(dt=0.05)
    groups = system.get_all_groups()
    alive_count = system.get_alive_count()
```

詳細範例與參數調整請參考 [docs/GUIDE.md](docs/GUIDE.md)。

### 使用 YAML 實驗設定檔啟動

```bash
# 列出可用設定檔
cd backend && uv run python server.py --help

# 使用內建預設
uv run python server.py --config default          # 平衡生態系統
uv run python server.py --config predator_heavy   # 高捕食者密度
uv run python server.py --config foraging_only    # 純覓食（無捕食者）
```

自訂實驗場景只需在 `configs/` 目錄新增 YAML 檔案（參考現有預設格式）。

---

## 測試

```bash
# 完整測試套件（目前 103 tests）
uv run pytest tests/ -v

# 特定測試
uv run pytest tests/test_physics.py -v          # 基礎物理
uv run pytest tests/test_foraging.py -v         # 覓食行為
uv run pytest tests/test_heterogeneous.py -v    # 異質性系統
uv run pytest tests/test_perception.py -v       # FOV 過濾
uv run pytest tests/test_navigation.py -v       # 目標導向
```

**測試覆蓋**：
- ✅ 基礎物理（Morse, Rayleigh, Alignment, PBC）
- ✅ 進階物理（Vicsek noise, Reflective/Absorbing walls）
- ✅ 異質性（Agent types, FOV, Goal-seeking）
- ✅ 障礙物（SDF, Collision, Dynamic obstacles）
- ✅ 群組偵測（Label propagation, PBC-aware）
- ✅ 覓食行為（Resource search, Consumption, FIFO competition）
- ✅ 捕食系統（Dynamic attack rate, Death mechanics）

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

**結論**：對於 N ≤ 1000，暴力法（flocking_3d）比 Cell List 更快。

詳細報告：[docs/PERFORMANCE.md](docs/PERFORMANCE.md)

---

## 文件

### 使用說明
- [**使用指南**](docs/GUIDE.md) - 完整使用說明與範例
- [**開發者指南**](AGENTS.md) - 架構設計與開發規範
- [**Backend README**](backend/README.md) - WebSocket 伺服器使用說明

### 技術報告
- [**性能報告**](docs/PERFORMANCE.md) - 性能測試與優化建議
- [**開發日誌**](docs/CHANGELOG.md) - 版本歷史與技術細節
- [**Phase 5 重構報告**](docs/REFACTORING_REPORT.md) - 模組化重構（-34% 代碼）
- [**Phase 6 計畫與成果**](docs/PHASE_6_PLAN.md) - 感知與導航模組（-7.5% 代碼）

### WebGPU 整合
- [**WebGPU 整合計畫**](docs/WEBGPU_INTEGRATION_PLAN.md) - React + WebGPU 前端架構
- [**WebGPU 快速開始**](docs/WEBGPU_QUICKSTART.md) - 30 分鐘快速指南

---

## 版本比較

| 版本 | 檔案 | 維度 | 積分器 | 複雜度 | 推薦用途 |
|------|------|------|--------|--------|----------|
| **2D** | `flocking_2d.py` | 2D | Verlet | O(N²) | 2D 生產使用（N ≤ 1000） |
| **3D** | `flocking_3d.py` | 3D | Verlet | O(N²) | 3D 生產使用（N ≤ 1000） |
| **Heterogeneous** | `flocking_heterogeneous.py` | 3D | Verlet | O(N) | 異質性 ABM（完整功能） |
| CellList | `flocking_celllist.py` | 3D | Verlet | O(N) | 大規模實驗（N > 5000） |

---

## 已知限制

1. **PBC 未完全穩定 Rg** - 主動能量導致群體尺度持續增長
2. **低對齊度** - 預設 beta=0.5 下 P ≈ 0.02-0.05（提高 beta 可改善）
3. **Cell List 在小規模下較慢** - 建設開銷在 N < 5000 時未被攤銷

---

## 開發歷程

### Phase 5 ✅ - 模組化重構
- 主檔案縮減 34%（1230 → 814 lines）
- 6 個獨立模組，完整測試覆蓋

### Phase 6 ✅ - 感知與導航
- PerceptionMixin（FOV 過濾）
- NavigationMixin（目標導向）
- 再減少 7.5% 代碼（814 → 753 lines）

### Phase 7 ✅ - 物理與行為系統改進
- 修正質量動力學（F=ma）
- 軟球排斥力（防止重疊）
- 健康/虛弱系統（4 級狀態）
- 動態攻擊成功率（5%-95%）
- 死亡 Agent 消失機制
- 資源競爭（FIFO 先到先得）

### Phase 8 ✅ - 可觀測性與實驗系統
- **族群動態可視化**：8 張即時圖表整合進前端 Dashboard（各類型數量、飢餓率、Lotka-Volterra 比、群組數）
- **YAML 實驗設定檔**：3 個內建預設，支援 `--config` 啟動參數
- 繁殖演化系統整合（待完成）
- WebGPU 前端開發（進行中）

---

## 授權

MIT License
