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

        # 向後相容：Foraging 可以被單獨 mixin 使用（測試/最小系統）
        # 若上層系統尚未提供必要欄位，則提供合理預設。
        if not hasattr(self, "agent_alive"):
            self.agent_alive = ti.field(ti.i32, N)
            self.agent_alive.fill(1)
        if not hasattr(self, "agent_type_field"):
            # 0=FOLLOWER（非掠食者），確保 kernel 中的「掠食者分支」可用
            self.agent_type_field = ti.field(ti.i32, N)
            self.agent_type_field.fill(0)

        # 能量系統
        self.agent_energy = ti.field(ti.f32, N)
        self.agent_target_resource = ti.field(ti.i32, N)
        # 記錄 agent 鎖定資源後的追逐步數（用於旅行時間補償）
        self.resource_seek_steps = ti.field(ti.i32, N)

        # 健康狀態系統（新增）
        # 0=健康, 1=疲勞, 2=虛弱, 3=瀕死
        self.agent_health_status = ti.field(ti.i32, N)

        # 參數
        self.energy_threshold = energy_threshold
        self.energy_consumption_rate = energy_consumption_rate
        # 統一能量上限，避免「初始能量 > 回復上限」導致系統必然單向失血
        self.energy_max = initial_energy
        # 掠食者較早進入資源覓食，避免只能靠掠食補能
        self.predator_energy_threshold = max(energy_threshold, initial_energy * 0.7)
        # 能量-質量耦合：能量每 9 份，質量增幅約 1 份（9:1）
        self.mass_energy_ratio = 9.0
        # 質量對能耗加成係數（越大表示重質量更耗能）
        self.mass_energy_cost_scale = 0.35
        # 僅在系統具備質量欄位時啟用（向後相容）
        self.enable_mass_energy_coupling = hasattr(self, "mass_individual") and hasattr(
            self, "mass_base"
        )

        # 初始化
        self.agent_energy.fill(initial_energy)
        self.agent_target_resource.fill(-1)
        self.resource_seek_steps.fill(0)
        self.agent_health_status.fill(0)  # 全部健康

        # 依初始能量同步一次動態質量（若支援）
        self._update_mass_from_energy()

        print(f"[ForagingBehavior] Initialized with threshold={energy_threshold:.1f}")

    @ti.kernel
    def find_nearest_resources(self):
        """
        每個 agent 搜尋最近的有效資源

        邏輯：
            • 若 energy < threshold 且無目標 → 搜尋最近資源
            • 計算到所有資源的距離
            • 選擇最近且有效的資源

        優化：
            • 只有能量不足時才搜尋
            • 資源數量通常很少（M≈10-32），O(N×M) 可接受
        """
        N_res = self.resources.n_resources

        for i in self.x:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                continue

            energy = self.agent_energy[i]
            current_target = self.agent_target_resource[i]

            # 檢查是否需要覓食（掠食者使用較高門檻，提早尋找資源）
            seek_threshold = self.energy_threshold
            if self.agent_type_field[i] == 3:
                seek_threshold = self.predator_energy_threshold

            if energy < seek_threshold:
                min_dist = 1e10
                best_res = -1

                # 搜尋所有資源（資源數量少，暴力搜尋可接受）
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
                if best_res >= 0:
                    if current_target == best_res and current_target >= 0:
                        self.resource_seek_steps[i] = ti.min(
                            self.resource_seek_steps[i] + 1, 10000
                        )
                    else:
                        self.resource_seek_steps[i] = 1
                else:
                    self.resource_seek_steps[i] = 0
                self.agent_target_resource[i] = best_res
            elif energy >= self.energy_max:
                # 能量已滿，清除目標
                self.agent_target_resource[i] = -1
                self.resource_seek_steps[i] = 0

    def _update_energy_consumption(
        self,
        velocity_factor: float,
        travel_relief_factor: float = 0.45,
        travel_relief_steps: float = 120.0,
    ):
        """
        Python 包裝：保持舊呼叫相容，並轉發至 Taichi kernel
        """
        self._update_energy_consumption_kernel(
            velocity_factor, travel_relief_factor, travel_relief_steps
        )

    @ti.kernel
    def _update_energy_consumption_kernel(
        self,
        velocity_factor: ti.f32,
        travel_relief_factor: ti.f32,
        travel_relief_steps: ti.f32,
    ):
        """
        更新所有 agent 的能量消耗（速度相關）

        消耗公式：base_rate + velocity_factor * speed
        - 靜止時：只消耗 base_rate
        - 移動時：額外消耗與速度成正比

        Args:
            velocity_factor: 速度消耗係數（建議 0.3-0.5）
        """
        for i in self.agent_energy:
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                continue

            # 基礎消耗
            base_consumption = self.energy_consumption_rate

            # 速度消耗（與當前速度成正比）
            speed = self.v[i].norm()
            velocity_consumption = velocity_factor * speed

            # 質量額外消耗：質量越大，維持活動所需能量越高
            mass_consumption = 0.0
            if ti.static(self.enable_mass_energy_coupling):
                reference_mass = ti.max(self.p[9], 1e-6)
                mass_ratio = self.mass_individual[i] / reference_mass
                mass_consumption = (
                    self.energy_consumption_rate
                    * self.mass_energy_cost_scale
                    * ti.max(0.0, mass_ratio - 1.0)
                )

            # 總消耗
            total_consumption = base_consumption + velocity_consumption + mass_consumption

            # 旅行時間補償：
            # 低能量且已鎖定資源時，隨追逐步數逐漸降低消耗，
            # 反映「到達資源需要時間」的能量平衡成本。
            low_energy_threshold = self.energy_threshold
            if self.agent_type_field[i] == 3:
                low_energy_threshold = self.predator_energy_threshold

            if self.agent_target_resource[i] >= 0 and self.agent_energy[i] < low_energy_threshold:
                progress = ti.min(
                    1.0, ti.cast(self.resource_seek_steps[i], ti.f32) / ti.max(travel_relief_steps, 1.0)
                )
                relief_multiplier = 1.0 - travel_relief_factor * progress
                total_consumption *= ti.max(0.35, relief_multiplier)

            # 更新能量（不低於 0）
            self.agent_energy[i] = ti.max(0.0, self.agent_energy[i] - total_consumption)

    @ti.kernel
    def _update_mass_from_energy(self):
        """
        依能量更新動態質量（9:1 比例）

        設計：
            • energy_ratio = energy / energy_max
            • mass_multiplier = 1 + energy_ratio / 9
            • 能量高時質量小幅增加（滿能量約 +11.1%）
        """
        for i in self.agent_energy:
            if self.agent_alive[i] == 0:
                continue

            if ti.static(self.enable_mass_energy_coupling):
                energy_ratio = self.agent_energy[i] / ti.max(self.energy_max, 1e-6)
                energy_ratio = ti.max(0.0, ti.min(1.0, energy_ratio))
                mass_multiplier = 1.0 + energy_ratio / self.mass_energy_ratio
                self.mass_individual[i] = self.mass_base[i] * mass_multiplier

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
            # 只處理存活的 agents
            if self.agent_alive[i] == 0:
                continue

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
        travel_relief_factor: float = 0.45,
        travel_relief_steps: float = 120.0,
        competition_mode: str = "fifo",
    ):
        """
        處理資源消耗（每步呼叫一次）

        Args:
            consumption_rate: 每個 agent 每步消耗資源的速率
            velocity_factor: 速度消耗係數（用於能量消耗）
            conversion_efficiency: 資源 → 能量轉換效率（0.5 = 消耗 10 資源獲得 5 能量）
            travel_relief_factor: 旅行補償強度（0-1，越大表示追資源時消耗下降越多）
            travel_relief_steps: 補償達到上限所需步數
            competition_mode: 競爭模式 ("fifo"=先到先得, "equal"=平均分配)
        """
        # 1. 先更新能量消耗（速度相關）
        self._update_energy_consumption(
            velocity_factor, travel_relief_factor, travel_relief_steps
        )

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
                # 🔧 FIX: 檢查資源是否 active 和有效（避免追逐已失效的資源）
                if self.resources.resource_active[target_res] == 0:
                    # 資源已失效，清除 agent 的目標
                    self.agent_target_resource[i] = -1
                    self.resource_seek_steps[i] = 0
                    continue

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

        # 5. 能量變動後更新質量（供下一步物理與能耗使用）
        self._update_mass_from_energy()

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

            # 🔧 FIX: 檢查資源是否已失效（耗盡且無補充）
            # 如果失效，清除所有 agents 的目標
            resource_depleted = False
            if self.resources.resource_active[res_id] == 0:
                resource_depleted = True

            # 平分
            per_agent_gain = (consumed / n_consumers) * conversion_efficiency if consumed > 0 else 0.0

            for agent_idx in agent_indices:
                current_energy = self.agent_energy[agent_idx]
                gain_multiplier = 1.0
                if self.agent_type_field[agent_idx] == 3:
                    gain_multiplier = 1.25

                self.agent_energy[agent_idx] = min(
                    self.energy_max, current_energy + per_agent_gain * gain_multiplier
                )

                # 若能量已滿或資源已耗盡，清除目標
                if self.agent_energy[agent_idx] >= self.energy_max or resource_depleted:
                    self.agent_target_resource[agent_idx] = -1
                    self.resource_seek_steps[agent_idx] = 0

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
                gain_multiplier = 1.0
                if self.agent_type_field[agent_idx] == 3:
                    gain_multiplier = 1.25

                self.agent_energy[agent_idx] = min(
                    self.energy_max, current_energy + energy_gain * gain_multiplier
                )

                # 扣除已消耗量
                available -= consumed

                # 若能量已滿，清除目標
                if self.agent_energy[agent_idx] >= self.energy_max:
                    self.agent_target_resource[agent_idx] = -1
                    self.resource_seek_steps[agent_idx] = 0

    @ti.kernel
    def _check_energy_death(self):
        """
        檢查能量耗盡導致的死亡（只檢查前 N 個活躍 agents）

        邏輯：
            • 能量 <= 0 → 標記為死亡 (agent_alive = 0)
            • 死亡 agent 移動到遠離模擬區域的位置（消失）
            • 速度設為 0，不再參與物理交互
        """
        dead_zone = 1e6  # 遠離模擬區域的位置

        # 只檢查前 N 個 agents（實際活躍的）
        for i in range(self.N):
            if self.agent_energy[i] <= 0.0:
                # 標記為死亡
                self.agent_alive[i] = 0

                # 清除目標（避免死亡 agent 繼續鎖定資源）
                self.agent_target_resource[i] = -1
                self.resource_seek_steps[i] = 0

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

        # 統計死亡數（只統計前 N 個 agents）
        alive_arr = self.agent_alive.to_numpy()[: self.N]
        alive_count = int(alive_arr.sum())
        dead_count = self.N - alive_count

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
