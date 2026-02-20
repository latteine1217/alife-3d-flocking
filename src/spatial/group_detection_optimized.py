"""
Group Detection Mixin - 群組檢測演算法（優化版）

改進點：
    1. 避免 ti.acos() - 直接比較 cos(angle)
    2. 預先計算速度 norm - 避免重複計算
    3. 降低迭代次數 - 1-2 次即可收斂
    4. Early termination - 群組穩定後提前終止
    5. 更激進的 max_check 限制

效能提升：預計從 55ms → <10ms (5x+ 加速)
"""

import taichi as ti
import numpy as np
from typing import Optional, List


@ti.data_oriented
class GroupDetectionMixinOptimized:
    """
    群組檢測 Mixin（優化版）

    依賴：
        • SpatialGridMixin: 需要先初始化
        • self.x: agent 位置 field
        • self.v: agent 速度 field
        • self.agent_type: agent 類型 field (可選)
        • self.params.boundary_mode: 邊界模式
        • self.pbc_dist: PBC 距離計算函數
    """

    def init_group_detection(self, N: int, max_groups: int = 32):
        """
        初始化群組檢測資料結構

        Args:
            N: Agent 數量
            max_groups: 最大群組數量（通常設為 N 的 1/3 到 1/2）
        """
        self.max_groups = max_groups

        # 群組 ID 與狀態
        self.group_id = ti.field(ti.i32, N)  # 每個 agent 的群組 ID（-1 = 無群組）
        self.group_active = ti.field(ti.i32, max_groups)  # 群組是否有效（0/1）

        # 群組統計資訊
        self.group_size = ti.field(ti.i32, max_groups)  # 每個群組的大小
        self.group_centroid = ti.Vector.field(3, ti.f32, max_groups)  # 群組質心
        self.group_velocity = ti.Vector.field(3, ti.f32, max_groups)  # 群組平均速度

        # 預先計算的速度 norm（避免重複計算）
        self.v_norm_cache = ti.field(ti.f32, N)

        # 初始化
        self.group_id.fill(-1)
        self.group_active.fill(0)

        # 群組檢測頻率控制
        self.group_detection_interval = 5  # 每 N 步檢測一次
        self.step_counter = 0

        print(f"[GroupDetection-Optimized] Initialized with max_groups={max_groups}")

    @ti.kernel
    def precompute_velocity_norms(self):
        """預先計算所有 agent 的速度 norm（避免重複計算）"""
        for i in self.v:
            self.v_norm_cache[i] = self.v[i].norm()

    @ti.kernel
    def detect_groups_iteration_optimized(
        self, r_cluster: ti.f32, cos_theta_cluster: ti.f32
    ):
        """
        執行單次群組偵測迭代（優化版）

        改進：
            • 避免 ti.acos() - 直接比較 cos_angle
            • 使用預先計算的 v_norm_cache
            • 更激進的 max_check=8

        Args:
            r_cluster: 聚類距離閾值
            cos_theta_cluster: 速度夾角的 cos 值（避免 acos 計算）
        """
        for i in self.x:
            vi_norm = self.v_norm_cache[i]

            if vi_norm < 1e-6:
                continue

            min_group = self.group_id[i]

            # 獲取 agent i 所在的 cell
            cell_id = self.agent_cell_id[i]
            if cell_id < 0:
                continue

            # 解析 cell_id 為 3D index
            res = self.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res

            xi = self.x[i]
            vi = self.v[i]

            # Loop unrolling: 27 cells
            for cell_offset in ti.static(range(27)):
                dz = (cell_offset // 9) - 1
                dy = ((cell_offset % 9) // 3) - 1
                dx = (cell_offset % 3) - 1

                nx = ix + dx
                ny = iy + dy
                nz = iz + dz

                # 邊界檢查
                if (
                    nx >= 0
                    and nx < res
                    and ny >= 0
                    and ny < res
                    and nz >= 0
                    and nz < res
                ):
                    neighbor_cell = nx + ny * res + nz * res * res
                    n_agents_in_cell = self.cell_count[neighbor_cell]

                    # 更激進的限制：max_check=8
                    max_check = ti.min(n_agents_in_cell, 8)

                    for local_idx in range(max_check):
                        j = self.cell_agents[neighbor_cell, local_idx]
                        if i == j:
                            continue

                        vj_norm = self.v_norm_cache[j]
                        if vj_norm < 1e-6:
                            continue

                        # 距離檢查
                        xj = self.x[j]
                        distance = 0.0
                        if self.params.boundary_mode == 0:  # PBC
                            distance = self.pbc_dist(xi, xj).norm()
                        else:
                            distance = (xj - xi).norm()

                        if distance > r_cluster:
                            continue

                        # 速度夾角檢查（避免 acos！）
                        vj = self.v[j]
                        cos_angle = (vi.dot(vj)) / (vi_norm * vj_norm)
                        cos_angle = ti.max(-1.0, ti.min(1.0, cos_angle))

                        # 直接比較 cos 值（cos 單調遞減，angle 越大 cos 越小）
                        if cos_angle < cos_theta_cluster:
                            continue

                        # 滿足條件：取較小的 group_id
                        neighbor_group = self.group_id[j]
                        if neighbor_group < min_group:
                            min_group = neighbor_group

            # 更新 group_id
            self.group_id[i] = min_group

    @ti.kernel
    def compute_group_statistics(self):
        """
        計算每個群組的統計資訊

        計算：
            • group_size: 群組大小
            • group_centroid: 質心位置
            • group_velocity: 平均速度
        """
        # 重置統計資訊
        for g in range(self.max_groups):
            self.group_size[g] = 0
            self.group_centroid[g] = ti.Vector([0.0, 0.0, 0.0])
            self.group_velocity[g] = ti.Vector([0.0, 0.0, 0.0])
            self.group_active[g] = 0

        # 第一輪：計算每個群組的總和
        for i in self.x:
            gid = self.group_id[i]
            if gid >= 0 and gid < self.max_groups:
                # 使用 atomic add 避免 race condition
                ti.atomic_add(self.group_size[gid], 1)
                for d in ti.static(range(3)):
                    ti.atomic_add(self.group_centroid[gid][d], self.x[i][d])
                    ti.atomic_add(self.group_velocity[gid][d], self.v[i][d])

        # 第二輪：計算平均值並標記有效群組
        for g in range(self.max_groups):
            size = self.group_size[g]
            if size > 0:
                self.group_active[g] = 1
                # 計算平均值
                for d in ti.static(range(3)):
                    self.group_centroid[g][d] /= ti.cast(size, ti.f32)
                    self.group_velocity[g][d] /= ti.cast(size, ti.f32)

    @ti.kernel
    def check_convergence(self) -> ti.i32:
        """
        檢查群組是否已收斂（early termination）

        Returns:
            變更數量（若為 0 則完全收斂）
        """
        change_count = 0

        for i in self.x:
            current_group = self.group_id[i]
            vi_norm = self.v_norm_cache[i]

            if vi_norm < 1e-6:
                continue

            # 檢查是否有更小的鄰居群組
            cell_id = self.agent_cell_id[i]
            if cell_id < 0:
                continue

            res = self.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res

            has_smaller_neighbor = 0

            # 只檢查直接相鄰的 cell（不是全部 27 個）
            for cell_offset in ti.static(range(7)):  # 自己 + 6 個面相鄰
                dx, dy, dz = 0, 0, 0
                if cell_offset == 1:
                    dx = 1
                elif cell_offset == 2:
                    dx = -1
                elif cell_offset == 3:
                    dy = 1
                elif cell_offset == 4:
                    dy = -1
                elif cell_offset == 5:
                    dz = 1
                elif cell_offset == 6:
                    dz = -1

                nx = ix + dx
                ny = iy + dy
                nz = iz + dz

                if (
                    nx >= 0
                    and nx < res
                    and ny >= 0
                    and ny < res
                    and nz >= 0
                    and nz < res
                ):
                    neighbor_cell = nx + ny * res + nz * res * res
                    n_agents = ti.min(self.cell_count[neighbor_cell], 4)

                    for local_idx in range(n_agents):
                        j = self.cell_agents[neighbor_cell, local_idx]
                        if self.group_id[j] < current_group:
                            has_smaller_neighbor = 1
                            break

                if has_smaller_neighbor == 1:
                    break

            if has_smaller_neighbor == 1:
                ti.atomic_add(change_count, 1)

        return change_count

    def update_groups(
        self, r_cluster: float = 5.0, theta_cluster: float = 30.0, n_iterations: int = 2
    ):
        """
        更新群組偵測（Python 介面，優化版）

        改進：
            • 預先計算速度 norm
            • 使用 cos(theta) 避免 acos
            • 降低迭代次數：5 → 2
            • Early termination（收斂後提前終止）

        Args:
            r_cluster: 聚類距離閾值
            theta_cluster: 速度夾角閾值（度數）
            n_iterations: 最大迭代次數（通常 1-2 次即可）
        """
        theta_rad = np.radians(theta_cluster)
        cos_theta = np.cos(theta_rad)  # 預先計算 cos，避免 acos

        # 動態更新 grid_cell_size（確保 cell_size = r_cluster）
        self.grid_cell_size = r_cluster
        self.grid_resolution = max(
            int(self.params.box_size / r_cluster) + 1, 4
        )  # 最小 4×4×4

        # Step 1: 將 agents 分配到 spatial grid（O(N)）
        self.assign_agents_to_grid()

        # Step 2: 預先計算速度 norm
        self.precompute_velocity_norms()

        # Step 3: 初始化：每個 agent 自己是一個群組
        self.group_id.fill(-1)
        N = len(self.x.to_numpy())
        for i in range(N):
            # 掠食者不參與群組（需要檢查 agent_types_np 是否存在）
            if hasattr(self, "agent_types_np") and self.agent_types_np[i] != 3:
                self.group_id[i] = i
            elif not hasattr(self, "agent_types_np"):
                # 沒有類型系統，所有 agent 參與
                self.group_id[i] = i

        # Step 4: 執行迭代（with early termination）
        for iteration in range(n_iterations):
            self.detect_groups_iteration_optimized(r_cluster, cos_theta)

            # Early termination: 檢查是否收斂
            if iteration > 0:  # 第一輪之後才檢查
                change_count = self.check_convergence()
                if change_count == 0:
                    print(
                        f"[GroupDetection] Converged after {iteration + 1} iterations"
                    )
                    break

        # Step 5: 計算群組統計
        self.compute_group_statistics()

    def get_group_info(self, group_id: int) -> Optional[dict]:
        """
        獲取群組資訊

        Args:
            group_id: 群組 ID

        Returns:
            群組資訊字典，若群組無效則返回 None
        """
        if group_id < 0 or group_id >= self.max_groups:
            return None

        if self.group_active[group_id] == 0:
            return None

        return {
            "group_id": group_id,
            "size": self.group_size[group_id],
            "centroid": self.group_centroid[group_id].to_numpy(),
            "velocity": self.group_velocity[group_id].to_numpy(),
        }

    def get_all_groups(self) -> List[dict]:
        """獲取所有有效群組的資訊"""
        groups = []
        for g in range(self.max_groups):
            info = self.get_group_info(g)
            if info is not None:
                groups.append(info)
        return groups

    def get_agent_groups(self) -> np.ndarray:
        """獲取每個 agent 的群組 ID（返回 numpy 陣列）"""
        return self.group_id.to_numpy()
