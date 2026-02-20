"""
快速測試：確認主系統切換到 Grid 版本後仍正常運作
"""

import sys

sys.path.insert(0, "src")
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)

# 建立小型系統
system = HeterogeneousFlocking3D(
    N=20,
    params=FlockingParams(),
    agent_types=[AgentType.FOLLOWER] * 15 + [AgentType.PREDATOR] * 5,
    enable_fov=True,
    max_agents=50,
)
system.initialize(box_size=15.0, seed=42)

print("✅ 系統初始化成功")

# 執行 10 步
print("\n⏳ 執行 10 步...")
for step in range(10):
    system.step(dt=0.1)
    n_alive = system.agent_alive.to_numpy().sum()
    print(f"  Step {step + 1:2d}: {n_alive} agents alive")

print("\n✅ 系統運作正常！Grid 優化版已整合")
