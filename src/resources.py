"""
Resource System for Foraging Behavior

提供資源管理系統，支援 agents 的覓食行為。

資源類型：
    • 可消耗資源（Consumable）：agents 採集後減少
    • 可再生資源（Renewable）：隨時間自動補充

機制：
    • agents 搜尋最近的資源
    • 移動到資源位置
    • 在範圍內時消耗資源、增加能量
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import taichi as ti


@dataclass
class ResourceConfig:
    """資源配置"""

    position: np.ndarray  # (3,) 位置
    amount: float = 100.0  # 資源數量
    radius: float = 2.0  # 採集範圍
    replenish_rate: float = 0.0  # 補充率（每步）
    max_amount: float = 100.0  # 最大數量（用於再生資源）


@ti.data_oriented
class ResourceSystem:
    """
    資源系統

    功能：
        • 管理多個資源點
        • 計算 agent-resource 距離
        • 處理資源消耗與補充
    """

    def __init__(self, max_resources: int = 32):
        """
        初始化資源系統

        Args:
            max_resources: 最大資源數量
        """
        self.max_resources = max_resources
        self.n_resources = 0

        # Taichi fields
        self.resource_pos = ti.Vector.field(3, ti.f32, max_resources)
        self.resource_amount = ti.field(ti.f32, max_resources)
        self.resource_radius = ti.field(ti.f32, max_resources)
        self.resource_replenish_rate = ti.field(ti.f32, max_resources)
        self.resource_max_amount = ti.field(ti.f32, max_resources)
        self.resource_active = ti.field(ti.i32, max_resources)  # 0/1

        # 初始化為 inactive
        self.resource_active.fill(0)

    def add_resource(self, config: ResourceConfig) -> int:
        """
        新增資源

        Args:
            config: 資源配置

        Returns:
            資源 ID（索引）

        Raises:
            RuntimeError: 超過最大數量
        """
        if self.n_resources >= self.max_resources:
            raise RuntimeError(f"Cannot add more resources (max={self.max_resources})")

        res_id = self.n_resources
        self.n_resources += 1

        # 寫入資料
        self.resource_pos[res_id] = config.position.astype(np.float32)
        self.resource_amount[res_id] = config.amount
        self.resource_radius[res_id] = config.radius
        self.resource_replenish_rate[res_id] = config.replenish_rate
        self.resource_max_amount[res_id] = config.max_amount
        self.resource_active[res_id] = 1

        return res_id

    def remove_resource(self, res_id: int):
        """移除資源（標記為 inactive）"""
        if 0 <= res_id < self.n_resources:
            self.resource_active[res_id] = 0

    def update_resource_position(self, res_id: int, new_pos: np.ndarray):
        """更新資源位置（支援動態資源）"""
        if 0 <= res_id < self.n_resources:
            self.resource_pos[res_id] = new_pos.astype(np.float32)

    @ti.kernel
    def replenish_resources(self):
        """補充所有資源（按 replenish_rate）"""
        for i in self.resource_active:
            if self.resource_active[i] == 1:
                rate = self.resource_replenish_rate[i]
                if rate > 0.0:
                    new_amount = self.resource_amount[i] + rate
                    max_amt = self.resource_max_amount[i]
                    self.resource_amount[i] = ti.min(new_amount, max_amt)

    @ti.func
    def compute_distance_to_resource(
        self, p: ti.math.vec3, res_id: ti.i32, pbc_func
    ) -> ti.f32:
        """
        計算點 p 到資源的距離

        Args:
            p: 點位置
            res_id: 資源 ID
            pbc_func: PBC 距離函式（可選）

        Returns:
            距離
        """
        res_pos = self.resource_pos[res_id]
        # 這裡簡化處理，不考慮 PBC（可擴展）
        return (p - res_pos).norm()

    @ti.func
    def is_in_range(self, p: ti.math.vec3, res_id: ti.i32, pbc_func) -> ti.i32:
        """
        檢查點 p 是否在資源範圍內

        Args:
            p: 點位置
            res_id: 資源 ID
            pbc_func: PBC 距離函式

        Returns:
            1 = 在範圍內，0 = 不在
        """
        if self.resource_active[res_id] == 0:
            return 0

        distance = self.compute_distance_to_resource(p, res_id, pbc_func)
        radius = self.resource_radius[res_id]

        if distance < radius:
            return 1
        return 0

    @ti.kernel
    def consume_resource(self, res_id: ti.i32, amount: ti.f32) -> ti.f32:
        """
        消耗資源（從 Python 呼叫）

        Args:
            res_id: 資源 ID
            amount: 要消耗的數量

        Returns:
            實際消耗的數量（可能小於請求）
        """
        consumed = 0.0

        if self.resource_active[res_id] == 1:
            available = self.resource_amount[res_id]
            consumed = ti.min(amount, available)
            self.resource_amount[res_id] -= consumed

            # 若資源耗盡且無補充，標記為 inactive
            if (
                self.resource_amount[res_id] <= 0.0
                and self.resource_replenish_rate[res_id] <= 0.0
            ):
                self.resource_active[res_id] = 0

        return consumed

    def get_resource_info(self, res_id: int) -> Optional[dict]:
        """獲取資源資訊"""
        if 0 <= res_id < self.n_resources:
            return {
                "res_id": res_id,
                "position": self.resource_pos[res_id].to_numpy(),
                "amount": self.resource_amount[res_id],
                "radius": self.resource_radius[res_id],
                "replenish_rate": self.resource_replenish_rate[res_id],
                "max_amount": self.resource_max_amount[res_id],
                "active": bool(self.resource_active[res_id]),
            }
        return None

    def get_all_resources(self) -> List[dict]:
        """獲取所有資源資訊"""
        return [
            self.get_resource_info(i)
            for i in range(self.n_resources)
            if self.resource_active[i] == 1
        ]


# ============================================================================
# Helper Functions
# ============================================================================
def create_resource(
    position: Tuple[float, float, float],
    amount: float = 100.0,
    radius: float = 2.0,
    replenish_rate: float = 0.0,
) -> ResourceConfig:
    """創建資源配置"""
    return ResourceConfig(
        position=np.array(position, dtype=np.float32),
        amount=amount,
        radius=radius,
        replenish_rate=replenish_rate,
        max_amount=amount,
    )


def create_renewable_resource(
    position: Tuple[float, float, float],
    amount: float = 100.0,
    radius: float = 2.0,
    replenish_rate: float = 1.0,
    max_amount: float = None,
) -> ResourceConfig:
    """創建可再生資源"""
    if max_amount is None:
        max_amount = amount  # 預設最大值等於初始值

    return ResourceConfig(
        position=np.array(position, dtype=np.float32),
        amount=amount,
        radius=radius,
        replenish_rate=replenish_rate,
        max_amount=max_amount,
    )
