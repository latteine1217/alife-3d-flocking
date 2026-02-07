"""
2D Flocking 可視化系統

Features:
    • 粒子速度著色（藍→綠→紅）
    • 速度向量顯示（黃色箭頭）
    • PBC 邊界框
    • 即時診斷 HUD
    • 互動控制（暫停、重置、縮放）
"""

import taichi as ti
import numpy as np
import sys

sys.path.insert(0, "/Users/latteine/Documents/coding/alife/src")
from flocking_2d import Flocking2D, FlockingParams


class Visualizer2D:
    """2D Flocking 可視化器（使用 Taichi GUI）"""

    def __init__(
        self,
        system: Flocking2D,
        window_size: tuple = (1200, 1000),
        show_velocity: bool = True,
        show_box: bool = True,
    ):
        """
        初始化 2D 可視化器

        Args:
            system: Flocking2D 實例
            window_size: 視窗大小
            show_velocity: 是否顯示速度向量
            show_box: 是否顯示邊界框
        """

        self.system = system
        self.show_velocity = show_velocity
        self.show_box = show_box

        # 創建 GUI
        self.gui = ti.GUI(
            "2D Flocking Simulation", res=window_size, background_color=0x1A1A1A
        )

        # 視窗參數
        self.window_size = window_size
        self.box_size = system.params.box_size

        # 視圖控制
        self.zoom = 1.0
        self.offset = np.array([0.0, 0.0])

        # 控制狀態
        self.paused = False
        self.step_count = 0
        self.show_info = True

        # 預計算常數
        self.particle_radius = max(3, min(8, 500 / system.N))  # 自適應半徑

        print(f"[Visualizer2D] 初始化完成，N={system.N}")

    def world_to_screen(self, pos: np.ndarray) -> np.ndarray:
        """
        將世界座標轉換為螢幕座標

        Args:
            pos: 世界座標 (N, 2)

        Returns:
            螢幕座標 (N, 2)，範圍 [0, 1]
        """
        # 標準化到 [0, 1]（假設粒子在 [-box_size/2, box_size/2] 範圍）
        half_box = self.box_size * 0.5
        normalized = (pos + half_box) / self.box_size

        # 應用縮放和偏移
        centered = (normalized - 0.5) * self.zoom + 0.5 + self.offset

        return centered

    def get_speed_colors(self) -> np.ndarray:
        """
        根據速度計算顏色

        Returns:
            顏色陣列 (N, 3)，範圍 [0, 1]
        """
        v_np = self.system.v.to_numpy()
        speed = np.linalg.norm(v_np, axis=1)

        # 標準化速度到 [0, 1]
        v_target = self.system.params.v0
        v_min, v_max = v_target * 0.3, v_target * 1.5
        speed_norm = np.clip((speed - v_min) / (v_max - v_min + 1e-6), 0, 1)

        # 藍→綠→紅插值
        colors = np.zeros((self.system.N, 3), dtype=np.float32)
        colors[:, 0] = speed_norm  # R (快)
        colors[:, 1] = 1.0 - np.abs(speed_norm - 0.5) * 2.0  # G (中)
        colors[:, 2] = 1.0 - speed_norm  # B (慢)

        return colors

    def render_particles(self):
        """繪製粒子"""
        x_np = self.system.x.to_numpy()
        screen_pos = self.world_to_screen(x_np)
        colors = self.get_speed_colors()

        # 轉換為整數顏色（GUI 需要）
        colors_int = (colors * 255).astype(np.uint32)
        colors_gui = (
            (colors_int[:, 0] << 16) | (colors_int[:, 1] << 8) | colors_int[:, 2]
        )

        # 繪製粒子
        for i in range(self.system.N):
            if 0 <= screen_pos[i, 0] <= 1 and 0 <= screen_pos[i, 1] <= 1:
                self.gui.circle(
                    pos=screen_pos[i],
                    color=int(colors_gui[i]),
                    radius=self.particle_radius,
                )

    def render_velocity_vectors(self):
        """繪製速度向量"""
        if not self.show_velocity:
            return

        x_np = self.system.x.to_numpy()
        v_np = self.system.v.to_numpy()

        # 向量長度縮放
        scale = self.box_size * 0.02
        endpoints = x_np + v_np * scale

        # 轉換為螢幕座標
        screen_start = self.world_to_screen(x_np)
        screen_end = self.world_to_screen(endpoints)

        # 繪製箭頭（使用線段）
        for i in range(self.system.N):
            if 0 <= screen_start[i, 0] <= 1 and 0 <= screen_start[i, 1] <= 1:
                self.gui.line(
                    begin=screen_start[i],
                    end=screen_end[i],
                    color=0xFFFF33,  # 亮黃色
                    radius=1.5,
                )

    def render_box(self):
        """繪製邊界框"""
        if not self.show_box:
            return

        half_box = self.box_size * 0.5
        corners = np.array(
            [
                [-half_box, -half_box],
                [half_box, -half_box],
                [half_box, half_box],
                [-half_box, half_box],
            ],
            dtype=np.float32,
        )

        screen_corners = self.world_to_screen(corners)

        # 繪製四條邊
        for i in range(4):
            start = screen_corners[i]
            end = screen_corners[(i + 1) % 4]
            self.gui.line(begin=start, end=end, color=0x888888, radius=2)

    def print_hud(self):
        """打印 HUD 資訊到控制台"""
        if not self.show_info or self.step_count % 50 != 0:
            return

        diag = self.system.compute_diagnostics()

        print("\n" + "=" * 70)
        print(
            f"  Step: {self.step_count:<10}  Status: {'⏸ PAUSED' if self.paused else '▶ RUNNING'}"
        )
        print("=" * 70)
        print(f"  System: 2D Flocking, N={self.system.N}")
        print(f"  Box Size: {self.system.params.box_size:.1f}")
        print("-" * 70)
        print(f"  Mean Speed:      {diag['mean_speed']:.4f} ± {diag['std_speed']:.4f}")
        print(f"  Target Speed:    {self.system.params.v0:.4f}")
        print(f"  Rg:              {diag['Rg']:.3f}")
        print(f"  Polarization:    {diag['polarization']:.4f}")
        print("-" * 70)
        print(
            f"  Params: beta={self.system.params.beta:.2f}, alpha={self.system.params.alpha:.2f}"
        )
        print("=" * 70)

    def render_text_overlay(self):
        """在螢幕上顯示文字"""
        # 左上角狀態
        status = "⏸ PAUSED" if self.paused else "▶ RUNNING"
        self.gui.text(
            content=f"Step: {self.step_count} | {status}",
            pos=(0.02, 0.97),
            color=0xFFFFFF,
            font_size=20,
        )

        # 右上角診斷
        if self.show_info and self.step_count % 10 == 0:
            diag = self.system.compute_diagnostics()
            info_text = (
                f"v={diag['mean_speed']:.3f} | "
                f"Rg={diag['Rg']:.2f} | "
                f"P={diag['polarization']:.3f}"
            )
            self.gui.text(
                content=info_text, pos=(0.98, 0.97), color=0x00FF00, font_size=18
            )

        # 底部控制提示
        controls = (
            "[SPACE] Pause | [R] Reset | [V] Vectors | [B] Box | [I] Info | [ESC] Exit"
        )
        self.gui.text(content=controls, pos=(0.5, 0.02), color=0xAAAAAA, font_size=16)

    def handle_input(self):
        """處理鍵盤輸入"""
        # 鍵盤事件
        if self.gui.get_event(ti.GUI.PRESS):
            key = self.gui.event.key

            if key == ti.GUI.SPACE:
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

            elif key == "v":
                self.show_velocity = not self.show_velocity
                print(f"\n>>> 速度向量: {'ON' if self.show_velocity else 'OFF'}")

            elif key == "b":
                self.show_box = not self.show_box
                print(f"\n>>> 邊界框: {'ON' if self.show_box else 'OFF'}")

            elif key == "i":
                self.show_info = not self.show_info
                print(f"\n>>> HUD 資訊: {'ON' if self.show_info else 'OFF'}")

            elif key == ti.GUI.ESCAPE:
                print("\n>>> 退出可視化")
                self.gui.running = False

    def run(self, steps: int = 0, dt: float = 0.01):
        """
        執行可視化模擬

        Args:
            steps: 最大步數（0 = 無限循環）
            dt: 時間步長
        """
        print("\n" + "=" * 70)
        print("  2D Flocking Visualization - Controls")
        print("=" * 70)
        print("  [SPACE]  暫停/恢復")
        print("  [R]      重置模擬（隨機種子）")
        print("  [V]      切換速度向量顯示")
        print("  [B]      切換邊界框顯示")
        print("  [I]      切換 HUD 資訊")
        print("  [ESC]    退出")
        print("=" * 70)
        print(f"\n>>> 開始模擬（N={self.system.N}, dt={dt}）\n")

        while self.gui.running:
            # 處理輸入
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
            self.gui.clear(0x1A1A1A)

            # 繪製元素（順序很重要）
            if self.show_box:
                self.render_box()

            self.render_particles()

            if self.show_velocity:
                self.render_velocity_vectors()

            self.render_text_overlay()

            # 顯示
            self.gui.show()

        # 最終報告
        self.print_final_report()

    def print_final_report(self):
        """打印最終報告"""
        diag = self.system.compute_diagnostics()

        print("\n" + "=" * 70)
        print("  Final Report (2D)")
        print("=" * 70)
        print(f"  Total Steps:      {self.step_count}")
        print(f"  Mean Speed:       {diag['mean_speed']:.4f}")
        print(f"  Target Speed:     {self.system.params.v0:.4f}")
        print(f"  Rg:               {diag['Rg']:.3f}")
        print(f"  Polarization:     {diag['polarization']:.4f}")
        print("-" * 70)

        # 物理解讀
        P = diag["polarization"]
        if P > 0.7:
            print("  ✅ 高度對齊（強集體運動）")
        elif P > 0.4:
            print("  🟡 中等對齊（部分集體運動）")
        else:
            print("  ❌ 低對齊（混亂狀態）")

        Rg = diag["Rg"]
        if Rg < self.system.params.box_size * 0.2:
            print("  ✅ 群體緊密")
        elif Rg < self.system.params.box_size * 0.4:
            print("  🟡 群體鬆散")
        else:
            print("  ❌ 群體分散")

        print("=" * 70 + "\n")


# ============================================================================
# Demo
# ============================================================================
if __name__ == "__main__":
    print("2D Flocking Visualization Demo")
    print("=" * 70)

    # 創建 2D 系統
    params = FlockingParams(
        dim=2,
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=1.0,
        box_size=50.0,
        use_pbc=True,
    )

    N = 300
    system = Flocking2D(N=N, params=params)
    system.initialize(box_size=5.0, seed=42)

    print(f"\n✅ 系統已初始化：N={N}, box_size={params.box_size}")

    # 創建可視化器
    viz = Visualizer2D(
        system=system, window_size=(1200, 1000), show_velocity=True, show_box=True
    )

    # 執行可視化
    viz.run(steps=0, dt=0.01)  # steps=0 表示無限循環
