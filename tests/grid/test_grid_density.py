"""
分析 Grid 密度分布：理解為何 max_check=12 沒效果
"""

import sys

sys.path.insert(0, "src")
import numpy as np
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)

# 建立系統
N = 100
system = HeterogeneousFlocking3D(
    N=N,
    params=FlockingParams(),
    agent_types=[AgentType.FOLLOWER] * N,
    enable_fov=False,
    max_agents=max(200, N),
)
system.initialize(box_size=20.0, seed=42)
system.assign_agents_to_grid()

# 分析 cell_count 分布
cell_counts = system.cell_count.to_numpy()
# 修正：只看合理範圍內的值（N=100，單個 cell 不可能有 665 個 agents）
cell_counts = cell_counts[cell_counts <= N]  # 過濾異常值
non_zero = cell_counts[cell_counts > 0]

print(f"{'=' * 60}")
print(f"Grid 密度分析 (N={N}, box_size=20.0)")
print(f"{'=' * 60}")
print(f"Grid resolution: {system.grid_resolution}³ = {system.grid_resolution**3} cells")
print(f"Max agents per cell: {system.max_agents_per_cell}")
print(
    f"\n非空 cells: {len(non_zero)}/{len(cell_counts)} ({100 * len(non_zero) / len(cell_counts):.1f}%)"
)

print(f"\nCell 內 agent 數量分布:")
print(f"  平均: {non_zero.mean():.2f}")
print(f"  中位數: {np.median(non_zero):.0f}")
print(f"  最大: {non_zero.max():.0f}")
print(
    f"  ≥8 個: {(non_zero >= 8).sum()}/{len(non_zero)} ({100 * (non_zero >= 8).sum() / len(non_zero):.1f}%)"
)
print(
    f"  ≥12 個: {(non_zero >= 12).sum()}/{len(non_zero)} ({100 * (non_zero >= 12).sum() / len(non_zero):.1f}%)"
)

print(f"\n分布直方圖:")
for i in range(1, min(20, non_zero.max() + 1)):
    count = (non_zero == i).sum()
    bar = "█" * int(count / len(non_zero) * 50)
    print(f"  {i:2d} agents: {count:3d} cells {bar}")

print(f"\n{'=' * 60}")
print(f"結論: max_check=12 vs max_check=8 的影響")
print(f"{'=' * 60}")

# 計算被 max_check 限制影響的 agents 數量
total_neighbors_8 = 0
total_neighbors_12 = 0
total_neighbors_full = 0

for cell_count in non_zero:
    total_neighbors_full += cell_count
    total_neighbors_8 += min(cell_count, 8)
    total_neighbors_12 += min(cell_count, 12)

coverage_8 = 100 * total_neighbors_8 / total_neighbors_full
coverage_12 = 100 * total_neighbors_12 / total_neighbors_full

print(f"max_check=8  覆蓋率: {coverage_8:.1f}%")
print(f"max_check=12 覆蓋率: {coverage_12:.1f}%")
print(f"額外增加: {coverage_12 - coverage_8:.1f}%")

if coverage_12 - coverage_8 < 5:
    print(f"\n⚠️  提高 max_check 幾乎沒有實際效益（<5% 改善）")
    print(f"   原因: 大部分 cells 的 agent 數量 < 8")
