"""
Spatial Grid Mixin - 空間網格加速結構

提供 O(N) 鄰居查詢，取代 O(N²) 的全局搜尋

設計理念：
    • 將3D空間劃分為均勻網格（Grid）
    • 每個 agent 被分配到對應的 cell
    • 查詢鄰居時只檢查 3×3×3 = 27 個鄰居 cell

效能：
    • 空間分配：O(N)
    • 鄰居查詢：O(k) where k ≈ agents_per_cell × 27
    • 適合：均勻分布的 agent 群體

使用方式：
    class MySystem(BaseClass, SpatialGridMixin):
        def __init__(self, N, ...):
            super().__init__(N, ...)
            self.init_spatial_grid(N, box_size=50.0, cell_size=5.0)
"""

import taichi as ti
import numpy as np


@ti.data_oriented
class SpatialGridMixin:
    """
    空間網格 Mixin

    依賴：
        • self.N: agent 數量
        • self.x: agent 位置 field (Vector.field(3, ti.f32, N))
        • self.params.box_size: 模擬邊界大小
        • self.agent_type: agent 類型 field (ti.field(ti.i32, N))
    """

    def init_spatial_grid(
        self,
        N: int,
        box_size: float = 50.0,
        cell_size: float = 5.0,
        max_agents_per_cell: int = 32,
    ):
        """
        初始化 Spatial Grid 資料結構

        Args:
            N: Agent 數量
            box_size: 模擬空間大小
            cell_size: Grid cell 的邊長（建議設為群組檢測的 r_cluster）
            max_agents_per_cell: 每個 cell 最多容納的 agent 數量
        """
        self.grid_cell_size = cell_size
        self.grid_resolution = max(int(box_size / cell_size) + 1, 4)  # 至少 4×4×4
        self.max_agents_per_cell = max_agents_per_cell

        # Grid 資料結構
        total_cells = self.grid_resolution**3
        self.agent_cell_id = ti.field(ti.i32, N)  # 每個 agent 所在的 cell ID
        self.cell_count = ti.field(ti.i32, total_cells)  # 每個 cell 中的 agent 數量
        self.cell_agents = ti.field(
            ti.i32, (total_cells, max_agents_per_cell)
        )  # cell → agents 映射

        # 初始化
        self.agent_cell_id.fill(-1)
        self.cell_count.fill(0)

        print(
            f"[SpatialGrid] Initialized {self.grid_resolution}³ grid "
            f"(cell_size={cell_size:.2f}, total_cells={total_cells})"
        )

    @ti.func
    def get_cell_id(self, pos: ti.template()) -> ti.i32:
        """
        計算位置對應的 cell ID

        Args:
            pos: 3D 位置向量

        Returns:
            cell_id: 一維 cell index
        """
        # 將位置從 [-box_size/2, box_size/2] 映射到 [0, grid_resolution]
        half_box = self.params.box_size / 2.0

        ix = ti.cast((pos[0] + half_box) / self.grid_cell_size, ti.i32)
        iy = ti.cast((pos[1] + half_box) / self.grid_cell_size, ti.i32)
        iz = ti.cast((pos[2] + half_box) / self.grid_cell_size, ti.i32)

        # 邊界處理：clamp 到 [0, grid_resolution-1]
        ix = ti.max(0, ti.min(ix, self.grid_resolution - 1))
        iy = ti.max(0, ti.min(iy, self.grid_resolution - 1))
        iz = ti.max(0, ti.min(iz, self.grid_resolution - 1))

        # 一維化：cell_id = ix + iy * res + iz * res²
        cell_id = (
            ix
            + iy * self.grid_resolution
            + iz * self.grid_resolution * self.grid_resolution
        )

        return cell_id

    @ti.kernel
    def assign_agents_to_grid(self):
        """
        將所有 agent 分配到對應的 spatial grid cell
        時間複雜度：O(N)

        Note:
            • 掠食者（type=3）會被跳過（不參與群組檢測）
            • 使用原子操作避免競爭條件
        """
        # 重置 cell_count
        for c in self.cell_count:
            self.cell_count[c] = 0

        # 第一遍：計算每個 agent 的 cell_id
        for i in self.x:
            cell_id = self.get_cell_id(self.x[i])
            self.agent_cell_id[i] = cell_id

            # 原子操作：計數該 cell 的 agent 數量
            old_count = ti.atomic_add(self.cell_count[cell_id], 1)

            # 將 agent 加入該 cell（如果未滿）
            if old_count < self.max_agents_per_cell:
                self.cell_agents[cell_id, old_count] = i

    @ti.func
    def get_neighbor_cells(self, cell_id: ti.i32) -> ti.types.vector(27, ti.i32):
        """
        獲取指定 cell 的所有鄰居 cell（包含自己）

        Args:
            cell_id: 中心 cell 的 ID

        Returns:
            neighbor_cells: 最多 27 個鄰居 cell 的 ID（3×3×3）
                           無效的位置填 -1
        """
        # 解析 cell_id 為 (ix, iy, iz)
        res = self.grid_resolution
        iz = cell_id // (res * res)
        remainder = cell_id % (res * res)
        iy = remainder // res
        ix = remainder % res

        # 遍歷 3×3×3 的鄰居 cell
        neighbors = ti.Vector([0] * 27, dt=ti.i32)
        count = 0

        for dz in ti.static(range(-1, 2)):
            for dy in ti.static(range(-1, 2)):
                for dx in ti.static(range(-1, 2)):
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
                        neighbors[count] = neighbor_cell
                        count += 1

        # 剩餘位置填 -1（無效）
        for k in range(count, 27):
            neighbors[k] = -1

        return neighbors

    def update_grid_resolution(self, new_cell_size: float):
        """
        動態調整 Grid 解析度（用於適應不同的 r_cluster）

        Args:
            new_cell_size: 新的 cell 大小

        Note:
            這會觸發重新分配記憶體，成本較高，建議在初始化時設定正確的值
        """
        self.grid_cell_size = new_cell_size
        new_resolution = max(int(self.params.box_size / new_cell_size) + 1, 4)

        if new_resolution != self.grid_resolution:
            print(
                f"[SpatialGrid] Resolution changed: {self.grid_resolution} → {new_resolution}"
            )
            self.grid_resolution = new_resolution

            # 重新分配 fields（警告：這會觸發 Taichi 重新編譯）
            total_cells = new_resolution**3
            self.cell_count = ti.field(ti.i32, total_cells)
            self.cell_agents = ti.field(ti.i32, (total_cells, self.max_agents_per_cell))
            self.cell_count.fill(0)
