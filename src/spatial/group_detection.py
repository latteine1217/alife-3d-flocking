"""
Group Detection Mixin - 群組檢測演算法

基於 Label Propagation + Spatial Grid 的群組檢測

演算法：
    1. 初始化：每個 agent 自成一組
    2. 迭代：滿足條件的鄰居合併到較小的群組 ID
    3. 統計：計算每個群組的大小、質心、平均速度

條件：
    • 距離 < r_cluster
    • 速度夾角 < theta_cluster

效能：
    • 使用 Spatial Grid 加速：O(N × k) where k ≈ 27 cells
    • 迭代次數：通常 3-5 次收斂

使用方式：
    class MySystem(SpatialGridMixin, GroupDetectionMixin):
        def __init__(self, N, ...):
            super().__init__(N, ...)
            self.init_spatial_grid(N, box_size, cell_size)
            self.init_group_detection(N, max_groups=32)
"""

import taichi as ti
import numpy as np
from typing import Optional, List


@ti.data_oriented
class GroupDetectionMixin:
    """
    群組檢測 Mixin

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

        # 初始化
        self.group_id.fill(-1)
        self.group_active.fill(0)

        # 群組檢測頻率控制
        self.group_detection_interval = 5  # 每 N 步檢測一次
        self.step_counter = 0

        print(f"[GroupDetection] Initialized with max_groups={max_groups}")

    @ti.kernel
    def detect_groups_iteration(self, r_cluster: ti.f32, theta_cluster: ti.f32):
        """
        執行單次群組偵測迭代（label propagation 的一輪）
        使用 Spatial Grid 加速鄰居搜尋：O(N × k) 取代 O(N²)

        條件：
            • 兩個 agents 距離 < r_cluster
            • 速度夾角 < theta_cluster

        Args:
            r_cluster: 聚類距離閾值
            theta_cluster: 速度夾角閾值（弧度）

        Note:
            掠食者排除邏輯需要在子類別中 override 這個方法
        """
        for i in self.x:
            xi = self.x[i]
            vi = self.v[i]
            vi_norm = vi.norm()

            if vi_norm < 1e-6:
                continue

            current_group = self.group_id[i]
            min_group = current_group

            # 獲取 agent i 所在的 cell
            cell_id = self.agent_cell_id[i]
            if cell_id < 0:  # 無效 cell（不應該發生）
                continue

            # 解析 cell_id 為 3D index (ix, iy, iz)
            res = self.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res

            # 只檢查 3×3×3=27 個相鄰 cell 中的 agents（取代原本的 O(N) 全局搜尋）
            for dz in ti.static(range(-1, 2)):
                for dy in ti.static(range(-1, 2)):
                    for dx in ti.static(range(-1, 2)):
                        nx = ix + dx
                        ny = iy + dy
                        nz = iz + dz

                        # 邊界檢查：只處理有效的鄰居 cell
                        if (
                            nx >= 0
                            and nx < res
                            and ny >= 0
                            and ny < res
                            and nz >= 0
                            and nz < res
                        ):
                            neighbor_cell = nx + ny * res + nz * res * res

                            # 檢查該 cell 中的所有 agents
                            n_agents_in_cell = self.cell_count[neighbor_cell]
                            for local_idx in range(n_agents_in_cell):
                                if local_idx >= self.max_agents_per_cell:
                                    break

                                j = self.cell_agents[neighbor_cell, local_idx]
                                if i == j:
                                    continue

                                xj = self.x[j]
                                vj = self.v[j]
                                vj_norm = vj.norm()

                                if vj_norm < 1e-6:
                                    continue

                                # 計算距離（考慮 PBC）
                                distance = 0.0
                                if self.params.boundary_mode == 0:  # PBC
                                    distance = self.pbc_dist(xi, xj).norm()
                                else:
                                    distance = (xj - xi).norm()

                                # 檢查空間接近度
                                if distance > r_cluster:
                                    continue

                                # 檢查速度夾角
                                cos_angle = (vi.dot(vj)) / (vi_norm * vj_norm)
                                # 處理數值誤差
                                cos_angle = ti.max(-1.0, ti.min(1.0, cos_angle))
                                angle = ti.acos(cos_angle)

                                if angle > theta_cluster:
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

    def update_groups(
        self, r_cluster: float = 5.0, theta_cluster: float = 30.0, n_iterations: int = 5
    ):
        """
        更新群組偵測（Python 介面）
        使用 Spatial Grid 加速：O(N × k) 取代 O(N²)

        Args:
            r_cluster: 聚類距離閾值
            theta_cluster: 速度夾角閾值（度數）
            n_iterations: 迭代次數（通常 3-5 次收斂）
        """
        theta_rad = np.radians(theta_cluster)

        # 動態更新 grid_cell_size（確保 cell_size = r_cluster）
        self.grid_cell_size = r_cluster
        self.grid_resolution = max(
            int(self.params.box_size / r_cluster) + 1, 4
        )  # 最小 4×4×4

        # Step 1: 將 agents 分配到 spatial grid（O(N)）
        self.assign_agents_to_grid()

        # Step 2: 初始化：每個 agent 自己是一個群組
        self.group_id.fill(-1)
        N = len(self.x.to_numpy())
        for i in range(N):
            # 掠食者不參與群組（需要檢查 agent_types_np 是否存在）
            if hasattr(self, "agent_types_np") and self.agent_types_np[i] != 3:
                self.group_id[i] = i
            elif not hasattr(self, "agent_types_np"):
                # 沒有類型系統，所有 agent 參與
                self.group_id[i] = i

        # Step 3: 執行多輪迭代（使用 Grid 加速的鄰居搜尋）
        for iteration in range(n_iterations):
            self.detect_groups_iteration(r_cluster, theta_rad)

        # Step 4: 計算群組統計
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
