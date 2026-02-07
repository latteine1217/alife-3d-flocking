"""
Field of View (FOV) Perception Module

提供視野限制功能，限制 agents 只能感知前方一定角度內的鄰居。

功能：
    • 可配置視野角度（預設 120 度）
    • 基於速度方向的視野檢查
    • 支援動態啟用/停用

使用方式：
    class MySystem(Flocking3D, PerceptionMixin):
        def __init__(self, N, params):
            super().__init__(N, params)
            self.init_perception(N, fov_angle=120.0, enable_fov=True)
"""

import taichi as ti
import numpy as np


@ti.data_oriented
class PerceptionMixin:
    """
    Field of View (FOV) Mixin

    提供視野限制功能，agents 只能看到前方一定角度內的鄰居。

    Fields:
        enable_fov: 是否啟用 FOV 限制
        fov_cos_angle: FOV 半角的 cos 值（用於快速計算）

    Methods:
        init_perception: 初始化感知系統
        is_in_fov: 檢查目標是否在視野內（@ti.func）
    """

    def init_perception(
        self, N: int, fov_angle: float = 120.0, enable_fov: bool = True
    ):
        """
        初始化感知系統

        Args:
            N: Agent 數量
            fov_angle: 視野角度（度數），範圍 [0, 180]
            enable_fov: 是否啟用 FOV 限制（False = 全方向視野）

        Notes:
            • fov_angle=120 表示左右各 60 度，總共 120 度視野
            • fov_angle=180 表示半球視野（只能看到前方）
            • enable_fov=False 則無視野限制（360 度）
        """
        self.enable_fov = enable_fov

        # 計算 FOV 半角的 cos 值（用於快速比較）
        # cos(angle) 單調遞減，所以 cos(60°) > cos(90°) > cos(120°)
        half_angle_rad = np.radians(fov_angle / 2.0)
        self.fov_cos_angle = np.cos(half_angle_rad)

        print(f"[PerceptionMixin] Initialized:")
        print(f"  FOV enabled: {enable_fov}")
        if enable_fov:
            print(f"  FOV angle: {fov_angle:.0f}° (half-angle: {fov_angle / 2:.0f}°)")
            print(f"  FOV cos threshold: {self.fov_cos_angle:.3f}")

    @ti.func
    def is_in_fov(self, vi: ti.math.vec3, rij: ti.math.vec3) -> ti.i32:
        """
        檢查目標是否在觀察者的視野內

        Args:
            vi: 觀察者的速度向量（視線方向）
            rij: 觀察者到目標的位移向量

        Returns:
            1 if 在視野內, 0 otherwise

        Algorithm:
            1. 計算速度方向與位移方向的夾角
            2. 若 cos(angle) >= cos(fov_half_angle)，則在視野內
            3. 特殊情況：速度為零時視為全方向可見

        Notes:
            • 使用 ti.static() 確保 enable_fov 在編譯時決定
            • 速度為零時（靜止 agent），視為全方向可見
            • rij 為零時（重疊），視為可見
        """
        in_fov = 1  # 預設為可見

        # 使用 ti.static 在編譯時決定是否檢查 FOV
        if ti.static(self.enable_fov):
            v_norm = vi.norm()
            r_norm = rij.norm()

            # 檢查向量長度是否有效
            if v_norm > 1e-6 and r_norm > 1e-6:
                # 計算 cos(angle) = (vi · rij) / (|vi| * |rij|)
                cos_angle = vi.dot(rij) / (v_norm * r_norm)

                # 在視野內當 cos(angle) >= cos(fov_half_angle)
                # 因為 cos 單調遞減，夾角越小 cos 越大
                if cos_angle < self.fov_cos_angle:
                    in_fov = 0
            else:
                # 速度為零或距離為零，視為在視野內
                in_fov = 1

        return in_fov

    @ti.func
    def is_in_fov_indexed(self, i: ti.i32, j: ti.i32, rij: ti.math.vec3) -> ti.i32:
        """
        檢查 agent j 是否在 agent i 的視野內（indexed 版本）

        Args:
            i: 觀察者 agent ID
            j: 目標 agent ID
            rij: i 到 j 的位移向量

        Returns:
            1 if 在視野內, 0 otherwise

        Notes:
            此版本假設 self.v 存在（繼承自 Flocking3D）
            適用於需要存取 agent velocity field 的場景
        """
        return self.is_in_fov(self.v[i], rij)
