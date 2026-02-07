"""
Spatial 模組：空間加速結構與演算法

包含：
    • SpatialGridMixin: 空間網格加速結構（O(N) 鄰居查詢）
    • GroupDetectionMixin: 群組檢測演算法（Label Propagation）
"""

from .grid import SpatialGridMixin
from .group_detection import GroupDetectionMixin

__all__ = ["SpatialGridMixin", "GroupDetectionMixin"]
