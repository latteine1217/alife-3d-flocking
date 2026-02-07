"""
Tests for Group Detection System

測試項目：
    • 單一群組偵測
    • 多群組分離
    • 群組統計計算
    • 邊界條件（PBC 下的群組）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest
import taichi as ti

from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams


# Initialize Taichi once for all tests
ti.init(arch=ti.metal)


# ============================================================================
# Basic Group Detection Tests
# ============================================================================
def test_single_group_detection():
    """測試單一緊密群組的偵測"""
    N = 20
    params = FlockingParams(
        box_size=50.0,
        boundary_mode=1,  # Reflective
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 設定：所有 agents 在原點附近，速度相同
    center = np.array([0.0, 0.0, 0.0])
    velocity = np.array([1.0, 0.0, 0.0])

    for i in range(N):
        # 隨機分布在半徑 2.0 的球內
        offset = np.random.randn(3) * 0.5
        sim.x[i] = center + offset
        sim.v[i] = velocity + np.random.randn(3) * 0.1

    # 執行群組偵測
    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=5)

    # 驗證：所有 agents 應該在同一個群組
    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    assert len(unique_groups) == 1, f"Expected 1 group, found {len(unique_groups)}"

    # 驗證群組統計
    groups = sim.get_all_groups()
    assert len(groups) == 1, "Should have exactly 1 active group"

    group_info = groups[0]
    assert group_info["size"] == N, f"Group size should be {N}"

    # 質心應該接近原點
    centroid = group_info["centroid"]
    assert np.linalg.norm(centroid - center) < 1.0, "Centroid should be near origin"

    print(f"✓ Single group detected: size={group_info['size']}, centroid={centroid}")


def test_two_separate_groups():
    """測試兩個分離群組的偵測"""
    N = 40
    params = FlockingParams(
        box_size=100.0,
        boundary_mode=1,  # Reflective
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 群組 1：20 agents 在 (-10, 0, 0) 附近，向 +x 移動
    # 群組 2：20 agents 在 (+10, 0, 0) 附近，向 -x 移動
    for i in range(20):
        sim.x[i] = np.array([-10.0, 0.0, 0.0]) + np.random.randn(3) * 0.5
        sim.v[i] = np.array([1.0, 0.0, 0.0]) + np.random.randn(3) * 0.1

    for i in range(20, 40):
        sim.x[i] = np.array([10.0, 0.0, 0.0]) + np.random.randn(3) * 0.5
        sim.v[i] = np.array([-1.0, 0.0, 0.0]) + np.random.randn(3) * 0.1

    # 執行群組偵測
    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=10)

    # 驗證：應該偵測到 2 個群組
    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    assert len(unique_groups) == 2, f"Expected 2 groups, found {len(unique_groups)}"

    # 驗證群組統計
    groups = sim.get_all_groups()
    assert len(groups) == 2, "Should have exactly 2 active groups"

    # 每個群組大小應該是 20
    sizes = [g["size"] for g in groups]
    assert all(s == 20 for s in sizes), f"Both groups should have size 20, got {sizes}"

    print(f"✓ Two groups detected: sizes={sizes}")


def test_velocity_direction_clustering():
    """測試基於速度方向的聚類"""
    N = 30
    params = FlockingParams(
        box_size=50.0,
        boundary_mode=1,
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 所有 agents 在原點附近，但速度方向不同
    # 群組 1: 向 +x
    # 群組 2: 向 -x
    center = np.array([0.0, 0.0, 0.0])

    for i in range(15):
        sim.x[i] = center + np.random.randn(3) * 0.5
        sim.v[i] = np.array([1.0, 0.0, 0.0]) + np.random.randn(3) * 0.05

    for i in range(15, 30):
        sim.x[i] = center + np.random.randn(3) * 0.5
        sim.v[i] = np.array([-1.0, 0.0, 0.0]) + np.random.randn(3) * 0.05

    # 執行群組偵測（嚴格的角度限制）
    sim.update_groups(r_cluster=5.0, theta_cluster=45.0, n_iterations=10)

    # 驗證：應該偵測到 2 個群組（儘管空間上重疊）
    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    assert len(unique_groups) == 2, (
        f"Expected 2 groups (opposite velocities), found {len(unique_groups)}"
    )

    print(f"✓ Velocity-based clustering: {len(unique_groups)} groups detected")


def test_no_group_formation():
    """測試無法形成群組的情況（agents 太分散）"""
    N = 20
    params = FlockingParams(
        box_size=100.0,
        boundary_mode=1,
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 隨機分布在大空間中，彼此距離遠
    for i in range(N):
        sim.x[i] = np.random.uniform(-40, 40, 3)
        sim.v[i] = np.random.randn(3)

    # 執行群組偵測（小的聚類半徑）
    sim.update_groups(r_cluster=2.0, theta_cluster=30.0, n_iterations=5)

    # 驗證：可能有多個小群組或每個 agent 自己一組
    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    # 至少應該有多於 1 個群組（因為很分散）
    assert len(unique_groups) > 5, (
        f"Expected many small groups, found {len(unique_groups)}"
    )

    print(f"✓ Dispersed agents: {len(unique_groups)} groups detected")


# ============================================================================
# Group Statistics Tests
# ============================================================================
def test_group_centroid_calculation():
    """測試群組質心計算"""
    N = 10
    params = FlockingParams(box_size=50.0, boundary_mode=1)

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 設定：agents 在已知位置
    known_center = np.array([5.0, 3.0, -2.0])
    for i in range(N):
        sim.x[i] = known_center + np.random.randn(3) * 0.3
        sim.v[i] = np.array([1.0, 0.0, 0.0])

    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=5)

    groups = sim.get_all_groups()
    assert len(groups) == 1

    centroid = groups[0]["centroid"]

    # 質心應該接近 known_center
    error = np.linalg.norm(centroid - known_center)
    assert error < 0.5, f"Centroid error too large: {error}"

    print(
        f"✓ Centroid calculation: expected={known_center}, got={centroid}, error={error:.3f}"
    )


def test_group_velocity_calculation():
    """測試群組平均速度計算"""
    N = 15
    params = FlockingParams(box_size=50.0, boundary_mode=1)

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 所有 agents 相同速度
    known_velocity = np.array([2.0, 1.0, -0.5])
    for i in range(N):
        sim.x[i] = np.random.randn(3) * 0.5
        sim.v[i] = known_velocity + np.random.randn(3) * 0.1

    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=5)

    groups = sim.get_all_groups()
    assert len(groups) == 1

    avg_velocity = groups[0]["velocity"]

    # 平均速度應該接近 known_velocity
    error = np.linalg.norm(avg_velocity - known_velocity)
    assert error < 0.3, f"Velocity error too large: {error}"

    print(
        f"✓ Average velocity: expected={known_velocity}, got={avg_velocity}, error={error:.3f}"
    )


# ============================================================================
# PBC Tests
# ============================================================================
def test_group_detection_with_pbc():
    """測試 PBC 邊界下的群組偵測"""
    N = 20
    params = FlockingParams(
        box_size=20.0,  # 小盒子
        boundary_mode=0,  # PBC
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 群組橫跨邊界：一半在 x=9，一半在 x=-9
    L = params.box_size
    for i in range(10):
        sim.x[i] = np.array([L / 2 - 1, 0.0, 0.0]) + np.random.randn(3) * 0.3
        sim.v[i] = np.array([1.0, 0.0, 0.0])

    for i in range(10, 20):
        sim.x[i] = np.array([-L / 2 + 1, 0.0, 0.0]) + np.random.randn(3) * 0.3
        sim.v[i] = np.array([1.0, 0.0, 0.0])

    # 執行群組偵測
    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=10)

    # 驗證：應該偵測為同一群組（因為 PBC）
    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    assert len(unique_groups) == 1, (
        f"Expected 1 group with PBC, found {len(unique_groups)}"
    )

    print(f"✓ PBC group detection: {len(unique_groups)} group detected across boundary")


# ============================================================================
# Edge Cases
# ============================================================================
def test_empty_simulation():
    """測試空系統（N=0）"""
    N = 1  # Taichi 不允許 N=0，用最小值
    params = FlockingParams(box_size=50.0, boundary_mode=1)

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)
    sim.update_groups(r_cluster=5.0, theta_cluster=30.0, n_iterations=5)

    groups = sim.get_all_groups()
    assert len(groups) == 1, "Single agent should form 1 group"

    print(f"✓ Single agent: {len(groups)} group")


def test_large_angle_threshold():
    """測試大角度閾值（應該合併所有群組）"""
    N = 30
    params = FlockingParams(box_size=50.0, boundary_mode=1)

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # agents 在原點附近，但速度方向隨機
    for i in range(N):
        sim.x[i] = np.random.randn(3) * 0.5
        sim.v[i] = np.random.randn(3)

    # 使用 180 度角度閾值（接受所有方向）
    sim.update_groups(r_cluster=5.0, theta_cluster=180.0, n_iterations=10)

    group_ids = sim.get_agent_groups()
    unique_groups = np.unique(group_ids)

    # 應該合併為單一群組
    assert len(unique_groups) == 1, (
        f"Expected 1 group with large angle threshold, found {len(unique_groups)}"
    )

    print(f"✓ Large angle threshold: all agents in 1 group")


# ============================================================================
# Run All Tests
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Group Detection Tests")
    print("=" * 70)

    test_single_group_detection()
    test_two_separate_groups()
    test_velocity_direction_clustering()
    test_no_group_formation()
    test_group_centroid_calculation()
    test_group_velocity_calculation()
    test_group_detection_with_pbc()
    test_empty_simulation()
    test_large_angle_threshold()

    print("=" * 70)
    print("All tests passed!")
    print("=" * 70)
