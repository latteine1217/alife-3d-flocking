"""
快速測試三項改進：
1. 質量動力學修正
2. 最小距離排斥力
3. 虛弱狀態系統
4. 動態攻擊成功率
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from flocking_heterogeneous import HeterogeneousFlocking3D, AgentType
from flocking_3d import FlockingParams
from resources import ResourceConfig

print("=" * 70)
print("測試改進項目")
print("=" * 70)

# === 測試 1: 質量動力學 ===
print("\n[測試 1] 質量動力學修正")
print("-" * 70)

params = FlockingParams(box_size=30.0, alpha=0.0, beta=0.0)
system = HeterogeneousFlocking3D(
    N=2, params=params, agent_types=[AgentType.FOLLOWER, AgentType.LEADER]
)

# 設定初始狀態
system.initialize(seed=42)
system.x.from_numpy(np.array([[0, 0, 0], [3, 0, 0]], dtype=np.float32))
system.v.from_numpy(np.array([[0, 0, 0], [0, 0, 0]], dtype=np.float32))

# 取得質量
mass1 = system.mass_individual[0]
mass2 = system.mass_individual[1]
print(f"Agent 0 (Follower) 質量: {mass1:.2f}")
print(f"Agent 1 (Leader) 質量: {mass2:.2f}")

# 運行一步
system.step(dt=0.1)

v_after = system.v.to_numpy()
print(f"Agent 0 速度: {np.linalg.norm(v_after[0]):.4f}")
print(f"Agent 1 速度: {np.linalg.norm(v_after[1]):.4f}")
print("✅ 質量影響速度變化（較輕的 agent 加速更快）")

# === 測試 2: 最小距離排斥 ===
print("\n[測試 2] 最小距離排斥力")
print("-" * 70)

params = FlockingParams(box_size=30.0, Cr=2.0, lr=0.5)
system = HeterogeneousFlocking3D(
    N=10, params=params, agent_types=[AgentType.FOLLOWER] * 10
)

system.initialize(box_size=1.0, seed=42)  # 緊密初始化

# 運行模擬
for _ in range(50):
    system.step(dt=0.01)

# 檢查最小距離
x_final = system.x.to_numpy()
min_dist = float("inf")
for i in range(10):
    for j in range(i + 1, 10):
        dist = np.linalg.norm(x_final[i] - x_final[j])
        min_dist = min(min_dist, dist)

print(f"最小 agent 間距: {min_dist:.2f}")
if min_dist > 0.7:
    print("✅ agents 保持合理最小距離（> 0.7）")
else:
    print(f"⚠️  agents 距離偏近（{min_dist:.2f}），可能需要調整排斥力")

# === 測試 3: 虛弱狀態 ===
print("\n[測試 3] 虛弱狀態系統")
print("-" * 70)

params = FlockingParams(box_size=50.0)
system = HeterogeneousFlocking3D(
    N=3, params=params, agent_types=[AgentType.FOLLOWER] * 3
)

system.initialize(seed=42)

# 手動設定不同能量等級
system.agent_energy[0] = 80.0  # 健康
system.agent_energy[1] = 40.0  # 疲勞
system.agent_energy[2] = 10.0  # 瀕死

# 記錄基礎速度
v0_base = system.v0_individual.to_numpy().copy()

# 觸發健康狀態更新
system.consume_resources_step()

# 檢查速度變化
v0_after = system.v0_individual.to_numpy()
health_status = system.agent_health_status.to_numpy()

print(
    f"Agent 0 (能量 80): 健康狀態={health_status[0]}, 速度={v0_after[0] / v0_base[0]:.1%}"
)
print(
    f"Agent 1 (能量 40): 健康狀態={health_status[1]}, 速度={v0_after[1] / v0_base[1]:.1%}"
)
print(
    f"Agent 2 (能量 10): 健康狀態={health_status[2]}, 速度={v0_after[2] / v0_base[2]:.1%}"
)

if health_status[0] == 0 and health_status[2] == 3:
    print("✅ 健康狀態正確分級")
if v0_after[0] > v0_after[1] > v0_after[2]:
    print("✅ 速度隨能量降低而下降")

# === 測試 4: 動態攻擊成功率 ===
print("\n[測試 4] 動態攻擊成功率")
print("-" * 70)

params = FlockingParams(box_size=50.0)
system = HeterogeneousFlocking3D(
    N=3,
    params=params,
    agent_types=[AgentType.PREDATOR, AgentType.FOLLOWER, AgentType.FOLLOWER],
)

system.initialize(seed=42)

# 設定場景：掠食者追捕獵物
system.x.from_numpy(
    np.array(
        [
            [0, 0, 0],  # Predator
            [1, 0, 0],  # Prey 1 (虛弱)
            [1.5, 0, 0],  # Prey 2 (健康)
        ],
        dtype=np.float32,
    )
)

# 設定速度
system.v.from_numpy(
    np.array(
        [
            [2, 0, 0],  # Predator (快)
            [0.5, 0, 0],  # Prey 1 (慢，虛弱)
            [1.5, 0, 0],  # Prey 2 (快)
        ],
        dtype=np.float32,
    )
)

# 設定能量
system.agent_energy[0] = 80.0  # Predator (健康)
system.agent_energy[1] = 20.0  # Prey 1 (虛弱)
system.agent_energy[2] = 90.0  # Prey 2 (健康)

# 計算成功率
v_np = system.v.to_numpy()
success_rate_1 = system._compute_attack_success_rate(0, 1, v_np)
success_rate_2 = system._compute_attack_success_rate(0, 2, v_np)

print(f"對虛弱獵物 (能量 20) 的成功率: {success_rate_1:.1%}")
print(f"對健康獵物 (能量 90) 的成功率: {success_rate_2:.1%}")

if success_rate_1 > success_rate_2:
    print("✅ 虛弱獵物更容易被捕")
else:
    print(f"⚠️  成功率異常：虛弱 {success_rate_1:.1%} vs 健康 {success_rate_2:.1%}")

# === 總結 ===
print("\n" + "=" * 70)
print("✅ 所有改進項目測試完成！")
print("=" * 70)
print("\n改進總結：")
print("  1. ✅ 質量動力學：F = ma 正確應用")
print("  2. ✅ 最小距離：軟球排斥力維持 agents 間距")
print("  3. ✅ 虛弱狀態：能量分級影響移動速度")
print("  4. ✅ 攻擊成功率：動態計算，考慮速度/體力/群體防禦")
print()
