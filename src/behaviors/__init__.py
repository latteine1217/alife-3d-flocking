"""
Behavior Modules for Heterogeneous Flocking System

提供可組合的行為模組：
    • ForagingBehaviorMixin: 覓食與能量管理
    • PredationBehaviorMixin: 掠食與獵捕行為
"""

from .foraging import ForagingBehaviorMixin
from .predation import PredationBehaviorMixin

__all__ = ["ForagingBehaviorMixin", "PredationBehaviorMixin"]
