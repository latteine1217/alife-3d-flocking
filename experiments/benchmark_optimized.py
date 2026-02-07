"""
性能測試：優化前後對比

測試優化後的核心實作效能
"""

import time
import numpy as np
from src.flocking_3d import Flocking3D, FlockingParams


def benchmark(N: int, steps: int = 100) -> float:
    """
    測試給定粒子數的性能

    Returns:
        平均每步時間 (ms)
    """
    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=0.5,
        box_size=50.0,
        use_pbc=True,
    )

    system = Flocking3D(N=N, params=params)
    system.initialize(box_size=5.0, seed=42)

    # Warmup
    for _ in range(10):
        system.step(0.01)

    # 計時
    start = time.time()
    for _ in range(steps):
        system.step(0.01)
    elapsed = time.time() - start

    return (elapsed / steps) * 1000  # ms per step


if __name__ == "__main__":
    print("=" * 70)
    print("性能基準測試 - 優化版本")
    print("=" * 70)

    test_sizes = [100, 200, 300, 500, 800, 1000]

    print(f"\n{'N':>6} | {'Time/Step (ms)':>15} | {'Steps/sec':>12}")
    print("-" * 70)

    results = []
    for N in test_sizes:
        try:
            time_per_step = benchmark(N, steps=50)
            steps_per_sec = 1000.0 / time_per_step
            results.append((N, time_per_step))
            print(f"{N:>6} | {time_per_step:>15.3f} | {steps_per_sec:>12.1f}")
        except Exception as e:
            print(f"{N:>6} | {'FAILED':>15} | {str(e)}")

    print("=" * 70)

    # 性能分析
    if len(results) >= 2:
        print("\n性能分析:")
        N1, t1 = results[0]
        N2, t2 = results[-1]
        scaling = (t2 / t1) / ((N2 / N1) ** 2)
        print(f"  從 N={N1} 到 N={N2}:")
        print(f"  時間增長: {t2 / t1:.2f}x")
        print(f"  理論 O(N²): {(N2 / N1) ** 2:.2f}x")
        print(f"  效率係數: {scaling:.3f} (接近 1.0 表示最佳)")

    print("=" * 70)
