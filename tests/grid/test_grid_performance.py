#!/usr/bin/env python3
"""
Spatial Grid 群組檢測效能測試（腳本）

Note:
    這個檔案是效能/診斷腳本，不是 pytest 的單元測試。
    為了避免 pytest 收集時執行耗時流程，所有邏輯都放在 main()。
"""


def main() -> None:
    import sys
    import time

    sys.path.insert(0, "src")

    import taichi as ti
    import numpy as np

    from flocking_heterogeneous import HeterogeneousFlocking3D
    from agents.types import AgentType
    from flocking_3d import FlockingParams

    # 初始化 Taichi（使用 CPU 以避免與後端 GPU 衝突）
    ti.init(arch=ti.cpu)

    # 測試參數
    N_values = [100, 200, 500]  # 不同規模
    r_cluster = 5.0
    theta_cluster = 30.0
    n_iterations = 3

    print("=" * 70)
    print("Spatial Grid 群組檢測效能測試")
    print("=" * 70)

    baseline_time = None
    baseline_N = None

    for N in N_values:
        print(f"\n{'=' * 70}")
        print(f"測試規模：N = {N}")
        print(f"{'=' * 70}")

        params = FlockingParams(
            Ca=1.5,
            Cr=2.0,
            la=2.5,
            lr=0.5,
            rc=15.0,
            alpha=2.0,
            v0=1.0,
            beta=1.0,
            eta=0.0,
            box_size=50.0,
            boundary_mode="pbc",
        )

        # 組成：30% Explorer, 50% Follower, 15% Leader, 5% Predator
        n_predator = max(1, int(N * 0.05))
        n_leader = int(N * 0.15)
        n_explorer = int(N * 0.30)
        n_follower = N - n_predator - n_leader - n_explorer

        agent_types = (
            [AgentType.EXPLORER] * n_explorer
            + [AgentType.FOLLOWER] * n_follower
            + [AgentType.LEADER] * n_leader
            + [AgentType.PREDATOR] * n_predator
        )

        system = HeterogeneousFlocking3D(
            N=N,
            max_agents=N,  # performance script: 容量需 >= N
            params=params,
            agent_types=agent_types,
            enable_fov=True,
            fov_angle=120.0,
            max_obstacles=10,
            max_resources=5,
        )

        system.initialize(box_size=50.0, seed=42)

        # 執行幾步讓系統穩定
        for _ in range(10):
            system.step(dt=0.01)

        # 效能測試：群組檢測
        n_runs = 20
        times = []

        print(f"\n執行 {n_runs} 次群組檢測...")
        for _ in range(n_runs):
            start = time.perf_counter()
            system.update_groups(
                r_cluster=r_cluster,
                theta_cluster=theta_cluster,
                n_iterations=n_iterations,
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        mean_time = float(np.mean(times))
        std_time = float(np.std(times))
        min_time = float(np.min(times))
        max_time = float(np.max(times))

        grid_res = max(int(50.0 / r_cluster) + 1, 4)
        total_cells = grid_res**3
        avg_agents_per_cell = N / total_cells

        print(f"\n--- Grid 配置 ---")
        print(f"  Grid Resolution: {grid_res}³ = {total_cells} cells")
        print(f"  Cell Size: {r_cluster} units")
        print(f"  Avg Agents/Cell: {avg_agents_per_cell:.2f}")
        print(f"  Neighbor Cells: 27 (3×3×3)")

        print(f"\n--- 效能結果 ---")
        print(f"  平均時間: {mean_time:.2f} ± {std_time:.2f} ms")
        print(f"  最小時間: {min_time:.2f} ms")
        print(f"  最大時間: {max_time:.2f} ms")

        theoretical_speedup = (N * N) / (N * avg_agents_per_cell * 27)
        print(f"\n  理論加速比: ~{theoretical_speedup:.1f}x")
        print(f"  (假設原始演算法 O(N²)，Grid 演算法 O(N×k_local×27))")

        groups = system.get_all_groups()
        print(f"\n--- 群組統計 ---")
        print(f"  檢測到 {len(groups)} 個群組 (size ≥ 3)")
        if len(groups) > 0:
            sizes = [g['size'] for g in groups]
            print(f"  群組大小範圍: {min(sizes)} - {max(sizes)}")
            print(f"  平均群組大小: {np.mean(sizes):.1f}")

        if baseline_time is None and N == N_values[0]:
            baseline_time = mean_time
            baseline_N = N

    print("\n" + "=" * 70)
    print("測試完成！")
    print("=" * 70)

    if baseline_time is None or baseline_N is None:
        return

    print("\n" + "=" * 70)
    print("效能預測（基於理論複雜度）")
    print("=" * 70)
    print(f"{'N':>6} | {'Grid (ms)':>12} | {'O(N²) 估計 (ms)':>18} | {'加速比':>8}")
    print("-" * 70)

    for N_pred in [100, 200, 500, 1000, 2000, 5000]:
        grid_time = baseline_time * (N_pred / baseline_N)
        naive_time = baseline_time * ((N_pred / baseline_N) ** 2) * 10
        speedup = naive_time / grid_time
        print(
            f"{N_pred:>6} | {grid_time:>10.2f} ms | {naive_time:>16.2f} ms | {speedup:>7.1f}x"
        )


if __name__ == "__main__":
    main()

