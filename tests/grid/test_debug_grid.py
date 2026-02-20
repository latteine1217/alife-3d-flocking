import sys
sys.path.insert(0, "src")
import time
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal, device_memory_GB=2.0)

N = 5  # 更小的 N
print(f"創建系統 N={N}...")

agent_types = [AgentType.FOLLOWER] * N
params = FlockingParams(rc=15.0, box_size=50.0)
system = HeterogeneousFlocking3D(
    N=N, params=params, agent_types=agent_types,
    enable_fov=False, max_agents=200
)

system.initialize(box_size=10.0, seed=42)
system.assign_agents_to_grid()

# 檢查 Grid 資料
print("\nGrid 資訊:")
print(f"  grid_resolution: {system.grid_resolution}")
print(f"  max_agents_per_cell: {system.max_agents_per_cell}")
print(f"  total_cells: {system.grid_resolution**3}")

# 檢查有多少 agents 在 Grid 中
cell_counts = system.cell_count.to_numpy()
non_zero_cells = (cell_counts > 0).sum()
max_count = cell_counts.max()
print(f"  使用的 cells: {non_zero_cells}")
print(f"  最多 agents/cell: {max_count}")

# 檢查 agent_cell_id
cell_ids = system.agent_cell_id.to_numpy()[:N]
print(f"  前 {N} 個 agents 的 cell_id: {cell_ids}")

print("\n開始測試 compute_forces_grid()...")
print("(如果卡住超過 5 秒，按 Ctrl+C 中止)")

start = time.time()
try:
    system.compute_forces_grid()
    elapsed = (time.time() - start) * 1000
    print(f"✅ 完成！時間: {elapsed:.2f} ms")
except KeyboardInterrupt:
    elapsed = time.time() - start
    print(f"\n❌ 被中斷！已執行 {elapsed:.1f} 秒")
    print("結論：Grid 版本確實卡住了")
