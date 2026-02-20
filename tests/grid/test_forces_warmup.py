import sys
sys.path.insert(0, "src")

import time
import numpy as np
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal, device_memory_GB=2.0)

def test_with_warmup(N):
    print(f"\n{'='*70}")
    print(f"測試 N={N} (含 Warmup)")
    print(f"{'='*70}")
    
    agent_types = [AgentType.FOLLOWER] * N
    params = FlockingParams(rc=15.0, box_size=50.0)
    
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types,
        enable_fov=False, max_agents=max(N, 200)
    )
    
    system.initialize(box_size=10.0, seed=42)
    system.assign_agents_to_grid()
    
    # === Warmup 階段 ===
    print("\n[Warmup] 執行 3 次預熱...")
    for i in range(3):
        system.compute_forces_grid()
        print(f"  Warmup {i+1}/3 完成")
    
    # === 實際測試 ===
    print("\n[測試] 執行 5 次並計算平均時間...")
    times = []
    for i in range(5):
        start = time.time()
        system.compute_forces_grid()
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"  Run {i+1}/5: {elapsed:.2f} ms")
    
    avg_time = np.mean(times)
    std_time = np.std(times)
    
    print(f"\n結果:")
    print(f"  平均時間: {avg_time:.2f} ± {std_time:.2f} ms")
    print(f"  最小時間: {min(times):.2f} ms")
    print(f"  最大時間: {max(times):.2f} ms")
    
    # 同樣測試原始版本
    print("\n[對比] 測試原始 compute_forces()...")
    times_old = []
    for i in range(5):
        start = time.time()
        system.compute_forces()
        elapsed = (time.time() - start) * 1000
        times_old.append(elapsed)
    
    avg_old = np.mean(times_old)
    
    print(f"  原始版本平均: {avg_old:.2f} ms")
    
    if avg_old > 0:
        ratio = avg_time / avg_old
        if ratio < 1:
            print(f"\n✅ Grid 版本更快: {1/ratio:.2f}x 加速")
        else:
            print(f"\n❌ Grid 版本更慢: {ratio:.2f}x")
    
    return avg_time, avg_old

# 測試不同 N
for N in [10, 20, 30]:
    try:
        test_with_warmup(N)
    except Exception as e:
        print(f"\n❌ N={N} 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        break
