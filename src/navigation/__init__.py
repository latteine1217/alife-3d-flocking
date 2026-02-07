"""
Navigation Module - Goal-seeking Behaviors

提供目標導向行為（Goal-seeking）的功能模組。

模組內容：
    • NavigationMixin: 目標導向行為 Mixin
    • 支援 PBC-aware 目標導向力計算
    • 可配置目標強度（per-agent）
"""

from .goal_seeking import NavigationMixin

__all__ = ["NavigationMixin"]
