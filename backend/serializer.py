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
        if hasattr(system, "resources") and hasattr(system.resources, "n_resources"):
            has_resources = system.resources.n_resources > 0

        has_obstacles = False  # 目前不支援障礙物序列化

        buffer.extend(struct.pack("I", N))  # uint32
        buffer.extend(struct.pack("I", step))  # uint32
        buffer.extend(struct.pack("B", int(has_resources)))  # uint8
        buffer.extend(struct.pack("B", int(has_obstacles)))  # uint8
        buffer.extend(b"\x00" * 10)  # reserved

        # === Agent Data ===
        # Positions (N * 3 * 4 bytes)
        x_np = system.x.to_numpy().astype(np.float32)
        buffer.extend(x_np.tobytes())

        # Velocities (N * 3 * 4 bytes)
        v_np = system.v.to_numpy().astype(np.float32)
        buffer.extend(v_np.tobytes())

        # Types (N * 1 bytes + padding)
        if hasattr(system, "agent_types_np"):
            types = system.agent_types_np.astype(np.uint8)
        else:
            types = np.zeros(N, dtype=np.uint8)
        buffer.extend(types.tobytes())

        # Padding to 4-byte alignment
        padding = (4 - (N % 4)) % 4
        buffer.extend(b"\x00" * padding)

        # Energies (N * 4 bytes)
        if hasattr(system, "energy"):
            energy_np = system.energy.to_numpy().astype(np.float32)
        else:
            energy_np = np.zeros(N, dtype=np.float32)
        buffer.extend(energy_np.tobytes())

        # Targets (N * 4 bytes)
        if hasattr(system, "target_resource"):
            target_np = system.target_resource.to_numpy().astype(np.int32)
        else:
            target_np = np.full(N, -1, dtype=np.int32)
        buffer.extend(target_np.tobytes())

        # Group Labels (N * 4 bytes) - NEW
        if hasattr(system, "group_id"):
            group_labels_np = system.group_id.to_numpy().astype(np.int32)
        else:
            group_labels_np = np.full(N, -1, dtype=np.int32)
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
            n_res = res_system.n_resources
            buffer.extend(struct.pack("I", n_res))

            # 讀取資源資料
            pos_np = res_system.resource_pos.to_numpy()
            amount_np = res_system.resource_amount.to_numpy()
            radius_np = res_system.resource_radius.to_numpy()
            replenish_np = res_system.resource_replenish_rate.to_numpy()
            active_np = res_system.resource_active.to_numpy()

            for i in range(n_res):
                if active_np[i] == 1:  # 只序列化活躍的資源
                    pos = pos_np[i]
                    buffer.extend(struct.pack("fff", pos[0], pos[1], pos[2]))
                    buffer.extend(struct.pack("f", amount_np[i]))
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
