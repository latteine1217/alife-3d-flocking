"""
Dashboard 邏輯測試腳本

測試 streamlit_app.py 的核心功能（不啟動實際的 Streamlit server）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import taichi as ti
from flocking_2d import Flocking2D
from flocking_3d import Flocking3D, FlockingParams
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from resources import create_resource, create_renewable_resource

# 初始化 Taichi
ti.init(arch=ti.cpu)

print("=" * 70)
print("Dashboard Logic Tests")
print("=" * 70)

# ============================================================================
# Test 1: 2D System Creation
# ============================================================================
print("\n[Test 1] 2D System Creation")
try:
    params = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    system_2d = Flocking2D(N=50, params=params)
    system_2d.initialize(box_size=50.0, seed=42)

    # 執行一步
    system_2d.step(0.05)

    # 計算統計
    diag = system_2d.compute_diagnostics()

    print(f"  ✅ 2D System created: N={system_2d.N}")
    print(f"     - Rg: {diag['Rg']:.2f}")
    print(f"     - Polarization: {diag['polarization']:.3f}")
    print(f"     - Avg Speed: {diag['mean_speed']:.2f}")
except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 2: 3D System Creation
# ============================================================================
print("\n[Test 2] 3D System Creation")
try:
    params = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    system_3d = Flocking3D(N=50, params=params)
    system_3d.initialize(box_size=50.0, seed=42)

    system_3d.step(0.05)
    diag = system_3d.compute_diagnostics()

    print(f"  ✅ 3D System created: N={system_3d.N}")
    print(f"     - Rg: {diag['Rg']:.2f}")
    print(f"     - Polarization: {diag['polarization']:.3f}")
except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 3: Heterogeneous System (Basic)
# ============================================================================
print("\n[Test 3] Heterogeneous System (Basic)")
try:
    params = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    N = 50
    agent_types = (
        [AgentType.EXPLORER] * 15 + [AgentType.FOLLOWER] * 25 + [AgentType.LEADER] * 10
    )

    system_het = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        enable_fov=True,
        fov_angle=120.0,
        max_obstacles=10,
        max_resources=5,
    )
    system_het.initialize(box_size=50.0, seed=42)

    system_het.step(0.05)
    diag = system_het.compute_diagnostics()

    energies = system_het.get_agent_energies()

    print(f"  ✅ Heterogeneous System created: N={N}")
    print(f"     - Agent composition: 15 Explorer / 25 Follower / 10 Leader")
    print(f"     - Avg Energy: {np.mean(energies):.1f}")
    print(f"     - Min Energy: {np.min(energies):.1f}")
except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 4: Heterogeneous System with Resources
# ============================================================================
print("\n[Test 4] Heterogeneous System with Resources")
try:
    params = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    N = 50
    agent_types = [AgentType.EXPLORER] * N

    system_res = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        enable_fov=True,
        fov_angle=120.0,
        max_obstacles=10,
        max_resources=5,
    )
    system_res.initialize(box_size=50.0, seed=42)

    # 新增資源
    res1 = create_resource(position=(0.0, 0.0, 0.0), amount=100.0, radius=3.0)
    res2 = create_renewable_resource(
        position=(10.0, 10.0, 10.0),
        amount=100.0,
        radius=3.0,
        replenish_rate=2.0,
        max_amount=200.0,
    )
    system_res.add_resource(res1)
    system_res.add_resource(res2)

    # 取得資源列表
    resources = system_res.get_all_resources()

    print(f"  ✅ System with resources created")
    print(f"     - Number of resources: {len(resources)}")
    print(
        f"     - Resource 1: pos={resources[0]['position']}, amount={resources[0]['amount']:.0f}"
    )
    print(
        f"     - Resource 2: pos={resources[1]['position']}, amount={resources[1]['amount']:.0f}, replenish_rate={resources[1]['replenish_rate']:.1f}"
    )

    # 執行模擬
    for _ in range(10):
        system_res.step(0.05)

    # 檢查覓食行為
    targets = system_res.get_agent_targets()
    n_foraging = np.sum(targets >= 0)

    print(f"     - After 10 steps: {n_foraging}/{N} agents foraging")

except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 5: Goal-Seeking Behavior
# ============================================================================
print("\n[Test 5] Goal-Seeking Behavior")
try:
    params = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    N = 30
    agent_types = [AgentType.FOLLOWER] * 20 + [AgentType.LEADER] * 10

    system_goal = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        enable_fov=True,
        fov_angle=120.0,
        max_obstacles=10,
        max_resources=5,
    )
    system_goal.initialize(box_size=50.0, seed=42)

    # 設定 Leaders 的目標
    leader_indices = [i for i, t in enumerate(agent_types) if t == AgentType.LEADER]
    goal_pos = [10.0, 10.0, 10.0]
    goals = np.tile(goal_pos, (len(leader_indices), 1))
    system_goal.set_goals(goals, leader_indices)

    print(f"  ✅ Goal-seeking enabled")
    print(f"     - Number of leaders: {len(leader_indices)}")
    print(f"     - Goal position: {goal_pos}")

    # 執行模擬
    for _ in range(20):
        system_goal.step(0.05)

    # 檢查 Leaders 是否接近目標
    x_np = system_goal.x.to_numpy()
    leader_positions = x_np[leader_indices]
    distances = np.linalg.norm(leader_positions - np.array(goal_pos), axis=1)
    avg_distance = np.mean(distances)

    print(f"     - After 20 steps: avg distance to goal = {avg_distance:.2f}")

except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 6: Data Export for Visualization
# ============================================================================
print("\n[Test 6] Data Export for Visualization")
try:
    # 使用 Test 5 的系統（最近的）
    x_np = system_goal.x.to_numpy()
    v_np = system_goal.v.to_numpy()

    expected_N = len(agent_types)
    assert x_np.shape == (expected_N, 3), (
        f"Expected shape ({expected_N}, 3), got {x_np.shape}"
    )
    assert v_np.shape == (expected_N, 3), (
        f"Expected shape ({expected_N}, 3), got {v_np.shape}"
    )

    # 速度採樣（模擬 Dashboard 行為）
    sample_rate = max(1, len(x_np) // 50)
    x_sample = x_np[::sample_rate]
    v_sample = v_np[::sample_rate]

    print(f"  ✅ Data export successful")
    print(f"     - Position array shape: {x_np.shape}")
    print(f"     - Velocity array shape: {v_np.shape}")
    print(f"     - Sampled {len(x_sample)}/{expected_N} agents for velocity vectors")

except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Test 7: Group Detection
# ============================================================================
print("\n[Test 7] Group Detection")
try:
    # 創建新系統用於 group detection
    params_group = FlockingParams(box_size=50.0, Ca=1.5, Cr=2.0, beta=1.0)
    N_group = 50
    agent_types_group = [AgentType.FOLLOWER] * N_group

    system_group = HeterogeneousFlocking3D(
        N=N_group,
        params=params_group,
        agent_types=agent_types_group,
        enable_fov=True,
        fov_angle=120.0,
        max_obstacles=10,
        max_resources=5,
    )
    system_group.initialize(box_size=50.0, seed=42)

    # 執行幾步讓 agents 形成群組
    for _ in range(30):
        system_group.step(0.05)

    groups = system_group.get_all_groups()

    print(f"  ✅ Group detection successful")
    print(f"     - Number of groups: {len(groups)}")
    if len(groups) > 0:
        print(f"     - Largest group size: {max(len(g) for g in groups)}")

except Exception as e:
    print(f"  ❌ Failed: {e}")
    sys.exit(1)

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("✅ All Dashboard Logic Tests Passed!")
print("=" * 70)
print("\nNext Steps:")
print("1. Run the actual Dashboard: ./run_dashboard.sh")
print("2. Test UI interactions manually")
print("3. Verify performance metrics (FPS)")
print("4. Check resource/obstacle visualization")
print("=" * 70)
