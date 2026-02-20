"""
資源競爭機制測試（腳本）

驗證：
1. FIFO 先到先得分配邏輯
2. 資源耗盡後後續 agents 無法獲得
3. FIFO vs 平均分配的差異

Note:
    這個檔案是快速診斷腳本，不是 pytest 的單元測試。
    為了避免 pytest 收集時執行耗時流程，所有邏輯都放在 main()。
"""


def main() -> None:
    import sys
    from pathlib import Path

    import numpy as np
    import taichi as ti

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from flocking_3d import FlockingParams
    from resources import ResourceSystem, ResourceConfig
    from behaviors.foraging import ForagingBehaviorMixin

    print("=" * 70)
    print("測試資源競爭機制（FIFO = 先到先得）")
    print("=" * 70)

    ti.init(arch=ti.metal)

    @ti.data_oriented
    class MinimalForagingSystem(ForagingBehaviorMixin):
        def __init__(self, N: int, box_size: float = 50.0):
            self.N = N
            self.params = FlockingParams(box_size=box_size)

            self.x = ti.Vector.field(3, ti.f32, N)
            self.v = ti.Vector.field(3, ti.f32, N)
            self.f = ti.Vector.field(3, ti.f32, N)
            self.agent_alive = ti.field(ti.i32, N)
            self.v0_base = ti.field(ti.f32, N)
            self.v0_individual = ti.field(ti.f32, N)

            self.agent_alive.fill(1)
            self.v0_base.fill(1.0)
            self.v0_individual.fill(1.0)

            resources = ResourceSystem(max_resources=32)
            self.init_foraging(
                N=N,
                resources=resources,
                energy_threshold=30.0,
                energy_consumption_rate=0.1,
                initial_energy=50.0,
            )

        def pbc_dist(self, p1, p2):
            return p2 - p1

    # === 測試 1: FIFO vs Equal 分配差異 ===
    print("\n[測試 1] FIFO vs 平均分配差異")
    print("-" * 70)

    N = 5
    system = MinimalForagingSystem(N)

    system.x.from_numpy(
        np.array(
            [
                [0.0, 0, 0],
                [0.5, 0, 0],
                [1.0, 0, 0],
                [1.5, 0, 0],
                [1.9, 0, 0],
            ],
            dtype=np.float32,
        )
    )
    system.v.fill(0)

    res_config = ResourceConfig(
        position=np.array([0, 0, 0], dtype=np.float32),
        amount=10.0,
        radius=2.0,
        replenish_rate=0.0,
    )
    system.add_resource(res_config)
    system.agent_target_resource.fill(0)

    energy_before = system.agent_energy.to_numpy().copy()
    print(f"\n初始能量：{energy_before}")
    print("資源總量：10.0")
    print("每 agent 需求：3.0 (consumption_rate)")
    print("理論可滿足：10.0 / 3.0 = 3.33 個 agents")

    print("\n--- 測試 FIFO 模式 ---")
    system.agent_energy.from_numpy(energy_before)
    system.resources.resource_amount[0] = 10.0
    system.resources.resource_active[0] = 1
    system.consume_resources_step(
        consumption_rate=3.0, velocity_factor=0.0, competition_mode="fifo"
    )
    energy_fifo = system.agent_energy.to_numpy()
    gains_fifo = energy_fifo - energy_before
    print(f"能量增益（FIFO）：{gains_fifo}")
    print(f"獲得資源的 agents：{np.where(gains_fifo > 0)[0].tolist()}")
    print(f"資源剩餘：{float(system.resources.resource_amount[0]):.2f}")

    print("\n--- 測試 Equal 模式 ---")
    system.agent_energy.from_numpy(energy_before)
    system.resources.resource_amount[0] = 10.0
    system.resources.resource_active[0] = 1
    system.agent_target_resource.fill(0)
    system.consume_resources_step(
        consumption_rate=3.0, velocity_factor=0.0, competition_mode="equal"
    )
    energy_equal = system.agent_energy.to_numpy()
    gains_equal = energy_equal - energy_before
    print(f"能量增益（Equal）：{gains_equal}")
    print(f"獲得資源的 agents：{np.where(gains_equal > 0)[0].tolist()}")
    print(f"資源剩餘：{float(system.resources.resource_amount[0]):.2f}")

    print("\n--- 驗證 ---")
    assert gains_fifo[0] > gains_fifo[4], "FIFO：最近的 agent 應獲得最多"
    assert gains_fifo[1] > gains_fifo[4], "FIFO：次近的 agent 應優於邊緣 agent"
    equal_gains_variance = float(np.var(gains_equal))
    assert equal_gains_variance < 0.01, f"Equal：能量增益應接近（方差 {equal_gains_variance:.4f}）"
    print("✅ 所有驗證通過！")

    # === 測試 2：資源耗盡情境 ===
    print("\n[測試 2] 資源耗盡 - FIFO 先到先得")
    print("-" * 70)

    system2 = MinimalForagingSystem(3)
    system2.x.from_numpy(
        np.array(
            [
                [0.1, 0, 0],
                [0.5, 0, 0],
                [1.0, 0, 0],
            ],
            dtype=np.float32,
        )
    )
    system2.v.fill(0)

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
    print("資源總量：5.0")
    print("每 agent 需求：3.0")

    system2.consume_resources_step(
        consumption_rate=3.0, velocity_factor=0.0, competition_mode="fifo"
    )
    energy_after2 = system2.agent_energy.to_numpy()
    gains2 = energy_after2 - energy_before2
    print(f"\n能量增益（FIFO）：{gains2}")
    print(f"資源剩餘：{float(system2.resources.resource_amount[0]):.2f}")

    assert gains2[0] > 1.0, "Agent 0 應獲得資源"
    assert gains2[1] > 0.5, "Agent 1 應獲得部分資源"
    assert gains2[2] < 0.1, "Agent 2 應幾乎無法獲得資源"
    print("✅ 資源競爭測試通過！")


if __name__ == "__main__":
    main()

