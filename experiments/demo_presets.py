"""
視覺化展示腳本集

提供多種預設參數配置的視覺化展示：
1. 標準配置（平衡的集體行為）
2. 高對齊配置（強方向一致性）
3. 混亂配置（低對齊）
4. 大規模配置（N=500）
"""

import sys
import argparse

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
from flocking_3d import OptimizedFlockingV2, FlockingParams

# 需要先載入視覺化器類別
exec(open("/Users/latteine/Documents/coding/alife/experiments/visualizer_3d.py").read())


def demo_standard():
    """標準配置 - 平衡的集體行為"""
    print("\n" + "=" * 70)
    print("  Demo 1: 標準配置")
    print("=" * 70)
    print("  目標：展示平衡的 Morse + Rayleigh + Alignment")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=0.5,  # 中等對齊力
        box_size=50.0,
        use_pbc=True,
    )

    system = OptimizedFlockingV2(N=300, params=params)
    system.initialize(box_size=5.0, seed=42)

    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    viz.run(steps=0, dt=0.01)


def demo_high_alignment():
    """高對齊配置 - 強方向一致性"""
    print("\n" + "=" * 70)
    print("  Demo 2: 高對齊配置")
    print("=" * 70)
    print("  目標：展示強烈的集體運動（高 beta）")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=2.0,  # 高對齊力
        box_size=50.0,
        use_pbc=True,
    )

    system = OptimizedFlockingV2(N=300, params=params)
    system.initialize(box_size=5.0, seed=123)

    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    viz.run(steps=0, dt=0.01)


def demo_chaos():
    """混亂配置 - 低對齊"""
    print("\n" + "=" * 70)
    print("  Demo 3: 混亂配置")
    print("=" * 70)
    print("  目標：展示無對齊力時的混亂狀態（beta=0）")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=0.0,  # 無對齊力
        box_size=50.0,
        use_pbc=True,
    )

    system = OptimizedFlockingV2(N=300, params=params)
    system.initialize(box_size=5.0, seed=456)

    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    viz.run(steps=0, dt=0.01)


def demo_large_scale():
    """大規模配置 - N=500"""
    print("\n" + "=" * 70)
    print("  Demo 4: 大規模配置")
    print("=" * 70)
    print("  目標：展示大規模系統（N=500）")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=1.0,  # 適中對齊力
        box_size=70.0,  # 增大 box 以容納更多粒子
        use_pbc=True,
    )

    system = OptimizedFlockingV2(N=500, params=params)
    system.initialize(box_size=7.0, seed=789)

    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    viz.run(steps=0, dt=0.01)


def demo_strong_attraction():
    """強吸引配置 - 群體凝聚"""
    print("\n" + "=" * 70)
    print("  Demo 5: 強吸引配置")
    print("=" * 70)
    print("  目標：展示強吸引力下的緊密群體")
    print("=" * 70)

    params = FlockingParams(
        Ca=3.0,  # 提高吸引力
        Cr=2.0,
        la=5.0,  # 增大吸引範圍
        lr=0.5,
        rc=20.0,  # 增大互動半徑
        alpha=1.0,  # 降低主動能量（避免分散）
        v0=0.8,
        beta=1.5,  # 高對齊力
        box_size=50.0,
        use_pbc=True,
    )

    system = OptimizedFlockingV2(N=300, params=params)
    system.initialize(box_size=5.0, seed=999)

    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
    )

    viz.run(steps=0, dt=0.01)


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="V2 視覺化展示腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
可用的 demo：
  1  標準配置     - 平衡的集體行為（推薦入門）
  2  高對齊配置   - 強烈的方向一致性（beta=2.0）
  3  混亂配置     - 無對齊力的混亂狀態（beta=0.0）
  4  大規模配置   - 500 個粒子
  5  強吸引配置   - 緊密群體（Ca=3.0）

範例：
  python experiments/demo_visualizations.py --demo 1
  python experiments/demo_visualizations.py --demo 2
        """,
    )

    parser.add_argument(
        "--demo",
        type=int,
        choices=[1, 2, 3, 4, 5],
        required=True,
        help="選擇 demo 編號（1-5）",
    )

    args = parser.parse_args()

    demos = {
        1: demo_standard,
        2: demo_high_alignment,
        3: demo_chaos,
        4: demo_large_scale,
        5: demo_strong_attraction,
    }

    demos[args.demo]()
