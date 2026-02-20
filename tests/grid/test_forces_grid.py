import sys
sys.path.insert(0, "src")

import time
import numpy as np
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal, device_memory_GB=2.0)

def test_forces(N):
    print(f"\n=== 測試 N={N} ===")
    
    agent_types = [AgentType.FOLLOWER] * N
    params = FlockingParams(rc=15.0, box_size=50.0)
    
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types,
        enable_fov=False, max_agents=max(N, 200)
    )
    
    system.initialize(box_size=10.0, seed=42)
    
    # 測試 Grid 優化版本
    system.assign_agents_to_grid()
    
    start = time.time()
    system.compute_forces_grid()
    grid_time = (time.time() - start) * 1000
    
    forces = system.f.to_numpy()
    print(f"  Grid 版本: {grid_time:.2f} ms")
    print(f"  力範圍: [{forces.min():.3f}, {forces.max():.3f}]")
    
    return grid_time

for N in [10, 30, 50, 100]:
    test_forces(N)
