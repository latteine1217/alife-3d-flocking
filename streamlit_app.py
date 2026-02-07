"""
Streamlit Dashboard for Heterogeneous Flocking Simulation

互動式 3D 集群模擬儀表板
- 即時參數調整
- Plotly 3D 互動視覺化
- 支援 2D/3D/異質性系統
- 覓食、障礙物、群組偵測整合
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import time
from typing import Optional, Dict, Any

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import taichi as ti

from flocking_2d import Flocking2D
from flocking_3d import Flocking3D, FlockingParams
from flocking_heterogeneous import (
    HeterogeneousFlocking3D,
    AgentType,
    AgentTypeProfile,
)
from obstacles import ObstacleConfig
from resources import create_resource, create_renewable_resource

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Flocking Simulation Dashboard",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Session State Initialization
# ============================================================================


def init_session_state():
    """初始化 session state"""
    if "system" not in st.session_state:
        st.session_state.system = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "step_count" not in st.session_state:
        st.session_state.step_count = 0
    if "fps_history" not in st.session_state:
        st.session_state.fps_history = []
    if "last_params" not in st.session_state:
        st.session_state.last_params = None
    if "ti_initialized" not in st.session_state:
        # 初始化 Taichi（只執行一次）
        ti.init(arch=ti.gpu, random_seed=42)
        st.session_state.ti_initialized = True


# ============================================================================
# System Creation
# ============================================================================


def create_system(
    system_type: str,
    N: int,
    params: FlockingParams,
    agent_config: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    創建模擬系統

    Args:
        system_type: "2D" / "3D" / "Heterogeneous"
        N: Agent 數量
        params: 物理參數
        agent_config: 異質性配置

    Returns:
        系統實例
    """
    if system_type == "2D":
        system = Flocking2D(N=N, params=params)
    elif system_type == "3D":
        system = Flocking3D(N=N, params=params)
    elif system_type == "Heterogeneous":
        # 建立 agent types
        if agent_config is None:
            agent_types = [AgentType.EXPLORER] * N
        else:
            n_explorer = int(N * agent_config["explorer_ratio"])
            n_follower = int(N * agent_config["follower_ratio"])
            n_leader = N - n_explorer - n_follower

            agent_types = (
                [AgentType.EXPLORER] * n_explorer
                + [AgentType.FOLLOWER] * n_follower
                + [AgentType.LEADER] * n_leader
            )

        system = HeterogeneousFlocking3D(
            N=N,
            params=params,
            agent_types=agent_types,
            enable_fov=agent_config.get("enable_fov", True),
            fov_angle=agent_config.get("fov_angle", 120.0),
            max_obstacles=agent_config.get("max_obstacles", 10),
            max_resources=agent_config.get("max_resources", 5),
        )

        # 設定 Leaders 的目標
        if agent_config.get("enable_goals", False):
            leader_indices = [
                i for i, t in enumerate(agent_types) if t == AgentType.LEADER
            ]
            if len(leader_indices) > 0:
                goal_pos = agent_config.get("goal_position", [10.0, 10.0, 10.0])
                goals = np.tile(goal_pos, (len(leader_indices), 1))
                system.set_goals(goals, leader_indices)

        # 新增資源
        if agent_config.get("enable_resources", False):
            for res_cfg in agent_config.get("resources", []):
                system.add_resource(res_cfg)

        # 新增障礙物
        if agent_config.get("enable_obstacles", False):
            for obs_cfg in agent_config.get("obstacles", []):
                system.add_obstacle(obs_cfg)

    else:
        raise ValueError(f"Unknown system type: {system_type}")

    # 初始化位置
    system.initialize(box_size=5.0, seed=42)

    return system


# ============================================================================
# Visualization
# ============================================================================


def create_3d_plot(system, show_velocity: bool = False, show_energy: bool = False):
    """
    創建 Plotly 3D 圖表

    Args:
        system: 模擬系統
        show_velocity: 是否顯示速度向量
        show_energy: 是否用能量著色（僅異質性系統）
    """
    x_np = system.x.to_numpy()
    v_np = system.v.to_numpy()

    # 基礎顏色
    if show_energy and hasattr(system, "get_agent_energies"):
        energies = system.get_agent_energies()
        colors = energies
        colorscale = "RdYlGn"  # 紅-黃-綠
        colorbar_title = "Energy"
    else:
        # 根據速度大小著色
        speeds = np.linalg.norm(v_np, axis=1)
        colors = speeds
        colorscale = "Viridis"
        colorbar_title = "Speed"

    # 創建圖表
    fig = go.Figure()

    # Agent 散點圖
    fig.add_trace(
        go.Scatter3d(
            x=x_np[:, 0],
            y=x_np[:, 1],
            z=x_np[:, 2],
            mode="markers",
            marker=dict(
                size=4,
                color=colors,
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(title=colorbar_title),
            ),
            name="Agents",
        )
    )

    # 速度向量（可選）
    if show_velocity:
        # 採樣顯示（避免過度擁擠）
        sample_rate = max(1, len(x_np) // 50)
        x_sample = x_np[::sample_rate]
        v_sample = v_np[::sample_rate]

        for i in range(len(x_sample)):
            x_start = x_sample[i]
            x_end = x_start + v_sample[i] * 2.0  # 縮放顯示

            fig.add_trace(
                go.Scatter3d(
                    x=[x_start[0], x_end[0]],
                    y=[x_start[1], x_end[1]],
                    z=[x_start[2], x_end[2]],
                    mode="lines",
                    line=dict(color="yellow", width=2),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # 資源（如果有）
    if hasattr(system, "get_all_resources"):
        resources = system.get_all_resources()
        for res in resources:
            pos = res["position"]
            radius = res["radius"]
            amount = res["amount"]

            # 球體表面採樣
            u = np.linspace(0, 2 * np.pi, 20)
            v = np.linspace(0, np.pi, 10)
            x_sphere = radius * np.outer(np.cos(u), np.sin(v)) + pos[0]
            y_sphere = radius * np.outer(np.sin(u), np.sin(v)) + pos[1]
            z_sphere = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + pos[2]

            fig.add_trace(
                go.Surface(
                    x=x_sphere,
                    y=y_sphere,
                    z=z_sphere,
                    colorscale=[[0, "lightblue"], [1, "lightblue"]],
                    showscale=False,
                    opacity=0.3,
                    name=f"Resource (amt={amount:.0f})",
                )
            )

    # 障礙物（如果有）
    if hasattr(system, "get_all_obstacles"):
        obstacles = system.get_all_obstacles()
        for obs in obstacles:
            if obs["type"] == 0:  # Sphere
                pos = obs["position"]
                radius = obs["param1"]

                u = np.linspace(0, 2 * np.pi, 20)
                v = np.linspace(0, np.pi, 10)
                x_sphere = radius * np.outer(np.cos(u), np.sin(v)) + pos[0]
                y_sphere = radius * np.outer(np.sin(u), np.sin(v)) + pos[1]
                z_sphere = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + pos[2]

                fig.add_trace(
                    go.Surface(
                        x=x_sphere,
                        y=y_sphere,
                        z=z_sphere,
                        colorscale=[[0, "gray"], [1, "gray"]],
                        showscale=False,
                        opacity=0.5,
                        name="Obstacle",
                    )
                )

    # 佈局
    box_size = system.params.box_size
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-box_size / 2, box_size / 2], title="X"),
            yaxis=dict(range=[-box_size / 2, box_size / 2], title="Y"),
            zaxis=dict(range=[-box_size / 2, box_size / 2], title="Z"),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        height=600,
        showlegend=True,
    )

    return fig


def create_2d_plot(system, show_velocity: bool = False):
    """創建 Plotly 2D 圖表"""
    x_np = system.x.to_numpy()
    v_np = system.v.to_numpy()

    speeds = np.linalg.norm(v_np, axis=1)

    fig = go.Figure()

    # Agent 散點圖
    fig.add_trace(
        go.Scatter(
            x=x_np[:, 0],
            y=x_np[:, 1],
            mode="markers",
            marker=dict(
                size=6,
                color=speeds,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Speed"),
            ),
            name="Agents",
        )
    )

    # 速度向量
    if show_velocity:
        sample_rate = max(1, len(x_np) // 50)
        x_sample = x_np[::sample_rate]
        v_sample = v_np[::sample_rate]

        for i in range(len(x_sample)):
            x_start = x_sample[i]
            x_end = x_start + v_sample[i] * 2.0

            fig.add_trace(
                go.Scatter(
                    x=[x_start[0], x_end[0]],
                    y=[x_start[1], x_end[1]],
                    mode="lines",
                    line=dict(color="yellow", width=2),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # 佈局
    box_size = system.params.box_size
    fig.update_layout(
        xaxis=dict(range=[-box_size / 2, box_size / 2], title="X"),
        yaxis=dict(
            range=[-box_size / 2, box_size / 2],
            title="Y",
            scaleanchor="x",
            scaleratio=1,
        ),
        height=600,
        margin=dict(l=0, r=0, b=0, t=30),
    )

    return fig


# ============================================================================
# Statistics Display
# ============================================================================


def display_statistics(system, step_count: int, fps: float):
    """顯示統計資訊"""
    diag = system.compute_diagnostics()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Step", step_count)
        st.metric("FPS", f"{fps:.1f}")

    with col2:
        st.metric("Avg Speed", f"{diag['mean_speed']:.2f}")
        st.metric("Speed Std", f"{diag['std_speed']:.2f}")

    with col3:
        st.metric("Rg", f"{diag['Rg']:.2f}")
        st.metric("Polarization", f"{diag['polarization']:.3f}")

    # 異質性系統的額外資訊
    if hasattr(system, "get_agent_energies"):
        with col4:
            energies = system.get_agent_energies()
            st.metric("Avg Energy", f"{np.mean(energies):.1f}")
            st.metric("Min Energy", f"{np.min(energies):.1f}")

        with col5:
            targets = system.get_agent_targets()
            n_foraging = np.sum(targets >= 0)
            st.metric("Foraging", f"{n_foraging}/{len(targets)}")

            groups = system.get_all_groups()
            st.metric("Groups", len(groups))


# ============================================================================
# Main App
# ============================================================================


def main():
    init_session_state()

    st.title("🐦 Heterogeneous Flocking Simulation Dashboard")

    # ========================================================================
    # Sidebar - Controls
    # ========================================================================

    with st.sidebar:
        st.header("⚙️ Configuration")

        # 系統類型選擇
        system_type = st.selectbox(
            "System Type", ["3D", "Heterogeneous", "2D"], index=1
        )

        st.divider()

        # 基礎參數
        st.subheader("Basic Parameters")

        N = st.slider("Number of Agents (N)", 10, 500, 100, 10)

        col1, col2 = st.columns(2)
        with col1:
            dt = st.slider("Time Step (dt)", 0.001, 0.1, 0.05, 0.001, format="%.3f")
        with col2:
            steps_per_frame = st.slider("Steps per Frame", 1, 10, 1)

        st.divider()

        # 物理參數
        st.subheader("Physics Parameters")

        with st.expander("Morse Potential", expanded=False):
            Ca = st.slider("Attraction (Ca)", 0.0, 5.0, 1.5, 0.1)
            Cr = st.slider("Repulsion (Cr)", 0.0, 5.0, 2.0, 0.1)
            la = st.slider("Attraction length (la)", 0.5, 5.0, 2.5, 0.1)
            lr = st.slider("Repulsion length (lr)", 0.1, 2.0, 0.5, 0.1)
            rc = st.slider("Cutoff radius (rc)", 5.0, 30.0, 15.0, 1.0)

        with st.expander("Rayleigh Friction", expanded=False):
            alpha = st.slider("Friction (alpha)", 0.0, 5.0, 2.0, 0.1)
            v0 = st.slider("Target speed (v0)", 0.1, 3.0, 1.0, 0.1)

        with st.expander("Alignment & Noise", expanded=False):
            beta = st.slider("Alignment (beta)", 0.0, 3.0, 1.0, 0.1)
            eta = st.slider("Vicsek Noise (eta)", 0.0, 1.0, 0.0, 0.05)

        with st.expander("Boundary & Space", expanded=False):
            box_size = st.slider("Box Size", 20.0, 100.0, 50.0, 5.0)
            boundary_mode = st.selectbox(
                "Boundary Mode", ["PBC (0)", "Reflective (1)", "Absorbing (2)"]
            )
            boundary_mode_int = int(boundary_mode.split("(")[1][0])

        st.divider()

        # 異質性參數（僅 Heterogeneous）
        agent_config = None
        if system_type == "Heterogeneous":
            st.subheader("Heterogeneity Config")

            with st.expander("Agent Types", expanded=True):
                explorer_ratio = st.slider("Explorer Ratio", 0.0, 1.0, 0.3, 0.05)
                follower_ratio = st.slider("Follower Ratio", 0.0, 1.0, 0.5, 0.05)
                # Leader ratio = 1 - explorer - follower

                st.caption(f"Leader Ratio: {1.0 - explorer_ratio - follower_ratio:.2f}")

            with st.expander("Field of View", expanded=False):
                enable_fov = st.checkbox("Enable FOV", value=True)
                fov_angle = st.slider("FOV Angle (degrees)", 30, 360, 120, 10)

            with st.expander("Goal-Seeking", expanded=False):
                enable_goals = st.checkbox("Enable Goals", value=False)
                if enable_goals:
                    goal_x = st.slider("Goal X", -20.0, 20.0, 10.0, 1.0)
                    goal_y = st.slider("Goal Y", -20.0, 20.0, 10.0, 1.0)
                    goal_z = st.slider("Goal Z", -20.0, 20.0, 10.0, 1.0)
                    goal_position = [goal_x, goal_y, goal_z]
                else:
                    goal_position = [0.0, 0.0, 0.0]

            with st.expander("Resources", expanded=False):
                enable_resources = st.checkbox("Enable Resources", value=False)
                n_resources = 0
                resources = []
                if enable_resources:
                    n_resources = st.slider("Number of Resources", 1, 5, 1)
                    for i in range(n_resources):
                        st.caption(f"Resource {i + 1}")
                        col1, col2 = st.columns(2)
                        with col1:
                            res_x = st.number_input(
                                f"X_{i}", value=0.0, key=f"res_x_{i}"
                            )
                            res_y = st.number_input(
                                f"Y_{i}", value=0.0, key=f"res_y_{i}"
                            )
                        with col2:
                            res_z = st.number_input(
                                f"Z_{i}", value=0.0, key=f"res_z_{i}"
                            )
                            renewable = st.checkbox(f"Renewable_{i}", key=f"ren_{i}")

                        if renewable:
                            resources.append(
                                create_renewable_resource(
                                    position=(res_x, res_y, res_z),
                                    amount=100.0,
                                    radius=3.0,
                                    replenish_rate=2.0,
                                    max_amount=200.0,
                                )
                            )
                        else:
                            resources.append(
                                create_resource(
                                    position=(res_x, res_y, res_z),
                                    amount=100.0,
                                    radius=3.0,
                                )
                            )

            # 組裝 agent_config
            agent_config = {
                "explorer_ratio": explorer_ratio,
                "follower_ratio": follower_ratio,
                "enable_fov": enable_fov,
                "fov_angle": fov_angle,
                "enable_goals": enable_goals,
                "goal_position": goal_position,
                "enable_resources": enable_resources,
                "resources": resources,
                "enable_obstacles": False,  # 暫時不支援
                "obstacles": [],
                "max_obstacles": 10,
                "max_resources": 5,
            }

        st.divider()

        # 視覺化選項
        st.subheader("Visualization")
        show_velocity = st.checkbox("Show Velocity Vectors", value=False)
        show_energy = st.checkbox("Show Energy Colors", value=True)

        st.divider()

        # 模擬控制
        st.subheader("Simulation Control")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.system = None
                st.session_state.step_count = 0
                st.session_state.running = False
                st.rerun()

        with col2:
            if st.button(
                "▶️ Start" if not st.session_state.running else "⏸️ Pause",
                use_container_width=True,
            ):
                st.session_state.running = not st.session_state.running

    # ========================================================================
    # Main Panel - Visualization
    # ========================================================================

    # 建立參數物件
    params = FlockingParams(
        Ca=Ca,
        Cr=Cr,
        la=la,
        lr=lr,
        rc=rc,
        alpha=alpha,
        v0=v0,
        beta=beta,
        eta=eta,
        box_size=box_size,
        boundary_mode=boundary_mode_int,
    )

    # 檢查是否需要重新創建系統
    current_params = {
        "system_type": system_type,
        "N": N,
        "params": params.__dict__,
        "agent_config": agent_config,
    }

    if (
        st.session_state.system is None
        or st.session_state.last_params != current_params
    ):
        with st.spinner("Creating system..."):
            st.session_state.system = create_system(
                system_type, N, params, agent_config
            )
            st.session_state.last_params = current_params
            st.session_state.step_count = 0
            st.info(f"✅ System created: {system_type}, N={N}")

    system = st.session_state.system

    # 統計資訊
    fps = (
        np.mean(st.session_state.fps_history[-10:])
        if st.session_state.fps_history
        else 0.0
    )
    display_statistics(system, st.session_state.step_count, fps)

    st.divider()

    # 視覺化
    plot_placeholder = st.empty()

    # 模擬循環
    if st.session_state.running:
        start_time = time.time()

        # 執行多步
        for _ in range(steps_per_frame):
            system.step(dt)
            st.session_state.step_count += 1

        # 計算 FPS
        elapsed = time.time() - start_time
        current_fps = steps_per_frame / elapsed if elapsed > 0 else 0
        st.session_state.fps_history.append(current_fps)
        if len(st.session_state.fps_history) > 50:
            st.session_state.fps_history.pop(0)

        # 自動重新執行
        time.sleep(0.01)  # 小延遲避免過度刷新
        st.rerun()

    # 繪製圖表
    with plot_placeholder.container():
        if system_type == "2D":
            fig = create_2d_plot(system, show_velocity=show_velocity)
        else:
            fig = create_3d_plot(
                system, show_velocity=show_velocity, show_energy=show_energy
            )
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
