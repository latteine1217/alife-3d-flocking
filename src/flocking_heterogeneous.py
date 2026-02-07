"""
Heterogeneous 3D Flocking System - 模組化主控類別

這是一個高度模組化的 3D 異質性群集模擬系統，透過 Mixin 組合模式整合多個功能模組。

核心功能：
    • Agent Types: 支援多種 agent 類型（Follower/Explorer/Leader/Predator）
    • Individual Parameters: 每個 agent 擁有獨立的行為參數
    • Field of View (FOV): 視野限制（可配置角度）
    • Goal-directed Behavior: 目標導向行為
    • Foraging: 覓食與能量管理
    • Predation: 掠食與獵捕行為
    • Group Detection: 基於 Label Propagation 的群組檢測

架構設計：
    • 繼承 Flocking3D 基礎物理引擎
    • 使用 Mixin 模式實現功能模組化
    • 向後相容：可退化為均質系統
    • 每個模組可獨立測試與擴展

重構歷程（Phase 1-4）：
    • Phase 1: Agent Types 提取 → agents/types.py
    • Phase 2: Spatial Grid 提取 → spatial/grid.py
    • Phase 3: Group Detection 提取 → spatial/group_detection.py
    • Phase 4: Behaviors 提取 → behaviors/{foraging,predation}.py
    • Phase 5: 主類別簡化（當前階段）

原始大小：1230 行 → 當前：801 行（-35%）
"""

import taichi as ti
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import IntEnum

# 匯入基礎類別
from flocking_3d import Flocking3D, FlockingParams
from obstacles import ObstacleSystem, ObstacleConfig
from resources import ResourceSystem, ResourceConfig

# 匯入 Agent 類型定義（Phase 1 重構）
from agents.types import AgentType, AgentTypeProfile, DEFAULT_PROFILES

# 匯入 Spatial Grid 與 Group Detection（Phase 2-3 重構）
from spatial.grid import SpatialGridMixin
from spatial.group_detection import GroupDetectionMixin

# 匯入 Behavior Mixins（Phase 4 重構）
from behaviors.foraging import ForagingBehaviorMixin
from behaviors.predation import PredationBehaviorMixin
from behaviors.reproduction import ReproductionBehaviorMixin

# 匯入 Perception Mixin（Phase 6.1 重構）
from perception.fov import PerceptionMixin

# 匯入 Navigation Mixin（Phase 6.2 重構）
from navigation.goal_seeking import NavigationMixin


@ti.data_oriented
class HeterogeneousFlocking3D(
    Flocking3D,
    SpatialGridMixin,
    GroupDetectionMixin,
    ForagingBehaviorMixin,
    PredationBehaviorMixin,
    ReproductionBehaviorMixin,  # Phase 4.3: Reproduction
    PerceptionMixin,  # Phase 6.1: FOV filtering
    NavigationMixin,  # Phase 6.2: Goal-seeking
):
    """
    支援 Agent 異質性的 3D Flocking 系統

    新增功能（相對於 Flocking3D）：
        • Agent Types: 不同類型的 agents（Explorer/Follower/Leader/Predator）
        • Individual Parameters: 每個 agent 獨立的 beta, eta, v0, mass
        • Field of View (FOV): 視野限制（只能看到前方一定角度內的鄰居）
        • Goal-directed Behavior: 目標導向行為
        • Foraging: 覓食與資源消耗
        • Predation: 掠食行為
        • Group Detection: 基於 Label Propagation + Spatial Grid 的群組檢測

    Mixins:
        • SpatialGridMixin: 空間網格加速結構（O(N) 鄰居查詢）
        • GroupDetectionMixin: 群組檢測與統計（Label Propagation 算法）
        • ForagingBehaviorMixin: 覓食與能量管理
        • PredationBehaviorMixin: 掠食與獵捕行為
    """

    def __init__(
        self,
        N: int,
        params: FlockingParams,
        agent_types: Optional[List[int]] = None,
        type_profiles: Optional[Dict[int, AgentTypeProfile]] = None,
        enable_fov: bool = True,
        fov_angle: float = 120.0,
        max_obstacles: int = 32,
        max_groups: int = 32,
        max_resources: int = 32,
        max_agents: int = 200,  # 繁殖系統預分配池大小
        enable_reproduction: bool = True,
    ):
        """
        初始化異質性系統

        Args:
            N: 初始 agent 數量
            params: 基礎物理參數（作為預設值）
            agent_types: 每個 agent 的類型（長度為 N 的列表）
            type_profiles: 類型 profile 字典（覆蓋預設值）
            enable_fov: 是否啟用視野限制
            fov_angle: 視野角度（度數，預設 120 度）
            max_obstacles: 最大障礙物數量
            max_groups: 最大群組數量（用於 group detection）
            max_resources: 最大資源數量（用於 foraging）
            max_agents: 系統最大 agent 容量（預分配池，用於繁殖）
            enable_reproduction: 是否啟用繁殖系統
        """
        # 先初始化父類別（使用 max_agents 作為容量）
        super().__init__(max_agents, params)

        # 記錄實際使用的 agent 數量
        self.N = N
        self.max_agents = max_agents

        # 初始化存活狀態（只有前 N 個是存活的）
        self.agent_alive = ti.field(ti.i32, max_agents)
        alive_arr = np.zeros(max_agents, dtype=np.int32)
        alive_arr[:N] = 1  # 前 N 個存活
        self.agent_alive.from_numpy(alive_arr)

        # ===== Perception (Phase 6.1) =====
        # 初始化感知系統（使用 PerceptionMixin）
        self.init_perception(N=max_agents, fov_angle=fov_angle, enable_fov=enable_fov)

        # ===== Navigation (Phase 6.2) =====
        # 初始化導航系統（使用 NavigationMixin）
        self.init_navigation(N=max_agents)

        # 類型 profiles（使用預設或自訂）
        self.type_profiles = type_profiles if type_profiles else DEFAULT_PROFILES

        # 個體參數 fields（使用 max_agents 作為容量）
        self.beta_individual = ti.field(ti.f32, max_agents)
        self.eta_individual = ti.field(ti.f32, max_agents)
        self.v0_individual = ti.field(ti.f32, max_agents)
        self.v0_base = ti.field(ti.f32, max_agents)  # 基礎速度（不受健康狀態影響）
        self.mass_individual = ti.field(ti.f32, max_agents)
        self.agent_type_field = ti.field(ti.i32, max_agents)  # 重命名避免衝突

        # Agent 類型 numpy array（用於繁殖時複製）
        self.agent_types_np = np.zeros(max_agents, dtype=np.int32)

        # 障礙物系統
        self.obstacles = ObstacleSystem(max_obstacles=max_obstacles)

        # ===== Spatial Grid & Group Detection =====
        # 初始化空間網格（使用 SpatialGridMixin）
        self.init_spatial_grid(
            N=N,
            box_size=params.box_size,
            cell_size=5.0,  # 預設值，與 r_cluster 一致
            max_agents_per_cell=32,
        )

        # 初始化群組檢測系統（使用 GroupDetectionMixin）
        self.init_group_detection(N=N, max_groups=max_groups)

        # 群組檢測頻率控制
        self.group_detection_interval = 5  # 每 5 步檢測一次
        self.step_counter = 0  # 步數計數器

        # ===== Foraging & Predation & Reproduction Behaviors =====
        # 初始化覓食行為（使用 ForagingBehaviorMixin）
        self.init_foraging(
            N=max_agents,
            resources=ResourceSystem(max_resources=max_resources),
            energy_threshold=30.0,
            energy_consumption_rate=0.2,  # 0.1 → 0.2 (基礎消耗提高 2 倍)
            initial_energy=100.0,
        )

        # 初始化掠食行為（使用 PredationBehaviorMixin）
        self.init_predation(N=max_agents)

        # 初始化繁殖行為（使用 ReproductionBehaviorMixin）
        if enable_reproduction:
            self.init_reproduction(
                max_agents=max_agents,
                reproduction_threshold=90.0,
                parent_energy_cost=0.5,
                offspring_energy_ratio=0.3,
                reproduction_cooldown=100,
                spawn_distance=2.0,
            )
            self.enable_reproduction = True
        else:
            self.enable_reproduction = False

        # 初始化 agent 類型與參數
        if agent_types is None:
            # 預設：全部是 FOLLOWER
            agent_types = [AgentType.FOLLOWER] * N

        self._init_agent_types(agent_types)

        # 輸出系統資訊
        type_counts = self._count_types()
        print(f"[HeterogeneousFlocking3D] Agent composition:")
        for atype, count in type_counts.items():
            profile = self.type_profiles[atype]
            print(
                f"  {profile.name}: {count}/{N} "
                f"(beta={profile.beta:.2f}, eta={profile.eta:.2f}, v0={profile.v0:.2f})"
            )
        if enable_fov:
            print(f"  FOV: {fov_angle:.0f} degrees")

    def _init_agent_types(self, agent_types: List[int]):
        """初始化 agent 類型與個體參數"""
        assert len(agent_types) == self.N, "agent_types 長度必須等於 N"

        # 轉換為 numpy arrays（大小 = max_agents，支援 pre-allocated pool）
        beta_arr = np.zeros(self.max_agents, dtype=np.float32)
        eta_arr = np.zeros(self.max_agents, dtype=np.float32)
        v0_arr = np.zeros(self.max_agents, dtype=np.float32)
        mass_arr = np.ones(self.max_agents, dtype=np.float32)  # 預設質量 = 1.0
        goal_strength_arr = np.zeros(self.max_agents, dtype=np.float32)
        hunt_range_arr = np.zeros(self.max_agents, dtype=np.float32)
        attack_range_arr = np.zeros(self.max_agents, dtype=np.float32)
        type_arr = np.zeros(self.max_agents, dtype=np.int32)  # 預設 type = 0 (FOLLOWER)

        # 只填充前 N 個 agents 的數據
        for i, atype in enumerate(agent_types):
            profile = self.type_profiles[atype]
            beta_arr[i] = profile.beta
            eta_arr[i] = profile.eta
            v0_arr[i] = profile.v0
            mass_arr[i] = profile.mass
            goal_strength_arr[i] = profile.goal_strength
            hunt_range_arr[i] = profile.hunt_range
            attack_range_arr[i] = profile.attack_range
            type_arr[i] = atype

        # 上傳到 GPU
        self.beta_individual.from_numpy(beta_arr)
        self.eta_individual.from_numpy(eta_arr)
        self.v0_individual.from_numpy(v0_arr)
        self.v0_base.from_numpy(v0_arr.copy())  # 保存基礎速度
        self.mass_individual.from_numpy(mass_arr)
        self.goal_strength.from_numpy(goal_strength_arr)
        self.predator_hunt_range.from_numpy(hunt_range_arr)
        self.predator_attack_range.from_numpy(attack_range_arr)
        self.agent_type_field.from_numpy(type_arr)  # 使用 agent_type_field

        # 保留 NumPy 陣列供序列化器使用
        self.agent_types_np = type_arr

        # 預設無目標
        self.has_goal.fill(0)

    def initialize(self, box_size: float = None, v_scale: float = 0.1, seed: int = 0):
        """
        初始化粒子位置與速度（覆寫父類別以支援 pre-allocated pool）

        Args:
            box_size: 初始分布範圍 (預設為 box_size * 0.3)
            v_scale: 初始速度尺度
            seed: 隨機種子

        Note:
            只初始化前 N 個 agents（活躍的），剩餘 (max_agents - N) 個保持未初始化狀態
        """
        if box_size is None:
            box_size = self.params.box_size * 0.3

        rng = np.random.default_rng(seed)

        # 創建大小為 max_agents 的陣列，只填充前 N 個
        x_init = np.zeros((self.max_agents, 3), dtype=np.float32)
        v_init = np.zeros((self.max_agents, 3), dtype=np.float32)
        rng_states = np.zeros(self.max_agents, dtype=np.uint32)

        # 只初始化前 N 個 agents
        x_init[: self.N] = rng.uniform(-box_size, box_size, (self.N, 3)).astype(
            np.float32
        )
        v_init[: self.N] = rng.uniform(-v_scale, v_scale, (self.N, 3)).astype(
            np.float32
        )
        rng_states[: self.N] = rng.integers(0, 2**32, size=self.N, dtype=np.uint32)

        self.x.from_numpy(x_init)
        self.v.from_numpy(v_init)
        self.rng_state.from_numpy(rng_states)

    def _count_types(self) -> Dict[int, int]:
        """統計各類型數量（只統計前 N 個活躍 agents）"""
        type_arr = self.agent_type_field.to_numpy()[: self.N]  # 只取前 N 個
        unique, counts = np.unique(type_arr, return_counts=True)
        return dict(zip(unique, counts))

    # Note: set_goals() 和 goal_seeking_force() 現在從 NavigationMixin 繼承

    @ti.kernel
    def compute_forces(self):
        """
        計算所有力（使用個體參數 + FOV + 目標導向）

        修改：
            • 使用 beta_individual[i] 取代全域 beta
            • 加入 FOV 檢查
            • 加入 goal seeking force
        """
        # 清空
        for i in self.f:
            self.f[i] = ti.Vector([0.0, 0.0, 0.0])

        # 讀取參數
        Ca, Cr = self.p[0], self.p[1]
        la, lr = self.p[2], self.p[3]
        rc = self.p[4]

        inv_la, inv_lr = 1.0 / la, 1.0 / lr
        rc2 = rc * rc

        # 主循環
        for i in self.x:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                continue

            xi, vi = self.x[i], self.v[i]
            force = ti.Vector([0.0, 0.0, 0.0])
            v_sum = ti.Vector([0.0, 0.0, 0.0])
            n_neighbors = 0

            # 個體參數
            beta_i = self.beta_individual[i]

            for j in range(self.N):
                if i == j:
                    continue

                rij = self.pbc_dist(xi, self.x[j])
                r2 = rij.dot(rij)

                if r2 < 1e-6 or r2 > rc2:
                    continue

                r = ti.sqrt(r2)
                inv_r = 1.0 / r

                # Morse force（無 FOV 限制，保持物理一致性）
                exp_a = ti.exp(-r * inv_la)
                exp_r = ti.exp(-r * inv_lr)
                coeff = Ca * inv_la * exp_a - Cr * inv_lr * exp_r
                force += coeff * rij * inv_r

                # Alignment force（受 FOV 限制）
                if beta_i > 0.0:
                    # FOV 檢查
                    if self.is_in_fov(vi, rij):
                        v_sum += self.v[j]
                        n_neighbors += 1

            # 儲存 Morse 力
            self.f[i] = force

            # Alignment force
            if beta_i > 0.0 and n_neighbors > 0:
                v_avg = v_sum / ti.cast(n_neighbors, ti.f32)
                self.f[i] += beta_i * (v_avg - vi)

            # Goal seeking force
            self.f[i] += self.goal_seeking_force(i)

            # Resource-seeking force
            target_res = self.agent_target_resource[i]
            if target_res >= 0:
                if self.resources.resource_active[target_res] == 1:
                    res_pos = self.resources.resource_pos[target_res]

                    # 計算方向（考慮 PBC）
                    direction = ti.Vector([0.0, 0.0, 0.0])
                    if self.params.boundary_mode == 0:  # PBC
                        direction = self.pbc_dist(xi, res_pos)
                    else:
                        direction = res_pos - xi

                    dist = direction.norm()

                    if dist > 1e-6:
                        # 施加吸引力（類似 goal force）
                        foraging_strength = 3.0  # 可調整
                        self.f[i] += foraging_strength * (direction / dist)

            # Predator hunting force (掠食者追捕)
            if self.agent_type_field[i] == 3 and self.agent_alive[i] == 1:  # PREDATOR
                target_prey = self.agent_target_prey[i]
                if target_prey >= 0 and self.agent_alive[target_prey] == 1:
                    # 計算方向（考慮 PBC）
                    direction = ti.Vector([0.0, 0.0, 0.0])
                    if self.params.boundary_mode == 0:  # PBC
                        direction = self.pbc_dist(xi, self.x[target_prey])
                    else:
                        direction = self.x[target_prey] - xi

                    dist = direction.norm()

                    if dist > 1e-6:
                        # 強力追捕（比覓食更強）
                        hunt_strength = 5.0
                        self.f[i] += hunt_strength * (direction / dist)

            # Prey escape force (獵物逃跑)
            if self.agent_type_field[i] != 3 and self.agent_alive[i] == 1:  # 非掠食者
                # 檢查附近是否有掠食者
                escape_force = ti.Vector([0.0, 0.0, 0.0])
                escape_range = 15.0  # 逃跑感知範圍

                for j in range(self.N):
                    if (
                        self.agent_type_field[j] == 3 and self.agent_alive[j] == 1
                    ):  # 是掠食者
                        # 計算距離
                        dx = ti.Vector([0.0, 0.0, 0.0])
                        if self.params.boundary_mode == 0:  # PBC
                            dx = self.pbc_dist(xi, self.x[j])
                        else:
                            dx = self.x[j] - xi

                        dist = dx.norm()

                        if dist < escape_range and dist > 1e-6:
                            # 逃跑力與距離成反比（越近越強）
                            escape_strength = 8.0 / (dist + 1.0)
                            escape_force -= escape_strength * (dx / dist)

                self.f[i] += escape_force

            # Obstacle avoidance force
            for obs_id in range(self.obstacles.n_obstacles):
                self.f[i] += self.obstacles.compute_obstacle_force(xi, obs_id)

    @ti.kernel
    def verlet_step2(self, dt: ti.f32):
        """
        Verlet 第二步：使用個體參數

        修改：
            • 使用 mass_individual[i], v0_individual[i], eta_individual[i]
        """
        alpha = self.p[5]

        for i in self.v:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                continue

            # 個體參數
            mass_i = self.mass_individual[i]
            v0_i = self.v0_individual[i]
            eta_i = self.eta_individual[i]

            # 保守力的第二個半步
            a = self.f[i] / mass_i
            v_new = self.v[i] + 0.5 * dt * a

            # Rayleigh friction（個體目標速度）
            v2 = v_new.dot(v_new)
            v0_sq = v0_i * v0_i
            rayleigh_coeff = alpha * (1.0 - v2 / (v0_sq + 1e-12))
            v_new += dt * rayleigh_coeff * v_new

            # Vicsek noise（個體 noise 強度）
            if eta_i > 0.0:
                speed = ti.sqrt(v_new.dot(v_new))
                if speed > 1e-6:
                    # 更新 RNG 狀態
                    state = self.rng_state[i]

                    # Random 1: 旋轉角度
                    state = self.xorshift32(state)
                    rand1 = self.rand_uniform(state)
                    noise_angle = (rand1 - 0.5) * 2.0 * eta_i

                    # Random 2-3: 隨機旋轉軸
                    state = self.xorshift32(state)
                    rand2 = self.rand_uniform(state)
                    state = self.xorshift32(state)
                    rand3 = self.rand_uniform(state)

                    u = rand2 * 2.0 - 1.0
                    v = rand3 * 2.0 - 1.0
                    s = u * u + v * v

                    # 初始化旋轉軸
                    axis = ti.Vector([1.0, 0.0, 0.0])

                    if s < 1.0 and s > 1e-6:
                        # Marsaglia 方法
                        sqrt_factor = ti.sqrt(1.0 - s)
                        axis = ti.Vector(
                            [
                                2.0 * u * sqrt_factor,
                                2.0 * v * sqrt_factor,
                                1.0 - 2.0 * s,
                            ]
                        )
                    else:
                        # Fallback
                        v_norm = v_new / speed
                        if ti.abs(v_norm[0]) < ti.abs(v_norm[1]):
                            if ti.abs(v_norm[0]) < ti.abs(v_norm[2]):
                                axis = ti.Vector([0.0, -v_norm[2], v_norm[1]])
                            else:
                                axis = ti.Vector([-v_norm[1], v_norm[0], 0.0])
                        else:
                            if ti.abs(v_norm[1]) < ti.abs(v_norm[2]):
                                axis = ti.Vector([-v_norm[2], 0.0, v_norm[0]])
                            else:
                                axis = ti.Vector([-v_norm[1], v_norm[0], 0.0])

                    # 正規化旋轉軸
                    axis_norm = ti.sqrt(axis.dot(axis))
                    if axis_norm > 1e-6:
                        axis /= axis_norm

                    # Rodrigues' rotation
                    cos_angle = ti.cos(noise_angle)
                    sin_angle = ti.sin(noise_angle)

                    v_norm = v_new / speed
                    k_cross_v = ti.Vector(
                        [
                            axis[1] * v_norm[2] - axis[2] * v_norm[1],
                            axis[2] * v_norm[0] - axis[0] * v_norm[2],
                            axis[0] * v_norm[1] - axis[1] * v_norm[0],
                        ]
                    )
                    k_dot_v = axis.dot(v_norm)

                    v_rotated = (
                        v_norm * cos_angle
                        + k_cross_v * sin_angle
                        + axis * k_dot_v * (1.0 - cos_angle)
                    )

                    v_new = v_rotated * speed
                    self.rng_state[i] = state

            self.v[i] = v_new

    # ========================================================================
    # Obstacle Management Methods (委派給 ObstacleSystem)
    # ========================================================================
    def add_obstacle(self, config: ObstacleConfig) -> int:
        """
        新增障礙物

        Args:
            config: 障礙物配置

        Returns:
            障礙物 ID
        """
        return self.obstacles.add_obstacle(config)

    def remove_obstacle(self, obs_id: int):
        """移除障礙物"""
        self.obstacles.remove_obstacle(obs_id)

    def update_obstacle_position(self, obs_id: int, new_pos: np.ndarray):
        """更新障礙物位置（支援動態障礙物）"""
        self.obstacles.update_obstacle_position(obs_id, new_pos)

    def get_obstacle_info(self, obs_id: int) -> dict:
        """獲取障礙物資訊"""
        return self.obstacles.get_obstacle_info(obs_id)

    def get_all_obstacles(self) -> List[dict]:
        """獲取所有障礙物資訊"""
        return self.obstacles.get_all_obstacles()

    # ========================================================================
    # Spatial Grid Methods (overrides from SpatialGridMixin)
    # ========================================================================
    @ti.kernel
    def assign_agents_to_grid(self):
        """
        將所有 agent 分配到對應的 spatial grid cell
        時間複雜度：O(N)

        Override: 排除掠食者（type=3）不參與 Grid
        """
        # 重置 cell_count
        for c in self.cell_count:
            self.cell_count[c] = 0

        # 分配 agents 到 Grid（排除掠食者）
        for i in self.x:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                self.agent_cell_id[i] = -1
                continue

            # 排除掠食者
            if self.agent_type_field[i] == 3:
                self.agent_cell_id[i] = -1
                continue

            cell_id = self.get_cell_id(self.x[i])
            self.agent_cell_id[i] = cell_id

            # 原子操作：計數該 cell 的 agent 數量
            old_count = ti.atomic_add(self.cell_count[cell_id], 1)

            # 將 agent 加入該 cell（如果未滿）
            if old_count < self.max_agents_per_cell:
                self.cell_agents[cell_id, old_count] = i

    # ========================================================================
    # Group Detection Methods (Override GroupDetectionMixin)
    # ========================================================================
    @ti.kernel
    def detect_groups_iteration(self, r_cluster: ti.f32, theta_cluster: ti.f32):
        """
        Override: 排除掠食者（type=3）不參與群組檢測

        執行單次群組偵測迭代（label propagation 的一輪）
        使用 Spatial Grid 加速鄰居搜尋：O(N) 取代 O(N²)
        """
        for i in self.x:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                self.group_id[i] = -1
                continue

            # 排除掠食者（type=3）不參與群組檢測
            if self.agent_type_field[i] == 3:
                self.group_id[i] = -1
                continue

            xi = self.x[i]
            vi = self.v[i]
            vi_norm = vi.norm()

            if vi_norm < 1e-6:
                continue

            current_group = self.group_id[i]
            min_group = current_group

            # 獲取 agent i 所在的 cell
            cell_id = self.agent_cell_id[i]
            if cell_id < 0:
                continue

            # 解析 cell_id 為 3D index
            res = self.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res

            # 檢查 3×3×3=27 個相鄰 cell
            for dz in ti.static(range(-1, 2)):
                for dy in ti.static(range(-1, 2)):
                    for dx in ti.static(range(-1, 2)):
                        nx = ix + dx
                        ny = iy + dy
                        nz = iz + dz

                        if (
                            nx >= 0
                            and nx < res
                            and ny >= 0
                            and ny < res
                            and nz >= 0
                            and nz < res
                        ):
                            neighbor_cell = nx + ny * res + nz * res * res

                            n_agents_in_cell = self.cell_count[neighbor_cell]
                            for local_idx in range(n_agents_in_cell):
                                if local_idx >= self.max_agents_per_cell:
                                    break

                                j = self.cell_agents[neighbor_cell, local_idx]
                                if i == j:
                                    continue

                                # 排除掠食者
                                if self.agent_type_field[j] == 3:
                                    continue

                                xj = self.x[j]
                                vj = self.v[j]
                                vj_norm = vj.norm()

                                if vj_norm < 1e-6:
                                    continue

                                # 計算距離（考慮 PBC）
                                distance = 0.0
                                if self.params.boundary_mode == 0:
                                    distance = self.pbc_dist(xi, xj).norm()
                                else:
                                    distance = (xj - xi).norm()

                                if distance > r_cluster:
                                    continue

                                # 檢查速度夾角
                                cos_angle = (vi.dot(vj)) / (vi_norm * vj_norm)
                                cos_angle = ti.max(-1.0, ti.min(1.0, cos_angle))
                                angle = ti.acos(cos_angle)

                                if angle > theta_cluster:
                                    continue

                                # 取較小的 group_id
                                neighbor_group = self.group_id[j]
                                if neighbor_group < min_group:
                                    min_group = neighbor_group

            self.group_id[i] = min_group

    @ti.kernel
    def compute_group_statistics(self):
        """
        Override: 排除掠食者不參與群組統計
        """
        # 重置統計資訊
        for g in range(self.max_groups):
            self.group_size[g] = 0
            self.group_centroid[g] = ti.Vector([0.0, 0.0, 0.0])
            self.group_velocity[g] = ti.Vector([0.0, 0.0, 0.0])
            self.group_active[g] = 0

        # 計算群組總和（排除掠食者）
        for i in self.x:
            if self.agent_type_field[i] == 3:
                continue

            gid = self.group_id[i]
            if gid >= 0 and gid < self.max_groups:
                ti.atomic_add(self.group_size[gid], 1)
                for d in ti.static(range(3)):
                    ti.atomic_add(self.group_centroid[gid][d], self.x[i][d])
                    ti.atomic_add(self.group_velocity[gid][d], self.v[i][d])

        # 計算平均值
        for g in range(self.max_groups):
            size = self.group_size[g]
            if size > 0:
                self.group_active[g] = 1
                for d in ti.static(range(3)):
                    self.group_centroid[g][d] /= ti.cast(size, ti.f32)
                    self.group_velocity[g][d] /= ti.cast(size, ti.f32)

    def step(self, dt: float):
        """
        執行一個時間步（覆寫父類別方法以整合異質與捕食者邏輯）

        整合順序：
            1. 更新資源與獵物目標
            2. 計算力（包含捕食/逃脫力）
            3. Verlet 積分器
            4. 資源消耗與捕食攻擊
            5. 資源再生
            6. 群組檢測（每 N 步執行一次）
        """
        # 1. 更新目標
        self.find_nearest_resources()  # 低能量 agent 尋找資源
        self.find_nearest_prey()  # 捕食者鎖定獵物

        # 2-3. 物理更新（Velocity Verlet）
        self.compute_forces()  # 計算所有力（含捕食/逃脫）
        self.verlet_step1(dt)
        self.compute_forces()
        self.verlet_step2(dt)

        # 4. 生態互動
        # 4.1 資源消耗（含速度相關能量消耗與資源競爭）
        self.consume_resources_step(
            consumption_rate=3.0,  # 降低消耗速率（10.0 → 3.0）
            velocity_factor=0.5,  # 速度影響能量消耗
            conversion_efficiency=0.5,  # 資源轉能量效率 50%
        )

        # 4.2 能量耗盡死亡檢查
        self.apply_energy_death()

        # 4.3 捕食者攻擊獵物（動態獎勵：獵物能量 × 70%）
        self.attack_prey_step()

        # 5. 環境更新
        self.resources.replenish_resources()  # 資源再生

        # 6. 群組檢測（每 N 步執行一次以減少計算負擔）
        # 第一步（step_counter=0）強制執行一次，確保有初始群組資料
        # 降低迭代次數：5 → 3（Label Propagation 收斂很快）
        if self.step_counter == 0 or self.step_counter >= self.group_detection_interval:
            self.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=3)
            self.step_counter = 1  # 重置為 1（下次在 interval 時執行）
        else:
            self.step_counter += 1

    # ========================================================================
    # Query API (for testing and monitoring)
    # ========================================================================
    def get_agent_targets(self) -> np.ndarray:
        """獲取所有 agents 的目標資源 ID"""
        return self.agent_target_resource.to_numpy()

    def get_agent_energies(self) -> np.ndarray:
        """獲取所有 agents 的能量"""
        return self.agent_energy.to_numpy()


# ============================================================================
# Demo & Testing Utilities
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Heterogeneous Flocking 3D - Quick Test")
    print("=" * 70)

    # 建立混合群體：20% Explorer, 70% Follower, 10% Leader
    N = 100
    agent_types = (
        [AgentType.EXPLORER] * 20 + [AgentType.FOLLOWER] * 70 + [AgentType.LEADER] * 10
    )

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        beta=1.0,  # 基礎值（會被個體參數覆蓋）
        box_size=50.0,
    )

    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, enable_fov=True, fov_angle=120.0
    )

    system.initialize(box_size=5.0, seed=42)

    # 設定目標：Leaders 向 (10, 10, 10) 移動
    leader_indices = np.where(np.array(agent_types) == AgentType.LEADER)[0]
    goals = np.tile([10.0, 10.0, 10.0], (len(leader_indices), 1))
    system.set_goals(goals, leader_indices)

    print("\n執行 100 步模擬...")
    system.run(steps=100, dt=0.01, log_every=20)

    print("\n" + "=" * 70)
    print("✅ Quick test 完成")
    print("=" * 70)
