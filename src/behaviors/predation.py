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
        # 掠食者目標與狀態
        self.agent_target_prey = ti.field(ti.i32, N)  # 目標獵物 ID（-1 = 無目標）
        self.agent_alive = ti.field(ti.i32, N)  # agent 是否存活（0/1）

        # 掠食者參數
        self.predator_hunt_range = ti.field(ti.f32, N)  # 追捕範圍
        self.predator_attack_range = ti.field(ti.f32, N)  # 攻擊範圍

        # 初始化
        self.agent_target_prey.fill(-1)
        self.agent_alive.fill(1)  # 所有 agent 初始存活

        print(f"[PredationBehavior] Initialized for N={N} agents")

    @ti.kernel
    def find_nearest_prey(self):
        """
        掠食者搜尋最近的獵物

        邏輯：
            • 只有 PREDATOR 類型（type=3）會執行
            • 搜尋範圍內最近且存活的非掠食者
            • 更新 agent_target_prey[i]
        """
        for i in self.x:
            # 只有存活的掠食者才追捕
            if self.agent_type_field[i] == 3 and self.agent_alive[i] == 1:  # PREDATOR
                hunt_range = self.predator_hunt_range[i]
                min_dist = hunt_range
                best_prey = -1

                # 搜尋所有存活的非掠食者
                for j in range(self.N):
                    if i == j:
                        continue

                    # 只追捕存活且非掠食者的 agent
                    if self.agent_alive[j] == 1 and self.agent_type_field[j] != 3:
                        # 計算距離（考慮 PBC）
                        dx = ti.Vector([0.0, 0.0, 0.0])
                        if self.params.boundary_mode == 0:  # PBC
                            dx = self.pbc_dist(self.x[i], self.x[j])
                        else:
                            dx = self.x[j] - self.x[i]

                        dist = dx.norm()

                        if dist < min_dist:
                            min_dist = dist
                            best_prey = j

                # 更新目標獵物
                self.agent_target_prey[i] = best_prey

    def attack_prey_step(self):
        """
        處理掠食者攻擊（每步呼叫一次）

        邏輯：
            • 掠食者在攻擊範圍內嘗試捕食獵物
            • 攻擊成功率動態計算（速度優勢、獵物虛弱度、掠食者體力）
            • 成功：獵物死亡，掠食者獲得能量
            • 失敗：掠食者損失體力
        """
        x_np = self.x.to_numpy()
        v_np = self.v.to_numpy()
        target_prey_np = self.agent_target_prey.to_numpy()
        alive_np = self.agent_alive.to_numpy()
        agent_type_np = self.agent_type_field.to_numpy()

        for i in range(len(x_np)):
            # 只有存活的掠食者才能攻擊
            if agent_type_np[i] == 3 and alive_np[i] == 1:  # PREDATOR
                target_prey = target_prey_np[i]

                if target_prey >= 0 and alive_np[target_prey] == 1:
                    # 計算距離
                    predator_pos = x_np[i]
                    prey_pos = x_np[target_prey]
                    distance = np.linalg.norm(predator_pos - prey_pos)

                    # 獲取攻擊範圍
                    attack_range = self.predator_attack_range[i]

                    if distance < attack_range:
                        # === 計算攻擊成功率（新增動態判定）===
                        success_rate = self._compute_attack_success_rate(
                            i, target_prey, v_np
                        )

                        # 擲骰子判定
                        if np.random.rand() < success_rate:
                            # 捕食成功！
                            prey_energy = self.agent_energy[target_prey]
                            energy_gain = prey_energy * 0.7
                            current_energy = self.agent_energy[i]
                            self.agent_energy[i] = min(
                                100.0, current_energy + energy_gain
                            )

                            print(
                                f"🦁 Predator {i} captured prey {target_prey}! "
                                f"(Success rate: {success_rate:.1%}, "
                                f"Gained {energy_gain:.1f} energy from prey's {prey_energy:.1f})"
                            )

                            # 獵物死亡：標記 + 消失
                            self._remove_dead_agent(target_prey)
                            self.agent_target_prey[i] = -1  # 清除目標
                        else:
                            # 攻擊失敗！消耗額外能量
                            energy_penalty = 10.0
                            self.agent_energy[i] = max(
                                0.0, self.agent_energy[i] - energy_penalty
                            )

                            print(
                                f"💨 Predator {i} failed to catch prey {target_prey} "
                                f"(Success rate: {success_rate:.1%}, Lost {energy_penalty:.1f} energy)"
                            )

    def _compute_attack_success_rate(
        self, predator_id: int, prey_id: int, v_np: np.ndarray
    ) -> float:
        """
        計算攻擊成功率（動態判定）

        考慮因素：
            • 速度優勢：掠食者越快於獵物，成功率越高
            • 獵物虛弱度：獵物能量越低，越容易被捕
            • 掠食者體力：掠食者能量不足會降低成功率
            • 群體防禦：獵物附近同伴越多，成功率越低（稀釋效應）

        Returns:
            攻擊成功率 (0.0-1.0)
        """
        # === 1. 速度優勢 ===
        v_predator = np.linalg.norm(v_np[predator_id])
        v_prey = np.linalg.norm(v_np[prey_id])

        # 速度優勢：(v_predator - v_prey) / v_predator
        # 範圍：[-inf, 1.0]，限制在 [0, 1]
        if v_predator > 1e-6:
            speed_advantage = max(0.0, (v_predator - v_prey) / v_predator)
        else:
            speed_advantage = 0.0

        # === 2. 獵物虛弱度 ===
        prey_energy = self.agent_energy[prey_id]
        prey_weakness = 1.0 - (prey_energy / 100.0)  # 能量越低越弱

        # === 3. 掠食者體力 ===
        predator_energy = self.agent_energy[predator_id]
        predator_stamina = predator_energy / 100.0  # 能量越低越弱

        # === 4. 群體防禦（稀釋效應）===
        group_defense = self._compute_group_defense_bonus(prey_id)

        # === 綜合成功率 ===
        base_rate = 0.3  # 基礎 30%
        success_rate = (
            base_rate
            + 0.25 * speed_advantage  # 速度優勢貢獻 25%
            + 0.25 * prey_weakness  # 獵物虛弱貢獻 25%
        )
        success_rate *= predator_stamina  # 掠食者體力乘數
        success_rate *= group_defense  # 群體防禦乘數

        # 限制在 [0.05, 0.95] 範圍內（總有小機率成功/失敗）
        return np.clip(success_rate, 0.05, 0.95)

    def _compute_group_defense_bonus(self, prey_id: int) -> float:
        """
        計算群體防禦加成（稀釋效應）

        機制：
            • 周圍同類越多 → 被攻擊機率越低
            • 每多 1 個同伴，成功率降低 5%
            • 最多降至 30%

        Returns:
            防禦乘數 (0.3-1.0)
        """
        x_np = self.x.to_numpy()
        alive_np = self.agent_alive.to_numpy()
        agent_type_np = self.agent_type.to_numpy()

        prey_pos = x_np[prey_id]
        prey_type = agent_type_np[prey_id]
        group_range = 5.0  # 5 單位內算同群

        n_nearby = 0
        for j in range(len(x_np)):
            if j == prey_id:
                continue
            if alive_np[j] == 0:
                continue
            if agent_type_np[j] != prey_type:  # 必須同類
                continue

            dist = np.linalg.norm(x_np[j] - prey_pos)
            if dist < group_range:
                n_nearby += 1

        # 稀釋效應：每多 1 個同伴，攻擊成功率降低 5%
        dilution_factor = 1.0 - (n_nearby * 0.05)

        # 最多降到 30%
        return max(0.3, dilution_factor)

    def _remove_dead_agent(self, agent_id: int):
        """
        移除死亡的 agent（讓它消失）

        Args:
            agent_id: 死亡 agent 的 ID
        """
        dead_zone = 1e6  # 遠離模擬區域的位置

        # 標記為死亡
        self.agent_alive[agent_id] = 0

        # 移動到遠處（消失）
        x_np = self.x.to_numpy()
        x_np[agent_id] = [dead_zone, dead_zone, dead_zone]
        self.x.from_numpy(x_np)

        # 停止運動
        v_np = self.v.to_numpy()
        v_np[agent_id] = [0.0, 0.0, 0.0]
        self.v.from_numpy(v_np)

    # ========================================================================
    # Query API
    # ========================================================================
    def get_alive_count(self) -> int:
        """獲取存活 agent 數量（只統計前 N 個活躍 agents）"""
        return int(self.agent_alive.to_numpy()[: self.N].sum())

    def get_predator_count(self) -> int:
        """獲取掠食者數量"""
        agent_type_np = self.agent_type.to_numpy()
        return int((agent_type_np == 3).sum())

    def get_prey_count(self) -> int:
        """獲取獵物數量（非掠食者且存活）"""
        agent_type_np = self.agent_type.to_numpy()
        alive_np = self.agent_alive.to_numpy()
        return int(((agent_type_np != 3) & (alive_np == 1)).sum())
