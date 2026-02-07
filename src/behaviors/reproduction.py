"""
Reproduction Behavior Mixin

提供繁殖與演化功能：
    • 能量閾值觸發繁殖
    • 子代繼承父代屬性
    • 預分配池管理（避免動態擴展 Taichi field）
    • 繁殖冷卻機制
"""

import taichi as ti
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flocking_heterogeneous import AgentType


@ti.data_oriented
class ReproductionBehaviorMixin:
    """
    繁殖行為 Mixin

    依賴：
        • self.x: Agent 位置 (ti.Vector.field)
        • self.v: Agent 速度 (ti.Vector.field)
        • self.agent_energy: Agent 能量
        • self.agent_alive: Agent 存活狀態
        • self.agent_types_np: Agent 類型（numpy array）
        • self.v0_base: Agent 基礎速度

    提供功能：
        • 能量充足時觸發繁殖
        • 子代繼承父代屬性
        • 預分配池管理（max_agents 容量）
    """

    def init_reproduction(
        self,
        max_agents: int,
        reproduction_threshold: float = 90.0,
        parent_energy_cost: float = 0.5,
        offspring_energy_ratio: float = 0.3,
        reproduction_cooldown: int = 100,
        spawn_distance: float = 2.0,
    ):
        """
        初始化繁殖行為

        Args:
            max_agents: 最大 agent 數量（預分配池大小）
            reproduction_threshold: 繁殖觸發的能量閾值
            parent_energy_cost: 父代繁殖消耗的能量比例（0.5 = 50%）
            offspring_energy_ratio: 子代獲得的能量比例（相對父代初始能量）
            reproduction_cooldown: 繁殖冷卻時間（步數）
            spawn_distance: 子代生成距離（父代附近）
        """
        self.max_agents = max_agents
        self.reproduction_threshold = reproduction_threshold
        self.parent_energy_cost = parent_energy_cost
        self.offspring_energy_ratio = offspring_energy_ratio
        self.reproduction_cooldown = reproduction_cooldown
        self.spawn_distance = spawn_distance

        # 繁殖冷卻計時器（每個 agent）
        self.reproduction_timer = ti.field(ti.i32, max_agents)
        self.reproduction_timer.fill(0)

        # 統計
        self.total_births = 0

        print(f"[ReproductionBehavior] Initialized:")
        print(f"  Max agents: {max_agents}")
        print(f"  Reproduction threshold: {reproduction_threshold}")
        print(f"  Parent energy cost: {parent_energy_cost * 100:.0f}%")
        print(f"  Offspring energy: {offspring_energy_ratio * 100:.0f}%")
        print(f"  Cooldown: {reproduction_cooldown} steps")

    def attempt_reproduction(self):
        """
        嘗試繁殖（每步呼叫）

        邏輯：
            1. 遍歷所有存活 agents
            2. 檢查能量 >= threshold 且冷卻結束
            3. 尋找閒置 slot（agent_alive[i] == 0）
            4. 複製父代屬性到子代
            5. 扣除父代能量，重置冷卻
        """
        energy_np = self.agent_energy.to_numpy()
        alive_np = self.agent_alive.to_numpy()
        timer_np = self.reproduction_timer.to_numpy()
        x_np = self.x.to_numpy()
        v_np = self.v.to_numpy()

        births_this_step = 0

        for parent_idx in range(len(alive_np)):
            # 只有存活且能量充足且冷卻結束的 agent 能繁殖
            if (
                alive_np[parent_idx] == 1
                and energy_np[parent_idx] >= self.reproduction_threshold
                and timer_np[parent_idx] <= 0
            ):
                # 尋找閒置 slot
                offspring_idx = self._find_empty_slot(alive_np)

                if offspring_idx is None:
                    # 無空位，停止繁殖
                    break

                # 執行繁殖
                self._spawn_offspring(parent_idx, offspring_idx, x_np, v_np, energy_np)

                # 扣除父代能量
                energy_cost = energy_np[parent_idx] * self.parent_energy_cost
                self.agent_energy[parent_idx] -= energy_cost

                # 重置冷卻
                self.reproduction_timer[parent_idx] = self.reproduction_cooldown

                # 更新存活狀態
                alive_np[offspring_idx] = 1

                births_this_step += 1
                self.total_births += 1

        # 更新計時器（遞減）
        self._update_cooldown_timers()

        # 日誌
        if births_this_step > 0:
            alive_count = int(alive_np.sum())
            print(
                f"🐣 Reproduction: {births_this_step} offspring born (population: {alive_count})"
            )

    def _find_empty_slot(self, alive_np):
        """
        尋找閒置 slot（agent_alive == 0）

        Returns:
            int or None: 閒置 slot 索引，若無則返回 None
        """
        for i in range(self.max_agents):
            if alive_np[i] == 0:
                return i
        return None

    def _spawn_offspring(self, parent_idx, offspring_idx, x_np, v_np, energy_np):
        """
        生成子代（複製父代屬性）

        Args:
            parent_idx: 父代索引
            offspring_idx: 子代索引
            x_np: 位置數組
            v_np: 速度數組
            energy_np: 能量數組
        """
        # 1. 位置：父代附近隨機偏移
        offset = np.random.randn(3) * self.spawn_distance
        offspring_pos = x_np[parent_idx] + offset

        # 邊界處理（簡單 clamp，可改為 PBC wrap）
        box_size = getattr(self.params, "box_size", 50.0)
        offspring_pos = np.clip(offspring_pos, -box_size / 2, box_size / 2)

        self.x[offspring_idx] = offspring_pos.astype(np.float32)

        # 2. 速度：繼承父代（加微小擾動模擬變異）
        mutation = np.random.randn(3) * 0.1
        offspring_vel = v_np[parent_idx] + mutation
        self.v[offspring_idx] = offspring_vel.astype(np.float32)

        # 3. 能量：初始能量（相對父代基礎能量）
        # 注意：offspring_energy_ratio 是相對 100.0（滿能量）
        offspring_energy = 100.0 * self.offspring_energy_ratio
        self.agent_energy[offspring_idx] = offspring_energy

        # 4. 類型：繼承父代
        parent_type = self.agent_types_np[parent_idx]
        self.agent_types_np[offspring_idx] = parent_type
        self.agent_type_field[offspring_idx] = int(parent_type)

        # 5. 基礎速度：繼承父代
        parent_v0 = self.v0_base[parent_idx]
        self.v0_base[offspring_idx] = parent_v0
        self.v0_individual[offspring_idx] = parent_v0

        # 6. 質量：繼承父代
        parent_mass = self.mass[parent_idx]
        self.mass[offspring_idx] = parent_mass

        # 7. 健康狀態：初始為健康
        self.agent_health_status[offspring_idx] = 0

        # 8. 清空目標資源與獵物
        self.agent_target_resource[offspring_idx] = -1
        if hasattr(self, "agent_target_prey"):
            self.agent_target_prey[offspring_idx] = -1

        # 9. 力場清零
        self.f[offspring_idx] = ti.Vector([0.0, 0.0, 0.0], dt=ti.f32)

    @ti.kernel
    def _update_cooldown_timers(self):
        """
        更新所有 agent 的繁殖冷卻計時器（遞減）
        """
        for i in self.reproduction_timer:
            if self.agent_alive[i] == 1 and self.reproduction_timer[i] > 0:
                self.reproduction_timer[i] -= 1

    def get_reproduction_stats(self):
        """
        獲取繁殖統計資訊

        Returns:
            dict: 繁殖統計
        """
        alive_np = self.agent_alive.to_numpy()
        alive_count = int(alive_np.sum())

        return {
            "total_births": self.total_births,
            "current_population": alive_count,
            "max_capacity": self.max_agents,
            "capacity_usage": f"{alive_count / self.max_agents * 100:.1f}%",
        }
