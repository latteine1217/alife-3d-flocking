"""
V2 專用增強視覺化系統

Features:
    1. 支援 PBC（週期邊界）視覺化
    2. 粒子速度著色（藍→綠→紅）
    3. 速度向量顯示（黃色箭頭）
    4. 對齊力場可視化
    5. 即時診斷 HUD
    6. 互動控制（暫停、重置、相機）
    7. Box 邊界顯示
"""

import taichi as ti
import numpy as np
import sys

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
from flocking_3d import Flocking3D, OptimizedFlockingV2, FlockingParams


@ti.data_oriented
class V2EnhancedVisualizer:
    """
    專為 OptimizedFlockingV2 設計的視覺化器

    特色：
        - PBC 視覺化（顯示 box 邊界）
        - 對齊力場可視化
        - 豐富的即時診斷
    """

    def __init__(
        self,
        system: OptimizedFlockingV2,
        window_size: tuple = (1400, 1000),
        show_velocity: bool = True,
        show_box: bool = True,
        show_alignment_field: bool = False,
    ):
        self.system = system
        self.show_velocity = show_velocity
        self.show_box = show_box
        self.show_alignment_field = show_alignment_field

        # 建立視窗
        self.window = ti.ui.Window(
            "Optimized Flocking v2 - Enhanced Visualization",
            window_size,
            vsync=True,
        )
        self.canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.camera = ti.ui.Camera()

        # 初始相機位置（俯視角度）
        box_center = self.system.params.box_size / 2.0
        cam_dist = self.system.params.box_size * 1.2
        self.camera.position(
            box_center, box_center + cam_dist * 0.6, box_center + cam_dist * 0.4
        )
        self.camera.lookat(box_center, box_center, box_center)

        # 控制狀態
        self.paused = False
        self.step_count = 0
        self.show_info = True

    def render_particles(self):
        """渲染粒子（根據速度著色）"""
        x_np = self.system.x.to_numpy()
        v_np = self.system.v.to_numpy()
        speed = np.linalg.norm(v_np, axis=1)

        # 速度映射到顏色（藍→綠→紅）
        v_target = self.system.params.v0
        v_min, v_max = v_target * 0.5, v_target * 1.5
        speed_norm = np.clip((speed - v_min) / (v_max - v_min), 0, 1)

        # RGB 插值
        colors = np.zeros((self.system.N, 3), dtype=np.float32)
        colors[:, 0] = speed_norm  # R（快）
        colors[:, 1] = 1.0 - np.abs(speed_norm - 0.5) * 2  # G（中）
        colors[:, 2] = 1.0 - speed_norm  # B（慢）

        # 轉換為 Taichi field
        color_field = ti.Vector.field(3, dtype=ti.f32, shape=self.system.N)
        color_field.from_numpy(colors)

        # 粒子大小根據 N 自適應
        radius = max(0.05, min(0.15, 5.0 / self.system.N**0.5))
        self.scene.particles(self.system.x, radius=radius, per_vertex_color=color_field)

    def render_velocity_vectors(self):
        """渲染速度向量（箭頭）"""
        x_np = self.system.x.to_numpy()
        v_np = self.system.v.to_numpy()

        # 向量長度縮放（根據 box_size）
        scale = self.system.params.box_size * 0.015
        endpoints = x_np + v_np * scale

        # 建立線段 field
        N = self.system.N
        lines = ti.Vector.field(3, dtype=ti.f32, shape=N * 2)

        lines_np = np.empty((N * 2, 3), dtype=np.float32)
        lines_np[0::2] = x_np
        lines_np[1::2] = endpoints
        lines.from_numpy(lines_np)

        # 繪製線段（亮黃色）
        self.scene.lines(lines, width=2.0, color=(1.0, 1.0, 0.3))

    def render_box(self):
        """渲染 PBC 邊界框"""
        if not self.show_box:
            return

        box_size = self.system.params.box_size

        # 定義 12 條邊（立方體）
        edges = [
            # 底面
            ([0, 0, 0], [box_size, 0, 0]),
            ([box_size, 0, 0], [box_size, box_size, 0]),
            ([box_size, box_size, 0], [0, box_size, 0]),
            ([0, box_size, 0], [0, 0, 0]),
            # 頂面
            ([0, 0, box_size], [box_size, 0, box_size]),
            ([box_size, 0, box_size], [box_size, box_size, box_size]),
            ([box_size, box_size, box_size], [0, box_size, box_size]),
            ([0, box_size, box_size], [0, 0, box_size]),
            # 垂直邊
            ([0, 0, 0], [0, 0, box_size]),
            ([box_size, 0, 0], [box_size, 0, box_size]),
            ([box_size, box_size, 0], [box_size, box_size, box_size]),
            ([0, box_size, 0], [0, box_size, box_size]),
        ]

        # 轉換為 Taichi field
        n_edges = len(edges)
        lines = ti.Vector.field(3, dtype=ti.f32, shape=n_edges * 2)

        lines_np = np.empty((n_edges * 2, 3), dtype=np.float32)
        for i, (p1, p2) in enumerate(edges):
            lines_np[2 * i] = p1
            lines_np[2 * i + 1] = p2
        lines.from_numpy(lines_np)

        # 繪製邊界（半透明白色）
        self.scene.lines(lines, width=1.5, color=(0.8, 0.8, 0.8))

    def render_alignment_field(self):
        """渲染對齊力場（可選）"""
        if not self.show_alignment_field:
            return

        # TODO: 實作網格化的對齊向量場
        # 可以採樣空間中若干點，計算局部平均速度
        pass

    def print_hud(self):
        """打印 HUD 資訊到控制台"""
        if not self.show_info or self.step_count % 50 != 0:
            return

        diagnostics = self.system.compute_diagnostics()

        print("\n" + "=" * 70)
        print(
            f"  Step: {self.step_count:<10}  Status: {'PAUSED' if self.paused else 'RUNNING'}"
        )
        print("=" * 70)
        print(f"  System Size (N):      {self.system.N}")
        print(f"  Box Size:             {self.system.params.box_size:.1f}")
        print(f"  PBC Enabled:          {self.system.params.use_pbc}")
        print("-" * 70)
        print(
            f"  Mean Speed:           {diagnostics['mean_speed']:.4f} ± {diagnostics['std_speed']:.4f}"
        )
        print(f"  Target Speed (v0):    {self.system.params.v0:.4f}")
        print(
            f"  Speed Error:          {abs(diagnostics['mean_speed'] - self.system.params.v0):.4f}"
        )
        print("-" * 70)
        print(f"  Radius of Gyration:   {diagnostics['Rg']:.3f}")
        print(f"  Polarization:         {diagnostics['polarization']:.4f}")
        print("-" * 70)
        print("  Parameters:")
        print(
            f"    Morse:   Ca={self.system.params.Ca:.2f}, Cr={self.system.params.Cr:.2f}"
        )
        print(
            f"             la={self.system.params.la:.2f}, lr={self.system.params.lr:.2f}, rc={self.system.params.rc:.1f}"
        )
        print(
            f"    Rayleigh: alpha={self.system.params.alpha:.2f}, v0={self.system.params.v0:.2f}"
        )
        print(f"    Alignment: beta={self.system.params.beta:.2f}")
        print("=" * 70)

    def handle_input(self):
        """處理鍵盤輸入"""
        if self.window.get_event(ti.ui.PRESS):
            key = self.window.event.key

            if key == ti.ui.SPACE:
                self.paused = not self.paused
                print(f"\n>>> {'⏸ 暫停' if self.paused else '▶ 恢復'}")

            elif key == "r":
                print("\n>>> 🔄 重置系統...")
                seed = np.random.randint(0, 100000)
                self.system.initialize(
                    box_size=self.system.params.box_size * 0.1, seed=seed
                )
                self.step_count = 0
                print(f"    新種子: {seed}")

            elif key == "i":
                self.show_info = not self.show_info
                print(f"\n>>> {'顯示' if self.show_info else '隱藏'} HUD 資訊")

            elif key == "v":
                self.show_velocity = not self.show_velocity
                print(f"\n>>> 速度向量: {'ON' if self.show_velocity else 'OFF'}")

            elif key == "b":
                self.show_box = not self.show_box
                print(f"\n>>> Box 邊界: {'ON' if self.show_box else 'OFF'}")

            elif key == ti.ui.ESCAPE:
                print("\n>>> 退出視覺化")
                self.window.running = False

    def run(self, steps: int = 0, dt: float = 0.01, log_every: int = 100):
        """
        執行視覺化模擬

        Args:
            steps: 最大步數（0 = 無限循環）
            dt: 時間步長
            log_every: 診斷輸出頻率
        """
        print("\n" + "=" * 70)
        print("  V2 Enhanced Visualization - Controls")
        print("=" * 70)
        print("  [SPACE]  暫停/恢復")
        print("  [R]      重置模擬（隨機種子）")
        print("  [I]      顯示/隱藏 HUD 資訊")
        print("  [V]      切換速度向量顯示")
        print("  [B]      切換 Box 邊界顯示")
        print("  [RMB]    旋轉相機（拖曳）")
        print("  [Scroll] 縮放")
        print("  [ESC]    退出")
        print("=" * 70)
        print(f"\n>>> 開始模擬（N={self.system.N}, dt={dt}）\n")

        while self.window.running:
            # 輸入處理
            self.handle_input()

            # 模擬步進
            if not self.paused:
                self.system.step(dt)
                self.step_count += 1

                # 達到最大步數
                if steps > 0 and self.step_count >= steps:
                    print(f"\n>>> 達到最大步數 {steps}，模擬結束。")
                    break

            # HUD 輸出
            self.print_hud()

            # === 渲染 ===
            self.camera.track_user_inputs(
                self.window, movement_speed=0.5, hold_key=ti.ui.RMB
            )
            self.scene.set_camera(self.camera)

            # 光照設置
            self.scene.ambient_light((0.4, 0.4, 0.4))
            self.scene.point_light(
                pos=(
                    self.system.params.box_size * 1.5,
                    self.system.params.box_size * 1.5,
                    self.system.params.box_size * 1.5,
                ),
                color=(1, 1, 1),
            )

            # 繪製元素
            self.render_particles()

            if self.show_velocity:
                self.render_velocity_vectors()

            if self.show_box:
                self.render_box()

            if self.show_alignment_field:
                self.render_alignment_field()

            # 顯示
            self.canvas.scene(self.scene)
            self.window.show()

        # 最終報告
        self.print_final_report()

    def print_final_report(self):
        """打印最終報告"""
        diagnostics = self.system.compute_diagnostics()

        print("\n" + "=" * 70)
        print("  Final Report")
        print("=" * 70)
        print(f"  Total Steps:        {self.step_count}")
        print(f"  Simulation Time:    {self.step_count * 0.01:.2f} (假設 dt=0.01)")
        print("-" * 70)
        print(f"  Mean Speed:         {diagnostics['mean_speed']:.4f}")
        print(f"  Target Speed:       {self.system.params.v0:.4f}")
        print(
            f"  Speed Achievement:  {diagnostics['mean_speed'] / self.system.params.v0 * 100:.1f}%"
        )
        print("-" * 70)
        print(f"  Rg:                 {diagnostics['Rg']:.3f}")
        print(f"  Polarization:       {diagnostics['polarization']:.4f}")
        print("-" * 70)
        print("  物理解讀：")
        P = diagnostics["polarization"]
        if P > 0.7:
            print("    ✅ 高度對齊（強集體運動）")
        elif P > 0.4:
            print("    🟡 中等對齊（部分集體運動）")
        else:
            print("    ❌ 低對齊（混亂狀態）")

        Rg = diagnostics["Rg"]
        if Rg < self.system.params.box_size * 0.2:
            print("    ✅ 群體緊密")
        elif Rg < self.system.params.box_size * 0.4:
            print("    🟡 群體鬆散")
        else:
            print("    ❌ 群體分散（可能需要調整參數）")

        print("=" * 70 + "\n")


# ============================================================================
# Demo Script
# ============================================================================

if __name__ == "__main__":
    print("V2 Enhanced Visualization Demo")
    print("=" * 70)

    # 建立系統
    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=0.5,  # 提高對齊力
        box_size=50.0,
        use_pbc=True,
    )

    N = 300  # 粒子數量
    system = OptimizedFlockingV2(N=N, params=params)
    system.initialize(box_size=5.0, seed=42)

    print(f"\n✅ 系統已初始化：N={N}, box_size={params.box_size}")

    # 建立視覺化器
    viz = V2EnhancedVisualizer(
        system=system,
        window_size=(1400, 1000),
        show_velocity=True,
        show_box=True,
        show_alignment_field=False,  # 暫不啟用（需進一步實作）
    )

    # 執行視覺化
    viz.run(steps=0, dt=0.01, log_every=100)  # steps=0 表示無限循環
