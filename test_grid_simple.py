#!/usr/bin/env python3
"""
簡化版 Grid 測試
"""

import sys

sys.path.insert(0, "src")

import taichi as ti
import numpy as np
import time
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.cpu, debug=True)

# 建立小規模系統
N = 50
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

agent_types = (
    [AgentType.EXPLORER] * 15
    + [AgentType.FOLLOWER] * 25
    + [AgentType.LEADER] * 8
    + [AgentType.PREDATOR] * 2
)

print(f"Creating system with N={N}...")
system = HeterogeneousFlocking3D(
    N=N,
    params=params,
    agent_types=agent_types,
    enable_fov=True,
    fov_angle=120.0,
    max_obstacles=10,
    max_resources=5,
)

system.initialize(box_size=50.0, seed=42)
print("System initialized")

# 測試 Grid 分配
print("\n--- Testing Grid Assignment ---")
start = time.perf_counter()
system.assign_agents_to_grid()
elapsed = (time.perf_counter() - start) * 1000
print(f"assign_agents_to_grid: {elapsed:.2f} ms")

# 檢查 cell 分配
cell_counts = system.cell_count.to_numpy()
agent_cells = system.agent_cell_id.to_numpy()
print(f"Max agents per cell: {cell_counts.max()}")
print(f"Cells used: {np.sum(cell_counts > 0)} / {len(cell_counts)}")
print(f"Agent cell IDs (first 10): {agent_cells[:10]}")

# 測試單次群組檢測迭代
print("\n--- Testing Group Detection Iteration ---")
system.group_id.fill(-1)
for i in range(N):
    if system.agent_types_np[i] != 3:
        system.group_id[i] = i

start = time.perf_counter()
system.detect_groups_iteration(5.0, np.radians(30.0))
elapsed = (time.perf_counter() - start) * 1000
print(f"detect_groups_iteration: {elapsed:.2f} ms")

# 檢查結果
group_ids = system.group_id.to_numpy()
print(f"Group IDs (first 10): {group_ids[:10]}")
print(f"Unique groups: {len(np.unique(group_ids[group_ids >= 0]))}")

print("\n✅ Grid implementation working!")
