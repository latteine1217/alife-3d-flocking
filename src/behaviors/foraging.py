"""
Foraging Behavior Mixin

提供覓食與能量管理功能：
    • 搜尋最近資源
    • 能量消耗與恢復
    • 資源目標管理
"""

import taichi as ti
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from resources import ResourceSystem


@ti.data_oriented
class ForagingBehaviorMixin:
    """
    覓食行為 Mixin

    依賴：
        • ResourceSystem: 資源管理系統
        • self.x: Agent 位置 (ti.Vector.field)
        • self.params.boundary_mode: 邊界模式
        • self.pbc_dist(): PBC 距離計算函式

    提供功能：
        • 能量管理（消耗/恢復）
        • 資源搜尋與鎖定
        • 資源消耗邏輯
    """

    def init_foraging(
        self,
        N: int,
        resources: "ResourceSystem",
        energy_threshold: float = 30.0,
        energy_consumption_rate: float = 0.1,
        initial_energy: float = 100.0,
    ):
        """
        初始化覓食行為

        Args:
            N: Agent 數量
            resources: ResourceSystem 實例
            energy_threshold: 開始覓食的能量閾值
            energy_consumption_rate: 每步消耗的能量
            initial_energy: 初始能量值
        """
        self.resources = resources

        # 能量系統
        self.agent_energy = ti.field(ti.f32, N)
        self.agent_target_resource = ti.field(ti.i32, N)

        # 健康狀態系統（新增）
        # 0=健康, 1=疲勞, 2=虛弱, 3=瀕死
        self.agent_health_status = ti.field(ti.i32, N)

        # 參數
        self.energy_threshold = energy_threshold
        self.energy_consumption_rate = energy_consumption_rate

        # 初始化
        self.agent_energy.fill(initial_energy)
        self.agent_target_resource.fill(-1)
        self.agent_health_status.fill(0)  # 全部健康

        print(f"[ForagingBehavior] Initialized with threshold={energy_threshold:.1f}")

    @ti.kernel
    def find_nearest_resources(self):
        """
        每個 agent 搜尋最近的有效資源

        邏輯：
            • 若 energy < threshold 且無目標 → 搜尋最近資源
            • 計算到所有資源的距離
            • 選擇最近且有效的資源
        """
        N_res = self.resources.n_resources

        for i in self.x:
            energy = self.agent_energy[i]
            current_target = self.agent_target_resource[i]

            # 檢查是否需要覓食
            if energy < self.energy_threshold or current_target >= 0:
                min_dist = 1e10
                best_res = -1

                # 搜尋所有資源
                for res_id in range(N_res):
                    if self.resources.resource_active[res_id] == 1:
                        if self.resources.resource_amount[res_id] > 0.0:
                            # 計算距離
                            res_pos = self.resources.resource_pos[res_id]

                            # 考慮 PBC
                            dx = ti.Vector([0.0, 0.0, 0.0])
                            if self.params.boundary_mode == 0:  # PBC
                                dx = self.pbc_dist(self.x[i], res_pos)
                            else:
                                dx = res_pos - self.x[i]

                            dist = dx.norm()

                            if dist < min_dist:
                                min_dist = dist
                                best_res = res_id

                # 更新目標
                self.agent_target_resource[i] = best_res

    @ti.kernel
    def _update_energy_consumption(self, velocity_factor: ti.f32):
        """
        更新所有 agent 的能量消耗（速度相關）

        消耗公式：base_rate + velocity_factor * speed
        - 靜止時：只消耗 base_rate
        - 移動時：額外消耗與速度成正比

        Args:
            velocity_factor: 速度消耗係數（建議 0.3-0.5）
        """
        for i in self.agent_energy:
            # 基礎消耗
            base_consumption = self.energy_consumption_rate

            # 速度消耗（與當前速度成正比）
            speed = self.v[i].norm()
            velocity_consumption = velocity_factor * speed

            # 總消耗
            total_consumption = base_consumption + velocity_consumption

            # 更新能量（不低於 0）
            self.agent_energy[i] = ti.max(0.0, self.agent_energy[i] - total_consumption)

    @ti.kernel
    def _update_health_status(self):
        """
        根據能量更新健康狀態並影響移動速度

        健康狀態分級：
            0 (健康):    能量 > 50  → 速度 100%
            1 (疲勞):    能量 30-50 → 速度  85%
            2 (虛弱):    能量 15-30 → 速度  60%
            3 (瀕死):    能量 <  15 → 速度  30%

        副作用：直接修改 v0_individual[i] 來影響速度
        """
        for i in self.agent_energy:
            energy = self.agent_energy[i]

            # 判定健康狀態與速度懲罰
            if energy > 50.0:
                self.agent_health_status[i] = 0  # 健康
                # v0 保持原樣（在 consume_resources_step 中恢復）

            elif energy > 30.0:
                self.agent_health_status[i] = 1  # 疲勞
                # 速度降低 15%

            elif energy > 15.0:
                self.agent_health_status[i] = 2  # 虛弱
                # 速度降低 40%

            else:
                self.agent_health_status[i] = 3  # 瀕死
                # 速度降低 70%

    @ti.kernel
    def _apply_health_speed_penalty(self):
        """
        根據健康狀態應用速度懲罰

        使用 v0_base 作為基準，計算懲罰後的 v0_individual
        """
        for i in self.agent_health_status:
            status = self.agent_health_status[i]
            base_speed = self.v0_base[i]

            if status == 0:
                # 健康：100%
                self.v0_individual[i] = base_speed
            elif status == 1:
                # 疲勞：85%
                self.v0_individual[i] = base_speed * 0.85
            elif status == 2:
                # 虛弱：60%
                self.v0_individual[i] = base_speed * 0.60
            elif status == 3:
                # 瀕死：30%
                self.v0_individual[i] = base_speed * 0.30

    def consume_resources_step(
        self,
        consumption_rate: float = 3.0,
        velocity_factor: float = 0.5,
        conversion_efficiency: float = 0.5,
        competition_mode: str = "fifo",
    ):
        """
        處理資源消耗（每步呼叫一次）

        Args:
            consumption_rate: 每個 agent 每步消耗資源的速率
            velocity_factor: 速度消耗係數（用於能量消耗）
            conversion_efficiency: 資源 → 能量轉換效率（0.5 = 消耗 10 資源獲得 5 能量）
            competition_mode: 競爭模式 ("fifo"=先到先得, "equal"=平均分配)
        """
        # 1. 先更新能量消耗（速度相關）
        self._update_energy_consumption(velocity_factor)

        # 2. 更新健康狀態（會影響移動速度）
        self._update_health_status()
        self._apply_health_speed_penalty()

        # 3. 統計每個資源有多少 agents 在範圍內（用於資源瓜分）
        x_np = self.x.to_numpy()
        target_res_np = self.agent_target_resource.to_numpy()
        alive_np = self.agent_alive.to_numpy()

        # resource_id -> [(agent_index, distance)]
        resource_consumers = {}

        for i in range(len(x_np)):
            # 跳過死亡 agent
            if alive_np[i] == 0:
                continue

            target_res = target_res_np[i]
            if target_res >= 0 and target_res < self.resources.n_resources:
                agent_pos = x_np[i]
                res_pos = self.resources.resource_pos[target_res].to_numpy()
                res_radius = self.resources.resource_radius[target_res]
                distance = np.linalg.norm(agent_pos - res_pos)

                if distance < res_radius:
                    if target_res not in resource_consumers:
                        resource_consumers[target_res] = []
                    resource_consumers[target_res].append((i, distance))

        # 4. 根據競爭模式分配資源
        if competition_mode == "fifo":
            self._allocate_fifo(
                resource_consumers, consumption_rate, conversion_efficiency
            )
        else:  # equal (原始平均分配)
            self._allocate_equal(
                resource_consumers, consumption_rate, conversion_efficiency
            )

    def _allocate_equal(
        self, resource_consumers, consumption_rate: float, conversion_efficiency: float
    ):
        """
        平均分配模式（原始實作）

        所有在範圍內的 agents 平分資源
        """
        for res_id, consumers in resource_consumers.items():
            n_consumers = len(consumers)
            agent_indices = [idx for idx, _ in consumers]

            # 總需求
            total_demand = consumption_rate * n_consumers

            # 實際消耗
            consumed = self.resources.consume_resource(res_id, total_demand)

            # 平分
            per_agent_gain = (consumed / n_consumers) * conversion_efficiency

            for agent_idx in agent_indices:
                current_energy = self.agent_energy[agent_idx]
                self.agent_energy[agent_idx] = min(
                    100.0, current_energy + per_agent_gain
                )

                # 若能量已滿，清除目標
                if self.agent_energy[agent_idx] >= 100.0:
                    self.agent_target_resource[agent_idx] = -1

    def _allocate_fifo(
        self, resource_consumers, consumption_rate: float, conversion_efficiency: float
    ):
        """
        先到先得分配模式（FIFO）

        按距離排序，近者優先獲得資源。
        資源耗盡後，後續 agents 無法獲得。

        策略：
            • 按距離升序排序
            • 依序分配 consumption_rate 給每個 agent
            • 資源不足時，部分滿足最後幾個 agents
        """
        for res_id, consumers in resource_consumers.items():
            # 按距離排序（距離近 = 先到）
            sorted_consumers = sorted(consumers, key=lambda x: x[1])

            # 可用資源總量
            available = self.resources.resource_amount[res_id]

            for agent_idx, distance in sorted_consumers:
                if available <= 0.0:
                    break  # 資源耗盡

                # 該 agent 的需求量
                demand = consumption_rate

                # 實際獲得（可能不足）
                take = min(demand, available)
                consumed = self.resources.consume_resource(res_id, take)

                # 轉換為能量
                energy_gain = consumed * conversion_efficiency

                # 更新 agent 能量
                current_energy = self.agent_energy[agent_idx]
                self.agent_energy[agent_idx] = min(100.0, current_energy + energy_gain)

                # 扣除已消耗量
                available -= consumed

                # 若能量已滿，清除目標
                if self.agent_energy[agent_idx] >= 100.0:
                    self.agent_target_resource[agent_idx] = -1

    @ti.kernel
    def _check_energy_death(self):
        """
        檢查能量耗盡導致的死亡

        邏輯：
            • 能量 <= 0 → 標記為死亡 (agent_alive = 0)
            • 死亡 agent 移動到遠離模擬區域的位置（消失）
            • 速度設為 0，不再參與物理交互
        """
        dead_zone = 1e6  # 遠離模擬區域的位置

        for i in self.agent_energy:
            if self.agent_energy[i] <= 0.0:
                # 標記為死亡
                self.agent_alive[i] = 0

                # 清除目標（避免死亡 agent 繼續鎖定資源）
                self.agent_target_resource[i] = -1

                # 移動到遠處（消失）
                self.x[i] = ti.Vector([dead_zone, dead_zone, dead_zone])

                # 停止運動
                self.v[i] = ti.Vector([0.0, 0.0, 0.0])

                # 清空力（避免計算）
                self.f[i] = ti.Vector([0.0, 0.0, 0.0])

    def apply_energy_death(self):
        """
        應用能量耗盡死亡機制（每步呼叫）

        注意：應在 consume_resources_step() 之後呼叫
        """
        self._check_energy_death()

        # 統計死亡數
        alive_count = int(self.agent_alive.to_numpy().sum())
        dead_count = len(self.agent_alive.to_numpy()) - alive_count

        if dead_count > 0:
            print(
                f"💀 Energy death: {dead_count} agents starved (alive: {alive_count})"
            )

    # ========================================================================
    # Resource Management API (委派給 ResourceSystem)
    # ========================================================================
    def add_resource(self, config):
        """新增資源"""
        return self.resources.add_resource(config)

    def remove_resource(self, res_id: int):
        """移除資源"""
        self.resources.remove_resource(res_id)

    def get_resource_info(self, res_id: int):
        """獲取資源資訊"""
        return self.resources.get_resource_info(res_id)

    def get_all_resources(self):
        """獲取所有資源"""
        return self.resources.get_all_resources()
