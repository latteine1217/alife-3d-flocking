"""
Foraging Behavior Demo - 覓食行為展示

展示 agents 如何搜尋資源、消耗資源、補充能量
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import taichi as ti

from flocking_3d import FlockingParams
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from resources import create_resource, create_renewable_resource

# ============================================================================
# Visualization Helper
# ============================================================================


def visualize_2d_projection(system, step: int):
    """2D 投影視覺化（XY 平面）"""
    gui = ti.GUI("Foraging Demo", res=(800, 800), background_color=0x112F41)

    # 獲取資料
    x_np = system.x.to_numpy()
    energies = system.get_agent_energies()
    targets = system.get_agent_targets()
    resources = system.get_all_resources()

    # 正規化座標到 [0, 1]
    box_size = system.params.box_size
    x_vis = (x_np[:, :2] + box_size / 2) / box_size

    # 顏色映射：能量 -> 顏色（綠色=高能量，紅色=低能量）
    colors = np.zeros((len(x_vis), 3))
    for i, energy in enumerate(energies):
        # 能量 [0, 100] -> 顏色 [red, green]
        ratio = energy / 100.0
        colors[i] = [1.0 - ratio, ratio, 0.0]  # RGB

    # 繪製 agents
    gui.circles(x_vis, radius=5, color=colors)

    # 繪製資源（藍色圓圈）
    for res in resources:
        if res["active"]:
            pos = res["position"][:2]
            pos_vis = (pos + box_size / 2) / box_size
            radius_vis = res["radius"] / box_size

            # 資源圓圈
            gui.circle(pos_vis, radius=int(radius_vis * 800), color=0x4A90E2)

            # 資源數量標示（大小）
            amount_ratio = res["amount"] / res["max_amount"]
            gui.circle(
                pos_vis, radius=int(radius_vis * 800 * amount_ratio), color=0x7EC8E3
            )

    # 繪製 agent -> 資源的連線
    for i, target_id in enumerate(targets):
        if target_id >= 0:
            res = system.get_resource_info(target_id)
            if res and res["active"]:
                agent_pos = x_vis[i]
                res_pos = (res["position"][:2] + box_size / 2) / box_size
                gui.line(agent_pos, res_pos, radius=1, color=0xFFFFFF)

    # 顯示統計資訊
    avg_energy = np.mean(energies)
    min_energy = np.min(energies)
    max_energy = np.max(energies)
    n_foraging = np.sum(targets >= 0)

    gui.text(
        content=f"Step: {step} | Agents: {len(x_np)}",
        pos=(0.02, 0.98),
        font_size=20,
        color=0xFFFFFF,
    )
    gui.text(
        content=f"Energy: avg={avg_energy:.1f}, min={min_energy:.1f}, max={max_energy:.1f}",
        pos=(0.02, 0.94),
        font_size=16,
        color=0xFFFFFF,
    )
    gui.text(
        content=f"Foraging: {n_foraging}/{len(x_np)} agents",
        pos=(0.02, 0.90),
        font_size=16,
        color=0xFFFFFF,
    )

    gui.show()
    return gui


# ============================================================================
# Scenario 1: Simple Foraging - 單一資源
# ============================================================================


def scenario_simple_foraging():
    """場景 1: 簡單覓食 - agents 發現並消耗單一資源"""
    print("=" * 70)
    print("Scenario 1: Simple Foraging")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        beta=1.0,
        box_size=50.0,
        boundary_mode=1,  # Reflective
    )

    ti.init(arch=ti.gpu, random_seed=42)
    N = 20
    agent_types = [AgentType.EXPLORER] * N

    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, enable_fov=False
    )

    # 初始化：agents 分散，能量低
    system.x.fill(0.0)
    for i in range(N):
        angle = 2 * np.pi * i / N
        radius = 15.0
        system.x[i] = [radius * np.cos(angle), radius * np.sin(angle), 0.0]
        system.v[i] = [0.0, 0.0, 0.0]
        system.agent_energy[i] = 30.0  # 低能量

    # 新增單一不可再生資源
    system.add_resource(
        create_resource(position=(0.0, 0.0, 0.0), amount=200.0, radius=3.0)
    )

    print("初始狀態:")
    print(f"  Agents: {N}")
    print(f"  資源: 1 個不可再生資源 (200 units)")
    print(f"  平均能量: 30.0")
    print("\n按任意鍵開始...")

    # 模擬
    gui = None
    for step in range(500):
        system.step(dt=0.05)

        if step % 5 == 0:
            gui = visualize_2d_projection(system, step)

        # 檢查結束條件
        resources = system.get_all_resources()
        if len(resources) == 0:
            print(f"\n資源耗盡！結束於步數 {step}")
            break

    if gui:
        gui.close()


# ============================================================================
# Scenario 2: Competitive Foraging - 多 agents 競爭
# ============================================================================


def scenario_competitive_foraging():
    """場景 2: 競爭覓食 - 多個 agents 競爭有限資源"""
    print("=" * 70)
    print("Scenario 2: Competitive Foraging")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        beta=1.0,
        box_size=50.0,
        boundary_mode=1,
    )

    ti.init(arch=ti.gpu, random_seed=43)
    N = 30
    agent_types = [AgentType.EXPLORER] * N

    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, enable_fov=False
    )

    # 初始化：隨機分布
    system.initialize(box_size=10.0, seed=43)
    for i in range(N):
        system.agent_energy[i] = 20.0  # 低能量

    # 新增兩個資源點（不同位置）
    system.add_resource(
        create_resource(position=(-10.0, -10.0, 0.0), amount=150.0, radius=4.0)
    )
    system.add_resource(
        create_resource(position=(10.0, 10.0, 0.0), amount=150.0, radius=4.0)
    )

    print("初始狀態:")
    print(f"  Agents: {N}")
    print(f"  資源: 2 個 (各 150 units)")
    print(f"  平均能量: 20.0")
    print("\n觀察 agents 如何分配到兩個資源點...")

    # 模擬
    gui = None
    for step in range(500):
        system.step(dt=0.05)

        if step % 5 == 0:
            gui = visualize_2d_projection(system, step)

    if gui:
        gui.close()


# ============================================================================
# Scenario 3: Renewable Resources - 可再生資源
# ============================================================================


def scenario_renewable_resources():
    """場景 3: 可再生資源 - 永續採集"""
    print("=" * 70)
    print("Scenario 3: Renewable Resources")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        beta=1.0,
        box_size=50.0,
        boundary_mode=0,  # PBC
    )

    ti.init(arch=ti.gpu, random_seed=44)
    N = 25
    agent_types = [AgentType.EXPLORER] * N

    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, enable_fov=False
    )

    # 初始化
    system.initialize(box_size=15.0, seed=44)
    for i in range(N):
        system.agent_energy[i] = 50.0

    # 新增可再生資源（自動補充）
    system.add_resource(
        create_renewable_resource(
            position=(0.0, 0.0, 0.0),
            amount=100.0,
            radius=5.0,
            replenish_rate=3.0,
            max_amount=200.0,
        )
    )

    print("初始狀態:")
    print(f"  Agents: {N}")
    print(f"  資源: 1 個可再生資源 (補充率 3.0/step)")
    print(f"  平均能量: 50.0")
    print("\n觀察可持續採集...")

    # 模擬
    gui = None
    for step in range(800):
        system.step(dt=0.05)

        if step % 5 == 0:
            gui = visualize_2d_projection(system, step)

    if gui:
        gui.close()


# ============================================================================
# Main
# ============================================================================


def main():
    """主程式"""
    print("\n" + "=" * 70)
    print("Foraging Behavior Demo")
    print("=" * 70)
    print("\n選擇場景:")
    print("  1. Simple Foraging - 單一資源")
    print("  2. Competitive Foraging - 多 agents 競爭")
    print("  3. Renewable Resources - 可再生資源")
    print()

    try:
        choice = input("請選擇 (1-3): ").strip()

        if choice == "1":
            scenario_simple_foraging()
        elif choice == "2":
            scenario_competitive_foraging()
        elif choice == "3":
            scenario_renewable_resources()
        else:
            print("無效選擇！")

    except KeyboardInterrupt:
        print("\n\n已中斷。")


if __name__ == "__main__":
    main()
