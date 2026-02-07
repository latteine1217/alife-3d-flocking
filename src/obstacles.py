"""
Obstacle System for Flocking Simulation

提供障礙物系統，支援多種幾何形狀與排斥力計算。

障礙物類型：
    • Sphere（球體）
    • Box（長方體）
    • Cylinder（圓柱體）

物理機制：
    • 使用 SDF (Signed Distance Field) 計算最近距離
    • 施加排斥力：F = -k * exp(-d/d0) * n（指數衰減）
    • 支援靜態與動態障礙物
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Tuple

import numpy as np
import taichi as ti


class ObstacleType(IntEnum):
    """障礙物類型"""

    SPHERE = 0  # 球體
    BOX = 1  # 長方體（軸對齊）
    CYLINDER = 2  # 圓柱體（沿 z 軸）


@dataclass
class ObstacleConfig:
    """障礙物配置"""

    obstacle_type: ObstacleType
    position: np.ndarray  # (3,)
    params: (
        np.ndarray
    )  # 依類型不同：Sphere:[r,0,0,0], Box:[hx,hy,hz,0], Cylinder:[r,h,0,0]
    strength: float = 10.0  # 排斥力強度
    decay_length: float = 2.0  # 衰減長度


@ti.data_oriented
class ObstacleSystem:
    """
    障礙物系統

    功能：
        • 管理多個障礙物
        • 計算 agent-obstacle 排斥力
        • 支援動態更新障礙物位置
    """

    def __init__(self, max_obstacles: int = 32):
        """
        初始化障礙物系統

        Args:
            max_obstacles: 最大障礙物數量
        """
        self.max_obstacles = max_obstacles
        self.n_obstacles = 0

        # Taichi fields
        self.obstacle_type = ti.field(ti.i32, max_obstacles)
        self.obstacle_pos = ti.Vector.field(3, ti.f32, max_obstacles)
        self.obstacle_params = ti.Vector.field(4, ti.f32, max_obstacles)
        self.obstacle_strength = ti.field(ti.f32, max_obstacles)
        self.obstacle_decay = ti.field(ti.f32, max_obstacles)
        self.obstacle_active = ti.field(ti.i32, max_obstacles)  # 0/1

        # 初始化為 inactive
        self.obstacle_active.fill(0)

    def add_obstacle(self, config: ObstacleConfig) -> int:
        """
        新增障礙物

        Args:
            config: 障礙物配置

        Returns:
            障礙物 ID（索引）

        Raises:
            RuntimeError: 超過最大數量
        """
        if self.n_obstacles >= self.max_obstacles:
            raise RuntimeError(f"Cannot add more obstacles (max={self.max_obstacles})")

        obs_id = self.n_obstacles
        self.n_obstacles += 1

        # 寫入資料
        obstacle_type_np = np.array([config.obstacle_type], dtype=np.int32)
        obstacle_pos_np = config.position.astype(np.float32)
        obstacle_params_np = config.params.astype(np.float32)
        obstacle_strength_np = np.array([config.strength], dtype=np.float32)
        obstacle_decay_np = np.array([config.decay_length], dtype=np.float32)
        obstacle_active_np = np.array([1], dtype=np.int32)

        # 使用 from_numpy 寫入單個元素
        self.obstacle_type[obs_id] = obstacle_type_np[0]
        self.obstacle_pos[obs_id] = obstacle_pos_np
        self.obstacle_params[obs_id] = obstacle_params_np
        self.obstacle_strength[obs_id] = obstacle_strength_np[0]
        self.obstacle_decay[obs_id] = obstacle_decay_np[0]
        self.obstacle_active[obs_id] = obstacle_active_np[0]

        return obs_id

    def remove_obstacle(self, obs_id: int):
        """移除障礙物（標記為 inactive）"""
        if 0 <= obs_id < self.n_obstacles:
            self.obstacle_active[obs_id] = 0

    def update_obstacle_position(self, obs_id: int, new_pos: np.ndarray):
        """更新障礙物位置（支援動態障礙物）"""
        if 0 <= obs_id < self.n_obstacles:
            self.obstacle_pos[obs_id] = new_pos.astype(np.float32)

    @ti.func
    def sdf_sphere(
        self, p: ti.math.vec3, center: ti.math.vec3, radius: ti.f32
    ) -> ti.f32:
        """球體的 SDF（Signed Distance Field）"""
        return (p - center).norm() - radius

    @ti.func
    def sdf_box(
        self, p: ti.math.vec3, center: ti.math.vec3, half_extents: ti.math.vec3
    ) -> ti.f32:
        """長方體的 SDF（軸對齊）"""
        q = ti.abs(p - center) - half_extents
        outside_dist = ti.max(q, 0.0).norm()
        inside_dist = ti.min(ti.max(q.x, ti.max(q.y, q.z)), 0.0)
        return outside_dist + inside_dist

    @ti.func
    def sdf_cylinder(
        self,
        p: ti.math.vec3,
        center: ti.math.vec3,
        radius: ti.f32,
        half_height: ti.f32,
    ) -> ti.f32:
        """圓柱體的 SDF（沿 z 軸）"""
        # 分解為 xy 平面圓 + z 軸高度
        p_rel = p - center
        d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
        d_z = ti.abs(p_rel.z) - half_height

        # 外部距離
        outside_dist = ti.sqrt(ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2)
        # 內部距離
        inside_dist = ti.min(ti.max(d_xy, d_z), 0.0)

        return outside_dist + inside_dist

    @ti.func
    def compute_obstacle_distance(self, p: ti.math.vec3, obs_id: ti.i32) -> ti.f32:
        """
        計算點 p 到障礙物的最短距離（使用 SDF）

        Returns:
            距離（正數 = 在外部，負數 = 在內部）
        """
        obs_type = self.obstacle_type[obs_id]
        center = self.obstacle_pos[obs_id]
        params = self.obstacle_params[obs_id]

        distance = 0.0

        if obs_type == 0:  # SPHERE
            radius = params[0]
            distance = self.sdf_sphere(p, center, radius)
        elif obs_type == 1:  # BOX
            half_extents = ti.Vector([params[0], params[1], params[2]])
            distance = self.sdf_box(p, center, half_extents)
        elif obs_type == 2:  # CYLINDER
            radius = params[0]
            half_height = params[1] * 0.5
            distance = self.sdf_cylinder(p, center, radius, half_height)

        return distance

    @ti.func
    def compute_obstacle_force(self, p: ti.math.vec3, obs_id: ti.i32) -> ti.math.vec3:
        """
        計算障礙物對點 p 的排斥力

        機制：
            F = -k * exp(-d/d0) * n
            其中 d = 距離，n = 法向量（指向遠離障礙物）

        Returns:
            排斥力向量
        """
        force = ti.Vector([0.0, 0.0, 0.0])

        if self.obstacle_active[obs_id] == 1:
            center = self.obstacle_pos[obs_id]
            strength = self.obstacle_strength[obs_id]
            decay = self.obstacle_decay[obs_id]

            # 計算距離（使用數值梯度近似法向量）
            eps = 1e-3
            d0 = self.compute_obstacle_distance(p, obs_id)

            # 只在接近障礙物時施加力（d < 3 * decay）
            if d0 < 3.0 * decay:
                # 計算梯度（法向量）
                dx = (
                    self.compute_obstacle_distance(
                        p + ti.Vector([eps, 0.0, 0.0]), obs_id
                    )
                    - d0
                )
                dy = (
                    self.compute_obstacle_distance(
                        p + ti.Vector([0.0, eps, 0.0]), obs_id
                    )
                    - d0
                )
                dz = (
                    self.compute_obstacle_distance(
                        p + ti.Vector([0.0, 0.0, eps]), obs_id
                    )
                    - d0
                )

                normal = ti.Vector([dx, dy, dz]) / eps
                norm = normal.norm()

                if norm > 1e-6:
                    normal = normal / norm
                    # 指數衰減排斥力
                    magnitude = strength * ti.exp(-d0 / decay)
                    force = magnitude * normal

        return force

    def get_obstacle_info(self, obs_id: int) -> dict:
        """獲取障礙物資訊"""
        if 0 <= obs_id < self.n_obstacles:
            return {
                "type": ObstacleType(self.obstacle_type[obs_id]),
                "position": self.obstacle_pos[obs_id].to_numpy(),
                "params": self.obstacle_params[obs_id].to_numpy(),
                "strength": self.obstacle_strength[obs_id],
                "decay": self.obstacle_decay[obs_id],
                "active": bool(self.obstacle_active[obs_id]),
            }
        return None

    def get_all_obstacles(self) -> List[dict]:
        """獲取所有障礙物資訊"""
        return [self.get_obstacle_info(i) for i in range(self.n_obstacles)]

    # ========================================================================
    # Testing Kernels (Python-callable versions)
    # ========================================================================
    @ti.kernel
    def compute_obstacle_distance_kernel(
        self, p: ti.types.vector(3, ti.f32), obs_id: ti.i32
    ) -> ti.f32:
        """
        [Python-callable] 計算點 p 到障礙物的距離

        Args:
            p: 測試點位置
            obs_id: 障礙物 ID

        Returns:
            距離
        """
        obs_type = self.obstacle_type[obs_id]
        center = self.obstacle_pos[obs_id]
        params = self.obstacle_params[obs_id]

        distance = 0.0

        if obs_type == 0:  # SPHERE
            radius = params[0]
            distance = (p - center).norm() - radius
        elif obs_type == 1:  # BOX
            half_extents = ti.Vector([params[0], params[1], params[2]])
            q = ti.abs(p - center) - half_extents
            outside_dist = ti.max(q, 0.0).norm()
            inside_dist = ti.min(ti.max(q.x, ti.max(q.y, q.z)), 0.0)
            distance = outside_dist + inside_dist
        elif obs_type == 2:  # CYLINDER
            radius = params[0]
            half_height = params[1] * 0.5
            p_rel = p - center
            d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
            d_z = ti.abs(p_rel.z) - half_height
            outside_dist = ti.sqrt(ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2)
            inside_dist = ti.min(ti.max(d_xy, d_z), 0.0)
            distance = outside_dist + inside_dist

        return distance

    @ti.kernel
    def compute_obstacle_force_test_kernel(
        self, p: ti.types.vector(3, ti.f32), obs_id: ti.i32, result: ti.types.ndarray()
    ):
        """
        [Python-callable] 計算障礙物力（結果寫入 ndarray）

        注意：這是測試用 kernel，不要與 @ti.func 版本混淆
        從 flocking kernel 內部呼叫時會使用 @ti.func 版本（Line 190-244）

        Args:
            p: 測試點位置
            obs_id: 障礙物 ID
            result: 輸出陣列 (3,)
        """
        force = ti.Vector([0.0, 0.0, 0.0])

        if self.obstacle_active[obs_id] == 1:
            center = self.obstacle_pos[obs_id]
            strength = self.obstacle_strength[obs_id]
            decay = self.obstacle_decay[obs_id]

            # 計算距離（直接複製 SDF 邏輯，避免呼叫其他 kernel）
            obs_type = self.obstacle_type[obs_id]
            params = self.obstacle_params[obs_id]
            eps = 1e-3

            # 先宣告 d0（Taichi 要求）
            d0 = 0.0

            # 計算 d0
            if obs_type == 0:  # SPHERE
                radius = params[0]
                d0 = (p - center).norm() - radius
            elif obs_type == 1:  # BOX
                half_extents = ti.Vector([params[0], params[1], params[2]])
                q = ti.abs(p - center) - half_extents
                outside_dist = ti.max(q, 0.0).norm()
                inside_dist = ti.min(ti.max(q.x, ti.max(q.y, q.z)), 0.0)
                d0 = outside_dist + inside_dist
            elif obs_type == 2:  # CYLINDER
                radius = params[0]
                half_height = params[1] * 0.5
                p_rel = p - center
                d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
                d_z = ti.abs(p_rel.z) - half_height
                outside_dist = ti.sqrt(ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2)
                inside_dist = ti.min(ti.max(d_xy, d_z), 0.0)
                d0 = outside_dist + inside_dist
            else:
                d0 = 999.0

            if d0 < 3.0 * decay:
                # 計算梯度（法向量） - 使用相同的內聯邏輯
                # dx
                p_dx = p + ti.Vector([eps, 0.0, 0.0])
                if obs_type == 0:
                    radius = params[0]
                    d_dx = (p_dx - center).norm() - radius
                elif obs_type == 1:
                    half_extents = ti.Vector([params[0], params[1], params[2]])
                    q = ti.abs(p_dx - center) - half_extents
                    d_dx = ti.max(q, 0.0).norm() + ti.min(
                        ti.max(q.x, ti.max(q.y, q.z)), 0.0
                    )
                elif obs_type == 2:
                    radius = params[0]
                    half_height = params[1] * 0.5
                    p_rel = p_dx - center
                    d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
                    d_z = ti.abs(p_rel.z) - half_height
                    d_dx = ti.sqrt(
                        ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2
                    ) + ti.min(ti.max(d_xy, d_z), 0.0)
                else:
                    d_dx = d0

                # dy
                p_dy = p + ti.Vector([0.0, eps, 0.0])
                if obs_type == 0:
                    radius = params[0]
                    d_dy = (p_dy - center).norm() - radius
                elif obs_type == 1:
                    half_extents = ti.Vector([params[0], params[1], params[2]])
                    q = ti.abs(p_dy - center) - half_extents
                    d_dy = ti.max(q, 0.0).norm() + ti.min(
                        ti.max(q.x, ti.max(q.y, q.z)), 0.0
                    )
                elif obs_type == 2:
                    radius = params[0]
                    half_height = params[1] * 0.5
                    p_rel = p_dy - center
                    d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
                    d_z = ti.abs(p_rel.z) - half_height
                    d_dy = ti.sqrt(
                        ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2
                    ) + ti.min(ti.max(d_xy, d_z), 0.0)
                else:
                    d_dy = d0

                # dz
                p_dz = p + ti.Vector([0.0, 0.0, eps])
                if obs_type == 0:
                    radius = params[0]
                    d_dz = (p_dz - center).norm() - radius
                elif obs_type == 1:
                    half_extents = ti.Vector([params[0], params[1], params[2]])
                    q = ti.abs(p_dz - center) - half_extents
                    d_dz = ti.max(q, 0.0).norm() + ti.min(
                        ti.max(q.x, ti.max(q.y, q.z)), 0.0
                    )
                elif obs_type == 2:
                    radius = params[0]
                    half_height = params[1] * 0.5
                    p_rel = p_dz - center
                    d_xy = ti.sqrt(p_rel.x * p_rel.x + p_rel.y * p_rel.y) - radius
                    d_z = ti.abs(p_rel.z) - half_height
                    d_dz = ti.sqrt(
                        ti.max(d_xy, 0.0) ** 2 + ti.max(d_z, 0.0) ** 2
                    ) + ti.min(ti.max(d_xy, d_z), 0.0)
                else:
                    d_dz = d0

                dx = d_dx - d0
                dy = d_dy - d0
                dz = d_dz - d0

                normal = ti.Vector([dx, dy, dz]) / eps
                norm = normal.norm()

                if norm > 1e-6:
                    normal = normal / norm
                    magnitude = strength * ti.exp(-d0 / decay)
                    force = magnitude * normal

        result[0] = force.x
        result[1] = force.y
        result[2] = force.z

    def compute_obstacle_force_py(self, p: np.ndarray, obs_id: int) -> np.ndarray:
        """
        [Python-callable wrapper] 計算障礙物力（用於測試）

        注意：這是 Python 介面，僅供測試使用
        從 Taichi kernel 內部不可呼叫此函式！

        Args:
            p: 測試點位置 (3,)
            obs_id: 障礙物 ID

        Returns:
            力向量 (3,)
        """
        result = np.zeros(3, dtype=np.float32)
        self.compute_obstacle_force_test_kernel(p.astype(np.float32), obs_id, result)
        return result


# ============================================================================
# Helper Functions
# ============================================================================
def create_sphere_obstacle(
    center: Tuple[float, float, float], radius: float, strength: float = 10.0
) -> ObstacleConfig:
    """創建球體障礙物"""
    return ObstacleConfig(
        obstacle_type=ObstacleType.SPHERE,
        position=np.array(center, dtype=np.float32),
        params=np.array([radius, 0, 0, 0], dtype=np.float32),
        strength=strength,
    )


def create_box_obstacle(
    center: Tuple[float, float, float],
    half_extents: Tuple[float, float, float],
    strength: float = 10.0,
) -> ObstacleConfig:
    """創建長方體障礙物"""
    return ObstacleConfig(
        obstacle_type=ObstacleType.BOX,
        position=np.array(center, dtype=np.float32),
        params=np.array(
            [half_extents[0], half_extents[1], half_extents[2], 0], dtype=np.float32
        ),
        strength=strength,
    )


def create_cylinder_obstacle(
    center: Tuple[float, float, float],
    radius: float,
    height: float,
    strength: float = 10.0,
) -> ObstacleConfig:
    """創建圓柱體障礙物"""
    return ObstacleConfig(
        obstacle_type=ObstacleType.CYLINDER,
        position=np.array(center, dtype=np.float32),
        params=np.array([radius, height, 0, 0], dtype=np.float32),
        strength=strength,
    )
