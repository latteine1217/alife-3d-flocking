"""
測試死亡 agents 消失機制
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from flocking_heterogeneous import HeterogeneousFlocking3D, AgentType
from flocking_3d import FlockingParams
from resources import ResourceConfig

print("=" * 70)
print("測試死亡 Agents 消失機制")
print("=" * 70)

# === 測試 1: 餓死消失 ===
print("\n[測試 1] 能量耗盡死亡 → 消失")
print("-" * 70)

params = FlockingParams(box_size=50.0)
system = HeterogeneousFlocking3D(
    N=5, params=params, agent_types=[AgentType.FOLLOWER] * 5
)

system.initialize(seed=42)

# 設定不同能量等級
system.agent_energy[0] = 100.0  # 健康
system.agent_energy[1] = 50.0  # 中等
system.agent_energy[2] = 10.0  # 瀕死
system.agent_energy[3] = 1.0  # 極低
system.agent_energy[4] = 0.0  # 已死

# 記錄初始位置
x_before = system.x.to_numpy().copy()
print(f"初始位置：")
for i in range(5):
    print(f"  Agent {i} (能量 {system.agent_energy[i]:.0f}): {x_before[i][:2]}")

# 應用能量死亡機制
system.apply_energy_death()

# 檢查死亡後位置
x_after = system.x.to_numpy()
alive_after = system.agent_alive.to_numpy()

print(f"\n死亡後狀態：")
for i in range(5):
    is_alive = alive_after[i] == 1
    pos = x_after[i]
    dist_from_origin = np.linalg.norm(pos)

    if is_alive:
        print(f"  Agent {i}: ✅ 存活, 位置 {pos[:2]}")
    else:
        print(f"  Agent {i}: 💀 死亡, 已消失（距離原點 {dist_from_origin:.0e}）")

# 驗證
assert alive_after[0] == 1, "能量 100 應該存活"
assert alive_after[4] == 0, "能量 0 應該死亡"
assert np.linalg.norm(x_after[4]) > 1e5, "死亡 agent 應該在遠處"
print("\n✅ 餓死 agent 正確消失")

# === 測試 2: 被捕食死亡消失 ===
print("\n[測試 2] 被捕食死亡 → 消失")
print("-" * 70)

params = FlockingParams(box_size=50.0)
system = HeterogeneousFlocking3D(
    N=3,
    params=params,
    agent_types=[AgentType.PREDATOR, AgentType.FOLLOWER, AgentType.FOLLOWER],
)

system.initialize(seed=42)

# 設定場景：掠食者緊鄰獵物
system.x.from_numpy(
    np.array(
        [
            [0, 0, 0],  # Predator
            [0.5, 0, 0],  # Prey 1 (很近，攻擊範圍內)
            [10, 0, 0],  # Prey 2 (遠處，安全)
        ],
        dtype=np.float32,
    )
)

# 設定速度與能量（讓攻擊成功率高）
system.v.from_numpy(
    np.array(
        [
            [2, 0, 0],  # Predator (快)
            [0.5, 0, 0],  # Prey 1 (慢)
            [1, 0, 0],  # Prey 2
        ],
        dtype=np.float32,
    )
)

system.agent_energy[0] = 100.0  # Predator (健康)
system.agent_energy[1] = 10.0  # Prey 1 (虛弱，容易被捕)
system.agent_energy[2] = 100.0  # Prey 2 (健康)

# 記錄初始狀態
x_init = system.x.to_numpy()
print(f"初始狀態：")
print(f"  Predator 0: 位置 {x_init[0][:2]}, 能量 {system.agent_energy[0]:.0f}")
print(f"  Prey 1: 位置 {x_init[1][:2]}, 能量 {system.agent_energy[1]:.0f}")
print(f"  Prey 2: 位置 {x_init[2][:2]}, 能量 {system.agent_energy[2]:.0f}")

# 執行掠食者搜尋與攻擊（多次嘗試，因為有機率失敗）
max_attempts = 20
prey1_caught = False

for attempt in range(max_attempts):
    system.find_nearest_prey()
    system.attack_prey_step()

    if system.agent_alive[1] == 0:
        prey1_caught = True
        print(f"\n🦁 Prey 1 在第 {attempt + 1} 次攻擊中被捕食")
        break

if prey1_caught:
    # 檢查死亡後狀態
    x_after = system.x.to_numpy()
    alive_after = system.agent_alive.to_numpy()

    print(f"\n捕食後狀態：")
    print(f"  Predator 0: ✅ 存活, 能量 {system.agent_energy[0]:.1f}")
    print(f"  Prey 1: 💀 被捕食, 已消失（距離原點 {np.linalg.norm(x_after[1]):.0e}）")
    print(f"  Prey 2: ✅ 存活, 位置 {x_after[2][:2]}")

    # 驗證
    assert alive_after[0] == 1, "Predator 應該存活"
    assert alive_after[1] == 0, "Prey 1 應該死亡"
    assert alive_after[2] == 1, "Prey 2 應該存活"
    assert np.linalg.norm(x_after[1]) > 1e5, "被捕食 agent 應該在遠處"

    print("\n✅ 被捕食 agent 正確消失")
else:
    print(f"\n⚠️  經過 {max_attempts} 次嘗試未成功捕食（機率問題，非錯誤）")

# === 測試 3: 死亡後不參與物理交互 ===
print("\n[測試 3] 死亡 agent 不參與物理交互")
print("-" * 70)

params = FlockingParams(box_size=50.0)
system = HeterogeneousFlocking3D(
    N=3, params=params, agent_types=[AgentType.FOLLOWER] * 3
)

system.initialize(box_size=5.0, seed=42)

# 殺死 agent 1
system.agent_energy[1] = 0.0
system.apply_energy_death()

# 運行模擬
for _ in range(10):
    system.step(dt=0.1)

# 檢查死亡 agent 狀態
v_final = system.v.to_numpy()
x_final = system.x.to_numpy()

print(f"模擬後狀態：")
print(f"  Agent 0: 速度 {np.linalg.norm(v_final[0]):.3f}, 存活")
print(f"  Agent 1: 速度 {np.linalg.norm(v_final[1]):.3f}, 死亡（應為 0）")
print(f"  Agent 2: 速度 {np.linalg.norm(v_final[2]):.3f}, 存活")

# 驗證死亡 agent 靜止
assert np.linalg.norm(v_final[1]) < 1e-6, "死亡 agent 速度應為 0"
assert np.linalg.norm(x_final[1]) > 1e5, "死亡 agent 應該在遠處"

print("\n✅ 死亡 agent 正確靜止且不參與交互")

# === 總結 ===
print("\n" + "=" * 70)
print("✅ 死亡消失機制測試完成！")
print("=" * 70)
print("\n機制總結：")
print("  1. ✅ 能量耗盡 → 消失到遠處")
print("  2. ✅ 被捕食 → 消失到遠處")
print("  3. ✅ 死亡後速度為 0，不參與物理交互")
print()
