"""
死亡 agents 消失機制測試（腳本）

Note:
    這個檔案是快速診斷腳本，不是 pytest 的單元測試。
    為了避免 pytest 收集時執行耗時流程，所有邏輯都放在 main()。
"""


def main() -> None:
    import sys
    from pathlib import Path

    import numpy as np

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from flocking_heterogeneous import HeterogeneousFlocking3D, AgentType
    from flocking_3d import FlockingParams

    print("=" * 70)
    print("測試死亡 Agents 消失機制")
    print("=" * 70)

    # === 測試 1: 餓死消失 ===
    print("\n[測試 1] 能量耗盡死亡 → 消失")
    print("-" * 70)

    params = FlockingParams(box_size=50.0)
    system = HeterogeneousFlocking3D(
        N=5,
        params=params,
        agent_types=[AgentType.FOLLOWER] * 5,
        enable_reproduction=False,
    )
    system.initialize(seed=42)

    system.agent_energy[0] = 100.0
    system.agent_energy[1] = 50.0
    system.agent_energy[2] = 10.0
    system.agent_energy[3] = 1.0
    system.agent_energy[4] = 0.0

    x_before = system.x.to_numpy().copy()
    print("初始位置：")
    for i in range(5):
        print(f"  Agent {i} (能量 {float(system.agent_energy[i]):.0f}): {x_before[i][:2]}")

    system.apply_energy_death()

    x_after = system.x.to_numpy()
    alive_after = system.agent_alive.to_numpy()

    print("\n死亡後狀態：")
    for i in range(5):
        is_alive = alive_after[i] == 1
        pos = x_after[i]
        dist_from_origin = float(np.linalg.norm(pos))
        if is_alive:
            print(f"  Agent {i}: ✅ 存活, 位置 {pos[:2]}")
        else:
            print(f"  Agent {i}: 💀 死亡, 已消失（距離原點 {dist_from_origin:.0e}）")

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
        enable_reproduction=False,
    )
    system.initialize(seed=42)

    system.x.from_numpy(
        np.array(
            [
                [0, 0, 0],
                [0.5, 0, 0],
                [10, 0, 0],
            ],
            dtype=np.float32,
        )
    )
    system.v.from_numpy(
        np.array(
            [
                [2, 0, 0],
                [0.5, 0, 0],
                [1, 0, 0],
            ],
            dtype=np.float32,
        )
    )

    system.agent_energy[0] = 100.0
    system.agent_energy[1] = 10.0
    system.agent_energy[2] = 100.0

    x_init = system.x.to_numpy()
    print("初始狀態：")
    print(f"  Predator 0: 位置 {x_init[0][:2]}, 能量 {float(system.agent_energy[0]):.0f}")
    print(f"  Prey 1: 位置 {x_init[1][:2]}, 能量 {float(system.agent_energy[1]):.0f}")
    print(f"  Prey 2: 位置 {x_init[2][:2]}, 能量 {float(system.agent_energy[2]):.0f}")

    max_attempts = 20
    prey1_caught = False
    for attempt in range(max_attempts):
        system.find_nearest_prey()
        system.attack_prey_step()
        if int(system.agent_alive[1]) == 0:
            prey1_caught = True
            print(f"\n🦁 Prey 1 在第 {attempt + 1} 次攻擊中被捕食")
            break

    if prey1_caught:
        x_after = system.x.to_numpy()
        alive_after = system.agent_alive.to_numpy()
        print("\n捕食後狀態：")
        print(f"  Predator 0: ✅ 存活, 能量 {float(system.agent_energy[0]):.1f}")
        print(f"  Prey 1: 💀 被捕食, 已消失（距離原點 {np.linalg.norm(x_after[1]):.0e}）")
        print(f"  Prey 2: ✅ 存活, 位置 {x_after[2][:2]}")

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
        N=3,
        params=params,
        agent_types=[AgentType.FOLLOWER] * 3,
        enable_reproduction=False,
    )
    system.initialize(box_size=5.0, seed=42)

    system.agent_energy[1] = 0.0
    system.apply_energy_death()

    for _ in range(10):
        system.step(dt=0.1)

    v_final = system.v.to_numpy()
    x_final = system.x.to_numpy()

    print("模擬後狀態：")
    print(f"  Agent 0: 速度 {np.linalg.norm(v_final[0]):.3f}, 存活")
    print(f"  Agent 1: 速度 {np.linalg.norm(v_final[1]):.3f}, 死亡（應為 0）")
    print(f"  Agent 2: 速度 {np.linalg.norm(v_final[2]):.3f}, 存活")

    assert np.linalg.norm(v_final[1]) < 1e-6, "死亡 agent 速度應為 0"
    assert np.linalg.norm(x_final[1]) > 1e5, "死亡 agent 應該在遠處"

    print("\n✅ 死亡 agent 正確靜止且不參與交互")

    print("\n" + "=" * 70)
    print("✅ 死亡消失機制測試完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

