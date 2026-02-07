"""
Unit Tests for NavigationMixin (Phase 6.2)

測試 Goal-seeking navigation 功能的正確性
"""

import pytest
import taichi as ti
import numpy as np
from navigation.goal_seeking import NavigationMixin, set_leader_goals
from flocking_3d import Flocking3D, FlockingParams


@ti.data_oriented
class TestNavigationSystem(Flocking3D, NavigationMixin):
    """
    測試用的最小系統，結合基礎物理 + Navigation
    """

    def __init__(self, N: int):
        super().__init__(N, FlockingParams())
        self.init_navigation(N)


class TestNavigationBasic:
    """基本導航功能測試"""

    def setup_method(self):
        """每個測試前重新初始化 Taichi"""
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_navigation_initialization(self):
        """測試導航系統正確初始化"""
        system = TestNavigationSystem(N=10)

        # 驗證 fields 存在
        assert hasattr(system, "goal")
        assert hasattr(system, "has_goal")
        assert hasattr(system, "goal_strength")

        # 驗證預設值：無目標
        has_goal_arr = system.has_goal.to_numpy()
        assert np.all(has_goal_arr == 0), "預設應無目標"

    def test_set_goals_explicit_indices(self):
        """測試設定特定 agent 的目標"""
        system = TestNavigationSystem(N=10)

        # 為 agent 0, 2, 5 設定目標
        goals = np.array([[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]])
        agent_indices = np.array([0, 2, 5])
        system.set_goals(goals, agent_indices)

        # 驗證 has_goal
        has_goal_arr = system.has_goal.to_numpy()
        assert has_goal_arr[0] == 1
        assert has_goal_arr[2] == 1
        assert has_goal_arr[5] == 1
        assert has_goal_arr[1] == 0  # 未設定的應為 0

        # 驗證目標位置
        goal_0 = system.goal[0]
        assert np.allclose(goal_0, [10.0, 0.0, 0.0], atol=1e-6)

    def test_set_goals_auto_selection(self):
        """測試自動選擇 goal_strength > 0 的 agent"""
        system = TestNavigationSystem(N=10)

        # 設定 goal_strength
        system.goal_strength[1] = 2.0
        system.goal_strength[3] = 1.5

        # 自動為 goal_strength > 0 的 agent 設定目標
        goals = np.array([[5.0, 5.0, 5.0], [10.0, 10.0, 10.0]])
        system.set_goals(goals)  # 不指定 agent_indices

        # 驗證 agent 1, 3 有目標
        has_goal_arr = system.has_goal.to_numpy()
        assert has_goal_arr[1] == 1
        assert has_goal_arr[3] == 1
        assert has_goal_arr[0] == 0

    def test_clear_goals_specific(self):
        """測試清除特定 agent 的目標"""
        system = TestNavigationSystem(N=10)

        # 設定目標
        goals = np.array([[10.0, 0.0, 0.0], [0.0, 10.0, 0.0]])
        system.set_goals(goals, agent_indices=[0, 2])

        # 清除 agent 0 的目標
        system.clear_goals(agent_indices=[0])

        # 驗證
        has_goal_arr = system.has_goal.to_numpy()
        assert has_goal_arr[0] == 0, "Agent 0 的目標應被清除"
        assert has_goal_arr[2] == 1, "Agent 2 的目標應保留"

    def test_clear_goals_all(self):
        """測試清除所有目標"""
        system = TestNavigationSystem(N=10)

        # 設定目標
        goals = np.array([[10.0, 0.0, 0.0]] * 5)
        system.set_goals(goals, agent_indices=[0, 1, 2, 3, 4])

        # 清除所有目標
        system.clear_goals()

        # 驗證
        has_goal_arr = system.has_goal.to_numpy()
        assert np.all(has_goal_arr == 0), "所有目標應被清除"


class TestGoalSeekingForce:
    """測試目標導向力計算"""

    def setup_method(self):
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_goal_seeking_force_direction(self):
        """測試目標導向力的方向正確"""
        system = TestNavigationSystem(N=10)

        # Agent 0: 位於原點，目標在 +X 方向
        system.x[0] = [0.0, 0.0, 0.0]
        system.goal[0] = [10.0, 0.0, 0.0]
        system.has_goal[0] = 1
        system.goal_strength[0] = 1.0

        # 測試力的方向
        @ti.kernel
        def test() -> ti.f32:
            force = system.goal_seeking_force(0)
            # 力應指向 +X 方向（force.x > 0）
            return force.x

        force_x = test()
        assert force_x > 0, "力應指向目標（+X 方向）"

    def test_goal_seeking_force_magnitude(self):
        """測試目標導向力的大小受 goal_strength 影響"""
        system = TestNavigationSystem(N=10)

        # Agent 0: 目標導向強度 = 2.0
        system.x[0] = [0.0, 0.0, 0.0]
        system.goal[0] = [10.0, 0.0, 0.0]
        system.has_goal[0] = 1
        system.goal_strength[0] = 2.0

        # Agent 1: 目標導向強度 = 1.0（相同距離）
        system.x[1] = [0.0, 0.0, 0.0]
        system.goal[1] = [10.0, 0.0, 0.0]
        system.has_goal[1] = 1
        system.goal_strength[1] = 1.0

        @ti.kernel
        def test() -> ti.f32:
            force0 = system.goal_seeking_force(0)
            force1 = system.goal_seeking_force(1)
            # 返回力的比值
            return force0.norm() / force1.norm()

        ratio = test()
        assert abs(ratio - 2.0) < 0.01, "力的大小應與 goal_strength 成正比"

    def test_goal_seeking_force_no_goal(self):
        """測試無目標時力為零"""
        system = TestNavigationSystem(N=10)

        # Agent 0: 無目標
        system.x[0] = [0.0, 0.0, 0.0]
        system.has_goal[0] = 0  # 無目標

        @ti.kernel
        def test() -> ti.f32:
            force = system.goal_seeking_force(0)
            return force.norm()

        force_magnitude = test()
        assert force_magnitude < 1e-6, "無目標時力應為零"

    def test_goal_seeking_force_pbc_aware(self):
        """測試 PBC 下的最短路徑導向"""
        system = TestNavigationSystem(N=10)
        system.p[8] = 50.0  # box_size = 50
        system.p[12] = 0  # PBC mode

        # Agent 0: 位於 (45, 0, 0)，目標在 (5, 0, 0)
        # PBC 下最短路徑應是 +X 方向（距離 10），而非 -X 方向（距離 40）
        system.x[0] = [45.0, 0.0, 0.0]
        system.goal[0] = [5.0, 0.0, 0.0]
        system.has_goal[0] = 1
        system.goal_strength[0] = 1.0

        @ti.kernel
        def test() -> ti.f32:
            force = system.goal_seeking_force(0)
            # PBC 下應指向 +X（最短路徑）
            return force.x

        force_x = test()
        assert force_x > 0, "PBC 下應選擇最短路徑（+X 方向）"

    def test_goal_seeking_force_at_goal(self):
        """測試到達目標時的行為"""
        system = TestNavigationSystem(N=10)

        # Agent 0: 已在目標位置
        system.x[0] = [10.0, 10.0, 10.0]
        system.goal[0] = [10.0, 10.0, 10.0]
        system.has_goal[0] = 1
        system.goal_strength[0] = 1.0

        @ti.kernel
        def test() -> ti.f32:
            force = system.goal_seeking_force(0)
            return force.norm()

        force_magnitude = test()
        # distance = 0，應避免除以零，返回零力或非常小的力
        assert force_magnitude < 1e-3, "到達目標時力應接近零"


class TestUtilityFunctions:
    """測試便捷函數"""

    def setup_method(self):
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_set_leader_goals(self):
        """測試 set_leader_goals 便捷函數"""
        from flocking_heterogeneous import HeterogeneousFlocking3D
        from agents.types import AgentType

        # 創建包含 LEADER 的系統
        N = 20
        agent_types = [AgentType.FOLLOWER] * 15 + [AgentType.LEADER] * 5
        system = HeterogeneousFlocking3D(
            N=N, params=FlockingParams(), agent_types=agent_types
        )
        system.initialize(box_size=50.0)

        # 使用便捷函數設定 LEADER 目標
        set_leader_goals(system, goal_position=[25.0, 25.0, 25.0])

        # 驗證所有 LEADER 有目標
        agent_types_arr = system.agent_type_field.to_numpy()
        has_goal_arr = system.has_goal.to_numpy()

        leader_indices = np.where(agent_types_arr == AgentType.LEADER)[0]
        for idx in leader_indices:
            assert has_goal_arr[idx] == 1, f"LEADER {idx} 應有目標"
            goal_pos = system.goal[idx]
            assert np.allclose(goal_pos, [25.0, 25.0, 25.0], atol=1e-6)


class TestEdgeCases:
    """邊界情況測試"""

    def setup_method(self):
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_set_goals_mismatched_size(self):
        """測試 goals 與 agent_indices 數量不符時拋出錯誤"""
        system = TestNavigationSystem(N=10)

        with pytest.raises(AssertionError, match="數量.*相同"):
            # 3 個目標，但只有 2 個 agent
            goals = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
            system.set_goals(goals, agent_indices=[0, 1])

    def test_set_goals_single_goal(self):
        """測試設定單一目標（1D 輸入）"""
        system = TestNavigationSystem(N=10)

        # 單一目標（應被轉為 2D）
        goal = np.array([10.0, 10.0, 10.0])
        system.set_goals(goal, agent_indices=[0])

        # 驗證
        has_goal_arr = system.has_goal.to_numpy()
        assert has_goal_arr[0] == 1

    @pytest.mark.skip(reason="Taichi 不支援 N=0 fields（底層限制，非程式錯誤）")
    def test_navigation_with_zero_agents(self):
        """測試 N=0 的邊界情況"""
        # 雖然不太可能發生，但應該不會崩潰
        try:
            system = TestNavigationSystem(N=0)
            assert True, "N=0 應該不會崩潰"
        except Exception as e:
            pytest.fail(f"N=0 導致崩潰: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
