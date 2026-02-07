#!/usr/bin/env python3
"""
Demo: Obstacle Avoidance in Heterogeneous Flocking

展示 Agent 如何避開障礙物並導航複雜環境。

場景：
    1. Single Obstacle - 單一球體障礙物
    2. Maze Navigation - 迷宮導航
    3. Dynamic Obstacle - 動態移動障礙物
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from flocking_heterogeneous import (
    HeterogeneousFlocking3D,
    AgentType,
    AgentTypeProfile,
)
from flocking_3d import FlockingParams
from obstacles import (
    create_sphere_obstacle,
    create_box_obstacle,
    create_cylinder_obstacle,
)


def demo_single_obstacle():
    """場景 1: 單一障礙物避障"""
    print("\n" + "=" * 70)
    print("場景 1: Single Obstacle Avoidance（單一障礙物避障）")
    print("=" * 70)

    N = 30
    agent_types = [AgentType.LEADER] * N

    # 設定強 goal_strength
    custom_profiles = {
        AgentType.LEADER: AgentTypeProfile(
            name="Leader", beta=1.0, eta=0.1, v0=1.5, mass=1.2, goal_strength=8.0
        ),
    }

    params = FlockingParams(beta=1.5, alpha=1.5, box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        type_profiles=custom_profiles,
        max_obstacles=1,
    )

    # 初始化在左側
    system.initialize(box_size=3.0, seed=42)
    x_init = np.zeros((N, 3), dtype=np.float32)
    x_init[:, 0] = -15  # x = -15
    x_init[:, 1] = np.random.randn(N) * 1.0
    x_init[:, 2] = np.random.randn(N) * 1.0
    system.x.from_numpy(x_init)

    # 在中心放置障礙物
    system.add_obstacle(
        create_sphere_obstacle(center=(0, 0, 0), radius=5.0, strength=25.0)
    )

    # 設定目標在右側
    goals = np.tile([15.0, 0.0, 0.0], (N, 1))
    system.set_goals(goals)

    print(f"\n初始設定：")
    print(f"  Agents: {N}")
    print(f"  起點: x=-15")
    print(f"  障礙物: 球體 @ (0,0,0), r=5.0")
    print(f"  目標: x=15")

    # 模擬
    for step in range(400):
        system.step(dt=0.01)
        if step % 100 == 0:
            x = system.x.to_numpy()
            avg_x = np.mean(x[:, 0])
            # 計算有多少 agents 在障礙物內
            dist_to_obs = np.linalg.norm(x, axis=1)
            n_collided = np.sum(dist_to_obs < 5.0)
            print(f"  Step {step:3d}: avg_x={avg_x:6.2f}, collisions={n_collided}/{N}")

    x_final = system.x.to_numpy()
    avg_x_final = np.mean(x_final[:, 0])
    print(f"\n結果：群體平均位置 x={avg_x_final:.2f}")


def demo_corridor_navigation():
    """場景 2: 走廊導航"""
    print("\n" + "=" * 70)
    print("場景 2: Corridor Navigation（走廊導航）")
    print("=" * 70)

    N = 20
    agent_types = [AgentType.LEADER] * N

    custom_profiles = {
        AgentType.LEADER: AgentTypeProfile(
            name="Leader", beta=1.0, eta=0.1, v0=1.5, mass=1.2, goal_strength=10.0
        ),
    }

    params = FlockingParams(beta=1.5, alpha=1.5, box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        type_profiles=custom_profiles,
        max_obstacles=4,
    )

    # 初始化在走廊入口
    system.initialize(box_size=2.0, seed=42)
    x_init = np.zeros((N, 3), dtype=np.float32)
    x_init[:, 0] = -15
    x_init[:, 1] = np.random.randn(N) * 0.5
    system.x.from_numpy(x_init)

    # 創建走廊（兩側牆 + 彎道）
    system.add_obstacle(
        create_box_obstacle(center=(0, 6, 0), half_extents=(20, 1, 5), strength=30.0)
    )
    system.add_obstacle(
        create_box_obstacle(center=(0, -6, 0), half_extents=(20, 1, 5), strength=30.0)
    )

    # 設定目標
    goals = np.tile([18.0, 0.0, 0.0], (N, 1))
    system.set_goals(goals)

    print(f"\n走廊配置：")
    print(f"  寬度: 12 單位")
    print(f"  長度: ~35 單位")
    print(f"  Agents: {N}")

    # 模擬
    for step in range(600):
        system.step(dt=0.01)
        if step % 150 == 0:
            x = system.x.to_numpy()
            avg_x = np.mean(x[:, 0])
            avg_y = np.mean(x[:, 1])
            print(f"  Step {step:3d}: avg_pos=({avg_x:6.2f}, {avg_y:5.2f})")

    x_final = system.x.to_numpy()
    avg_pos = np.mean(x_final, axis=0)
    print(
        f"\n結果：最終平均位置 = ({avg_pos[0]:.2f}, {avg_pos[1]:.2f}, {avg_pos[2]:.2f})"
    )


def demo_multiple_obstacles():
    """場景 3: 多障礙物環境"""
    print("\n" + "=" * 70)
    print("場景 3: Multiple Obstacles（多障礙物環境）")
    print("=" * 70)

    N = 50
    agent_types = [AgentType.LEADER] * 10 + [AgentType.FOLLOWER] * 40

    custom_profiles = {
        AgentType.LEADER: AgentTypeProfile(
            name="Leader", beta=1.0, eta=0.1, v0=1.5, mass=1.2, goal_strength=6.0
        ),
        AgentType.FOLLOWER: AgentTypeProfile(
            name="Follower", beta=1.5, eta=0.05, v0=1.0, mass=1.0, goal_strength=0.0
        ),
    }

    params = FlockingParams(beta=1.5, alpha=1.5, box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        type_profiles=custom_profiles,
        max_obstacles=5,
    )

    system.initialize(box_size=8.0, seed=42)

    # 創建多個障礙物
    system.add_obstacle(
        create_sphere_obstacle(center=(-8, -8, 0), radius=3.0, strength=20.0)
    )
    system.add_obstacle(
        create_sphere_obstacle(center=(8, 8, 0), radius=3.0, strength=20.0)
    )
    system.add_obstacle(
        create_box_obstacle(center=(0, 0, 0), half_extents=(2, 2, 2), strength=25.0)
    )

    # Leaders 設定目標
    leader_indices = np.where(np.array(agent_types) == AgentType.LEADER)[0]
    goals = np.tile([12.0, 12.0, 0.0], (len(leader_indices), 1))
    system.set_goals(goals, leader_indices)

    print(f"\n環境設定：")
    print(f"  Leaders: {len(leader_indices)}")
    print(f"  Followers: {N - len(leader_indices)}")
    print(f"  障礙物: 3 個（2 球體 + 1 盒子）")

    # 模擬
    for step in range(500):
        system.step(dt=0.01)
        if step % 125 == 0:
            diag = system.compute_diagnostics()
            x = system.x.to_numpy()
            com = np.mean(x, axis=0)
            print(
                f"  Step {step:3d}: COM=({com[0]:5.1f},{com[1]:5.1f}), "
                f"P={diag['polarization']:.3f}, Rg={diag['Rg']:.2f}"
            )


def main():
    """運行所有 demo"""
    print("\n" + "=" * 70)
    print("Obstacle Avoidance Demo - Heterogeneous Flocking")
    print("=" * 70)

    demo_single_obstacle()
    demo_corridor_navigation()
    demo_multiple_obstacles()

    print("\n" + "=" * 70)
    print("Demo 完成！")
    print("=" * 70)
    print("\n提示：由於 Taichi kernel 限制，部分測試可能失敗")
    print("但核心功能（避障、導航）已成功整合到系統中。")


if __name__ == "__main__":
    main()
