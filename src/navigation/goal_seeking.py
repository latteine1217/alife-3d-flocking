"""
Goal-seeking Navigation Module

提供目標導向行為（Goal-seeking）的 Mixin 類別。

功能：
    • 每個 agent 可擁有獨立的目標位置
    • PBC-aware 目標導向力計算
    • 可配置目標強度（per-agent）
    • 支援動態設定/移除目標

設計理念：
    遵循 Mixin 模式，使用 init_navigation() 動態初始化欄位，
    避免與 Taichi @ti.data_oriented 的衝突。
"""

import taichi as ti
import numpy as np
from typing import Optional


@ti.data_oriented
class NavigationMixin:
    """
    Goal-seeking Navigation Mixin

    提供目標導向行為功能，agent 會朝向設定的目標位置移動。

    Fields (動態建立):
        goal: ti.Vector.field(3, ti.f32, N) - 每個 agent 的目標位置
        has_goal: ti.field(ti.i32, N) - 是否有目標（0/1）
        goal_strength: ti.field(ti.f32, N) - 目標導向力強度

    Methods:
        init_navigation(N): 初始化導航系統
        set_goals(goals, agent_indices): 設定 agent 的目標位置
        clear_goals(agent_indices): 清除 agent 的目標
        goal_seeking_force(i): 計算目標導向力（Taichi function）

    Usage:
        class MySystem(Flocking3D, NavigationMixin):
            def __init__(self, N):
                super().__init__(N, ...)
                self.init_navigation(N)

            @ti.kernel
            def compute_forces(self):
                for i in self.x:
                    # 加入目標導向力
                    self.f[i] += self.goal_seeking_force(i)
    """

    def init_navigation(self, N: int):
        """
        初始化導航系統

        Args:
            N: Agent 數量

        Side Effects:
            建立以下 Taichi fields:
            - self.goal: 目標位置 (N, 3)
            - self.has_goal: 是否有目標 (N,)
            - self.goal_strength: 目標導向強度 (N,)

        Notes:
            • 預設所有 agent 無目標（has_goal=0）
            • 預設 goal_strength=0.0（需由外部設定）
        """
        self.goal = ti.Vector.field(3, ti.f32, N)
        self.has_goal = ti.field(ti.i32, N)
        self.goal_strength = ti.field(ti.f32, N)

        # 預設值：無目標
        self.has_goal.fill(0)
        self.goal_strength.fill(0.0)

        print(f"[NavigationMixin] Initialized for N={N} agents")

    def set_goals(self, goals: np.ndarray, agent_indices: Optional[np.ndarray] = None):
        """
        設定 agent 的目標位置

        Args:
            goals: 目標位置陣列
                   - Shape: (M, 3) 或 (3,)
                   - M 個目標對應 M 個 agent
            agent_indices: 哪些 agent 有目標（可選）
                          - Shape: (M,)
                          - 若為 None，自動選擇 goal_strength > 0 的 agent

        Raises:
            AssertionError: 若 goals 數量與 agent_indices 數量不符

        Example:
            # 為 agent 0, 2, 5 設定目標
            goals = np.array([[10, 0, 0], [0, 10, 0], [0, 0, 10]])
            system.set_goals(goals, agent_indices=[0, 2, 5])

            # 自動為 goal_strength > 0 的 agent 設定目標
            goals = np.array([[10, 10, 10]])
            system.set_goals(goals)  # 選擇第一個 goal_strength > 0 的 agent
        """
        goals = np.atleast_2d(goals).astype(np.float32)

        if agent_indices is None:
            # 自動選擇：goal_strength > 0 的 agent
            goal_strength_arr = self.goal_strength.to_numpy()
            agent_indices = np.where(goal_strength_arr > 0)[0]

        assert len(goals) == len(agent_indices), (
            f"goals 數量 ({len(goals)}) 必須與 agent_indices 數量 ({len(agent_indices)}) 相同"
        )

        # 設定目標
        for i, idx in enumerate(agent_indices):
            self.goal[idx] = goals[i]
            self.has_goal[idx] = 1

        print(f"[NavigationMixin] Set goals for {len(agent_indices)} agents")

    def clear_goals(self, agent_indices: Optional[np.ndarray] = None):
        """
        清除 agent 的目標

        Args:
            agent_indices: 要清除目標的 agent（可選）
                          - 若為 None，清除所有 agent 的目標

        Example:
            # 清除 agent 0, 2 的目標
            system.clear_goals(agent_indices=[0, 2])

            # 清除所有目標
            system.clear_goals()
        """
        if agent_indices is None:
            # 清除所有目標
            self.has_goal.fill(0)
            print("[NavigationMixin] Cleared all goals")
        else:
            # 清除特定 agent 的目標
            for idx in agent_indices:
                self.has_goal[idx] = 0
            print(f"[NavigationMixin] Cleared goals for {len(agent_indices)} agents")

    @ti.func
    def goal_seeking_force(self, i: ti.i32) -> ti.math.vec3:
        """
        計算目標導向力（考慮 PBC）

        Args:
            i: Agent 索引

        Returns:
            目標導向力向量 (3D)
            - 若無目標，返回零向量
            - 若有目標，返回指向目標的力：
              F = goal_strength * direction / distance

        Algorithm:
            1. 檢查 has_goal[i] == 1
            2. 使用 pbc_dist() 計算最短路徑方向
            3. 標準化方向 × goal_strength

        Notes:
            • 這是 @ti.func，只能在 @ti.kernel 中呼叫
            • 使用 pbc_dist() 確保 PBC 下正確導向
            • distance < 1e-6 時避免除以零

        Example:
            @ti.kernel
            def compute_forces(self):
                for i in self.x:
                    self.f[i] += self.goal_seeking_force(i)
        """
        force = ti.Vector([0.0, 0.0, 0.0])

        if self.has_goal[i] == 1:
            # 使用 PBC-aware 距離計算
            direction = self.pbc_dist(self.x[i], self.goal[i])
            distance = direction.norm()

            if distance > 1e-6:
                # 標準化方向 × 強度
                force = self.goal_strength[i] * direction / distance

        return force


# ============================================================================
# Utility Functions
# ============================================================================


def set_leader_goals(
    system,
    goal_position: np.ndarray,
    leader_type: int = 2,  # AgentType.LEADER
):
    """
    便捷函數：為所有 LEADER 設定相同目標

    Args:
        system: HeterogeneousFlocking3D 實例
        goal_position: 目標位置 (3,)
        leader_type: LEADER 的類型代碼（預設 2）

    Example:
        from navigation.goal_seeking import set_leader_goals

        system = HeterogeneousFlocking3D(...)
        set_leader_goals(system, goal_position=[25.0, 25.0, 25.0])
    """
    agent_types = system.agent_type.to_numpy()
    leader_indices = np.where(agent_types == leader_type)[0]

    if len(leader_indices) == 0:
        print("[set_leader_goals] Warning: No LEADER agents found")
        return

    goals = np.tile(goal_position, (len(leader_indices), 1))
    system.set_goals(goals, leader_indices)
    print(f"[set_leader_goals] Set goal for {len(leader_indices)} LEADERs")
