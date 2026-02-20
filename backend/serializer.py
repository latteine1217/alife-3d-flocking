"""
Binary Serialization Module
將 Taichi 模擬狀態序列化為二進制格式

資料格式:
- Header (20 bytes): N, step, has_resources, has_obstacles
- Agent Data (N * 37 bytes): positions, velocities, types, energies, targets, group_labels
- Statistics (64 bytes): mean_speed, std_speed, Rg, polarization, n_groups
- Resources (optional): n_resources, [positions, amounts, radii]
- Group Statistics (optional): n_active_groups, [group_id, size, centroid, velocity, radius]
"""

import struct
import numpy as np


# 延遲匯入（避免循環依賴）
def _get_agent_type():
    from agents.types import AgentType

    return AgentType


class BinarySerializer:
    """二進制序列化器"""

    @staticmethod
    def serialize_state(system) -> bytes:
        """
        將模擬系統狀態序列化為二進制格式

        Args:
            system: Flocking3D 或 HeterogeneousFlocking3D 實例

        Returns:
            bytes: 序列化後的二進制資料
        """
        buffer = bytearray()

        # === Header (20 bytes) ===
        N = system.N
        step = getattr(system, "step_count", 0)

        # 檢查是否有資源系統
        has_resources = False
        active_resource_indices = []
        if hasattr(system, "resources") and hasattr(system.resources, "n_resources"):
            active_np = system.resources.resource_active.to_numpy()
            n_res = system.resources.n_resources
            active_resource_indices = [i for i in range(n_res) if active_np[i] == 1]
            has_resources = len(active_resource_indices) > 0

        has_obstacles = False  # 目前不支援障礙物序列化

        # 🔧 FIX: 過濾死亡的 agents
        # 只序列化 agent_alive == 1 的 agents
        if hasattr(system, "agent_alive"):
            alive_mask_full = system.agent_alive.to_numpy()
            # 只取前 N 個（避免維度不匹配）
            alive_mask = (alive_mask_full[:N] == 1)
            N_alive = np.sum(alive_mask)
        else:
            alive_mask = np.ones(N, dtype=bool)
            N_alive = N

        buffer.extend(struct.pack("I", N_alive))  # uint32（實際存活數）
        buffer.extend(struct.pack("I", step))  # uint32
        buffer.extend(struct.pack("B", int(has_resources)))  # uint8
        buffer.extend(struct.pack("B", int(has_obstacles)))  # uint8
        buffer.extend(b"\x00" * 10)  # reserved

        # === Agent Data ===
        # Positions (N_alive * 3 * 4 bytes)
        # system.x 是 Vector.field(3, ti.f32, max_agents)
        # to_numpy() 返回 shape=(max_agents, 3) 的數組
        x_np_full = system.x.to_numpy().astype(np.float32)  # shape=(max_agents, 3)
        x_np = x_np_full[:N]  # 只取前 N 個 agents，shape=(N, 3)
        x_alive = x_np[alive_mask]  # shape=(N_alive, 3)
        buffer.extend(x_alive.flatten().tobytes())

        # Velocities (N_alive * 3 * 4 bytes)
        v_np_full = system.v.to_numpy().astype(np.float32)  # shape=(max_agents, 3)
        v_np = v_np_full[:N]  # shape=(N, 3)
        v_alive = v_np[alive_mask]  # shape=(N_alive, 3)
        buffer.extend(v_alive.flatten().tobytes())

        # Types (N_alive * 1 bytes + padding)
        if hasattr(system, "agent_types_np"):
            types_full = system.agent_types_np.astype(np.uint8)
            types = types_full[:N][alive_mask]
        else:
            types = np.zeros(N_alive, dtype=np.uint8)
        buffer.extend(types.tobytes())

        # Padding to 4-byte alignment
        padding = (4 - (N_alive % 4)) % 4
        buffer.extend(b"\x00" * padding)

        # Energies (N_alive * 4 bytes)
        # 優先使用異質系統的 agent_energy，向後相容舊欄位 energy
        if hasattr(system, "agent_energy"):
            energy_full = system.agent_energy.to_numpy().astype(np.float32)
            energy_np = energy_full[:N][alive_mask]
        elif hasattr(system, "energy"):
            energy_full = system.energy.to_numpy().astype(np.float32)
            energy_np = energy_full[:N][alive_mask]
        else:
            energy_np = np.zeros(N_alive, dtype=np.float32)
        buffer.extend(energy_np.tobytes())

        # Targets (N_alive * 4 bytes)
        if hasattr(system, "target_resource"):
            target_full = system.target_resource.to_numpy().astype(np.int32)
            target_np = target_full[:N][alive_mask]
        else:
            target_np = np.full(N_alive, -1, dtype=np.int32)
        buffer.extend(target_np.tobytes())

        # Group Labels (N_alive * 4 bytes) - NEW
        if hasattr(system, "group_id"):
            group_labels_full = system.group_id.to_numpy().astype(np.int32)
            group_labels_np = group_labels_full[:N][alive_mask]
        else:
            group_labels_np = np.full(N_alive, -1, dtype=np.int32)
        buffer.extend(group_labels_np.tobytes())

        # === Statistics (64 bytes) ===
        stats = system.compute_diagnostics()

        # 將統計資料打包為 float32
        stat_values = [
            stats.get("mean_speed", 0.0),
            stats.get("std_speed", 0.0),
            stats.get("Rg", 0.0),
            stats.get("polarization", 0.0),
            0.0,  # reserved
            0.0,  # reserved
            0.0,  # reserved
            0.0,  # reserved
        ]
        buffer.extend(struct.pack("8f", *stat_values))

        # n_groups (uint32)
        n_groups = stats.get("n_groups", 0)
        buffer.extend(struct.pack("I", n_groups))

        # Padding to 64 bytes
        buffer.extend(b"\x00" * 28)

        # === Resources (optional) ===
        if has_resources:
            res_system = system.resources
            # 只寫入活躍資源數量，確保前後端解析偏移一致
            buffer.extend(struct.pack("I", len(active_resource_indices)))

            # 讀取資源資料
            pos_np = res_system.resource_pos.to_numpy()
            amount_np = res_system.resource_amount.to_numpy()
            radius_np = res_system.resource_radius.to_numpy()
            replenish_np = res_system.resource_replenish_rate.to_numpy()
            max_amount_np = res_system.resource_max_amount.to_numpy()

            for i in active_resource_indices:
                pos = pos_np[i]
                buffer.extend(struct.pack("fff", pos[0], pos[1], pos[2]))

                # amount 轉為標準化值（0-1）給前端著色
                max_amt = max_amount_np[i]
                amount_ratio = amount_np[i] / max_amt if max_amt > 0 else 0.0
                amount_ratio = max(0.0, min(1.0, amount_ratio))

                buffer.extend(struct.pack("f", amount_ratio))
                buffer.extend(struct.pack("f", radius_np[i]))

                # is_renewable (uint8)
                is_renewable = int(replenish_np[i] > 0)
                buffer.extend(struct.pack("B", is_renewable))
                buffer.extend(b"\x00" * 3)  # padding

        # === Group Statistics (optional) ===
        # 只有 HeterogeneousFlocking3D 才有群組資料
        if hasattr(system, "get_all_groups"):
            groups = system.get_all_groups()
            n_active_groups = len(groups)
            buffer.extend(struct.pack("I", n_active_groups))

            # 每個群組: group_id(4) + size(4) + centroid(12) + velocity(12) + radius(4) = 36 bytes
            for group_info in groups:
                gid = group_info["group_id"]
                size = group_info["size"]
                centroid = group_info["centroid"]
                velocity = group_info["velocity"]

                # 計算 bounding radius（用 Rg 估計：半徑 ≈ sqrt(N) 的典型距離）
                # 簡化：radius = sqrt(size) * 2.0
                radius = np.sqrt(size) * 2.0

                buffer.extend(struct.pack("I", gid))
                buffer.extend(struct.pack("I", size))
                buffer.extend(struct.pack("fff", centroid[0], centroid[1], centroid[2]))
                buffer.extend(struct.pack("fff", velocity[0], velocity[1], velocity[2]))
                buffer.extend(struct.pack("f", radius))
        else:
            # 無群組資料，寫入 0
            buffer.extend(struct.pack("I", 0))

        return bytes(buffer)

    @staticmethod
    def get_frame_size(N: int, n_resources: int = 0) -> int:
        """
        計算單幀資料大小

        Args:
            N: 粒子數量
            n_resources: 資源數量

        Returns:
            int: 資料大小（bytes）
        """
        header = 20
        agents = (
            N * 37
        )  # positions(12) + velocities(12) + types(1+pad3) + energies(4) + targets(4) + groups(4)
        stats = 64
        resources = n_resources * 20 if n_resources > 0 else 0
        return header + agents + stats + resources


# === 測試與效能分析 ===
if __name__ == "__main__":
    import sys
    import time

    sys.path.insert(0, "../src")

    import taichi as ti
    from flocking_heterogeneous import HeterogeneousFlocking3D
    from agents.types import AgentType
    from flocking_3d import FlockingParams

    # 初始化 Taichi
    ti.init(arch=ti.gpu)

    # 建立測試系統
    N = 100
    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=1.0,
        eta=0.0,
        box_size=50.0,
        boundary_mode="pbc",
    )

    agent_types = (
        [AgentType.EXPLORER] * 30 + [AgentType.FOLLOWER] * 50 + [AgentType.LEADER] * 20
    )

    system = HeterogeneousFlocking3D(
        N=N,
        params=params,
        agent_types=agent_types,
        enable_fov=True,
        fov_angle=120.0,
        max_obstacles=10,
        max_resources=5,
    )

    system.initialize(box_size=50.0, seed=42)

    # 測試序列化效能
    print("=== Serialization Performance Test ===")
    iterations = 1000

    start = time.time()
    for i in range(iterations):
        data = BinarySerializer.serialize_state(system)
        if i == 0:
            print(f"Frame size: {len(data)} bytes ({len(data) / 1024:.2f} KB)")

    elapsed = time.time() - start
    fps = iterations / elapsed

    print(f"\nIterations: {iterations}")
    print(f"Time: {elapsed:.2f} s")
    print(f"Speed: {fps:.1f} FPS")
    print(f"Latency: {1000 / fps:.2f} ms/frame")

    # 估算頻寬
    bandwidth_kbps = (len(data) * fps) / 1024
    print(f"\nBandwidth @ 30 FPS: {bandwidth_kbps * 30 / fps:.2f} KB/s")
    print(f"Bandwidth @ 60 FPS: {bandwidth_kbps * 60 / fps:.2f} KB/s")

    # 驗證反序列化
    print("\n=== Data Validation ===")
    import struct

    view_bytes = data
    N_read = struct.unpack("I", view_bytes[0:4])[0]
    step_read = struct.unpack("I", view_bytes[4:8])[0]

    print(f"N: {N_read} (expected: {N})")
    print(f"Step: {step_read}")

    # 讀取第一個粒子位置
    offset = 20  # header
    x, y, z = struct.unpack("fff", view_bytes[offset : offset + 12])
    print(f"First particle position: ({x:.2f}, {y:.2f}, {z:.2f})")

    print("\n✅ Serializer test completed!")
