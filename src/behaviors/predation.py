"""
Predation Behavior Mixin

提供掠食與獵捕功能：
    • 掠食者搜尋獵物
    • 追捕與攻擊邏輯
    • 獵物存活狀態管理
"""

import taichi as ti
import numpy as np


@ti.data_oriented
class PredationBehaviorMixin:
    """
    掠食行為 Mixin

    依賴：
        • self.x: Agent 位置 (ti.Vector.field)
        • self.agent_type: Agent 類型 (ti.field(ti.i32))
        • self.params.boundary_mode: 邊界模式
        • self.pbc_dist(): PBC 距離計算函式
        • self.agent_energy: 能量系統（ForagingBehaviorMixin）

    提供功能：
        • 掠食者搜尋獵物
        • 攻擊與捕食邏輯
        • 存活狀態管理
    """

    def init_predation(self, N: int):
        """
        初始化掠食行為

        Args:
            N: Agent 數量
        """
        # 保存 predation 使用的容量（支援 pre-allocated pool + 繁殖）
        # 注意：不要使用 self.N（它在某些系統代表「初始活躍數量」而非容量）
        self.predation_N = int(N)

        # 掠食者目標與狀態
        self.agent_target_prey = ti.field(ti.i32, N)  # 目標獵物 ID（-1 = 無目標）
        # agent_alive 可能由主系統先建立（例如 pre-allocated pool）
        # 向後相容：若不存在才建立；避免覆寫使用者設定的存活分佈。
        created_agent_alive = False
        if not hasattr(self, "agent_alive"):
            self.agent_alive = ti.field(ti.i32, N)  # agent 是否存活（0/1）
            created_agent_alive = True

        # 掠食者參數
        self.predator_hunt_range = ti.field(ti.f32, N)  # 追捕範圍
        self.predator_attack_range = ti.field(ti.f32, N)  # 攻擊範圍

        # 群體防禦乘數（預先計算）
        self.agent_group_defense_multiplier = ti.field(ti.f32, N)

        # 初始化
        self.agent_target_prey.fill(-1)
        if created_agent_alive:
            # 兼容舊行為：Predation 單獨使用時，預設全存活
            self.agent_alive.fill(1)
        self.agent_group_defense_multiplier.fill(1.0)

        print(f"[PredationBehavior] Initialized for N={N} agents")

    @ti.kernel
    def find_nearest_prey(self):
        """
        掠食者搜尋最近的獵物（使用 Spatial Grid 加速）

        邏輯：
            • 只有 PREDATOR 類型（type=3）會執行
            • 使用 Grid 搜尋 27 個鄰近 cells，取代 O(N²) 全局搜尋
            • 限制檢查數量避免編譯超時（max_check=12）
            • 更新 agent_target_prey[i]

        複雜度：O(N_predators × k)，k ≈ 12
        """
        for i in self.x:
            # 只有存活的掠食者才追捕
            if self.agent_type_field[i] == 3 and self.agent_alive[i] == 1:  # PREDATOR
                hunt_range = self.predator_hunt_range[i]
                min_dist = hunt_range
                best_prey = -1

                # 獲取掠食者所在的 cell
                cell_id = self.agent_cell_id[i]
                if cell_id < 0:
                    continue

                # 解析 cell_id 為 3D index (ix, iy, iz)
                res = self.grid_resolution
                iz = cell_id // (res * res)
                remainder = cell_id % (res * res)
                iy = remainder // res
                ix = remainder % res

                # 使用 loop unrolling 搜尋 27 個鄰近 cells
                for cell_offset in ti.static(range(27)):
                    dz = (cell_offset // 9) - 1
                    dy = ((cell_offset % 9) // 3) - 1
                    dx = (cell_offset % 3) - 1

                    nx = ix + dx
                    ny = iy + dy
                    nz = iz + dz

                    # 邊界檢查
                    if (
                        nx >= 0
                        and nx < res
                        and ny >= 0
                        and ny < res
                        and nz >= 0
                        and nz < res
                    ):
                        neighbor_cell = nx + ny * res + nz * res * res
                        cell_count = self.cell_count[neighbor_cell]

                        # 限制檢查數量避免編譯超時
                        max_check = ti.min(cell_count, 12)

                        for local_idx in range(max_check):
                            j = self.cell_agents[neighbor_cell, local_idx]
                            if i == j:
                                continue

                            # 只追捕存活且非掠食者的 agent
                            if (
                                self.agent_alive[j] == 1
                                and self.agent_type_field[j] != 3
                            ):
                                # 計算距離（考慮 PBC）
                                dx_vec = ti.Vector([0.0, 0.0, 0.0])
                                if self.params.boundary_mode == 0:  # PBC
                                    dx_vec = self.pbc_dist(self.x[i], self.x[j])
                                else:
                                    dx_vec = self.x[j] - self.x[i]

                                dist = dx_vec.norm()

                                if dist < min_dist:
                                    min_dist = dist
                                    best_prey = j

                # 更新目標獵物
                self.agent_target_prey[i] = best_prey

    @ti.kernel
    def attack_prey_kernel(
        self,
        base_rate: ti.f32,
        speed_weight: ti.f32,
        weakness_weight: ti.f32,
        energy_conversion: ti.f32,
        energy_penalty: ti.f32,
    ) -> ti.i32:
        """
        處理掠食者攻擊（Taichi kernel 版本）

        邏輯：
            • 掠食者在攻擊範圍內嘗試捕食獵物
            • 攻擊成功率動態計算（速度優勢、獵物虛弱度、掠食者體力、群體防禦）
            • 成功：獵物死亡，掠食者獲得能量
            • 失敗：掠食者損失體力

        Returns:
            成功捕食的數量
        """
        success_count = 0

        for i in self.x:
            # 只有存活的掠食者才能攻擊
            if self.agent_type_field[i] != 3 or self.agent_alive[i] != 1:
                continue

            target_prey = self.agent_target_prey[i]

            # 檢查目標是否有效
            if target_prey < 0 or target_prey >= self.predation_N:
                continue
            if self.agent_alive[target_prey] != 1:
                continue

            # 計算距離
            dx_vec = ti.Vector([0.0, 0.0, 0.0])
            if self.params.boundary_mode == 0:  # PBC
                dx_vec = self.pbc_dist(self.x[i], self.x[target_prey])
            else:
                dx_vec = self.x[target_prey] - self.x[i]

            distance = dx_vec.norm()
            attack_range = self.predator_attack_range[i]

            if distance < attack_range:
                # === 計算攻擊成功率 ===
                # 1. 速度優勢
                v_predator = self.v[i].norm()
                v_prey = self.v[target_prey].norm()
                speed_advantage = 0.0
                if v_predator > 1e-6:
                    speed_advantage = ti.max(0.0, (v_predator - v_prey) / v_predator)

                # 2. 獵物虛弱度
                prey_energy = self.agent_energy[target_prey]
                energy_max = ti.max(self.energy_max, 1e-6)
                prey_weakness = 1.0 - (prey_energy / energy_max)

                # 3. 掠食者體力
                predator_energy = self.agent_energy[i]
                predator_stamina = predator_energy / energy_max

                # 4. 群體防禦（預先計算）
                group_defense = self.agent_group_defense_multiplier[target_prey]

                # 綜合成功率
                success_rate = (
                    base_rate
                    + speed_weight * speed_advantage
                    + weakness_weight * prey_weakness
                )
                success_rate *= predator_stamina
                success_rate *= group_defense
                success_rate = ti.max(0.05, ti.min(0.95, success_rate))

                # 擲骰子判定
                if ti.random(ti.f32) < success_rate:
                    # 捕食成功！
                    energy_gain = prey_energy * energy_conversion
                    current_energy = self.agent_energy[i]
                    self.agent_energy[i] = ti.min(
                        self.energy_max, current_energy + energy_gain
                    )

                    # 獵物死亡（移到遠處）
                    dead_zone = 1e6
                    self.agent_alive[target_prey] = 0
                    self.x[target_prey] = ti.Vector([dead_zone, dead_zone, dead_zone])
                    self.v[target_prey] = ti.Vector([0.0, 0.0, 0.0])
                    self.f[target_prey] = ti.Vector([0.0, 0.0, 0.0])

                    # 清除目標
                    self.agent_target_prey[i] = -1
                    ti.atomic_add(success_count, 1)
                else:
                    # 攻擊失敗！消耗額外能量
                    self.agent_energy[i] = ti.max(
                        0.0, self.agent_energy[i] - energy_penalty
                    )

        return success_count

    def attack_prey_step(self):
        """
        處理掠食者攻擊（Python 介面）

        調用 Taichi kernel 進行 GPU 加速計算
        """
        # 預先計算群體防禦乘數
        self.compute_group_defense(group_range=5.0)

        # 調用 kernel 處理攻擊
        success_count = self.attack_prey_kernel(
            base_rate=0.3,
            speed_weight=0.25,
            weakness_weight=0.25,
            energy_conversion=0.7,
            energy_penalty=10.0,
        )

        if success_count > 0:
            print(f"🦁 {success_count} successful predations this step")

    @ti.kernel
    def compute_group_defense(self, group_range: ti.f32):
        """
        預先計算每個 agent 的群體防禦加成（使用 Grid 加速）

        機制：
            • 使用 Spatial Grid 搜尋鄰近同類
            • 周圍同類越多 → 防禦乘數越低（稀釋效應）
            • 每多 1 個同伴，攻擊成功率降低 5%
            • 最多降至 30%

        將結果存儲在 agent_group_defense_multiplier field 中
        """
        for i in self.x:
            if self.agent_alive[i] == 0:
                self.agent_group_defense_multiplier[i] = 1.0
                continue

            prey_type = self.agent_type_field[i]
            n_nearby = 0

            # 獲取 agent i 所在的 cell
            cell_id = self.agent_cell_id[i]
            if cell_id < 0:
                self.agent_group_defense_multiplier[i] = 1.0
                continue

            # 解析 cell_id 為 3D index (ix, iy, iz)
            res = self.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res

            # 搜尋 27 個鄰近 cells（loop unrolling）
            for cell_offset in ti.static(range(27)):
                dz = (cell_offset // 9) - 1
                dy = ((cell_offset % 9) // 3) - 1
                dx = (cell_offset % 3) - 1

                nx = ix + dx
                ny = iy + dy
                nz = iz + dz

                # 邊界檢查
                if (
                    nx >= 0
                    and nx < res
                    and ny >= 0
                    and ny < res
                    and nz >= 0
                    and nz < res
                ):
                    neighbor_cell = nx + ny * res + nz * res * res
                    cell_count = self.cell_count[neighbor_cell]

                    # 限制檢查數量
                    max_check = ti.min(cell_count, 12)

                    for local_idx in range(max_check):
                        j = self.cell_agents[neighbor_cell, local_idx]
                        if i == j:
                            continue
                        if self.agent_alive[j] == 0:
                            continue
                        if self.agent_type_field[j] != prey_type:
                            continue

                        # 計算距離
                        dx_vec = ti.Vector([0.0, 0.0, 0.0])
                        if self.params.boundary_mode == 0:  # PBC
                            dx_vec = self.pbc_dist(self.x[i], self.x[j])
                        else:
                            dx_vec = self.x[j] - self.x[i]

                        dist = dx_vec.norm()

                        if dist < group_range:
                            n_nearby += 1

            # 稀釋效應：每多 1 個同伴，攻擊成功率降低 5%
            dilution_factor = 1.0 - (ti.cast(n_nearby, ti.f32) * 0.05)

            # 最多降到 30%
            self.agent_group_defense_multiplier[i] = ti.max(0.3, dilution_factor)

    # ========================================================================
    # Query API
    # ========================================================================
    def get_alive_count(self) -> int:
        """獲取存活 agent 數量（只統計前 N 個活躍 agents）"""
        return int(self.agent_alive.to_numpy()[: self.N].sum())

    def get_predator_count(self) -> int:
        """獲取掠食者數量"""
        agent_type_np = self.agent_type_field.to_numpy()
        return int((agent_type_np == 3).sum())

    def get_prey_count(self) -> int:
        """獲取獵物數量（非掠食者且存活）"""
        agent_type_np = self.agent_type_field.to_numpy()
        alive_np = self.agent_alive.to_numpy()
        return int(((agent_type_np != 3) & (alive_np == 1)).sum())
