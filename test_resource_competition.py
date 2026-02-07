"""
測試資源競爭機制（FIFO 策略）

驗證：
    1. 先到先得分配邏輯
    2. 資源耗盡後後續 agents 無法獲得
    3. FIFO vs 平均分配的差異
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from flocking_3d import FlockingParams
from resources import ResourceSystem, ResourceConfig
from behaviors.foraging import ForagingBehaviorMixin
import taichi as ti

print("=" * 70)
print("測試資源競爭機制（FIFO = 先到先得）")
print("=" * 70)

# 初始化 Taichi
ti.init(arch=ti.metal)


# 創建最小測試系統（僅 ForagingBehaviorMixin）
@ti.data_oriented
class MinimalForagingSystem(ForagingBehaviorMixin):
    def __init__(self, N, box_size=50.0):
        self.N = N
        self.params = FlockingParams(box_size=box_size)

        # 必要 fields
        self.x = ti.Vector.field(3, ti.f32, N)
        self.v = ti.Vector.field(3, ti.f32, N)
        self.f = ti.Vector.field(3, ti.f32, N)
        self.agent_alive = ti.field(ti.i32, N)
        self.v0_base = ti.field(ti.f32, N)
        self.v0_individual = ti.field(ti.f32, N)
        self.agent_health_status = ti.field(ti.i32, N)

        # 初始化
        self.agent_alive.fill(1)
        self.v0_base.fill(1.0)
        self.v0_individual.fill(1.0)

        # 初始化覓食行為
        resources = ResourceSystem(max_resources=32)
        self.init_foraging(
            N=N,
            resources=resources,
            energy_threshold=30.0,
            energy_consumption_rate=0.1,
            initial_energy=50.0,
        )

    def pbc_dist(self, p1, p2):
        """Placeholder PBC distance"""
        return p2 - p1


# === 測試 1: FIFO vs Equal 分配差異 ===
print("\n[測試 1] FIFO vs 平均分配差異")
print("-" * 70)

N = 5
system = MinimalForagingSystem(N)

# 設定 5 個 agents 在不同距離
system.x.from_numpy(
    np.array(
        [
            [0.0, 0, 0],  # Agent 0：最近（距離 0.0）
            [0.5, 0, 0],  # Agent 1：次近（距離 0.5）
            [1.0, 0, 0],  # Agent 2：中等（距離 1.0）
            [1.5, 0, 0],  # Agent 3：較遠（距離 1.5）
            [1.9, 0, 0],  # Agent 4：邊緣（距離 1.9，恰好在範圍內）
        ],
        dtype=np.float32,
    )
)

# 設定速度為 0（避免能量消耗影響）
system.v.fill(0)

# 添加資源（位置 [0,0,0]，範圍 2.0，總量 10.0）
res_config = ResourceConfig(
    position=np.array([0, 0, 0], dtype=np.float32),
    amount=10.0,  # 總量 10，consumption_rate=3，只能滿足 3.33 個 agents
    radius=2.0,
    replenish_rate=0.0,
)
system.add_resource(res_config)

# 設定所有 agents 鎖定資源 0
system.agent_target_resource.fill(0)

# 記錄初始能量
energy_before = system.agent_energy.to_numpy().copy()
print(f"\n初始能量：{energy_before}")
print(f"資源總量：10.0")
print(f"每 agent 需求：3.0 (consumption_rate)")
print(f"理論可滿足：10.0 / 3.0 = 3.33 個 agents")

# === 測試 FIFO 模式 ===
print("\n--- 測試 FIFO 模式 ---")
system.agent_energy.from_numpy(energy_before)  # 重置能量
system.resources.resource_amount[0] = 10.0  # 重置資源
system.resources.resource_active[0] = 1  # 確保資源啟用

system.consume_resources_step(
    consumption_rate=3.0, velocity_factor=0.0, competition_mode="fifo"
)

energy_fifo = system.agent_energy.to_numpy()
gains_fifo = energy_fifo - energy_before

print(f"能量增益（FIFO）：{gains_fifo}")
print(f"獲得資源的 agents：{np.where(gains_fifo > 0)[0].tolist()}")
print(f"資源剩餘：{system.resources.resource_amount[0]:.2f}")

# === 測試 Equal 模式 ===
print("\n--- 測試 Equal 模式 ---")
system.agent_energy.from_numpy(energy_before)  # 重置能量
system.resources.resource_amount[0] = 10.0  # 重置資源
system.resources.resource_active[0] = 1  # 重新啟用資源（重要！）
system.agent_target_resource.fill(0)  # 重新設定目標（重要！）

system.consume_resources_step(
    consumption_rate=3.0, velocity_factor=0.0, competition_mode="equal"
)

energy_equal = system.agent_energy.to_numpy()
gains_equal = energy_equal - energy_before

print(f"能量增益（Equal）：{gains_equal}")
print(f"獲得資源的 agents：{np.where(gains_equal > 0)[0].tolist()}")
print(f"資源剩餘：{system.resources.resource_amount[0]:.2f}")

# === 驗證 ===
print("\n--- 驗證 ---")
print(f"✅ FIFO：前 3-4 個 agents 應獲得較多資源")
print(f"   實際：{gains_fifo[:4]}")
print(f"✅ Equal：所有 agents 應平分資源")
print(f"   實際：{gains_equal}")

# 檢查 FIFO 是否優先滿足近距離 agents
assert gains_fifo[0] > gains_fifo[4], "FIFO：最近的 agent 應獲得最多"
assert gains_fifo[1] > gains_fifo[4], "FIFO：次近的 agent 應優於邊緣 agent"

# 檢查 Equal 是否平分
equal_gains_variance = np.var(gains_equal)
assert equal_gains_variance < 0.01, (
    f"Equal：能量增益應接近（方差 {equal_gains_variance:.4f}）"
)

print("\n✅ 所有驗證通過！")

# === 測試 2：資源耗盡情境 ===
print("\n[測試 2] 資源耗盡 - FIFO 先到先得")
print("-" * 70)

system2 = MinimalForagingSystem(3)

# 設定 3 個 agents
system2.x.from_numpy(
    np.array(
        [
            [0.1, 0, 0],  # Agent 0：最近
            [0.5, 0, 0],  # Agent 1：中等
            [1.0, 0, 0],  # Agent 2：較遠
        ],
        dtype=np.float32,
    )
)

system2.v.fill(0)

# 添加資源（總量 5.0，只能滿足 1.66 個 agents）
res_config2 = ResourceConfig(
    position=np.array([0, 0, 0], dtype=np.float32),
    amount=5.0,
    radius=2.0,
    replenish_rate=0.0,
)
system2.add_resource(res_config2)
system2.agent_target_resource.fill(0)

energy_before2 = system2.agent_energy.to_numpy().copy()
print(f"初始能量：{energy_before2}")
print(f"資源總量：5.0")
print(f"每 agent 需求：3.0")

system2.consume_resources_step(
    consumption_rate=3.0, velocity_factor=0.0, competition_mode="fifo"
)

energy_after2 = system2.agent_energy.to_numpy()
gains2 = energy_after2 - energy_before2

print(f"\n能量增益（FIFO）：{gains2}")
print(f"資源剩餘：{system2.resources.resource_amount[0]:.2f}")

# 驗證
print("\n--- 驗證 ---")
print(f"✅ Agent 0（最近）應獲得全部 3.0 資源")
print(f"   實際增益：{gains2[0]:.2f}")
print(f"✅ Agent 1（中等）應獲得部分資源（約 2.0）")
print(f"   實際增益：{gains2[1]:.2f}")
print(f"✅ Agent 2（較遠）應無法獲得資源")
print(f"   實際增益：{gains2[2]:.2f}")

assert gains2[0] > 1.0, "Agent 0 應獲得資源"
assert gains2[1] > 0.5, "Agent 1 應獲得部分資源"
assert gains2[2] < 0.1, "Agent 2 應幾乎無法獲得資源"

print("\n✅ 資源競爭測試通過！")

# === 總結 ===
print("\n" + "=" * 70)
print("✅ 資源競爭機制測試完成！")
print("=" * 70)
print("\n機制總結：")
print("  1. ✅ FIFO 模式：按距離排序，近者優先獲得資源")
print("  2. ✅ Equal 模式：所有在範圍內的 agents 平分資源")
print("  3. ✅ 資源耗盡：後續 agents 無法獲得資源（FIFO）")
print()
