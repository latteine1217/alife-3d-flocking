import sys
sys.path.insert(0, "src")
import time
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal, device_memory_GB=2.0)

N = 10
print(f"創建系統 N={N}...")

agent_types = [AgentType.FOLLOWER] * N
params = FlockingParams(rc=15.0, box_size=50.0)
system = HeterogeneousFlocking3D(
    N=N, params=params, agent_types=agent_types,
    enable_fov=False, max_agents=200
)

print("初始化...")
system.initialize(box_size=10.0, seed=42)

print("更新 Grid...")
system.assign_agents_to_grid()

print("\n測試原始 compute_forces()...")
start = time.time()
system.compute_forces()
t1 = (time.time() - start) * 1000
print(f"  第 1 次: {t1:.2f} ms")

start = time.time()
system.compute_forces()
t2 = (time.time() - start) * 1000
print(f"  第 2 次: {t2:.2f} ms (warmup 後)")

print("\n測試 Grid 優化 compute_forces_grid()...")
print("  第 1 次執行中...", flush=True)
start = time.time()
system.compute_forces_grid()
t3 = (time.time() - start) * 1000
print(f"  第 1 次: {t3:.2f} ms")

print("  第 2 次執行中...", flush=True)
start = time.time()
system.compute_forces_grid()
t4 = (time.time() - start) * 1000
print(f"  第 2 次: {t4:.2f} ms (warmup 後)")

print(f"\n對比 (warmup 後):")
print(f"  原始版本: {t2:.2f} ms")
print(f"  Grid 版本: {t4:.2f} ms")
if t2 > 0:
    print(f"  比例: {t4/t2:.2f}x")
