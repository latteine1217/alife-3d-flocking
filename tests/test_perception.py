"""
Unit Tests for PerceptionMixin (Phase 6.1)

測試 FOV (Field of View) 功能的正確性
"""

import pytest
import taichi as ti
import numpy as np
from perception.fov import PerceptionMixin
from flocking_3d import Flocking3D, FlockingParams


@ti.data_oriented
class TestPerceptionSystem(Flocking3D, PerceptionMixin):
    """
    測試用的最小系統，結合基礎物理 + FOV
    """

    def __init__(self, N: int, fov_angle: float = 90.0, enable_fov: bool = True):
        super().__init__(N, FlockingParams())
        self.init_perception(N, fov_angle=fov_angle, enable_fov=enable_fov)


class TestFOVBasic:
    """基本 FOV 功能測試"""

    def setup_method(self):
        """每個測試前重新初始化 Taichi"""
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_fov_90_degree_front(self):
        """90度視野：應該能看到正前方的 agent"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=True)

        # Agent 0: 位於原點，朝 +X 方向移動
        system.x[0] = [0.0, 0.0, 0.0]
        system.v[0] = [1.0, 0.0, 0.0]

        # Agent 1 在正前方 (+X 方向)
        rij_front = ti.math.vec3(1.0, 0.0, 0.0)

        # 測試：應該在視野內
        @ti.kernel
        def test() -> ti.i32:
            return system.is_in_fov(system.v[0], rij_front)

        assert test() == 1, "正前方的 agent 應該在 90° FOV 內"

    def test_fov_90_degree_behind(self):
        """90度視野：不應該看到正後方的 agent"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=True)

        # Agent 0: 位於原點，朝 +X 方向移動
        system.x[0] = [0.0, 0.0, 0.0]
        system.v[0] = [1.0, 0.0, 0.0]

        # Agent 2 在正後方 (-X 方向)
        rij_behind = ti.math.vec3(-1.0, 0.0, 0.0)

        # 測試：應該不在視野內
        @ti.kernel
        def test() -> ti.i32:
            return system.is_in_fov(system.v[0], rij_behind)

        assert test() == 0, "正後方的 agent 不應該在 90° FOV 內"

    def test_fov_90_degree_side(self):
        """90度視野：側面 45° 應該在視野內"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=True)

        # Agent 0: 位於原點，朝 +X 方向移動
        system.x[0] = [0.0, 0.0, 0.0]
        system.v[0] = [1.0, 0.0, 0.0]

        # Agent 3 在 +X+Y 方向（45度角）
        rij_45deg = ti.math.vec3(1.0, 1.0, 0.0)  # 45度

        # 測試：應該在視野內（因為 45° < 90°/2）
        @ti.kernel
        def test() -> ti.i32:
            return system.is_in_fov(system.v[0], rij_45deg)

        assert test() == 1, "45度側面應該在 90° FOV 內"

    def test_fov_120_degree(self):
        """120度視野：測試更大的視野範圍"""
        system = TestPerceptionSystem(N=10, fov_angle=120.0, enable_fov=True)

        # Agent 0: 朝 +Z 方向移動
        system.v[0] = [0.0, 0.0, 1.0]

        # 測試各個方向
        @ti.kernel
        def test_directions() -> ti.i32:
            front = ti.math.vec3(0.0, 0.0, 1.0)  # 正前
            side = ti.math.vec3(0.866, 0.0, 0.5)  # 60度（120°的邊界）
            behind = ti.math.vec3(0.0, 0.0, -1.0)  # 正後

            result = 0
            if system.is_in_fov(system.v[0], front) == 1:
                result += 1  # 應該看到
            if system.is_in_fov(system.v[0], side) == 1:
                result += 10  # 應該看到（剛好在邊界）
            if system.is_in_fov(system.v[0], behind) == 0:
                result += 100  # 不應該看到

            return result

        result = test_directions()
        assert result == 111, f"120° FOV 測試失敗，result={result}"


class TestFOVDisabled:
    """測試 FOV 停用時的行為"""

    def setup_method(self):
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_fov_disabled_all_visible(self):
        """停用 FOV 時，所有方向都應該可見"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=False)

        system.v[0] = [1.0, 0.0, 0.0]

        @ti.kernel
        def test_all_directions() -> ti.i32:
            front = ti.math.vec3(1.0, 0.0, 0.0)
            behind = ti.math.vec3(-1.0, 0.0, 0.0)
            side = ti.math.vec3(0.0, 1.0, 0.0)

            result = 0
            if system.is_in_fov(system.v[0], front) == 1:
                result += 1
            if system.is_in_fov(system.v[0], behind) == 1:
                result += 10
            if system.is_in_fov(system.v[0], side) == 1:
                result += 100

            return result

        result = test_all_directions()
        assert result == 111, "FOV 停用時所有方向都應該可見"


class TestFOVEdgeCases:
    """邊界情況測試"""

    def setup_method(self):
        ti.reset()
        ti.init(arch=ti.cpu, log_level=ti.ERROR)

    def test_zero_velocity(self):
        """零速度時，FOV 應該退化為全向可見"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=True)

        # Agent 0 靜止（零速度）
        system.v[0] = [0.0, 0.0, 0.0]

        @ti.kernel
        def test() -> ti.i32:
            rij = ti.math.vec3(1.0, 0.0, 0.0)
            return system.is_in_fov(system.v[0], rij)

        # 零速度時應該全向可見（根據實作邏輯）
        assert test() == 1, "零速度時應該全向可見"

    def test_fov_indexed(self):
        """測試 is_in_fov_indexed 便捷方法"""
        system = TestPerceptionSystem(N=10, fov_angle=90.0, enable_fov=True)

        system.x[0] = [0.0, 0.0, 0.0]
        system.v[0] = [1.0, 0.0, 0.0]
        system.x[1] = [1.0, 0.0, 0.0]

        @ti.kernel
        def test() -> ti.i32:
            rij = system.x[1] - system.x[0]
            return system.is_in_fov_indexed(0, 1, rij)

        assert test() == 1, "is_in_fov_indexed 應該正確工作"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
