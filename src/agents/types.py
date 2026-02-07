"""
Agent Types and Profiles
定義 Agent 的行為類型與特徵參數
"""

from enum import IntEnum
from dataclasses import dataclass


class AgentType(IntEnum):
    """Agent 行為類型"""

    FOLLOWER = 0  # 追隨者：強對齊、低 noise、標準速度
    EXPLORER = 1  # 探索者：弱對齊、高 noise、快速
    LEADER = 2  # 領導者：中對齊、中 noise、快速、目標導向
    PREDATOR = 3  # 掠食者：極快速度、追捕其他 agents、獨行


@dataclass
class AgentTypeProfile:
    """Agent 類型的行為特徵"""

    name: str
    beta: float  # 對齊強度
    eta: float  # Vicsek noise 強度
    v0: float  # 目標速度
    mass: float  # 質量
    goal_strength: float = 0.0  # 目標導向強度（0 = 無目標）
    hunt_range: float = 20.0  # 追捕範圍（僅用於掠食者）
    attack_range: float = 2.0  # 攻擊範圍（僅用於掠食者）


# 預設類型 profiles
DEFAULT_PROFILES = {
    AgentType.FOLLOWER: AgentTypeProfile(
        name="Follower", beta=1.5, eta=0.05, v0=1.0, mass=1.0, goal_strength=0.0
    ),
    AgentType.EXPLORER: AgentTypeProfile(
        name="Explorer", beta=0.5, eta=0.3, v0=1.3, mass=0.8, goal_strength=0.0
    ),
    AgentType.LEADER: AgentTypeProfile(
        name="Leader", beta=1.0, eta=0.15, v0=1.4, mass=1.2, goal_strength=2.0
    ),
    AgentType.PREDATOR: AgentTypeProfile(
        name="Predator",
        beta=0.0,  # 不對齊（獨行）
        eta=0.1,  # 低 noise（專注追捕）
        v0=1.3,  # 快速但不過度（原 1.8 → 1.3，比 Explorer 快一點）
        mass=1.5,  # 較重（攻擊力強）
        goal_strength=0.0,  # 不追目標點
        hunt_range=20.0,  # 追捕範圍
        attack_range=2.0,  # 攻擊範圍
    ),
}
