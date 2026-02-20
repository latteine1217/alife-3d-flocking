"""
測試 Reproduction System
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import taichi as ti

from flocking_heterogeneous import AgentType, HeterogeneousFlocking3D
from flocking_3d import FlockingParams


def test_reproduction_spawns_offspring_and_marks_alive():
    ti.init(arch=ti.cpu, random_seed=123)

    params = FlockingParams(box_size=50.0, boundary_mode="pbc")
    system = HeterogeneousFlocking3D(
        N=2,
        max_agents=5,
        params=params,
        agent_types=[AgentType.FOLLOWER, AgentType.FOLLOWER],
        enable_fov=False,
        enable_reproduction=True,
    )
    system.initialize(box_size=5.0, seed=1)

    # 只讓 agent 0 達到繁殖門檻
    system.reproduction_threshold = 190.0
    system.reproduction_timer[0] = 0
    system.reproduction_timer[1] = 9999

    system.agent_energy[0] = 200.0
    system.agent_energy[1] = 10.0

    alive_before = int(system.agent_alive.to_numpy().sum())
    assert alive_before == 2

    system.attempt_reproduction()

    alive_np = system.agent_alive.to_numpy()
    alive_after = int(alive_np.sum())
    assert alive_after == 3

    # 預期第一個空位就是 index=2
    assert alive_np[2] == 1

    # 子代類型與參數應繼承
    assert int(system.agent_type_field[2]) == int(system.agent_type_field[0])
    assert float(system.v0_base[2]) == float(system.v0_base[0])
    assert float(system.mass_individual[2]) == float(system.mass_individual[0])
    assert float(system.beta_individual[2]) == float(system.beta_individual[0])
    assert float(system.eta_individual[2]) == float(system.eta_individual[0])

    # 子代能量使用 energy_max × ratio
    assert np.isclose(
        float(system.agent_energy[2]), float(system.energy_max) * system.offspring_energy_ratio
    )

    # 父代能量應扣除 cost（0.5）
    assert np.isclose(float(system.agent_energy[0]), 100.0)

    # 初始化狀態應清空目標
    assert int(system.agent_target_resource[2]) == -1
    assert int(system.agent_target_prey[2]) == -1
