#!/usr/bin/env python3
"""
測試掠食者序列化
驗證 types 資料是否正確傳遞
"""

import sys

sys.path.insert(0, "src")
sys.path.insert(0, "backend")

import taichi as ti
import numpy as np
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams
from serializer import BinarySerializer

# 初始化 Taichi
ti.init(arch=ti.cpu)  # 使用 CPU 以避免 GPU 衝突

# 建立系統（與 simulation_manager.py 相同的配置）
N = 100
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
agent_types = (
    [AgentType.EXPLORER] * 30
    + [AgentType.FOLLOWER] * 50
    + [AgentType.LEADER] * 15
    + [AgentType.PREDATOR] * 5
)

print(f"Creating system with {len(agent_types)} agents...")
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

# 檢查 agent_types_np 是否存在
if hasattr(system, "agent_types_np"):
    print("✅ agent_types_np 存在")
    print(f"   Shape: {system.agent_types_np.shape}")
    print(f"   Dtype: {system.agent_types_np.dtype}")

    # 檢查掠食者位置
    predator_indices = np.where(system.agent_types_np == AgentType.PREDATOR)[0]
    print(
        f"\n🦁 Found {len(predator_indices)} predators at indices: {predator_indices.tolist()}"
    )
else:
    print("❌ agent_types_np 不存在！")

# 測試序列化
print("\n=== Testing Serialization ===")
data = BinarySerializer.serialize_state(system)
print(f"Serialized data size: {len(data)} bytes")

# 手動解析 types 資料
import struct

# Header: 20 bytes
# Positions: N * 3 * 4 = 1200 bytes
# Velocities: N * 3 * 4 = 1200 bytes
# Types: N bytes + padding
offset = 20 + 1200 + 1200
types_bytes = data[offset : offset + N]
types_decoded = list(types_bytes)

print(f"\n=== Decoded Types (first 10 and last 10) ===")
print(f"First 10: {types_decoded[:10]}")
print(f"Last 10: {types_decoded[-10:]}")

# 檢查掠食者
predator_count = types_decoded.count(AgentType.PREDATOR)
predator_indices_decoded = [
    i for i, t in enumerate(types_decoded) if t == AgentType.PREDATOR
]
print(f"\n🦁 Decoded predators: {predator_count} at indices {predator_indices_decoded}")

if predator_count == 5:
    print("✅ 序列化成功！")
else:
    print(f"❌ 序列化失敗！Expected 5 predators, got {predator_count}")
