# API 參考文件

本文件提供 3D Heterogeneous Flocking Simulation 的完整 API 參考。

---

## 目錄

- [核心系統](#核心系統)
  - [HeterogeneousFlocking3D](#heterogeneousflocking3d)
  - [Flocking3D](#flocking3d)
  - [FlockingParams](#flockingparams)
- [Agent 類型系統](#agent-類型系統)
  - [AgentType](#agenttype)
  - [AgentTypeProfile](#agenttypeprofile)
- [空間模組](#空間模組)
  - [SpatialGridMixin](#spatialgridmixin)
  - [GroupDetectionMixin](#groupdetectionmixin)
- [行為模組](#行為模組)
  - [ForagingBehaviorMixin](#foragingbehaviormixin)
  - [PredationBehaviorMixin](#predationbehaviormixin)
- [資源系統](#資源系統)
  - [ResourceSystem](#resourcesystem)
  - [ResourceConfig](#resourceconfig)
- [障礙物系統](#障礙物系統)
  - [ObstacleSystem](#obstaclesystem)

---

## 核心系統

### HeterogeneousFlocking3D

**檔案**: `src/flocking_heterogeneous.py`

異質性集群模擬系統，整合物理引擎、空間加速、群體偵測、覓食與捕食行為。

#### 建構子

```python
HeterogeneousFlocking3D(
    N: int,
    params: FlockingParams,
    agent_types: List[AgentType],
    max_groups: int = 32,
    max_resources: int = 32,
    max_obstacles: int = 32,
)
```

**參數**：
- `N` (int): Agent 數量
- `params` (FlockingParams): 物理參數配置
- `agent_types` (List[AgentType]): 每個 agent 的類型（長度必須為 N）
- `max_groups` (int): 最大群體數量（預設 32）
- `max_resources` (int): 最大資源數量（預設 32）
- `max_obstacles` (int): 最大障礙物數量（預設 32）

**範例**：
```python
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

params = FlockingParams(beta=1.0, eta=0.1, box_size=50.0)
agent_types = [AgentType.FOLLOWER] * 80 + [AgentType.EXPLORER] * 20

system = HeterogeneousFlocking3D(
    N=100,
    params=params,
    agent_types=agent_types,
    max_groups=16
)
```

---

#### 主要方法

##### `initialize(box_size: float, seed: int = None)`

初始化系統狀態（隨機位置與速度）。

**參數**：
- `box_size` (float): 初始化範圍 `[-box_size/2, +box_size/2]³`
- `seed` (int, optional): 隨機種子（可重現性）

**範例**：
```python
system.initialize(box_size=50.0, seed=42)
```

---

##### `step(dt: float)`

執行單步模擬（物理更新 + 生態互動 + 群體偵測）。

**參數**：
- `dt` (float): 時間步長（建議 0.01-0.1）

**執行流程**：
1. 更新空間網格索引
2. 尋找最近資源與獵物
3. Velocity Verlet 物理積分
4. 消耗資源、執行攻擊
5. 資源再生
6. 週期性群體偵測（每 10 步）

**範例**：
```python
for _ in range(1000):
    system.step(dt=0.05)
```

---

##### `add_resource(config: ResourceConfig) -> int`

新增資源到系統中。

**參數**：
- `config` (ResourceConfig): 資源配置（位置、數量、半徑等）

**返回**：
- `int`: 資源 ID（-1 表示失敗）

**範例**：
```python
from resources import ResourceConfig
import numpy as np

config = ResourceConfig(
    position=np.array([10.0, 0.0, 5.0]),
    amount=100.0,
    radius=3.0,
    replenish_rate=2.0,
    max_amount=150.0
)
resource_id = system.add_resource(config)
```

---

##### `get_state() -> Tuple[np.ndarray, np.ndarray]`

獲取當前系統狀態。

**返回**：
- `positions` (np.ndarray): 形狀 `(N, 3)` 的位置陣列
- `velocities` (np.ndarray): 形狀 `(N, 3)` 的速度陣列

**範例**：
```python
positions, velocities = system.get_state()
print(f"Agent 0 位置: {positions[0]}")
print(f"Agent 0 速度: {velocities[0]}")
```

---

##### `get_all_groups() -> List[dict]`

獲取所有檢測到的群體資訊。

**返回**：
- `List[dict]`: 每個群體的統計資料
  - `group_id` (int): 群體 ID
  - `size` (int): 群體成員數量
  - `centroid` (np.ndarray): 群體中心位置 `(3,)`
  - `mean_velocity` (np.ndarray): 群體平均速度 `(3,)`
  - `radius` (float): 群體半徑

**範例**：
```python
groups = system.get_all_groups()
for group in groups:
    print(f"群體 {group['group_id']}: {group['size']} 個成員")
    print(f"  中心: {group['centroid']}")
    print(f"  半徑: {group['radius']:.2f}")
```

---

##### `get_alive_count() -> int`

獲取存活 agent 數量。

**範例**：
```python
alive = system.get_alive_count()
print(f"{alive}/{system.N} agents 存活")
```

---

##### `get_predator_count() -> int`

獲取捕食者數量。

---

##### `get_prey_count() -> int`

獲取獵物數量（非捕食者）。

---

### Flocking3D

**檔案**: `src/flocking_3d.py`

基礎 3D 集群物理引擎（Morse potential + Rayleigh friction + Cucker-Smale alignment）。

#### 建構子

```python
Flocking3D(N: int, params: FlockingParams)
```

**參數**：
- `N` (int): Agent 數量
- `params` (FlockingParams): 物理參數

---

#### 主要方法

##### `compute_forces()`

計算所有作用力（Morse potential + Alignment force + Rayleigh friction）。

---

##### `verlet_step1(dt: float)`

Velocity Verlet 第一階段（預測位置）。

---

##### `verlet_step2(dt: float)`

Velocity Verlet 第二階段（更新速度）。

---

##### `compute_diagnostics() -> dict`

計算診斷指標。

**返回**：
- `dict`:
  - `mean_speed` (float): 平均速率
  - `std_speed` (float): 速率標準差
  - `Rg` (float): Radius of gyration
  - `polarization` (float): 極化度 `P = |Σv| / Σ|v|`

**範例**：
```python
diag = system.compute_diagnostics()
print(f"Rg: {diag['Rg']:.2f}, P: {diag['polarization']:.3f}")
```

---

### FlockingParams

**檔案**: `src/flocking_3d.py`

物理參數配置（dataclass）。

#### 參數列表

```python
@dataclass
class FlockingParams:
    # Morse Potential
    Ca: float = 1.5         # 吸引強度
    Cr: float = 2.0         # 排斥強度
    la: float = 2.5         # 吸引長度尺度
    lr: float = 0.5         # 排斥長度尺度
    rc: float = 15.0        # 截斷半徑
    
    # Rayleigh Friction
    alpha: float = 2.0      # 摩擦係數
    v0: float = 1.0         # 目標速度
    
    # Alignment
    beta: float = 0.1       # 對齊強度（0=無對齊，2.0=強對齊）
    
    # Noise
    eta: float = 0.0        # Vicsek noise 強度（弧度）
    
    # Boundary
    box_size: float = 50.0  # 邊界尺寸
    boundary_mode: str = "pbc"  # "pbc" / "reflective" / "absorbing"
    wall_stiffness: float = 10.0  # 反射壁面剛度
```

**範例**：
```python
# 高對齊配置
params = FlockingParams(
    beta=2.0,
    alpha=1.5,
    eta=0.1,
    boundary_mode="pbc"
)

# 混亂配置
params = FlockingParams(
    beta=0.0,
    alpha=3.0,
    eta=0.3,
    boundary_mode="reflective"
)
```

---

## Agent 類型系統

### AgentType

**檔案**: `src/agents/types.py`

Agent 類型枚舉。

```python
from enum import IntEnum

class AgentType(IntEnum):
    FOLLOWER = 0   # 跟隨者：高對齊、低 noise
    EXPLORER = 1   # 探索者：低對齊、高 noise、高速
    LEADER = 2     # 領導者：中等對齊、低 noise、有目標
    PREDATOR = 3   # 捕食者：無對齊、中等 noise、高速
```

**範例**：
```python
from agents.types import AgentType

agent_types = [
    AgentType.FOLLOWER,
    AgentType.EXPLORER,
    AgentType.PREDATOR
]
```

---

### AgentTypeProfile

**檔案**: `src/agents/types.py`

Agent 行為參數配置（dataclass）。

```python
@dataclass
class AgentTypeProfile:
    beta: float    # 對齊強度倍數（相對於基準值）
    eta: float     # Noise 強度（弧度）
    v0: float      # 目標速度倍數
    color: Tuple[float, float, float]  # 視覺化顏色 (RGB)
```

**預設配置**：
```python
DEFAULT_PROFILES = {
    AgentType.FOLLOWER: AgentTypeProfile(
        beta=1.5,   # 高對齊
        eta=0.05,   # 低 noise
        v0=1.0,     # 標準速度
        color=(0.3, 0.7, 1.0)  # 藍色
    ),
    AgentType.EXPLORER: AgentTypeProfile(
        beta=0.5,   # 低對齊
        eta=0.3,    # 高 noise
        v0=1.3,     # 高速
        color=(1.0, 0.8, 0.2)  # 黃色
    ),
    AgentType.LEADER: AgentTypeProfile(
        beta=1.0,   # 中等對齊
        eta=0.1,    # 低 noise
        v0=1.0,     # 標準速度
        color=(0.2, 1.0, 0.3)  # 綠色
    ),
    AgentType.PREDATOR: AgentTypeProfile(
        beta=0.0,   # 無對齊
        eta=0.1,    # 中等 noise
        v0=1.3,     # 高速
        color=(1.0, 0.2, 0.2)  # 紅色
    ),
}
```

---

## 空間模組

### SpatialGridMixin

**檔案**: `src/spatial/grid.py`

空間網格加速結構（O(N) neighbor search）。

#### 初始化

```python
def init_spatial_grid(
    self,
    N: int,
    box_size: float,
    cell_size: float = 5.0
):
    """
    初始化空間網格結構
    
    Args:
        N: Agent 數量
        box_size: 空間尺寸
        cell_size: 網格單元大小（建議 = 2 * rc）
    """
```

**自動呼叫**：由 `HeterogeneousFlocking3D.__init__()` 自動呼叫

---

#### 主要方法

##### `assign_agents_to_grid()`

**Taichi kernel**：將所有 agent 分配到對應的空間網格。

**說明**：
- 根據 agent 位置計算 cell ID
- 更新 `agent_cell_id` field
- 在 `step()` 中自動呼叫

---

##### `get_cell_id(pos: ti.math.vec3) -> int`

**Taichi func**：計算位置對應的 cell ID。

**參數**：
- `pos` (vec3): 3D 位置

**返回**：
- `int`: Cell ID（線性索引）

---

### GroupDetectionMixin

**檔案**: `src/spatial/group_detection.py`

Label Propagation 群體偵測演算法。

#### 初始化

```python
def init_group_detection(
    self,
    N: int,
    max_groups: int = 32
):
    """
    初始化群體偵測系統
    
    Args:
        N: Agent 數量
        max_groups: 最大群體數量
    """
```

---

#### 主要方法

##### `update_groups()`

執行完整群體偵測（迭代式 Label Propagation）。

**流程**：
1. 執行 5 次迭代（`detect_groups_iteration()`）
2. 計算群體統計（`compute_group_statistics()`）

**說明**：在 `step()` 中每 10 步自動呼叫一次

---

##### `detect_groups_iteration(r_cluster: float, theta_cluster: float)`

**Taichi kernel**：單次 Label Propagation 迭代。

**參數**：
- `r_cluster` (float): 空間距離閾值
- `theta_cluster` (float): 速度夾角閾值（弧度）

**覆寫**：子類別可覆寫此方法以客製化行為（例如排除特定類型 agent）

---

##### `compute_group_statistics()`

**Taichi kernel**：計算每個群體的統計資料（大小、中心、速度、半徑）。

---

## 行為模組

### ForagingBehaviorMixin

**檔案**: `src/behaviors/foraging.py`

覓食行為與能量管理。

#### 初始化

```python
def init_foraging(
    self,
    N: int,
    resources: ResourceSystem,
    energy_threshold: float = 30.0,
    initial_energy: float = 100.0
):
    """
    初始化覓食系統
    
    Args:
        N: Agent 數量
        resources: 資源系統實例
        energy_threshold: 低能量閾值（觸發覓食）
        initial_energy: 初始能量
    """
```

---

#### 主要方法

##### `find_nearest_resources()`

**Taichi kernel**：為低能量 agent 尋找最近的資源。

**更新**：
- `agent_target` field：目標資源位置
- `agent_has_target` field：是否鎖定資源

---

##### `consume_resources_step()`

**Taichi kernel**：消耗資源、更新能量。

**流程**：
1. 扣除每步基礎能量消耗
2. 檢查是否在資源範圍內
3. 從資源消耗、增加 agent 能量
4. 標記能量耗盡的 agent

---

##### `get_starved_count() -> int`

獲取餓死的 agent 數量。

---

### PredationBehaviorMixin

**檔案**: `src/behaviors/predation.py`

捕食行為與生死狀態管理。

#### 初始化

```python
def init_predation(
    self,
    N: int,
    attack_radius: float = 2.0
):
    """
    初始化捕食系統
    
    Args:
        N: Agent 數量
        attack_radius: 攻擊範圍
    """
```

---

#### 主要方法

##### `find_nearest_prey()`

**Taichi kernel**：為捕食者尋找最近的獵物。

**更新**：
- `agent_target` field：目標獵物位置
- `agent_has_target` field：是否鎖定獵物

---

##### `attack_prey_step()`

**Taichi kernel**：執行攻擊、更新生死狀態。

**流程**：
1. 捕食者移動至獵物位置
2. 在攻擊範圍內時殺死獵物
3. 記錄最後攻擊時間

---

##### `get_alive_count() -> int`

獲取存活 agent 數量。

---

## 資源系統

### ResourceSystem

**檔案**: `src/resources.py`

資源管理系統（可消耗 + 可再生）。

#### 建構子

```python
ResourceSystem(max_resources: int = 32)
```

---

#### 主要方法

##### `add_resource(config: ResourceConfig) -> int`

新增資源。

**返回**：資源 ID（-1 表示已達上限）

---

##### `remove_resource(resource_id: int)`

移除資源。

---

##### `regenerate_step()`

**Taichi kernel**：執行資源再生（根據 `replenish_rate`）。

---

##### `get_active_resources() -> List[dict]`

獲取所有活動資源的資訊。

**返回**：
- `List[dict]`:
  - `id` (int)
  - `position` (np.ndarray)
  - `amount` (float)
  - `radius` (float)

---

### ResourceConfig

**檔案**: `src/resources.py`

資源配置（dataclass）。

```python
@dataclass
class ResourceConfig:
    position: np.ndarray      # (3,) 位置
    amount: float = 100.0     # 資源數量
    radius: float = 2.0       # 採集範圍
    replenish_rate: float = 0.0  # 每步補充量（0=不再生）
    max_amount: float = 100.0    # 最大數量上限
```

**範例**：
```python
# 可消耗資源（不再生）
config = ResourceConfig(
    position=np.array([10.0, 0.0, 0.0]),
    amount=100.0,
    radius=3.0,
    replenish_rate=0.0
)

# 可再生資源
config = ResourceConfig(
    position=np.array([0.0, 10.0, 0.0]),
    amount=100.0,
    radius=3.0,
    replenish_rate=2.0,
    max_amount=200.0
)
```

---

## 障礙物系統

### ObstacleSystem

**檔案**: `src/obstacles.py`

SDF-based 障礙物系統（Sphere / Box / Cylinder）。

#### 建構子

```python
ObstacleSystem(max_obstacles: int = 32)
```

---

#### 主要方法

##### `add_sphere(center: np.ndarray, radius: float) -> int`

新增球形障礙物。

---

##### `add_box(center: np.ndarray, size: np.ndarray) -> int`

新增立方體障礙物。

**參數**：
- `size` (np.ndarray): 半邊長 `(3,)`

---

##### `add_cylinder(center: np.ndarray, radius: float, height: float, axis: int = 1) -> int`

新增圓柱體障礙物。

**參數**：
- `axis` (int): 軸向（0=X, 1=Y, 2=Z）

---

##### `compute_obstacle_force(pos: ti.math.vec3, stiffness: float) -> ti.math.vec3`

**Taichi func**：計算障礙物排斥力（基於 SDF 梯度）。

---

## 範例：完整工作流程

```python
import numpy as np
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams
from resources import ResourceConfig

# 1. 建立系統
N = 100
params = FlockingParams(beta=1.0, eta=0.1, box_size=50.0)
agent_types = (
    [AgentType.FOLLOWER] * 70 +
    [AgentType.EXPLORER] * 20 +
    [AgentType.PREDATOR] * 10
)

system = HeterogeneousFlocking3D(
    N=N,
    params=params,
    agent_types=agent_types,
    max_groups=16,
    max_resources=5
)

# 2. 初始化
system.initialize(box_size=50.0, seed=42)

# 3. 新增資源
for i in range(3):
    config = ResourceConfig(
        position=np.random.rand(3) * 50 - 25,
        amount=100.0,
        radius=3.0,
        replenish_rate=2.0,
        max_amount=150.0
    )
    system.add_resource(config)

# 4. 模擬循環
for step in range(1000):
    system.step(dt=0.05)
    
    # 5. 查詢狀態
    if step % 50 == 0:
        positions, velocities = system.get_state()
        groups = system.get_all_groups()
        alive = system.get_alive_count()
        
        print(f"Step {step}: {len(groups)} groups, {alive} alive")
        
        # 診斷指標
        diag = system.compute_diagnostics()
        print(f"  Rg: {diag['Rg']:.2f}, P: {diag['polarization']:.3f}")
```

---

## 進階主題

### 自訂 Agent 類型

```python
from agents.types import AgentType, AgentTypeProfile, DEFAULT_PROFILES

# 定義新類型的行為參數
DEFAULT_PROFILES[AgentType.LEADER] = AgentTypeProfile(
    beta=2.0,       # 更高對齊
    eta=0.05,       # 更低 noise
    v0=1.5,         # 更高速度
    color=(0.0, 1.0, 0.0)  # 綠色
)
```

---

### 覆寫群體偵測邏輯

```python
class CustomFlocking(HeterogeneousFlocking3D):
    @ti.kernel
    def detect_groups_iteration(self, r_cluster: ti.f32, theta_cluster: ti.f32):
        """排除 EXPLORER 和 PREDATOR"""
        for i in self.x:
            if self.agent_type[i] in [1, 3]:  # EXPLORER or PREDATOR
                self.group_id[i] = -1
                continue
            
            # ... 其餘 Label Propagation 邏輯
```

---

### 動態參數調整

```python
# 執行時修改物理參數
system.params.beta = 2.0   # 增強對齊
system.params.eta = 0.2    # 增加 noise

# 修改資源再生率
system.resources.replenish_rate[0] = 5.0
```

---

## 效能建議

1. **N ≤ 1000**：使用 `HeterogeneousFlocking3D`（O(N²) 可接受）
2. **N > 5000**：考慮實驗性 `flocking_celllist.py`（O(N)）
3. **時間步長**：建議 `dt=0.05`（平衡精度與速度）
4. **群體偵測頻率**：預設每 10 步（可調整 `group_detection_interval`）
5. **空間網格大小**：`cell_size ≈ 2 * rc`（最佳鄰域搜尋）

---

## 疑難排解

### 問題：數值爆炸

**症狀**：位置/速度變成 `NaN` 或 `inf`

**解決**：
- 減少 `dt`（試 0.01）
- 檢查 Morse potential 參數（`Cr` 不要過大）
- 確保初始速度不會過高

---

### 問題：群體無法形成

**症狀**：所有 agent 的 `group_id = -1`

**解決**：
- 增加 `r_cluster`（空間閾值）
- 增加 `theta_cluster`（速度夾角閾值）
- 增強對齊力（`beta`）
- 增加迭代次數（`n_iterations`）

---

### 問題：捕食者無法捕獵

**症狀**：獵物數量不減少

**解決**：
- 確認 `attack_radius` 足夠大
- 確認捕食者速度 ≥ 獵物速度（調整 `v0`）
- 檢查 `agent_alive` field 是否正確初始化

---

## 參考資源

- [使用指南](GUIDE.md) - 完整教學與範例
- [重構報告](REFACTORING_REPORT.md) - 架構設計細節
- [Backend API](../backend/README.md) - WebSocket 介面文件
- [WebGPU 整合](WEBGPU_INTEGRATION_PLAN.md) - 前端架構

---

**最後更新**：2026-02-07  
**版本**：Phase 5（模組化架構）
