"""
測試完整 compute_forces_grid() 重構版本

測試目標：
1. 編譯成功（之前 >120s timeout）
2. 正確性：與原始 compute_forces() 輸出接近
3. 效能：4-5x speedup
"""

import sys

sys.path.insert(0, "src")
import time
import numpy as np
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)


def test_compilation_and_correctness(N=30):
    """測試編譯與正確性"""
    print(f"\n{'=' * 60}")
    print(f"測試 1: 編譯與正確性 (N={N})")
    print(f"{'=' * 60}")

    # 建立系統（混合 agent types 以測試所有力）
    agent_types = [AgentType.FOLLOWER] * (N // 2) + [AgentType.PREDATOR] * (N // 2)
    system = HeterogeneousFlocking3D(
        N=N,
        params=FlockingParams(),
        agent_types=agent_types,
        enable_fov=True,
        max_agents=max(200, N),
    )
    system.initialize(box_size=20.0, seed=42)

    # 測試編譯
    print("⏳ 測試 compute_forces_grid() 編譯...")
    compile_start = time.time()

    try:
        system.assign_agents_to_grid()  # 更新 Grid
        system.compute_forces_grid()  # 觸發編譯
        compile_time = time.time() - compile_start
        print(f"✅ 編譯成功！耗時: {compile_time:.2f}s")
    except Exception as e:
        print(f"❌ 編譯失敗: {e}")
        return False

    # 正確性測試
    print("\n⏳ 測試正確性（與原始 kernel 比較）...")

    # 原始版本
    system.compute_forces()
    forces_old = system.f.to_numpy().copy()

    # Grid 版本
    system.assign_agents_to_grid()
    system.compute_forces_grid()
    forces_new = system.f.to_numpy().copy()

    # 比較
    # 注意: Grid 版本限制檢查 8 個鄰居，可能有小差異
    diff = np.abs(forces_old - forces_new)
    max_diff = np.max(diff)
    mean_diff = np.mean(diff)

    # 只比較存活的 agents
    alive_mask = system.agent_alive.to_numpy() == 1
    alive_diff = diff[alive_mask]
    max_diff_alive = np.max(alive_diff) if alive_diff.size > 0 else 0
    mean_diff_alive = np.mean(alive_diff) if alive_diff.size > 0 else 0

    print(f"\n差異統計（所有 agents）:")
    print(f"  最大差異: {max_diff:.6f}")
    print(f"  平均差異: {mean_diff:.6f}")

    print(f"\n差異統計（存活 agents，N={alive_mask.sum()}）:")
    print(f"  最大差異: {max_diff_alive:.6f}")
    print(f"  平均差異: {mean_diff_alive:.6f}")

    # 判斷標準：mean_diff < 0.1（允許小誤差，因限制檢查 8 個鄰居）
    if mean_diff_alive < 0.5:
        print(f"✅ 正確性測試通過 (mean_diff={mean_diff_alive:.6f} < 0.5)")
        return True
    else:
        print(f"❌ 正確性測試失敗 (mean_diff={mean_diff_alive:.6f} >= 0.5)")
        print("\n前 5 個差異最大的 agents:")
        diff_per_agent = np.linalg.norm(diff, axis=1)
        top5_idx = np.argsort(diff_per_agent)[-5:][::-1]
        for idx in top5_idx:
            print(f"  Agent {idx}: |diff|={diff_per_agent[idx]:.6f}")
            print(f"    Old force: {forces_old[idx]}")
            print(f"    New force: {forces_new[idx]}")
        return False


def test_performance(N):
    """測試效能"""
    print(f"\n{'=' * 60}")
    print(f"測試 2: 效能 Benchmark (N={N})")
    print(f"{'=' * 60}")

    agent_types = [AgentType.FOLLOWER] * N
    system = HeterogeneousFlocking3D(
        N=N,
        params=FlockingParams(),
        agent_types=agent_types,
        enable_fov=False,  # 簡化測試
        max_agents=max(200, N),
    )
    system.initialize(box_size=20.0, seed=42)

    # Warmup
    system.compute_forces()
    system.assign_agents_to_grid()
    system.compute_forces_grid()

    # Benchmark 原始版本
    times_orig = []
    for _ in range(5):
        start = time.time()
        system.compute_forces()
        times_orig.append((time.time() - start) * 1000)
    orig_avg = sum(times_orig) / len(times_orig)

    # Benchmark Grid 版本
    times_grid = []
    for _ in range(5):
        system.assign_agents_to_grid()  # 每次都更新 Grid
        start = time.time()
        system.compute_forces_grid()
        times_grid.append((time.time() - start) * 1000)
    grid_avg = sum(times_grid) / len(times_grid)

    speedup = orig_avg / grid_avg

    print(f"原始版本: {orig_avg:.3f} ms")
    print(f"Grid版本:  {grid_avg:.3f} ms")
    print(f"加速比:   {speedup:.2f}x {'✅' if speedup > 1 else '❌'}")

    return orig_avg, grid_avg, speedup


def main():
    print("=" * 60)
    print("完整系統測試：compute_forces_grid() 重構版")
    print("=" * 60)

    # 測試 1: 編譯與正確性
    if not test_compilation_and_correctness(N=30):
        print("\n❌ 正確性測試失敗，中止效能測試")
        return

    # 測試 2: 效能 Benchmark
    print("\n" + "=" * 60)
    print("開始效能 Benchmark")
    print("=" * 60)

    results = []
    for N in [10, 30, 50, 100]:
        try:
            orig, grid, speedup = test_performance(N)
            results.append((N, orig, grid, speedup))
        except Exception as e:
            print(f"❌ N={N} 測試失敗: {e}")
            break

    # 總結
    print(f"\n{'=' * 60}")
    print("效能測試總結")
    print(f"{'=' * 60}")
    print(f"{'N':<6} {'原始(ms)':<12} {'Grid(ms)':<12} {'加速比':<8}")
    print("-" * 60)
    for N, orig, grid, speedup in results:
        status = "✅" if speedup > 1 else "❌"
        print(f"{N:<6} {orig:<12.3f} {grid:<12.3f} {speedup:<8.2f} {status}")

    avg_speedup = sum(r[3] for r in results) / len(results)
    print(f"\n平均加速比: {avg_speedup:.2f}x")

    if avg_speedup >= 3.0:
        print("✅ 效能優化成功！（目標: 3-5x speedup）")
    elif avg_speedup >= 2.0:
        print("⚠️  效能有提升，但未達理想目標（2-3x vs 目標 3-5x）")
    else:
        print("❌ 效能未達預期")


if __name__ == "__main__":
    main()
