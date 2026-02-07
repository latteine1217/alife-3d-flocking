"""
Perception Module

提供感知相關功能，包括視野限制（Field of View）與感知範圍計算。

模組：
    • fov.py: Field of View (FOV) 限制
"""

from .fov import PerceptionMixin

__all__ = ["PerceptionMixin"]
