# AGENTS.md - 專案開發指南

**目標讀者**：Python 工程師、研究人員、貢獻者

本文件從工程師角度描述專案目標、技術架構、所需知識與技能。

---

## 專案目標

### 核心目標

建立一個**高效能、模組化、可擴展**的 3D 異質性集群模擬系統，用於：

1. **科學研究**：集體行為、自組織現象、生態動力學
2. **教學展示**：互動式視覺化、參數探索、演算法驗證
3. **工程應用**：多智能體系統、群體機器人、交通流模擬

### 設計哲學

遵循 Linux Kernel 開發哲學與現代軟體工程原則：

1. **Good Taste**：追求簡潔優雅的邏輯結構，消除不必要的條件判斷
2. **Never Break Userspace**：絕對維持 API 相容性，任何修改都向後相容
3. **Pragmatism**：解決真實問題，可落地執行，避免過度設計
4. **Simplicity**：複雜性是風險來源，程式碼應短小精悍、職責單一
5. **Correctness First**：先證明邏輯正確，再談最佳化
6. **Observability**：系統可理解、可診斷、可驗證

---

## 技術架構

### 技術棧

| 層級 | 技術 | 用途 | 選型理由 |
|-----|------|------|---------|
| **計算核心** | Taichi (Python) | GPU 加速物理引擎 | 接近 C/CUDA 效能，Python 語法 |
| **科學計算** | NumPy | 資料處理、陣列運算 | 生態系統成熟，效能優異 |
| **後端服務** | WebSocket (asyncio) | 即時資料流 | 低延遲 (<33ms)，雙向通訊 |
| **前端渲染** | React + WebGPU | 3D 視覺化 | 現代化，GPU 加速，跨平台 |
| **測試框架** | pytest | 單元/整合測試 | Python 標準，插件豐富 |
| **文檔工具** | Markdown + Docstring | API 文件、指南 | 簡單、版本控制友善 |

---

### 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  ┌───────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ WebGPU    │  │ Zustand   │  │ Control Panel      │  │
│  │ Renderer  │  │ State Mgr │  │ (Parameters)       │  │
│  └─────┬─────┘  └─────┬─────┘  └──────────┬─────────┘  │
└────────┼──────────────┼───────────────────┼─────────────┘
         │              │                   │
         │         WebSocket (ws://localhost:8765)
         │              │                   │
┌────────▼──────────────▼───────────────────▼─────────────┐
│                  Backend (Python)                        │
│  ┌──────────────────┐  ┌───────────────────────────┐   │
│  │ WebSocket Server │  │  Simulation Manager       │   │
│  │  (asyncio)       │  │  - State management       │   │
│  │  - Binary proto  │  │  - Parameter updates      │   │
│  │  - 30 FPS stream │  │  - Lifecycle control      │   │
│  └────────┬─────────┘  └──────────┬────────────────┘   │
└───────────┼────────────────────────┼────────────────────┘
            │                        │
            │                        │
┌───────────▼────────────────────────▼────────────────────┐
│              Taichi Physics Engine (GPU)                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │         HeterogeneousFlocking3D (814 lines)     │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────────┐ │    │
│  │  │ Agents  │ │ Spatial  │ │   Behaviors      │ │    │
│  │  │ Types   │ │ Grid +   │ │   Foraging +     │ │    │
│  │  │ (54L)   │ │ Groups   │ │   Predation      │ │    │
│  │  │         │ │ (497L)   │ │   (327L)         │ │    │
│  │  └─────────┘ └──────────┘ └──────────────────┘ │    │
│  │               Flocking3D (Base Physics)          │    │
│  └─────────────────────────────────────────────────┘    │
│           Resources        Obstacles                     │
└──────────────────────────────────────────────────────────┘
```

---

### 模組化架構（Mixin Pattern）

#### 為何使用 Mixin？

**Taichi 限制**：
- `@ti.data_oriented` 類別要求所有 fields 在 `__init__` 時定義
- 無法使用傳統的深層繼承（會導致 field 重複定義）
- Kernel 中無法使用 `hasattr()` 等動態檢查

**解決方案**：
- 使用 **Mixin Pattern** 實現功能組合
- 每個 Mixin 負責一個獨立功能模組
- 主類別透過多重繼承組合所有功能

#### 架構圖

```python
class HeterogeneousFlocking3D(
    Flocking3D,                # 基礎物理引擎
    SpatialGridMixin,          # 空間加速（O(N) neighbor search）
    GroupDetectionMixin,       # 群體偵測（Label Propagation）
    ForagingBehaviorMixin,     # 覓食行為與能量管理
    PredationBehaviorMixin,    # 捕食行為與生死狀態
):
    """
    主協調器：整合所有模組功能
    
    職責：
    1. 初始化所有 Mixins（呼叫 init_*() 方法）
    2. 實作主循環（step() 方法）
    3. 覆寫特定行為（如排除 predators 的 group detection）
    4. 提供統一對外介面
    """
```

#### 初始化流程

```python
def __init__(self, N, params, agent_types, ...):
    # 1. 基礎物理引擎
    super().__init__(N, params)
    
    # 2. 依序初始化各 Mixin（注意順序：有依賴關係）
    self.init_spatial_grid(N, box_size, cell_size)
    self.init_group_detection(N, max_groups)
    self.init_foraging(N, resources, energy_threshold)
    self.init_predation(N, attack_radius)
    
    # 3. Agent 類型系統
    self._init_agent_types(agent_types)
```

**關鍵原則**：
- ✅ 每個 Mixin 有獨立的 `init_*()` 方法
- ✅ 主類別負責呼叫順序
- ✅ Mixin 之間透過 Taichi fields 通訊（如 `self.x`, `self.v`）

#### 主循環設計

```python
def step(self, dt: float):
    """
    單步模擬循環
    
    階段：
    1. 預處理：更新空間索引
    2. 目標搜尋：覓食資源、捕獵獵物
    3. 物理更新：Velocity Verlet 積分
    4. 生態互動：消耗資源、執行攻擊
    5. 資源再生
    6. 週期性群體偵測
    """
    # Phase 1: 空間索引
    self.assign_agents_to_grid()
    
    # Phase 2: 目標搜尋（使用空間網格加速）
    self.find_nearest_resources()  # ForagingBehaviorMixin
    self.find_nearest_prey()       # PredationBehaviorMixin
    
    # Phase 3: 物理積分（Velocity Verlet）
    self.compute_forces()
    self.verlet_step1(dt)
    self.compute_forces()
    self.verlet_step2(dt)
    
    # Phase 4: 生態互動
    self.consume_resources_step()  # ForagingBehaviorMixin
    self.attack_prey_step()        # PredationBehaviorMixin
    self.resources.regenerate_step()
    
    # Phase 5: 週期性群體偵測（每 10 步）
    self.step_counter += 1
    if self.step_counter >= self.group_detection_interval:
        self.update_groups()       # GroupDetectionMixin
        self.step_counter = 0
```

---

### 模組職責

| 模組 | 職責 | 行數 | 狀態 |
|-----|------|------|-----|
| **agents/types.py** | Agent 類型定義（FOLLOWER, EXPLORER, LEADER, PREDATOR）與行為參數 | 54 | ✅ |
| **spatial/grid.py** | O(N) 空間網格加速結構（Cell-based neighbor search） | 206 | ✅ |
| **spatial/group_detection.py** | Label Propagation 群體偵測演算法 | 291 | ✅ |
| **behaviors/foraging.py** | 覓食行為（搜尋資源、消耗、能量管理） | 178 | ✅ |
| **behaviors/predation.py** | 捕食行為（搜尋獵物、攻擊、生死狀態） | 149 | ✅ |
| **flocking_3d.py** | 基礎物理引擎（Morse, Rayleigh, Alignment, Verlet） | ~500 | ✅ |
| **flocking_heterogeneous.py** | 主協調器（整合所有模組） | 814 | ✅ |
| **resources.py** | 資源系統（可消耗、可再生） | ~240 | ✅ |
| **obstacles.py** | 障礙物系統（SDF-based collision） | ~220 | ✅ |

---

## 所需知識與技能

### 必備知識（Required）

#### 1. Python 程式設計 ⭐⭐⭐⭐⭐

**範圍**：
- 物件導向程式設計（OOP）：類別、繼承、Mixin
- 型別提示（Type Hints）：`dataclass`, `List`, `Tuple`, `Optional`
- NumPy：陣列操作、向量化運算
- Asyncio：非同步程式設計（用於 WebSocket）

**學習資源**：
- [Python Official Tutorial](https://docs.python.org/3/tutorial/)
- [NumPy User Guide](https://numpy.org/doc/stable/user/)
- [Real Python - OOP](https://realpython.com/python3-object-oriented-programming/)

---

#### 2. Taichi 程式設計 ⭐⭐⭐⭐

**範圍**：
- `@ti.data_oriented` 裝飾器
- `@ti.kernel` 與 `@ti.func` 差異
- Taichi fields：`ti.field()`, `ti.Vector.field()`
- 平行化：`for i in self.x` 自動平行化
- 限制：不可使用 Python 標準庫、動態型別檢查

**核心概念**：
```python
@ti.data_oriented
class MySystem:
    def __init__(self, N):
        # Taichi fields: GPU 上的資料結構
        self.x = ti.Vector.field(3, dtype=ti.f32, shape=N)
        self.v = ti.Vector.field(3, dtype=ti.f32, shape=N)
    
    @ti.kernel
    def update(self):
        """
        @ti.kernel: 在 GPU 上執行的函式
        - 自動平行化
        - 不可呼叫 Python 函式（除了其他 @ti.kernel）
        - 不可使用動態型別
        """
        for i in self.x:  # 平行迴圈
            self.v[i] += ti.math.vec3(0, -9.8, 0) * 0.01
            self.x[i] += self.v[i] * 0.01
    
    @ti.func
    def helper_function(self, a: ti.f32) -> ti.f32:
        """
        @ti.func: 可在 @ti.kernel 中呼叫
        - 會被內聯（inline）
        - 不可獨立執行
        """
        return a * 2.0
```

**學習資源**：
- [Taichi Documentation](https://docs.taichi-lang.org/)
- [Taichi GitHub Examples](https://github.com/taichi-dev/taichi/tree/master/python/taichi/examples)

---

#### 3. 物理模擬基礎 ⭐⭐⭐

**範圍**：
- **力學**：牛頓運動定律、作用力/反作用力
- **數值積分**：Euler method, Velocity Verlet
- **週期邊界條件（PBC）**：最小映像法（Minimum Image Convention）

**核心公式**：

**Morse Potential**（短程排斥 + 長程吸引）：
```
F_morse = Cr * exp(-r/lr) - Ca * exp(-r/la)
```

**Cucker-Smale Alignment**（速度對齊）：
```
F_align = (β/N) * Σ_j (v_j - v_i) / (1 + r_ij²)
```

**Velocity Verlet Integration**（二階精度）：
```
# Step 1: 預測位置
v_half = v + 0.5 * F/m * dt
x_new = x + v_half * dt

# Step 2: 更新速度（使用新位置的力）
v_new = v_half + 0.5 * F_new/m * dt
```

**學習資源**：
- [Physics-Based Simulation (ETH Zurich)](https://cgl.ethz.ch/teaching/simulation/)
- [The Art of Molecular Dynamics Simulation](https://www.cambridge.org/core/books/art-of-molecular-dynamics-simulation/)

---

### 進階知識（Recommended）

#### 4. 集體行為理論 ⭐⭐⭐

**範圍**：
- Vicsek Model：角度 noise 對集體運動的影響
- Order-Disorder Transition：相變現象
- Metric vs Topological Interaction：基於距離 vs 基於鄰居數量

**關鍵指標**：
- **Polarization** `P = |Σv_i| / Σ|v_i|`：方向一致性（0=混亂，1=對齊）
- **Radius of Gyration** `Rg`：群體緊密程度
- **Clustering Coefficient**：局部連通性

**學習資源**：
- Vicsek et al., "Novel type of phase transition in a system of self-driven particles" (1995)
- Cucker & Smale, "Emergent Behavior in Flocks" (2007)

---

#### 5. 空間資料結構 ⭐⭐⭐

**範圍**：
- **Spatial Grid (Cell List)**：O(N²) → O(N)
- **Quadtree / Octree**：動態空間分割
- **K-d Tree**：範圍搜尋

**本專案實作**：Spatial Grid (Cell List)

```python
# 原理：將空間分割為立方體網格
cell_size = 2 * r_cutoff
grid_nx = ceil(box_size / cell_size)
total_cells = grid_nx³

# Agent i 所在的 cell
cell_id = floor(x_i / cell_size)

# 只需搜尋 27 個鄰近 cells（3x3x3）
for neighbor_cell in adjacent_27_cells(cell_id):
    for j in agents_in_cell(neighbor_cell):
        if distance(i, j) < r_cutoff:
            compute_force(i, j)
```

**學習資源**：
- [Spatial Data Structures (Stanford CS166)](http://web.stanford.edu/class/cs166/)

---

#### 6. 群體偵測演算法 ⭐⭐

**範圍**：
- **Label Propagation**：迭代式標籤傳播
- **DBSCAN**：基於密度的聚類
- **Connected Components**：圖論方法

**本專案實作**：Label Propagation

```python
# 演算法流程
for iteration in range(5):
    for agent_i in all_agents:
        # 1. 找到空間 + 速度上接近的鄰居
        neighbors = find_neighbors(
            r_cluster=5.0,        # 空間距離閾值
            theta_cluster=π/6     # 速度夾角閾值（30度）
        )
        
        # 2. 採用最常見的群體 ID
        most_common_label = mode(neighbor_labels)
        agent_i.group_id = most_common_label
```

**學習資源**：
- [Scikit-learn Clustering](https://scikit-learn.org/stable/modules/clustering.html)

---

### 軟體工程技能（Essential）

#### 7. 版本控制（Git） ⭐⭐⭐⭐

**必備操作**：
```bash
# 分支管理
git checkout -b feature/new-module
git commit -m "feat: add perception module"
git push origin feature/new-module

# 審查變更
git diff
git status
git log --oneline --graph

# 合併
git merge main
git rebase main  # 保持線性歷史
```

---

#### 8. 測試驅動開發（TDD） ⭐⭐⭐

**測試金字塔**：
```
       ┌───────────────┐
       │  E2E Tests    │  少量（整合測試）
       ├───────────────┤
       │  Integration  │  適量（模組間互動）
       ├───────────────┤
       │  Unit Tests   │  大量（單一功能）
       └───────────────┘
```

**範例**：
```python
# tests/test_spatial_grid.py
def test_grid_assigns_agents_correctly():
    """驗證 agents 被正確分配到網格中"""
    system = TestSystem(N=100)
    system.assign_agents_to_grid()
    
    # 驗證：每個 agent 的 cell_id 對應其位置
    for i in range(system.N):
        pos = system.x[i]
        expected_cell = floor(pos / system.cell_size)
        assert system.agent_cell_id[i] == expected_cell

def test_neighbor_search_correctness():
    """驗證鄰居搜尋與暴力法結果一致"""
    # ... 實作
```

**執行測試**：
```bash
# 全部測試
pytest tests/ -v

# 單一檔案
pytest tests/test_spatial_grid.py -v

# 覆蓋率報告
pytest --cov=src tests/
```

---

#### 9. 效能分析（Profiling） ⭐⭐⭐

**工具**：
- **cProfile**：Python 函式呼叫分析
- **line_profiler**：逐行效能分析
- **Taichi Profiler**：Kernel 效能分析

**範例**：
```python
import cProfile
import pstats

# 分析模擬效能
profiler = cProfile.Profile()
profiler.enable()

for _ in range(1000):
    system.step(dt=0.05)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(20)  # 顯示前 20 個最耗時函式
```

---

#### 10. 文檔撰寫 ⭐⭐⭐

**規範**：
- **Docstring**：使用 Google Style
- **README**：快速開始、範例、API 參考
- **CHANGELOG**：記錄每次變更

**範例**：
```python
def compute_forces(self):
    """
    計算所有作用力（Morse + Alignment + Rayleigh friction）
    
    Forces:
        - Morse potential: 短程排斥 + 長程吸引
        - Cucker-Smale alignment: 速度對齊力
        - Rayleigh friction: 定速機制
    
    Notes:
        使用空間網格加速（O(N) 平均複雜度）
        
    See Also:
        - SpatialGridMixin.assign_agents_to_grid()
        - Flocking3D.verlet_step1()
    """
```

---

## 開發工作流程

### 1. 環境設定

```bash
# 安裝 uv（推薦的 Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆專案
git clone <repository-url>
cd alife

# 安裝依賴
uv pip install taichi numpy pytest

# 驗證安裝
uv run python -c "import taichi as ti; ti.init(arch=ti.cpu); print('Taichi OK')"
```

---

### 2. 開發新功能（範例：新增 Mixin）

#### Step 1: 規劃

- 定義模組職責（單一職責原則）
- 識別與其他模組的依賴關係
- 設計 API（公開方法、參數）

#### Step 2: 實作

**檔案結構**：
```
src/
└── new_module/
    ├── __init__.py
    └── feature.py
```

**程式碼範例**：
```python
# src/new_module/feature.py
import taichi as ti

@ti.data_oriented
class NewFeatureMixin:
    """新功能模組"""
    
    def init_new_feature(self, N: int, param1: float):
        """
        初始化新功能
        
        Args:
            N: Agent 數量
            param1: 功能參數
        """
        self.feature_field = ti.field(dtype=ti.f32, shape=N)
        self.param1 = param1
    
    @ti.kernel
    def compute_new_feature(self):
        """計算新功能（在 GPU 上執行）"""
        for i in self.feature_field:
            # 實作邏輯
            self.feature_field[i] = ti.sin(self.x[i].x) * self.param1
```

#### Step 3: 整合到主類別

```python
# src/flocking_heterogeneous.py
from new_module.feature import NewFeatureMixin

class HeterogeneousFlocking3D(
    ...,
    NewFeatureMixin,  # 加入繼承
):
    def __init__(self, ...):
        super().__init__(...)
        self.init_new_feature(N, param1=1.0)  # 呼叫初始化
    
    def step(self, dt):
        # ... 既有邏輯
        self.compute_new_feature()  # 加入新功能
```

#### Step 4: 測試

```python
# tests/test_new_feature.py
import pytest
from new_module.feature import NewFeatureMixin
from flocking_3d import Flocking3D, FlockingParams

class TestNewFeature(Flocking3D, NewFeatureMixin):
    def __init__(self, N):
        super().__init__(N, FlockingParams())
        self.init_new_feature(N, param1=2.0)

def test_feature_initialization():
    """驗證初始化正確"""
    system = TestNewFeature(N=10)
    assert system.param1 == 2.0

def test_feature_computation():
    """驗證計算正確"""
    system = TestNewFeature(N=10)
    system.compute_new_feature()
    # 驗證結果...
```

#### Step 5: 文檔

更新以下文件：
- `README.md`：新增功能說明
- `docs/API.md`：新增 API 參考
- `CHANGELOG.md`：記錄變更

---

### 3. 提交變更

```bash
# 1. 確保測試通過
pytest tests/ -v

# 2. 提交變更
git add src/new_module/ tests/test_new_feature.py
git commit -m "feat: add new feature module

- Implement NewFeatureMixin
- Add unit tests (5 tests)
- Update API documentation"

# 3. 推送到遠端
git push origin feature/new-module
```

---

## 常見開發任務

### 任務 1: 新增 Agent 類型

**檔案**：`src/agents/types.py`

```python
# 1. 新增 enum
class AgentType(IntEnum):
    # ... 既有類型
    NEW_TYPE = 4  # 新類型

# 2. 定義行為參數
DEFAULT_PROFILES[AgentType.NEW_TYPE] = AgentTypeProfile(
    beta=1.2,
    eta=0.15,
    v0=1.1,
    color=(0.5, 0.5, 0.5)  # 灰色
)
```

**測試**：
```python
def test_new_agent_type():
    agent_types = [AgentType.NEW_TYPE] * 10
    system = HeterogeneousFlocking3D(N=10, params, agent_types)
    system.initialize(box_size=50.0)
    
    # 驗證參數正確應用
    # ...
```

---

### 任務 2: 調整物理參數

**檔案**：`src/flocking_3d.py`

```python
# 修改預設參數
@dataclass
class FlockingParams:
    beta: float = 1.5  # 原本 0.1，增強對齊
    eta: float = 0.05  # 原本 0.0，加入 noise
```

**驗證**：
```bash
# 執行視覺化觀察變化
uv run python experiments/demo_3d.py
```

---

### 任務 3: 最佳化效能

**流程**：

1. **效能分析**：
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()
system.run(steps=1000, dt=0.05)
profiler.disable()
profiler.print_stats(sort='cumtime')
```

2. **識別瓶頸**（常見問題）：
   - ❌ 過多的 Python-Taichi 邊界跨越
   - ❌ 未使用空間加速（O(N²) neighbor search）
   - ❌ 頻繁的 GPU-CPU 資料傳輸

3. **優化策略**：
   - ✅ 合併多個 `@ti.kernel` 減少 launch overhead
   - ✅ 使用空間網格（已實作）
   - ✅ 減少 `to_numpy()` 呼叫頻率

---

### 任務 4: 除錯技巧

#### 4.1 Taichi Kernel 除錯

```python
@ti.kernel
def debug_kernel(self):
    for i in self.x:
        # 使用 print 除錯（會在 console 顯示）
        if i == 0:
            print(f"Agent 0: pos={self.x[i]}, vel={self.v[i]}")
```

#### 4.2 視覺化除錯

```python
# 匯出狀態到 NumPy
positions, velocities = system.get_state()

# 使用 Matplotlib 視覺化
import matplotlib.pyplot as plt
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2])
plt.show()
```

#### 4.3 單元測試隔離問題

```bash
# 只執行失敗的測試
pytest tests/test_spatial_grid.py::test_neighbor_search -v

# 使用 pdb 除錯
pytest tests/test_spatial_grid.py::test_neighbor_search --pdb
```

---

## 進階主題

### 1. 覆寫 Mixin 行為

**範例**：排除特定 agent 類型的群體偵測

```python
class CustomFlocking(HeterogeneousFlocking3D):
    @ti.kernel
    def detect_groups_iteration(self, r_cluster: ti.f32, theta_cluster: ti.f32):
        """覆寫父類別方法：排除 EXPLORER"""
        for i in self.x:
            # 自訂邏輯
            if self.agent_type[i] == AgentType.EXPLORER:
                self.group_id[i] = -1
                continue
            
            # 呼叫原始邏輯（複製自 GroupDetectionMixin）
            # ... 或重新實作
```

---

### 2. 動態參數調整

```python
# 執行時修改參數（無需重新初始化）
system.params.beta = 2.0       # 增強對齊
system.params.eta = 0.3        # 增加 noise
system.goal_strength[None] = 5.0  # 增強目標導向
```

---

### 3. 自訂資源行為

```python
# 實作有限資源（耗盡後消失）
class FiniteResourceSystem(ResourceSystem):
    @ti.kernel
    def consume_step(self, agent_positions):
        for i in agent_positions:
            # ... 消耗邏輯
            if self.amount[res_id] <= 0:
                self.active[res_id] = 0  # 標記為非活動
```

---

## 常見問題（FAQ）

### Q1: 如何處理 Taichi 的型別錯誤？

**問題**：`TypeError: expected ti.f32, got float`

**解決**：
```python
# ❌ 錯誤
self.field[i] = 1.0

# ✅ 正確
self.field[i] = ti.f32(1.0)

# 或在 field 定義時指定型別
self.field = ti.field(dtype=ti.f32, shape=N)
```

---

### Q2: Mixin 的 field 找不到？

**問題**：LSP 報錯 `Attribute 'agent_energy' does not exist`

**解釋**：
- 這是 **預期行為**，非錯誤
- Mixin fields 在執行時動態建立
- LSP 無法靜態分析 Taichi fields

**解決**：
- 忽略警告（不影響執行）
- 或使用 `# type: ignore` 註解

---

### Q3: 效能為何比預期慢？

**檢查清單**：
1. ✅ 使用 GPU backend？ `ti.init(arch=ti.gpu)`
2. ✅ 避免頻繁 GPU-CPU 傳輸？（減少 `to_numpy()` 呼叫）
3. ✅ 使用空間加速？（`SpatialGridMixin`）
4. ✅ 避免過深巢狀迴圈？（<3 層）

**Benchmark**：
```bash
uv run python experiments/benchmark_optimized.py
```

---

### Q4: 如何除錯 Kernel 中的邏輯錯誤？

**技巧**：
1. **Print 除錯**：在 kernel 中使用 `print()`
2. **視覺化**：匯出中間結果到 NumPy，用 Matplotlib 檢視
3. **單元測試**：隔離測試特定功能
4. **簡化問題**：減少 N 到 5-10，手動驗證

---

## 參考資源

### 官方文檔

- [Taichi Documentation](https://docs.taichi-lang.org/)
- [NumPy Documentation](https://numpy.org/doc/stable/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

### 專案文檔

- [README.md](../README.md) - 快速開始
- [API.md](API.md) - 完整 API 參考
- [REFACTORING_REPORT.md](REFACTORING_REPORT.md) - 架構設計細節
- [PHASE_6_PLAN.md](PHASE_6_PLAN.md) - 未來規劃

### 學術論文

- Vicsek et al., "Novel type of phase transition in a system of self-driven particles", PRL 1995
- Cucker & Smale, "Emergent Behavior in Flocks", TAM 2007
- Reynolds, "Flocks, herds and schools: A distributed behavioral model", SIGGRAPH 1987

---

## 貢獻指南

### 提交 Pull Request

1. **Fork 專案** → 建立分支 → 實作功能
2. **撰寫測試**：確保覆蓋率 > 80%
3. **通過 CI**：所有測試必須通過
4. **更新文檔**：同步更新 API 文件
5. **Code Review**：回應 reviewer 意見

### Commit Message 規範

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**範例**：
```
feat(perception): add FOV filtering mixin

- Implement PerceptionMixin with is_in_fov() method
- Integrate with compute_forces() for neighbor filtering
- Add unit tests (5 tests, 100% coverage)

Closes #42
```

**Type**：
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔更新
- `refactor`: 重構（不改變功能）
- `test`: 測試
- `perf`: 效能優化

---

## 專案路線圖

### Phase 5 ✅ 完成（2026-02-07）

- ✅ 模組化重構（-34% 主檔案大小）
- ✅ 6 個獨立模組（agents, spatial, behaviors）
- ✅ 完整測試與文檔

### Phase 6 🚀 規劃中

- ⏳ PerceptionMixin（FOV filtering）
- ⏳ NavigationMixin（Goal-seeking）
- ⏳ 進一步降低主檔案 26%（814 → ~600 lines）

### Phase 7+ 💡 未來

- WebGPU 前端整合
- 更多 Agent 類型（Scavenger, Guardian, etc.）
- 3D 障礙物視覺化
- 參數自動調優（Bayesian Optimization）

---

**最後更新**：2026-02-07  
**維護者**：專案團隊  
**問題回報**：GitHub Issues
