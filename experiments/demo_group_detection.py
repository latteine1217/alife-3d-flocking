"""
Group Detection Demo

展示群組偵測功能的三個場景：
    1. 單一群組形成
    2. 多群組分離與合併
    3. 動態群組演化（隨時間變化）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import taichi as ti

from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

# Initialize Taichi
ti.init(arch=ti.metal)


def demo_single_group_formation():
    """
    場景 1: 單一群組形成

    設定：
        • 30 agents 隨機分布
        • 經過若干步後收斂為單一群組
    """
    print("=" * 70)
    print("場景 1: Single Group Formation（單一群組形成）")
    print("=" * 70)

    N = 30
    params = FlockingParams(
        box_size=50.0,
        boundary_mode=1,  # Reflective
        beta=2.0,  # 強對齊
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 初始化：所有 agents 隨機分布在原點附近
    for i in range(N):
        sim.x[i] = np.random.randn(3) * 2.0
        sim.v[i] = np.random.randn(3) * 0.5

    print(f"\n初始設定：")
    print(f"  Agents: {N}")
    print(f"  初始分布：隨機，標準差=2.0")

    # 模擬並記錄群組數量
    for step in range(0, 201, 50):
        if step > 0:
            for _ in range(50):
                sim.step(0.1)

        # 執行群組偵測
        sim.update_groups(r_cluster=5.0, theta_cluster=45.0, n_iterations=10)

        groups = sim.get_all_groups()
        n_groups = len(groups)

        if n_groups > 0:
            avg_size = np.mean([g["size"] for g in groups])
            print(f"  Step {step:3d}: {n_groups} groups, avg size={avg_size:.1f}")
        else:
            print(f"  Step {step:3d}: No groups formed")

    # 最終結果
    final_groups = sim.get_all_groups()
    print(f"\n結果：形成 {len(final_groups)} 個群組")
    for g in final_groups:
        print(f"  群組 {g['group_id']}: size={g['size']}, centroid={g['centroid']}")


def demo_multiple_groups():
    """
    場景 2: 多群組分離

    設定：
        • 40 agents 分為兩組，位置和速度不同
        • 觀察群組如何被正確識別
    """
    print("\n" + "=" * 70)
    print("場景 2: Multiple Separate Groups（多群組分離）")
    print("=" * 70)

    N = 40
    params = FlockingParams(
        box_size=100.0,
        boundary_mode=1,
    )

    sim = HeterogeneousFlocking3D(N, params, enable_fov=False)

    # 群組 1: 20 agents @ (-10, 0, 0)，向 +x 移動
    for i in range(20):
        sim.x[i] = np.array([-10.0, 0.0, 0.0]) + np.random.randn(3) * 0.5
        sim.v[i] = np.array([1.0, 0.0, 0.0]) + np.random.randn(3) * 0.1

    # 群組 2: 20 agents @ (+10, 0, 0)，向 -x 移動
    for i in range(20, 40):
        sim.x[i] = np.array([10.0, 0.0, 0.0]) + np.random.randn(3) * 0.5
        sim.v[i] = np.array([-1.0, 0.0, 0.0]) + np.random.randn(3) * 0.1

    print(f"\n初始設定：")
    print(f"  群組 1: 20 agents @ (-10, 0, 0)，向 +x")
    print(f"  群組 2: 20 agents @ (+10, 0, 0)，向 -x")

    # 執行群組偵測
    sim.update_groups(r_cluster=5.0, theta_cluster=45.0, n_iterations=10)

    groups = sim.get_all_groups()
    print(f"\n偵測結果：")
    print(f"  群組數量: {len(groups)}")

    for g in groups:
        print(
            f"  群組 {g['group_id']}: size={g['size']}, "
            f"centroid=[{g['centroid'][0]:.1f}, {g['centroid'][1]:.1f}, {g['centroid'][2]:.1f}], "
            f"velocity=[{g['velocity'][0]:.2f}, {g['velocity'][1]:.2f}, {g['velocity'][2]:.2f}]"
        )


def demo_dynamic_group_evolution():
    """
    場景 3: 動態群組演化

    設定：
        • 50 agents 隨機初始化
        • 觀察群組如何隨時間形成、分裂、合併
    """
    print("\n" + "=" * 70)
    print("場景 3: Dynamic Group Evolution（動態群組演化）")
    print("=" * 70)

    N = 50
    params = FlockingParams(
        box_size=80.0,
        boundary_mode=0,  # PBC
        beta=1.5,
    )

    # 混合類型：10 Leaders, 40 Followers
    agent_types = [AgentType.FOLLOWER] * 40 + [AgentType.LEADER] * 10
    sim = HeterogeneousFlocking3D(N, params, agent_types=agent_types, enable_fov=True)

    # 隨機初始化
    for i in range(N):
        sim.x[i] = np.random.uniform(-30, 30, 3)
        sim.v[i] = np.random.randn(3)

    # Leaders 設定目標（簡化版本：不設定目標，讓系統自然演化）
    # 注：set_goals API 較複雜，這裡省略目標設定

    print(f"\n初始設定：")
    print(f"  Agents: 50 (40 Followers + 10 Leaders)")
    print(f"  邊界: PBC")
    print(f"  隨機初始化")

    # 模擬並追蹤群組演化
    print(f"\n群組演化：")
    for step in range(0, 251, 50):
        if step > 0:
            for _ in range(50):
                sim.step(0.1)

        # 執行群組偵測
        sim.update_groups(r_cluster=8.0, theta_cluster=60.0, n_iterations=10)

        groups = sim.get_all_groups()
        n_groups = len(groups)

        if n_groups > 0:
            sizes = [g["size"] for g in groups]
            avg_size = np.mean(sizes)
            max_size = np.max(sizes)
            print(
                f"  Step {step:3d}: {n_groups} groups "
                f"(sizes: min={min(sizes)}, max={max_size}, avg={avg_size:.1f})"
            )
        else:
            print(f"  Step {step:3d}: No groups formed")

    # 最終分析
    final_groups = sim.get_all_groups()
    print(f"\n最終結果：")
    print(f"  群組數量: {len(final_groups)}")

    # 計算每個群組中 Leaders 和 Followers 的比例
    agent_groups = sim.get_agent_groups()
    for g in final_groups:
        gid = g["group_id"]
        members = np.where(agent_groups == gid)[0]
        n_leaders = np.sum(members >= 40)
        n_followers = np.sum(members < 40)
        print(
            f"  群組 {gid}: size={g['size']}, "
            f"Leaders={n_leaders}, Followers={n_followers}"
        )


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Group Detection Demo - Heterogeneous Flocking")
    print("=" * 70)

    demo_single_group_formation()
    demo_multiple_groups()
    demo_dynamic_group_evolution()

    print("\n" + "=" * 70)
    print("Demo 完成！")
    print("=" * 70)
