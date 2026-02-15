"""
Simulation Manager
管理 Taichi 模擬系統的生命週期
"""

import sys

sys.path.insert(0, "../src")

import taichi as ti
from flocking_3d import Flocking3D, FlockingParams
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from resources import create_resource, create_renewable_resource


class SimulationManager:
    """模擬系統管理器"""

    def __init__(self, initial_config: dict | None = None):
        # 初始化 Taichi（只執行一次）
        # Taichi 會自動選擇最佳可用架構
        ti.init(arch=ti.gpu)

        self.system = None
        self.params = None
        self.step_count = 0

        # 創建預設系統（確保總是有資料可以傳送）
        default_params = {
            "systemType": "Heterogeneous",
            "N": 100,
            "Ca": 1.5,
            "Cr": 2.0,
            "la": 2.5,
            "lr": 0.5,
            "rc": 15.0,
            "alpha": 2.0,
            "v0": 1.0,
            "beta": 1.0,
            "eta": 0.0,
            "boxSize": 50.0,
            "boundaryMode": "pbc",
            "agentConfig": {
                "explorerRatio": 0.3,
                "followerRatio": 0.5,
                "predatorRatio": 0.05,  # 5 捕食者（5%）
                "enableFov": True,
                "fovAngle": 120.0,
            },
            "resources": [
                # 資源 #1（3D corner cluster）
                {
                    "position": [16.0, 14.0, 15.0],
                    "amount": 280.0,
                    "radius": 5.5,
                    "renewable": True,
                    "replenishRate": 90.0,
                    "maxAmount": 420.0,
                },
                # 資源 #2
                {
                    "position": [-17.0, 15.0, -14.0],
                    "amount": 260.0,
                    "radius": 5.0,
                    "renewable": True,
                    "replenishRate": 85.0,
                    "maxAmount": 380.0,
                },
                # 資源 #3
                {
                    "position": [14.0, -16.0, -13.0],
                    "amount": 250.0,
                    "radius": 4.8,
                    "renewable": True,
                    "replenishRate": 80.0,
                    "maxAmount": 360.0,
                },
                # 資源 #4（一次性）
                {
                    "position": [-15.0, -14.0, 16.0],
                    "amount": 420.0,
                    "radius": 5.4,
                    "renewable": False,
                },
                # 資源 #5（中心偏上，避免完全四角化）
                {
                    "position": [0.0, 0.0, -4.0],
                    "amount": 220.0,
                    "radius": 4.6,
                    "renewable": True,
                    "replenishRate": 70.0,
                    "maxAmount": 320.0,
                },
            ],
        }
        # 若有外部設定檔，覆蓋 default_params
        if initial_config is not None:
            default_params = initial_config
        print("🚀 Creating default system on startup...")
        self.create_system(default_params)

    def create_system(self, params: dict):
        """
        創建模擬系統

        Args:
            params: 參數字典，包含 systemType, N, physics params 等
        """
        system_type = params.get("systemType", "Heterogeneous")
        N = params.get("N", 100)

        # 建立物理參數
        flocking_params = FlockingParams(
            Ca=params.get("Ca", 1.5),
            Cr=params.get("Cr", 2.0),
            la=params.get("la", 2.5),
            lr=params.get("lr", 0.5),
            rc=params.get("rc", 15.0),
            alpha=params.get("alpha", 2.0),
            v0=params.get("v0", 1.0),
            beta=params.get("beta", 1.0),
            eta=params.get("eta", 0.0),
            box_size=params.get("boxSize", 50.0),
            boundary_mode=params.get("boundaryMode", "pbc"),
        )

        # 建立系統
        if system_type == "Heterogeneous":
            agent_config = params.get("agentConfig", {})
            explorer_ratio = agent_config.get("explorerRatio", 0.3)
            follower_ratio = agent_config.get("followerRatio", 0.5)
            predator_ratio = agent_config.get("predatorRatio", 0.05)

            n_explorer = int(N * explorer_ratio)
            n_follower = int(N * follower_ratio)
            n_predator = int(N * predator_ratio)
            n_leader = N - n_explorer - n_follower - n_predator

            agent_types = (
                [AgentType.EXPLORER] * n_explorer
                + [AgentType.FOLLOWER] * n_follower
                + [AgentType.LEADER] * n_leader
                + [AgentType.PREDATOR] * n_predator
            )

            resources = params.get("resources", [])
            max_resources = max(5, len(resources))
            self.system = HeterogeneousFlocking3D(
                N=N,
                params=flocking_params,
                agent_types=agent_types,
                enable_fov=agent_config.get("enableFov", True),
                fov_angle=agent_config.get("fovAngle", 120.0),
                max_obstacles=10,
                max_resources=max_resources,
            )

            # 設定 goals
            if agent_config.get("enableGoals", False):
                goal_pos = agent_config.get("goalPosition", [10.0, 10.0, 10.0])
                leader_indices = [
                    i for i, t in enumerate(agent_types) if t == AgentType.LEADER
                ]
                if len(leader_indices) > 0:
                    import numpy as np

                    goals = np.tile(goal_pos, (len(leader_indices), 1))
                    self.system.set_goals(goals, leader_indices)

            # 新增資源
            resources = params.get("resources", [])
            for res_cfg in resources:
                pos = tuple(res_cfg["position"])
                if res_cfg.get("renewable", False):
                    res = create_renewable_resource(
                        position=pos,
                        amount=res_cfg.get("amount", 100.0),
                        radius=res_cfg.get("radius", 3.0),
                        replenish_rate=res_cfg.get("replenishRate", 2.0),
                        max_amount=res_cfg.get("maxAmount", 200.0),
                    )
                else:
                    res = create_resource(
                        position=pos,
                        amount=res_cfg.get("amount", 100.0),
                        radius=res_cfg.get("radius", 3.0),
                    )
                self.system.add_resource(res)

        elif system_type == "3D":
            self.system = Flocking3D(N=N, params=flocking_params)

        # 初始化
        # 注意：initialize 的 box_size 參數是「初始散佈半徑」，不是邊界盒尺寸。
        # 直接傳 flocking_params.box_size 會把粒子撒到邊界外（視覺上超出 box）。
        # 這裡改用系統預設（box_size * 0.3）以確保初始位置在邊界內且密度合理。
        self.system.initialize(seed=42)
        self.system.step_count = 0
        self.step_count = 0
        self.params = params

        print(f"✅ Created {system_type} system with N={N}")

    def update_params(self, params: dict):
        """更新參數（重建系統）"""
        print(f"📝 Updating parameters...")
        self.create_system(params)

    def step(self):
        """執行一幀模擬"""
        if self.system:
            self.system.step(0.1)  # dt = 0.1 (加倍，讓軌跡更明顯)
            self.step_count += 1
            self.system.step_count = self.step_count

            # 群組檢測已整合至 HeterogeneousFlocking3D.step() 中
            # 每 3 步自動執行一次，無需手動呼叫

    def reset(self):
        """重置模擬"""
        if self.params:
            print("🔄 Resetting simulation...")
            self.create_system(self.params)


# === 測試 ===
if __name__ == "__main__":
    print("=== SimulationManager Test ===\n")

    manager = SimulationManager()

    # 測試參數
    test_params = {
        "systemType": "Heterogeneous",
        "N": 100,
        "Ca": 1.5,
        "Cr": 2.0,
        "la": 2.5,
        "lr": 0.5,
        "rc": 15.0,
        "alpha": 2.0,
        "v0": 1.0,
        "beta": 1.0,
        "eta": 0.0,
        "boxSize": 50.0,
        "boundaryMode": "pbc",
        "agentConfig": {
            "explorerRatio": 0.3,
            "followerRatio": 0.5,
            "enableFov": True,
            "fovAngle": 120.0,
        },
    }

    # 建立系統
    print("1. Creating system...")
    manager.create_system(test_params)
    print(f"   System N: {manager.system.N}")

    # 執行幾步
    print("\n2. Running 10 steps...")
    for i in range(10):
        manager.step()
    print(f"   Step count: {manager.step_count}")

    # 計算統計
    print("\n3. Computing statistics...")
    stats = manager.system.compute_diagnostics()
    print(f"   Mean speed: {stats['mean_speed']:.3f}")
    print(f"   Polarization: {stats['polarization']:.3f}")
    print(f"   Rg: {stats['Rg']:.3f}")

    # 重置
    print("\n4. Resetting...")
    manager.reset()
    print(f"   Step count after reset: {manager.step_count}")

    print("\n✅ SimulationManager test completed!")
