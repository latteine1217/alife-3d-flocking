"""
效能基準測試

測試不同 N 值下的執行時間，識別瓶頸
"""

import sys
import time

import numpy as np

sys.path.insert(0, "src")

from agents.types import AgentType
from flocking_3d import FlockingParams
from flocking_heterogeneous import HeterogeneousFlocking3D


def benchmark_system(N: int, steps: int = 100) -> dict:
    """
    測試指定 N 值下的系統效能

    Args:
        N: Agent 數量
        steps: 模擬步數

    Returns:
        效能統計字典
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmark: N={N}, steps={steps}")
    print(f"{'=' * 60}")

    # 創建系統
    params = FlockingParams(box_size=50.0)
    agent_types = [AgentType.FOLLOWER] * int(N * 0.8) + [AgentType.PREDATOR] * int(
        N * 0.2
    )

    # 初始化時間
    t0 = time.time()
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    init_time = time.time() - t0

    # 模擬時間
    step_times = []
    t_start = time.time()

    for step in range(steps):
        t_step = time.time()
        system.step(dt=0.1)
        step_times.append(time.time() - t_step)

    total_time = time.time() - t_start

    # 統計
    avg_step_time = np.mean(step_times)
    std_step_time = np.std(step_times)
    fps = 1.0 / avg_step_time if avg_step_time > 0 else 0

    results = {
        "N": N,
        "steps": steps,
        "init_time": init_time,
        "total_time": total_time,
        "avg_step_time": avg_step_time,
        "std_step_time": std_step_time,
        "fps": fps,
        "complexity": "O(N²)" if avg_step_time > 0 else "unknown",
    }

    print(f"初始化時間:     {init_time:.3f} s")
    print(f"總模擬時間:     {total_time:.3f} s")
    print(f"平均單步時間:   {avg_step_time * 1000:.2f} ± {std_step_time * 1000:.2f} ms")
    print(f"FPS:           {fps:.1f}")
    print(f"吞吐量:         {N * fps:.0f} agents/s")

    return results


def main():
    """執行一系列基準測試"""
    # 測試不同規模
    test_sizes = [10, 20, 50, 100, 200]
    steps_per_test = 50

    all_results = []

    print("\n" + "=" * 60)
    print("效能基準測試")
    print("=" * 60)
    print(f"測試規模: {test_sizes}")
    print(f"每次測試步數: {steps_per_test}")

    for N in test_sizes:
        result = benchmark_system(N, steps=steps_per_test)
        all_results.append(result)

    # 分析複雜度
    print(f"\n{'=' * 60}")
    print("複雜度分析")
    print(f"{'=' * 60}")
    print(f"{'N':>6} | {'Time (ms)':>12} | {'Ratio':>8} | {'Complexity':>12}")
    print("-" * 60)

    prev_N = None
    prev_time = None

    for result in all_results:
        N = result["N"]
        t = result["avg_step_time"] * 1000

        ratio_str = "-"
        complexity_str = "-"

        if prev_N is not None and prev_time is not None:
            n_ratio = N / prev_N
            t_ratio = t / prev_time
            ratio_str = f"{t_ratio:.2f}x"

            # 判斷複雜度
            if 0.9 * n_ratio <= t_ratio <= 1.1 * n_ratio:
                complexity_str = "O(N)"
            elif 0.9 * n_ratio**2 <= t_ratio <= 1.1 * n_ratio**2:
                complexity_str = "O(N²)"
            else:
                complexity_str = f"O(N^{np.log(t_ratio) / np.log(n_ratio):.2f})"

        print(f"{N:>6} | {t:>12.2f} | {ratio_str:>8} | {complexity_str:>12}")

        prev_N = N
        prev_time = t

    print(f"\n{'=' * 60}")
    print("結論")
    print(f"{'=' * 60}")

    # 預測 N=500 的時間
    if len(all_results) >= 2:
        # 假設 O(N²)
        last = all_results[-1]
        N_last = last["N"]
        t_last = last["avg_step_time"]

        N_predict = 500
        t_predict = t_last * (N_predict / N_last) ** 2

        print(f"當前 N={N_last} 的平均時間: {t_last * 1000:.2f} ms")
        print(
            f"預測 N={N_predict} 的時間 (O(N²)): {t_predict * 1000:.2f} ms ({t_predict:.3f} s)"
        )
        print(f"預測 FPS (N={N_predict}): {1.0 / t_predict:.1f}")

        if t_predict > 1.0:
            print(f"\n⚠️  警告: N={N_predict} 時 FPS < 1，需要優化！")


if __name__ == "__main__":
    main()
