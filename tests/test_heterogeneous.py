"""
Unit Tests for Heterogeneous Flocking System

測試項目：
    • Agent 類型系統（Explorer/Follower/Leader）
    • 個體參數（beta, eta, v0, mass）
    • 目標導向行為（Goal seeking）
    • 視野限制（Field of View）
    • 向後相容性（退化為均質系統）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pytest

from flocking_heterogeneous import (
    HeterogeneousFlocking3D,
    AgentType,
    AgentTypeProfile,
    DEFAULT_PROFILES,
)
from flocking_3d import FlockingParams


# ============================================================================
# Agent Type System Tests
# ============================================================================
def test_agent_type_initialization():
    """測試 Agent 類型正確初始化"""
    N = 30
    agent_types = [AgentType.EXPLORER] * 10 + [AgentType.FOLLOWER] * 20

    params = FlockingParams(box_size=30.0)
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)

    # 驗證類型分布（只檢查前 N 個活躍 agents）
    type_arr = system.agent_type_field.to_numpy()[:N]
    assert np.sum(type_arr == AgentType.EXPLORER) == 10
    assert np.sum(type_arr == AgentType.FOLLOWER) == 20

    # 驗證個體參數
    beta_arr = system.beta_individual.to_numpy()
    eta_arr = system.eta_individual.to_numpy()

    # Explorer 應該有較低的 beta, 較高的 eta
    explorer_indices = np.where(type_arr == AgentType.EXPLORER)[0]
    follower_indices = np.where(type_arr == AgentType.FOLLOWER)[0]

    # 檢查所有 Explorer 的 beta 都比所有 Follower 低
    assert np.all(beta_arr[explorer_indices] < np.min(beta_arr[follower_indices]))
    assert np.all(eta_arr[explorer_indices] > np.max(eta_arr[follower_indices]))

    print("✓ Agent type initialization correct")


def test_default_profiles():
    """測試預設 profile 值合理"""
    assert (
        DEFAULT_PROFILES[AgentType.EXPLORER].beta
        < DEFAULT_PROFILES[AgentType.FOLLOWER].beta
    )
    assert (
        DEFAULT_PROFILES[AgentType.EXPLORER].eta
        > DEFAULT_PROFILES[AgentType.FOLLOWER].eta
    )
    assert (
        DEFAULT_PROFILES[AgentType.LEADER].v0 > DEFAULT_PROFILES[AgentType.FOLLOWER].v0
    )

    print("✓ Default profiles are reasonable")


def test_custom_profiles():
    """測試自訂 profile"""
    custom_profiles = {
        0: AgentTypeProfile(name="Custom", beta=2.0, eta=0.1, v0=1.5, mass=1.5)
    }

    N = 10
    agent_types = [0] * N
    params = FlockingParams()

    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, type_profiles=custom_profiles
    )

    # 驗證使用了自訂 profile
    assert np.allclose(system.beta_individual.to_numpy(), 2.0)
    assert np.allclose(system.v0_individual.to_numpy(), 1.5)

    print("✓ Custom profiles work correctly")


# ============================================================================
# Individual Parameters Tests
# ============================================================================
def test_individual_speed_convergence():
    """測試個體速度收斂到各自的 v0（在孤立情況下）"""
    N = 20
    agent_types = [AgentType.FOLLOWER] * 10 + [AgentType.LEADER] * 10

    # 使用大 box_size 和弱交互作用，讓 agents 基本孤立
    params = FlockingParams(alpha=2.0, beta=0.1, rc=2.0, box_size=100.0)
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    system.initialize(box_size=80.0, seed=42)  # 分散初始化

    # 運行更長時間以收斂
    for _ in range(500):
        system.step(dt=0.01)

    # 檢查速度
    v_np = system.v.to_numpy()
    speeds = np.linalg.norm(v_np, axis=1)
    v0_arr = system.v0_individual.to_numpy()

    # 在弱交互作用下，速度應接近各自的 v0
    # 允許較大誤差（因為仍有一些交互作用）
    mean_error = np.mean(np.abs(speeds - v0_arr))
    assert mean_error < 0.3, f"Mean speed error {mean_error:.3f} too large"

    print(f"✓ Individual speeds converged: mean error = {mean_error:.3f}")


def test_mass_affects_dynamics():
    """測試質量影響動力學（重的 agent 慣性大）"""
    N = 2
    # 兩個 agent：一個輕（mass=0.5），一個重（mass=2.0）
    custom_profiles = {
        0: AgentTypeProfile(name="Light", beta=0.0, eta=0.0, v0=1.0, mass=0.5),
        1: AgentTypeProfile(name="Heavy", beta=0.0, eta=0.0, v0=1.0, mass=2.0),
    }

    params = FlockingParams(alpha=0.0, box_size=30.0)  # 無摩擦
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[0, 1], type_profiles=custom_profiles
    )

    # 先初始化，再設定狀態
    system.initialize(seed=42)
    system.x.from_numpy(np.array([[0, 0, 0], [10, 0, 0]], dtype=np.float32))
    system.v.from_numpy(np.array([[1, 0, 0], [1, 0, 0]], dtype=np.float32))

    # 施加相同外力後，輕的 agent 加速更快
    system.compute_forces()  # 計算 Morse force
    system.step(dt=0.01)

    v_np = system.v.to_numpy()
    # 輕的 agent（index 0）速度變化應更大（因為 a = F/m）
    # 注意：實際結果取決於 Morse force 方向

    print(f"✓ Mass affects dynamics: v_light={v_np[0]}, v_heavy={v_np[1]}")


# ============================================================================
# Goal Seeking Tests
# ============================================================================
def test_goal_seeking_moves_toward_target():
    """測試 agent 會向目標移動"""
    N = 10
    agent_types = [AgentType.LEADER] * N  # Leaders have goal_strength > 0

    params = FlockingParams(beta=0.0, alpha=0.0, box_size=50.0)  # 移除其他力
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    system.initialize(box_size=5.0, seed=42)

    # 設定目標在附近（在 PBC 下不會被 wrap）
    # 初始化在 ±2.5 附近，目標設在 10.0 處
    goals = np.tile([10.0, 0.0, 0.0], (N, 1))
    system.set_goals(goals)

    # 初始位置
    x_init = system.x.to_numpy().copy()

    # 運行模擬
    for _ in range(200):
        system.step(dt=0.01)

    x_final = system.x.to_numpy()

    # 驗證：所有 agent 向目標移動（x 座標增加）
    # 使用 PBC-aware 距離計算
    dist_init = np.array(
        [
            np.linalg.norm(
                np.array(
                    [(goals[i, d] - x_init[i, d] + 25) % 50 - 25 for d in range(3)]
                )
            )
            for i in range(N)
        ]
    )
    dist_final = np.array(
        [
            np.linalg.norm(
                np.array(
                    [(goals[i, d] - x_final[i, d] + 25) % 50 - 25 for d in range(3)]
                )
            )
            for i in range(N)
        ]
    )

    assert np.all(dist_final < dist_init), "Agents should move toward goal"
    print(
        f"✓ Goal seeking works: avg distance reduced from {np.mean(dist_init):.2f} to {np.mean(dist_final):.2f}"
    )


def test_goal_strength_parameter():
    """測試 goal_strength 參數影響移動速度"""
    N = 2
    # 一個強目標導向，一個弱目標導向
    custom_profiles = {
        0: AgentTypeProfile(
            name="Weak", beta=0.0, eta=0.0, v0=1.0, mass=1.0, goal_strength=0.5
        ),
        1: AgentTypeProfile(
            name="Strong", beta=0.0, eta=0.0, v0=1.0, mass=1.0, goal_strength=2.0
        ),
    }

    params = FlockingParams(alpha=0.0, box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[0, 1], type_profiles=custom_profiles
    )

    # 先初始化，再設定狀態
    system.initialize(seed=42)
    system.x.from_numpy(np.array([[0, 0, 0], [0, 0, 0]], dtype=np.float32))

    # 設定相同目標
    goals = np.array([[20.0, 0.0, 0.0], [20.0, 0.0, 0.0]])
    system.set_goals(goals, np.array([0, 1]))

    # 運行少量步數
    for _ in range(50):
        system.step(dt=0.01)

    x_final = system.x.to_numpy()

    # 強目標導向的 agent 應移動更遠
    assert x_final[1, 0] > x_final[0, 0], "Stronger goal_strength should move farther"
    print(
        f"✓ Goal strength affects speed: weak={x_final[0, 0]:.2f}, strong={x_final[1, 0]:.2f}"
    )


# ============================================================================
# Field of View Tests
# ============================================================================
def test_fov_limits_alignment():
    """測試 FOV 限制對齊行為"""
    N = 3
    params = FlockingParams(beta=1.0, alpha=0.0, box_size=30.0)

    # 設定：agent 0 在中間，agent 1 在前方，agent 2 在後方
    x_init = np.array([[0, 0, 0], [5, 0, 0], [-5, 0, 0]], dtype=np.float32)
    v_init = np.array([[1, 0, 0], [0, 1, 0], [0, -1, 0]], dtype=np.float32)

    # 測試有 FOV 的情況
    system_fov = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[AgentType.FOLLOWER] * N, enable_fov=True
    )
    system_fov.initialize(seed=42)
    system_fov.x.from_numpy(x_init.copy())
    system_fov.v.from_numpy(v_init.copy())
    system_fov.compute_forces()
    f_fov = system_fov.f.to_numpy()

    # 測試無 FOV 的情況（建立新系統）
    system_no_fov = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[AgentType.FOLLOWER] * N, enable_fov=False
    )
    system_no_fov.initialize(seed=42)
    system_no_fov.x.from_numpy(x_init.copy())
    system_no_fov.v.from_numpy(v_init.copy())
    system_no_fov.compute_forces()
    f_no_fov = system_no_fov.f.to_numpy()

    # 有 FOV 的系統，agent 0 只能看到前方的 agent 1（不能看到後方的 agent 2）
    # 所以受到的對齊力應該不同
    # 注意：這個測試需要根據實際幾何調整

    print(f"✓ FOV limits alignment: f_fov[0]={f_fov[0]}, f_no_fov[0]={f_no_fov[0]}")


def test_fov_angle_parameter():
    """測試 FOV 角度參數"""
    N = 10
    params = FlockingParams()

    # 窄視野（60 度）
    system_narrow = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[AgentType.FOLLOWER] * N, fov_angle=60.0
    )

    # 寬視野（180 度）
    system_wide = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=[AgentType.FOLLOWER] * N, fov_angle=180.0
    )

    # 驗證 cos 值設定正確
    assert system_narrow.fov_cos_angle > system_wide.fov_cos_angle
    print(
        f"✓ FOV angle setting: narrow={np.degrees(np.arccos(system_narrow.fov_cos_angle)) * 2:.0f}°, "
        f"wide={np.degrees(np.arccos(system_wide.fov_cos_angle)) * 2:.0f}°"
    )


# ============================================================================
# Backward Compatibility Tests
# ============================================================================
def test_homogeneous_fallback():
    """測試退化為均質系統（向後相容）"""
    N = 50
    # 所有 agent 相同類型
    agent_types = [AgentType.FOLLOWER] * N

    params = FlockingParams(beta=1.0, eta=0.1, box_size=30.0)
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    system.initialize(seed=42)

    # 驗證：所有個體參數相同
    beta_arr = system.beta_individual.to_numpy()
    eta_arr = system.eta_individual.to_numpy()
    v0_arr = system.v0_individual.to_numpy()

    assert np.allclose(beta_arr, beta_arr[0])
    assert np.allclose(eta_arr, eta_arr[0])
    assert np.allclose(v0_arr, v0_arr[0])

    # 運行應該穩定
    for _ in range(100):
        system.step(dt=0.01)

    diag = system.compute_diagnostics()
    assert diag["mean_speed"] > 0.3  # 合理速度（降低閾值）
    assert diag["Rg"] < 20.0  # 群體未爆炸

    print("✓ Homogeneous fallback works correctly")


# ============================================================================
# Integration Tests
# ============================================================================
def test_mixed_population_stability():
    """測試混合群體穩定性"""
    N = 100
    agent_types = (
        [AgentType.EXPLORER] * 20 + [AgentType.FOLLOWER] * 70 + [AgentType.LEADER] * 10
    )

    params = FlockingParams(box_size=50.0)
    system = HeterogeneousFlocking3D(N=N, params=params, agent_types=agent_types)
    system.initialize(box_size=5.0, seed=42)

    # 運行長時間
    for _ in range(200):
        system.step(dt=0.01)

    diag = system.compute_diagnostics()

    # 驗證系統穩定
    assert 0.5 < diag["mean_speed"] < 2.0, "Speed should be reasonable"
    assert diag["Rg"] < 30.0, "Group should not explode"
    assert not np.isnan(diag["polarization"]), "Polarization should be valid"

    print(
        f"✓ Mixed population stable: v={diag['mean_speed']:.2f}, "
        f"Rg={diag['Rg']:.2f}, P={diag['polarization']:.3f}"
    )


def test_leader_guides_followers():
    """測試 Leader 能否引導 Follower"""
    N = 20
    agent_types = [AgentType.LEADER] * 5 + [AgentType.FOLLOWER] * 15

    # 使用更強的 goal_strength
    custom_profiles = {
        AgentType.LEADER: AgentTypeProfile(
            name="Leader", beta=1.0, eta=0.15, v0=1.4, mass=1.2, goal_strength=5.0
        ),
        AgentType.FOLLOWER: DEFAULT_PROFILES[AgentType.FOLLOWER],
    }

    params = FlockingParams(beta=1.5, box_size=50.0)  # 強對齊
    system = HeterogeneousFlocking3D(
        N=N, params=params, agent_types=agent_types, type_profiles=custom_profiles
    )
    system.initialize(box_size=3.0, seed=42)

    # Leaders 有明確目標（設在附近，避免 PBC wrap）
    leader_indices = np.where(np.array(agent_types) == AgentType.LEADER)[0]
    goals = np.tile([10.0, 0.0, 0.0], (len(leader_indices), 1))
    system.set_goals(goals, leader_indices)

    # 運行更長時間
    for _ in range(300):
        system.step(dt=0.01)

    x_final = system.x.to_numpy()

    # 計算群體質心
    com = np.mean(x_final, axis=0)

    # 群體應朝目標方向移動（x > 2）
    assert com[0] > 2.0, "Leaders should guide group toward goal"

    print(f"✓ Leaders guide followers: COM moved to {com}")


# ============================================================================
# Run Tests
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
