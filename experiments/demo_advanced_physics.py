#!/usr/bin/env python3
"""
進階物理展示 - Vicsek Noise 與壁面邊界

展示新實現的功能：
1. Vicsek noise (角度隨機擾動)
2. Reflective walls (反射邊界)
3. Absorbing walls (吸收邊界)
"""

import sys

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")

from flocking_2d import Flocking2D, FlockingParams
import numpy as np


def demo_vicsek_noise():
    """展示 Vicsek noise 對秩序的影響"""
    print("=" * 70)
    print("  Demo 1: Vicsek Noise Effect")
    print("=" * 70)

    # 比較不同 noise 強度
    noise_levels = [0.0, 0.1, 0.3, 0.5]

    for eta in noise_levels:
        params = FlockingParams(
            beta=1.0,  # 強對齊
            eta=eta,  # 變動 noise
            boundary_mode="pbc",
            box_size=50.0,
        )

        system = Flocking2D(N=100, params=params)
        system.initialize(box_size=5.0, seed=42)

        # 演化 100 步
        for _ in range(100):
            system.step(dt=0.01)

        # 測量 Polarization
        diag = system.compute_diagnostics()
        polarization = diag["polarization"]

        print(f"  η={eta:.2f} → Polarization={polarization:.3f}")

    print("\n✓ 觀察：noise 越大，Polarization 越低（秩序被破壞）\n")


def demo_reflective_walls():
    """展示反射邊界效應"""
    print("=" * 70)
    print("  Demo 2: Reflective Walls")
    print("=" * 70)

    params = FlockingParams(
        beta=0.5,
        eta=0.0,
        boundary_mode="reflective",  # 反射邊界
        box_size=20.0,
        wall_stiffness=10.0,
    )

    system = Flocking2D(N=50, params=params)
    system.initialize(box_size=5.0, seed=42)

    print("  Boundary mode: Reflective")
    print("  Box size: 20.0")
    print("  演化 200 步...\n")

    for step in range(200):
        system.step(dt=0.01)

        if step % 50 == 0:
            diag = system.compute_diagnostics()
            rg = diag["Rg"]
            print(f"    Step {step:3d}: Rg={rg:.3f}")

    print("\n✓ 觀察：粒子被限制在 box 內，Rg 不會超過 box_size/2\n")


def demo_absorbing_walls():
    """展示吸收邊界效應"""
    print("=" * 70)
    print("  Demo 3: Absorbing Walls")
    print("=" * 70)

    params = FlockingParams(
        beta=0.5,
        eta=0.0,
        boundary_mode="absorbing",  # 吸收邊界
        box_size=20.0,
    )

    system = Flocking2D(N=50, params=params)
    system.initialize(box_size=5.0, seed=42)

    print("  Boundary mode: Absorbing (粒子到達邊界時停止)")
    print("  Box size: 20.0")
    print("  演化 200 步...\n")

    for step in range(200):
        system.step(dt=0.01)

        if step % 50 == 0:
            diag = system.compute_diagnostics()
            mean_speed = diag["mean_speed"]
            print(f"    Step {step:3d}: <|v|>={mean_speed:.3f}")

    print("\n✓ 觀察：部分粒子到達邊界後停止，平均速度可能下降\n")


def demo_combined():
    """展示組合效果：Vicsek noise + Reflective walls"""
    print("=" * 70)
    print("  Demo 4: Vicsek Noise + Reflective Walls")
    print("=" * 70)

    params = FlockingParams(
        beta=1.0,
        eta=0.2,  # 中等 noise
        boundary_mode="reflective",
        box_size=30.0,
    )

    system = Flocking2D(N=100, params=params)
    system.initialize(box_size=10.0, seed=42)

    print("  β=1.0 (強對齊), η=0.2 (中等 noise), Reflective walls")
    print("  演化 200 步...\n")

    for step in range(200):
        system.step(dt=0.01)

        if step % 50 == 0:
            diag = system.compute_diagnostics()
            polarization = diag["polarization"]
            rg = diag["Rg"]
            print(f"    Step {step:3d}: P={polarization:.3f}, Rg={rg:.3f}")

    print("\n✓ 觀察：noise 與壁面的競爭效應\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  進階物理功能展示")
    print("=" * 70 + "\n")

    demo_vicsek_noise()
    demo_reflective_walls()
    demo_absorbing_walls()
    demo_combined()

    print("=" * 70)
    print("  ✅ 所有展示完成")
    print("=" * 70)
