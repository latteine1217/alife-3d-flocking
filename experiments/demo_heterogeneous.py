#!/usr/bin/env python3
"""
Demo: Heterogeneous Flocking System
展示 Agent 異質性功能

場景：
    1. Leader Guidance - Leaders 引導 Followers 前往目標
    2. Explorer vs Follower - 探索者與跟隨者的混合行為
    3. FOV Effect - 視野限制對群體動力學的影響
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


def demo_leader_guidance():
    """場景 1: Leaders 引導 Followers 前往目標"""
    print("\n" + "=" * 70)
    print("場景 1: Leader Guidance（領導者引導）")
    print("=" * 70)

    N = 50
    agent_types = [AgentType.LEADER] * 5 + [AgentType.FOLLOWER] * 45

    # 設定強對齊 + 較強的 goal_strength
    custom_profiles = {
        AgentType.LEADER: AgentTypeProfile(
            name="Leader", beta=1.0, eta=0.1, v0=1.5, mass=1.2, goal_strength=5.0
        ),
        AgentType.FOLLOWER: AgentTypeProfile(
            name="Follower", beta=1.5, eta=0.05, v0=1.0, mass=1.0, goal_strength=0.0
        ),
    }

    params = FlockingParams(beta=1.5, alpha=1.0, box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, type_profiles=custom_profiles
    )
    system.initialize(box_size=5.0, seed=42)

    # Leaders 目標：向 x 方向移動
    leader_indices = np.where(np.array(agent_types) == AgentType.LEADER)[0]
    goals = np.tile([15.0, 0.0, 0.0], (len(leader_indices), 1))
    system.set_goals(goals, leader_indices)

    print(f"\n初始狀態：")
    print(f"  Leaders: {len(leader_indices)}, Followers: {N - len(leader_indices)}")
    print(f"  目標位置: {goals[0]}")

    # 模擬
    com_history = []
    for step in range(500):
        system.step(dt=0.01)
        if step % 100 == 0:
            x = system.x.to_numpy()
            com = np.mean(x, axis=0)
            com_history.append(com)
            diag = system.compute_diagnostics()
            print(
                f"\nStep {step:4d}: COM={com}, P={diag['polarization']:.3f}, Rg={diag['Rg']:.2f}"
            )

    print(f"\n結果：群體質心從 {com_history[0]} 移動到 {com_history[-1]}")
    print(f"  X 方向位移: {com_history[-1][0] - com_history[0][0]:.2f}")


def demo_explorer_vs_follower():
    """場景 2: Explorer vs Follower 混合行為"""
    print("\n" + "=" * 70)
    print("場景 2: Explorer vs Follower（探索者 vs 跟隨者）")
    print("=" * 70)

    N = 100
    agent_types = [AgentType.EXPLORER] * 30 + [AgentType.FOLLOWER] * 70

    params = FlockingParams(beta=1.0, alpha=1.5, eta=0.0, box_size=50.0)
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    system.initialize(box_size=10.0, seed=42)

    print(f"\n群體組成：")
    print(f"  Explorers: 30 (高 noise, 弱 alignment)")
    print(f"  Followers: 70 (低 noise, 強 alignment)")

    # 模擬
    for step in range(300):
        system.step(dt=0.01)
        if step % 100 == 0:
            diag = system.compute_diagnostics()
            v = system.v.to_numpy()
            type_arr = system.agent_type.to_numpy()

            explorer_v = v[type_arr == AgentType.EXPLORER]
            follower_v = v[type_arr == AgentType.FOLLOWER]

            explorer_speed = np.mean(np.linalg.norm(explorer_v, axis=1))
            follower_speed = np.mean(np.linalg.norm(follower_v, axis=1))

            print(f"\nStep {step:4d}:")
            print(
                f"  整體: P={diag['polarization']:.3f}, Rg={diag['Rg']:.2f}, v_mean={diag['mean_speed']:.2f}"
            )
            print(
                f"  Explorer 平均速度: {explorer_speed:.2f}, Follower 平均速度: {follower_speed:.2f}"
            )


def demo_fov_effect():
    """場景 3: FOV 限制的效果"""
    print("\n" + "=" * 70)
    print("場景 3: Field of View Effect（視野限制效果）")
    print("=" * 70)

    N = 50
    agent_types = [AgentType.FOLLOWER] * N
    params = FlockingParams(beta=1.5, alpha=1.0, box_size=30.0)

    print(f"\n比較兩個系統：")
    print(f"  系統 A: FOV = 60 度（窄視野）")
    print(f"  系統 B: FOV = 180 度（寬視野）")

    # 先運行窄視野系統
    print("\n[執行窄視野系統]")
    system_narrow = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, fov_angle=60.0
    )
    system_narrow.initialize(box_size=5.0, seed=42)

    narrow_results = []
    for step in range(300):
        system_narrow.step(dt=0.01)
        if step % 100 == 0:
            diag = system_narrow.compute_diagnostics()
            narrow_results.append((step, diag))

    # 再運行寬視野系統
    print("\n[執行寬視野系統]")
    system_wide = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, fov_angle=180.0
    )
    system_wide.initialize(box_size=5.0, seed=42)

    wide_results = []
    for step in range(300):
        system_wide.step(dt=0.01)
        if step % 100 == 0:
            diag = system_wide.compute_diagnostics()
            wide_results.append((step, diag))

    # 顯示結果
    print("\n[結果比較]")
    for i in range(len(narrow_results)):
        step_n, diag_n = narrow_results[i]
        step_w, diag_w = wide_results[i]
        print(f"\nStep {step_n:4d}:")
        print(f"  窄視野 (60°): P={diag_n['polarization']:.3f}, Rg={diag_n['Rg']:.2f}")
        print(f"  寬視野 (180°): P={diag_w['polarization']:.3f}, Rg={diag_w['Rg']:.2f}")


def main():
    """運行所有 demo"""
    print("\n" + "=" * 70)
    print("Heterogeneous Flocking System Demo")
    print("=" * 70)

    demo_leader_guidance()
    demo_explorer_vs_follower()
    demo_fov_effect()

    print("\n" + "=" * 70)
    print("Demo 完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
