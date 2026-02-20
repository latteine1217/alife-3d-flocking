"""
診斷前端顯示問題

檢查項目：
1. Type 資料是否正確序列化
2. Group 計算是否有執行
3. Position 是否有超出邊界的問題
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "backend")

import taichi as ti
import numpy as np
from backend.simulation_manager import SimulationManager
from backend.serializer import BinarySerializer

# 初始化 Taichi
ti.init(arch=ti.cpu)

# 創建 simulation manager
manager = SimulationManager()

print("=== 運行模擬並檢查數據 ===\n")

# 運行 20 步（讓群組有時間形成）
print("Step 1: 運行 20 步模擬...")
for i in range(20):
    manager.step()
    if i % 5 == 0:
        print(f"  Step {i}/20")

print("✅ 模擬運行完成\n")

# 序列化當前狀態
print("Step 2: 序列化當前狀態...")
data = BinarySerializer.serialize_state(manager.system)
print(f"✅ 序列化完成，數據大小: {len(data)} bytes\n")

# 解析數據並檢查
print("Step 3: 解析並檢查數據...\n")

import struct
view_bytes = data
offset = 0

# Header
N = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
step = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
has_resources = struct.unpack("B", view_bytes[offset:offset+1])[0]; offset += 1
has_obstacles = struct.unpack("B", view_bytes[offset:offset+1])[0]; offset += 1
offset += 10  # reserved

print(f"📊 Header:")
print(f"  N = {N}")
print(f"  step = {step}")
print(f"  has_resources = {has_resources}")
print(f"  has_obstacles = {has_obstacles}")
print()

# Positions
positions = np.frombuffer(view_bytes[offset:offset+N*3*4], dtype=np.float32)
offset += N * 3 * 4
print(f"📍 Positions:")
print(f"  範圍: X [{positions[0::3].min():.2f}, {positions[0::3].max():.2f}]")
print(f"        Y [{positions[1::3].min():.2f}, {positions[1::3].max():.2f}]")
print(f"        Z [{positions[2::3].min():.2f}, {positions[2::3].max():.2f}]")
print(f"  ⚠️ 問題: 粒子是否在邊界 [-25, 25] 內? {positions.min() >= -25 and positions.max() <= 25}")
print()

# Velocities
velocities = np.frombuffer(view_bytes[offset:offset+N*3*4], dtype=np.float32)
offset += N * 3 * 4

# Types
types = np.frombuffer(view_bytes[offset:offset+N], dtype=np.uint8)
offset += N
padding = (4 - (N % 4)) % 4
offset += padding

print(f"🎭 Types:")
type_counts = {
    0: (types == 0).sum(),
    1: (types == 1).sum(),
    2: (types == 2).sum(),
    3: (types == 3).sum(),
}
print(f"  Follower (0): {type_counts[0]}")
print(f"  Explorer (1): {type_counts[1]}")
print(f"  Leader (2): {type_counts[2]}")
print(f"  Predator (3): {type_counts[3]}")
print(f"  ⚠️ 問題: 是否有 Predators? {type_counts[3] > 0}")
if type_counts[3] > 0:
    predator_indices = np.where(types == 3)[0]
    print(f"  Predator 索引: {predator_indices}")
    print(f"  Predator 位置:")
    for idx in predator_indices[:5]:  # 只顯示前 5 個
        px = positions[idx*3]
        py = positions[idx*3+1]
        pz = positions[idx*3+2]
        print(f"    Agent {idx}: ({px:.2f}, {py:.2f}, {pz:.2f})")
print()

# Energies
energies = np.frombuffer(view_bytes[offset:offset+N*4], dtype=np.float32)
offset += N * 4

# Targets
targets = np.frombuffer(view_bytes[offset:offset+N*4], dtype=np.int32)
offset += N * 4

# Group labels
group_labels = np.frombuffer(view_bytes[offset:offset+N*4], dtype=np.int32)
offset += N * 4

print(f"🌈 Group Labels:")
unique_groups = np.unique(group_labels[group_labels >= 0])
print(f"  有效群組數: {len(unique_groups)}")
print(f"  群組 IDs: {unique_groups}")
print(f"  ⚠️ 問題: 是否有計算群組? {len(unique_groups) > 0}")
if len(unique_groups) > 0:
    for gid in unique_groups[:5]:  # 只顯示前 5 個
        count = (group_labels == gid).sum()
        print(f"    Group {gid}: {count} agents")
else:
    print(f"  ⚠️ 所有 group_labels 值: {np.unique(group_labels)}")
print()

# Statistics
mean_speed = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
std_speed = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
Rg = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
polarization = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
offset += 16  # skip reserved
n_groups_stat = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
offset += 28  # padding

print(f"📈 Statistics:")
print(f"  mean_speed = {mean_speed:.3f}")
print(f"  std_speed = {std_speed:.3f}")
print(f"  Rg = {Rg:.3f}")
print(f"  polarization = {polarization:.3f}")
print(f"  n_groups (from stats) = {n_groups_stat}")
print()

# Resources
if has_resources:
    n_resources = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
    print(f"💎 Resources: {n_resources}")
    for i in range(n_resources):
        x = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        y = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        z = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        amount = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        radius = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        renewable = struct.unpack("B", view_bytes[offset:offset+1])[0]; offset += 1
        offset += 3  # padding
        print(f"  Resource {i}: pos=({x:.1f}, {y:.1f}, {z:.1f}), amount={amount:.2f}, radius={radius:.1f}, renewable={renewable}")
    print()

# Group statistics
if offset + 4 <= len(view_bytes):
    n_active_groups = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
    print(f"🔮 Group Statistics: {n_active_groups} active groups")

    for i in range(n_active_groups):
        if offset + 36 > len(view_bytes):
            print(f"  ⚠️ 資料不足，無法讀取 group {i}")
            break
        group_id = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
        size = struct.unpack("I", view_bytes[offset:offset+4])[0]; offset += 4
        cx = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        cy = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        cz = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        vx = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        vy = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        vz = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        radius = struct.unpack("f", view_bytes[offset:offset+4])[0]; offset += 4
        print(f"  Group {group_id}: size={size}, centroid=({cx:.1f}, {cy:.1f}, {cz:.1f}), velocity=({vx:.2f}, {vy:.2f}, {vz:.2f}), radius={radius:.1f}")
    print()
else:
    print("⚠️ 無 group statistics 資料")
    print()

print("=== 診斷完成 ===\n")
print("🔍 問題總結:")
print(f"  1. Type 顏色問題: Predator 數量 = {type_counts[3]} (預期 > 0)")
print(f"  2. Group 計算問題: 群組數量 = {len(unique_groups)} (預期 > 0)")
print(f"  3. 邊界問題: 位置範圍 = [{positions.min():.2f}, {positions.max():.2f}] (預期 [-25, 25])")
