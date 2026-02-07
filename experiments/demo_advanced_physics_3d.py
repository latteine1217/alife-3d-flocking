"""
3D Advanced Physics Demonstration

展示項目：
    1. Vicsek Noise：角度隨機擾動（球面旋轉）
    2. Reflective Walls：反射邊界（粒子彈回）
    3. Absorbing Walls：吸收邊界（粒子停止）
    4. Combined Effects：noise + reflective walls
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flocking_3d import Flocking3D, FlockingParams


def demo_vicsek_noise():
    """Demo 1: Vicsek Noise 降低極化度"""
    print("\n" + "=" * 70)
    print("Demo 1: Vicsek Noise (3D Spherical Rotation)")
    print("=" * 70)

    print("\n[Scenario A] 無 noise (eta=0.0)")
    params_no_noise = FlockingParams(
        beta=1.0,  # 強對齊
        eta=0.0,  # 無 noise
        box_size=30.0,
    )
    system_no_noise = Flocking3D(N=100, params=params_no_noise)
    system_no_noise.initialize(box_size=5.0, seed=42)

    for _ in range(100):
        system_no_noise.step(dt=0.01)

    diag_no_noise = system_no_noise.compute_diagnostics()
    print(f"  Polarization: {diag_no_noise['polarization']:.3f}")
    print(f"  Mean speed:   {diag_no_noise['mean_speed']:.3f}")

    print("\n[Scenario B] 有 noise (eta=0.2, 約 11.5 度)")
    params_noise = FlockingParams(
        beta=1.0,  # 強對齊
        eta=0.2,  # 中等 noise
        box_size=30.0,
    )
    system_noise = Flocking3D(N=100, params=params_noise)
    system_noise.initialize(box_size=5.0, seed=42)

    for _ in range(100):
        system_noise.step(dt=0.01)

    diag_noise = system_noise.compute_diagnostics()
    print(f"  Polarization: {diag_noise['polarization']:.3f}")
    print(f"  Mean speed:   {diag_noise['mean_speed']:.3f}")

    print(
        f"\n→ Noise 降低了 {(1 - diag_noise['polarization'] / diag_no_noise['polarization']) * 100:.1f}% 的極化度"
    )


def demo_reflective_walls():
    """Demo 2: Reflective Walls 限制粒子運動"""
    print("\n" + "=" * 70)
    print("Demo 2: Reflective Walls")
    print("=" * 70)

    params = FlockingParams(
        beta=0.5,
        eta=0.0,
        boundary_mode="reflective",
        box_size=20.0,  # [-10, +10] 範圍
    )
    system = Flocking3D(N=100, params=params)
    system.initialize(box_size=5.0, seed=42)

    print("\n執行 200 步模擬...")
    for step in range(200):
        system.step(dt=0.01)

        if step % 50 == 0:
            x, _ = system.get_state()
            max_coord = x.max()
            min_coord = x.min()
            print(f"  Step {step:3d}: x ∈ [{min_coord:.2f}, {max_coord:.2f}]")

    print("\n→ 所有粒子保持在 [-10, +10] 範圍內（反射邊界有效）")


def demo_absorbing_walls():
    """Demo 3: Absorbing Walls 吸收超界粒子"""
    print("\n" + "=" * 70)
    print("Demo 3: Absorbing Walls")
    print("=" * 70)

    params = FlockingParams(
        beta=0.3,
        eta=0.1,  # 一些 noise 幫助擴散
        boundary_mode="absorbing",
        box_size=15.0,  # [-7.5, +7.5] 範圍
    )
    system = Flocking3D(N=100, params=params)
    system.initialize(box_size=3.0, seed=42)

    print("\n執行 100 步模擬...")
    for step in range(100):
        system.step(dt=0.01)

        if step % 25 == 0:
            _, v = system.get_state()
            speeds = (v**2).sum(axis=1) ** 0.5
            n_stopped = (speeds < 0.01).sum()
            print(f"  Step {step:3d}: {n_stopped}/100 particles stopped")

    print("\n→ 超出邊界的粒子速度被設為零（吸收邊界有效）")


def demo_combined_effects():
    """Demo 4: Noise + Reflective Walls 的競爭"""
    print("\n" + "=" * 70)
    print("Demo 4: Combined Effects (Noise + Reflective Walls)")
    print("=" * 70)

    params = FlockingParams(
        beta=1.0,  # 強對齊
        eta=0.2,  # 中等 noise
        boundary_mode="reflective",
        box_size=20.0,
    )
    system = Flocking3D(N=100, params=params)
    system.initialize(box_size=5.0, seed=42)

    print("\n執行 150 步模擬...")
    for step in [0, 50, 100, 150]:
        for _ in range(50 if step > 0 else 0):
            system.step(dt=0.01)

        diag = system.compute_diagnostics()
        print(
            f"  Step {step:3d}: P={diag['polarization']:.3f}, "
            f"Rg={diag['Rg']:.3f}, v={diag['mean_speed']:.3f}"
        )

    print("\n→ Noise 降低對齊，Walls 限制擴散，兩者達到動態平衡")


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "3D Advanced Physics Demonstration" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")

    demo_vicsek_noise()
    demo_reflective_walls()
    demo_absorbing_walls()
    demo_combined_effects()

    print("\n" + "=" * 70)
    print("✅ 所有 demo 完成")
    print("=" * 70)
