"""
2D Flocking System - 高效能實作

結合：
    • Morse potential (短程排斥 + 長程吸引)
    • Rayleigh friction (主動定速)
    • Cucker-Smale alignment (方向對齊)
    • Periodic Boundary Conditions (週期邊界)

積分器：Velocity Verlet (O(dt³) 精度)
複雜度：O(N²)，適用於 N ≤ 1000
"""

import taichi as ti
import numpy as np
from dataclasses import dataclass


@dataclass
class FlockingParams:
    """物理參數配置"""

    # Morse potential
    Ca: float = 1.5  # 吸引強度
    Cr: float = 2.0  # 排斥強度
    la: float = 2.5  # 吸引長度
    lr: float = 0.5  # 排斥長度
    rc: float = 15.0  # 截斷半徑

    # Rayleigh friction
    alpha: float = 2.0  # 摩擦係數
    v0: float = 1.0  # 目標速度

    # Alignment
    beta: float = 0.1  # 對齊強度

    # Advanced Physics (新增)
    eta: float = 0.0  # Vicsek noise 強度（角度隨機擾動，範圍 [-eta, +eta] radians）
    boundary_mode: str = (
        "pbc"  # 邊界模式："pbc" (週期), "reflective" (反射), "absorbing" (吸收)
    )
    wall_stiffness: float = 10.0  # 壁面排斥力強度（reflective 模式使用）

    # Space
    box_size: float = 50.0
    use_pbc: bool = True  # 向後相容（deprecated，使用 boundary_mode）

    # Numerics
    m: float = 1.0  # 質量


@ti.data_oriented
class Flocking2D:
    """2D Flocking 系統（優化版）"""

    def __init__(self, N: int, params: FlockingParams):
        """
        初始化系統

        Args:
            N: 粒子數量
            params: 物理參數
        """
        try:
            ti.init(arch=ti.metal, device_memory_GB=2.0)
        except:
            pass

        self.N = N
        self.params = params

        # 向後相容：如果 use_pbc=True，設定 boundary_mode
        if params.boundary_mode == "pbc" or params.use_pbc:
            self.boundary_mode = 0  # PBC
        elif params.boundary_mode == "reflective":
            self.boundary_mode = 1  # 反射邊界
        elif params.boundary_mode == "absorbing":
            self.boundary_mode = 2  # 吸收邊界
        else:
            self.boundary_mode = 0  # 預設 PBC

        # 粒子狀態
        self.x = ti.Vector.field(2, ti.f32, N)
        self.v = ti.Vector.field(2, ti.f32, N)
        self.f = ti.Vector.field(2, ti.f32, N)

        # 參數快取（擴展為 13 個參數）
        # [Ca, Cr, la, lr, rc, alpha, v0, beta, box, m, eta, wall_stiffness, boundary_mode]
        self.p = ti.field(ti.f32, 13)
        self._sync_params()

        # 診斷用累加器
        self.diag = ti.field(ti.f32, 5)  # [sum_vx, vy, speed, sum_x, y]
        self.diag_r2 = ti.field(ti.f32, ())

        # 隨機數生成器狀態（用於 Vicsek noise）
        self.rng_state = ti.field(ti.u32, N)

        boundary_str = ["PBC", "Reflective", "Absorbing"][self.boundary_mode]
        print(
            f"[Flocking2D] N={N}, Boundary={boundary_str}, beta={params.beta}, eta={params.eta}"
        )

    def _sync_params(self):
        """同步參數到 GPU"""
        self.p[0] = self.params.Ca
        self.p[1] = self.params.Cr
        self.p[2] = self.params.la
        self.p[3] = self.params.lr
        self.p[4] = self.params.rc
        self.p[5] = self.params.alpha
        self.p[6] = self.params.v0
        self.p[7] = self.params.beta
        self.p[8] = self.params.box_size
        self.p[9] = self.params.m
        self.p[10] = self.params.eta  # Vicsek noise
        self.p[11] = self.params.wall_stiffness  # 壁面剛度
        self.p[12] = float(self.boundary_mode)  # 邊界模式

    def initialize(self, box_size: float = None, v_scale: float = 0.1, seed: int = 0):
        """
        初始化粒子位置與速度

        Args:
            box_size: 初始分布範圍 (預設為 box_size * 0.3)
            v_scale: 初始速度尺度
            seed: 隨機種子
        """
        if box_size is None:
            box_size = self.params.box_size * 0.3

        rng = np.random.default_rng(seed)
        x_init = rng.uniform(-box_size, box_size, (self.N, 2)).astype(np.float32)
        v_init = rng.uniform(-v_scale, v_scale, (self.N, 2)).astype(np.float32)

        self.x.from_numpy(x_init)
        self.v.from_numpy(v_init)

        # 初始化 RNG 狀態（用於 Vicsek noise）
        rng_states = rng.integers(0, 2**32, size=self.N, dtype=np.uint32)
        self.rng_state.from_numpy(rng_states)

    @ti.func
    def pbc_dist(self, xi: ti.template(), xj: ti.template()) -> ti.math.vec2:
        """計算週期性邊界下的最小距離向量（minimum image convention）
        回傳: rij = xj - xi （從 i 指向 j 的向量）
        """
        rij = xj - xi

        boundary_mode = ti.cast(self.p[12], ti.i32)

        # Mode 0: PBC (向後相容)
        if ti.static(self.params.use_pbc) or boundary_mode == 0:
            box = self.p[8]
            half_box = box * 0.5

            for d in ti.static(range(2)):
                if rij[d] > half_box:
                    rij[d] -= box
                elif rij[d] < -half_box:
                    rij[d] += box

        return rij

    @ti.func
    def xorshift32(self, state: ti.u32) -> ti.u32:
        """XorShift32 隨機數生成器（快速、高品質）"""
        x = state
        x ^= x << 13
        x ^= x >> 17
        x ^= x << 5
        return x

    @ti.func
    def rand_uniform(self, state: ti.u32) -> ti.f32:
        """生成 [0, 1) 均勻分布隨機數"""
        return ti.cast(state, ti.f32) / 4294967296.0  # 2^32

    @ti.kernel
    def compute_forces(self):
        """計算所有力（Morse + Alignment）"""
        # 清空
        for i in self.f:
            self.f[i] = ti.Vector([0.0, 0.0])

        # 讀取參數（減少重複存取）
        Ca, Cr = self.p[0], self.p[1]
        la, lr = self.p[2], self.p[3]
        rc, beta = self.p[4], self.p[7]

        inv_la, inv_lr = 1.0 / la, 1.0 / lr
        rc2 = rc * rc

        # 主循環
        for i in self.x:
            xi, vi = self.x[i], self.v[i]
            force = ti.Vector([0.0, 0.0])
            v_sum = ti.Vector([0.0, 0.0])
            n_neighbors = 0

            for j in range(self.N):
                if i == j:
                    continue

                rij = self.pbc_dist(xi, self.x[j])
                r2 = rij.dot(rij)

                if r2 < 1e-6 or r2 > rc2:
                    continue

                r = ti.sqrt(r2)
                inv_r = 1.0 / r

                # Morse force
                exp_a = ti.exp(-r * inv_la)
                exp_r = ti.exp(-r * inv_lr)
                coeff = Ca * inv_la * exp_a - Cr * inv_lr * exp_r

                force += coeff * rij * inv_r

                # 收集鄰居速度
                if beta > 0.0:
                    v_sum += self.v[j]
                    n_neighbors += 1

            # 儲存 Morse 力
            self.f[i] = force

            # Alignment force (Cucker-Smale)
            if beta > 0.0 and n_neighbors > 0:
                v_avg = v_sum / ti.cast(n_neighbors, ti.f32)
                self.f[i] += beta * (v_avg - vi)

    @ti.kernel
    def verlet_step1(self, dt: ti.f32):
        """Verlet 第一步：半步速度 + 位置更新 + 邊界處理"""
        inv_m = 1.0 / self.p[9]
        box = self.p[8]
        half_box = box * 0.5
        boundary_mode = ti.cast(self.p[12], ti.i32)
        wall_k = self.p[11]  # 壁面剛度

        for i in self.x:
            # 半步速度
            a = self.f[i] * inv_m
            v_half = self.v[i] + 0.5 * dt * a

            # 位置更新
            x_new = self.x[i] + dt * v_half

            # 邊界處理
            if boundary_mode == 0:  # PBC
                for d in ti.static(range(2)):
                    if x_new[d] > half_box:
                        x_new[d] -= box
                    elif x_new[d] < -half_box:
                        x_new[d] += box

            elif boundary_mode == 1:  # Reflective walls
                for d in ti.static(range(2)):
                    if x_new[d] > half_box:
                        x_new[d] = half_box
                        v_half[d] = -v_half[d]  # 反彈
                    elif x_new[d] < -half_box:
                        x_new[d] = -half_box
                        v_half[d] = -v_half[d]  # 反彈

            elif boundary_mode == 2:  # Absorbing (粒子消失)
                # 超出邊界的粒子速度設為零
                out_of_bounds = 0
                for d in ti.static(range(2)):
                    if x_new[d] > half_box or x_new[d] < -half_box:
                        out_of_bounds = 1

                if out_of_bounds:
                    v_half = ti.Vector([0.0, 0.0])
                    x_new = self.x[i]  # 不移動

            self.x[i] = x_new
            self.v[i] = v_half

    @ti.kernel
    def verlet_step2(self, dt: ti.f32):
        """Verlet 第二步：完整速度更新 + Rayleigh friction + Vicsek noise"""
        inv_m = 1.0 / self.p[9]
        alpha, v0 = self.p[5], self.p[6]
        eta = self.p[10]  # Vicsek noise 強度
        v0_sq = v0 * v0

        for i in self.v:
            # 保守力的第二個半步
            a = self.f[i] * inv_m
            v_new = self.v[i] + 0.5 * dt * a

            # Rayleigh friction
            v2 = v_new.dot(v_new)
            rayleigh_coeff = alpha * (1.0 - v2 / (v0_sq + 1e-12))
            v_new += dt * rayleigh_coeff * v_new

            # Vicsek noise: 角度隨機擾動
            if eta > 0.0:
                # 更新 RNG 狀態
                state = self.rng_state[i]
                state = self.xorshift32(state)
                self.rng_state[i] = state

                # 生成 [-eta, +eta] 範圍的隨機角度
                rand_val = self.rand_uniform(state)
                noise_angle = (rand_val - 0.5) * 2.0 * eta

                # 旋轉速度向量
                speed = ti.sqrt(v_new.dot(v_new))
                if speed > 1e-6:
                    # 當前角度
                    theta = ti.atan2(v_new[1], v_new[0])
                    # 新角度
                    theta_new = theta + noise_angle
                    # 新速度（保持速度大小）
                    v_new = ti.Vector(
                        [speed * ti.cos(theta_new), speed * ti.sin(theta_new)]
                    )

            self.v[i] = v_new

    def step(self, dt: float):
        """執行一個時間步"""
        self.compute_forces()
        self.verlet_step1(dt)
        self.compute_forces()
        self.verlet_step2(dt)

    @ti.kernel
    def _accumulate_diag(self):
        """累加診斷量（第一次掃描）"""
        for i in ti.static(range(5)):
            self.diag[i] = 0.0

        for i in self.v:
            v = self.v[i]
            speed = v.norm()
            x = self.x[i]

            # 原子累加（避免競爭）
            ti.atomic_add(self.diag[0], v[0])
            ti.atomic_add(self.diag[1], v[1])
            ti.atomic_add(self.diag[2], speed)
            ti.atomic_add(self.diag[3], x[0])
            ti.atomic_add(self.diag[4], x[1])

    @ti.kernel
    def _accumulate_rg(self, cx: ti.f32, cy: ti.f32):
        """累加 Rg（第二次掃描）"""
        self.diag_r2[None] = 0.0

        for i in self.x:
            dx = self.x[i][0] - cx
            dy = self.x[i][1] - cy
            r2 = dx * dx + dy * dy
            ti.atomic_add(self.diag_r2[None], r2)

    def compute_diagnostics(self) -> dict:
        """
        計算診斷指標

        Returns:
            {mean_speed, std_speed, Rg, polarization}
        """
        # 第一次掃描
        self._accumulate_diag()

        # 讀取累加結果
        inv_N = 1.0 / self.N
        v_sum = np.array([self.diag[0], self.diag[1]])
        sum_speed = self.diag[2]
        x_cm = np.array([self.diag[3], self.diag[4]]) * inv_N

        # 計算 Polarization
        v_total_norm = np.linalg.norm(v_sum)
        polarization = v_total_norm / (sum_speed + 1e-12)

        # 第二次掃描（Rg）
        self._accumulate_rg(x_cm[0], x_cm[1])
        rg = np.sqrt(self.diag_r2[None] * inv_N)

        # 標準差（需完整陣列）
        v_np = self.v.to_numpy()
        speed_np = np.linalg.norm(v_np, axis=1)

        return {
            "mean_speed": float(sum_speed * inv_N),
            "std_speed": float(np.std(speed_np)),
            "Rg": float(rg),
            "polarization": float(polarization),
        }

    def get_state(self):
        """獲取當前狀態"""
        return self.x.to_numpy(), self.v.to_numpy()

    def run(self, steps: int, dt: float, log_every: int = 0):
        """無視覺化運行"""
        for n in range(steps):
            self.step(dt)

            if log_every > 0 and n % log_every == 0:
                diag = self.compute_diagnostics()
                print(
                    f"step {n:5d} | "
                    f"v={diag['mean_speed']:.3f}±{diag['std_speed']:.3f}  "
                    f"Rg={diag['Rg']:.3f}  "
                    f"P={diag['polarization']:.3f}"
                )


# ============================================================================
# Demo
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("2D Flocking Demo")
    print("=" * 70)

    params = FlockingParams(
        Ca=1.5,
        Cr=2.0,
        la=2.5,
        lr=0.5,
        rc=15.0,
        alpha=2.0,
        v0=1.0,
        beta=0.5,
        box_size=50.0,
        use_pbc=True,
    )

    system = Flocking2D(N=300, params=params)
    system.initialize(box_size=5.0, seed=42)

    print("\n執行 100 步模擬...")
    system.run(steps=100, dt=0.01, log_every=20)

    print("\n" + "=" * 70)
    print("✅ Demo 完成")
    print("=" * 70)
