"""
優化版 v3b：使用固定大小陣列 + atomic counter 實作 Cell List

Why：
    避免 Dynamic SNode 的限制
    使用傳統的預分配陣列 + 計數器方式

複雜度：仍然是 O(N)，只要 max_particles_per_cell 設定合理
"""

import taichi as ti
import numpy as np
from dataclasses import dataclass


@dataclass
class FlockingParams:
    """參數集"""

    # Morse 势能
    Ca: float = 1.5
    Cr: float = 2.0
    la: float = 2.5
    lr: float = 0.5
    rc: float = 15.0

    # Rayleigh friction
    alpha: float = 2.0
    v0: float = 1.0

    # 方向對齊
    beta: float = 0.1

    # 空間參數
    box_size: float = 50.0
    use_pbc: bool = True

    # 數值參數
    m: float = 1.0


@ti.data_oriented
class CellListFlockingFixed:
    """
    優化版 v3b：使用固定大小陣列實作 Cell List

    Key Idea:
        - 預分配 cell_particles[total_cells, max_per_cell]
        - 用 cell_count[total_cells] 記錄每個 cell 的實際粒子數
        - 使用 atomic_add 安全插入
    """

    def __init__(self, N: int, params: FlockingParams, arch=ti.metal):
        try:
            ti.init(arch=arch)
        except:
            pass

        self.N = N
        self.params = params

        # === 粒子資料 ===
        self.x = ti.Vector.field(3, ti.f32, N)
        self.v = ti.Vector.field(3, ti.f32, N)
        self.f = ti.Vector.field(3, ti.f32, N)

        # === Cell List 參數 ===
        self.cell_size = params.rc
        self.grid_n = max(3, int(params.box_size / self.cell_size) + 1)
        self.total_cells = self.grid_n**3

        # 估計每個 cell 的平均粒子數
        avg_per_cell = N / self.total_cells
        self.max_per_cell = max(32, int(avg_per_cell * 4))  # 留 4x 安全邊界

        # Cell List 資料結構
        self.cell_count = ti.field(ti.i32, shape=self.total_cells)
        self.cell_particles = ti.field(
            ti.i32, shape=(self.total_cells, self.max_per_cell)
        )

        # === 參數 field ===
        self.p_Ca = ti.field(ti.f32, ())
        self.p_Cr = ti.field(ti.f32, ())
        self.p_la = ti.field(ti.f32, ())
        self.p_lr = ti.field(ti.f32, ())
        self.p_rc = ti.field(ti.f32, ())
        self.p_alpha = ti.field(ti.f32, ())
        self.p_v0 = ti.field(ti.f32, ())
        self.p_beta = ti.field(ti.f32, ())
        self.p_box = ti.field(ti.f32, ())
        self.p_m = ti.field(ti.f32, ())

        self._update_params()

        # === GPU 診斷 ===
        self.diag_sum_v = ti.Vector.field(3, dtype=ti.f32, shape=())
        self.diag_sum_speed = ti.field(ti.f32, shape=())
        self.diag_sum_x = ti.Vector.field(3, dtype=ti.f32, shape=())
        self.diag_sum_r2 = ti.field(ti.f32, shape=())

        print(f"[INFO] CellListFlockingFixed initialized")
        print(f"[INFO] N={N}, Grid={self.grid_n}³={self.total_cells} cells")
        print(f"[INFO] Max particles/cell={self.max_per_cell}")

    def _update_params(self):
        """將參數複製到 Taichi field"""
        self.p_Ca[None] = self.params.Ca
        self.p_Cr[None] = self.params.Cr
        self.p_la[None] = self.params.la
        self.p_lr[None] = self.params.lr
        self.p_rc[None] = self.params.rc
        self.p_alpha[None] = self.params.alpha
        self.p_v0[None] = self.params.v0
        self.p_beta[None] = self.params.beta
        self.p_box[None] = self.params.box_size
        self.p_m[None] = self.params.m

    def initialize(
        self, box_size: float = None, v_init_scale: float = 0.1, seed: int = 0
    ):
        """初始化粒子"""
        if box_size is None:
            box_size = self.params.box_size * 0.3

        rng = np.random.default_rng(seed)
        x_init = rng.uniform(-box_size, box_size, size=(self.N, 3)).astype(np.float32)
        v_init = rng.uniform(-v_init_scale, v_init_scale, size=(self.N, 3)).astype(
            np.float32
        )

        self.x.from_numpy(x_init)
        self.v.from_numpy(v_init)

    @ti.func
    def periodic_distance(self, xi: ti.template(), xj: ti.template()) -> ti.math.vec3:
        """計算週期性邊界下的最小距離向量"""
        rij = xi - xj
        box = self.p_box[None]

        if self.params.use_pbc:
            for d in ti.static(range(3)):
                if rij[d] > box * 0.5:
                    rij[d] -= box
                elif rij[d] < -box * 0.5:
                    rij[d] += box

        return rij

    @ti.func
    def hash_coord(self, pos: ti.math.vec3) -> ti.i32:
        """將 3D 座標映射到 cell ID"""
        box = self.p_box[None]
        p = pos + box * 0.5

        ix = ti.cast(p[0] / self.cell_size, ti.i32) % self.grid_n
        iy = ti.cast(p[1] / self.cell_size, ti.i32) % self.grid_n
        iz = ti.cast(p[2] / self.cell_size, ti.i32) % self.grid_n

        return ix + iy * self.grid_n + iz * self.grid_n * self.grid_n

    @ti.kernel
    def build_cell_list(self):
        """
        建立 Cell List（O(N) 複雜度）

        使用 atomic_add 安全地並行插入粒子
        """
        # 清空計數器
        for i in range(self.total_cells):
            self.cell_count[i] = 0

        # 將每個粒子插入對應 cell
        for i in self.x:
            cell_id = self.hash_coord(self.x[i])
            # Atomic add 獲取插入位置
            offset = ti.atomic_add(self.cell_count[cell_id], 1)

            # 檢查是否超出容量
            if offset < self.max_per_cell:
                self.cell_particles[cell_id, offset] = i

    @ti.kernel
    def compute_forces_celllist(self):
        """使用 Cell List 計算力（O(N) 複雜度）"""
        # 清空力
        for i in self.f:
            self.f[i] = ti.Vector([0.0, 0.0, 0.0])

        # 遍歷所有粒子
        for i in self.x:
            xi = self.x[i]
            vi = self.v[i]

            cell_id = self.hash_coord(xi)
            cx = cell_id % self.grid_n
            cy = (cell_id // self.grid_n) % self.grid_n
            cz = cell_id // (self.grid_n * self.grid_n)

            force = ti.Vector([0.0, 0.0, 0.0])
            v_neighbors_sum = ti.Vector([0.0, 0.0, 0.0])
            n_neighbors = 0

            # 檢查 27 個鄰近 cell
            for dx in ti.static(range(-1, 2)):
                for dy in ti.static(range(-1, 2)):
                    for dz in ti.static(range(-1, 2)):
                        ncx = (cx + dx) % self.grid_n
                        ncy = (cy + dy) % self.grid_n
                        ncz = (cz + dz) % self.grid_n
                        neighbor_cell = (
                            ncx + ncy * self.grid_n + ncz * self.grid_n * self.grid_n
                        )

                        # 遍歷該 cell 的粒子
                        n_particles = self.cell_count[neighbor_cell]
                        for k in range(n_particles):
                            j = self.cell_particles[neighbor_cell, k]

                            if i == j:
                                continue

                            rij_vec = self.periodic_distance(xi, self.x[j])
                            r2 = rij_vec.dot(rij_vec)

                            rc = self.p_rc[None]
                            if r2 > rc * rc or r2 < 1e-6:
                                continue

                            r = ti.sqrt(r2)

                            # Morse 力
                            Ca = self.p_Ca[None]
                            Cr = self.p_Cr[None]
                            la = self.p_la[None]
                            lr = self.p_lr[None]

                            coeff = (Ca / la) * ti.exp(-r / la) - (Cr / lr) * ti.exp(
                                -r / lr
                            )
                            force += coeff * (rij_vec / r)

                            v_neighbors_sum += self.v[j]
                            n_neighbors += 1

            self.f[i] = force

            # 對齊力
            beta = self.p_beta[None]
            if beta > 0.0 and n_neighbors > 0:
                v_avg = v_neighbors_sum / ti.cast(n_neighbors, ti.f32)
                self.f[i] += beta * (v_avg - vi)

    @ti.kernel
    def integrate_verlet_step1(self, dt: ti.f32):
        """Velocity Verlet 第一步"""
        for i in self.x:
            a = self.f[i] / self.p_m[None]
            v_half = self.v[i] + 0.5 * dt * a

            new_x = self.x[i] + dt * v_half

            if self.params.use_pbc:
                box = self.p_box[None]
                for d in ti.static(range(3)):
                    while new_x[d] > box * 0.5:
                        new_x[d] -= box
                    while new_x[d] < -box * 0.5:
                        new_x[d] += box

            self.x[i] = new_x
            self.v[i] = v_half

    @ti.kernel
    def integrate_verlet_step2(self, dt: ti.f32):
        """Velocity Verlet 第二步 + Rayleigh friction"""
        for i in self.x:
            a = self.f[i] / self.p_m[None]
            v_new = self.v[i] + 0.5 * dt * a

            alpha = self.p_alpha[None]
            v0 = self.p_v0[None]
            v2 = v_new.dot(v_new)
            a_rayleigh = alpha * (1.0 - v2 / (v0 * v0 + 1e-12)) * v_new

            v_new += dt * a_rayleigh

            self.v[i] = v_new

    def step(self, dt: float):
        """執行一個完整時間步"""
        self.build_cell_list()
        self.compute_forces_celllist()
        self.integrate_verlet_step1(dt)

        self.build_cell_list()
        self.compute_forces_celllist()
        self.integrate_verlet_step2(dt)

    @ti.kernel
    def compute_diagnostics_gpu(self):
        """GPU 診斷計算"""
        self.diag_sum_v[None] = ti.Vector([0.0, 0.0, 0.0])
        self.diag_sum_speed[None] = 0.0
        self.diag_sum_x[None] = ti.Vector([0.0, 0.0, 0.0])
        self.diag_sum_r2[None] = 0.0

        for i in self.v:
            v = self.v[i]
            speed = v.norm()

            ti.atomic_add(self.diag_sum_v[None], v)
            ti.atomic_add(self.diag_sum_speed[None], speed)
            ti.atomic_add(self.diag_sum_x[None], self.x[i])

        x_cm = self.diag_sum_x[None] / ti.cast(self.N, ti.f32)

        for i in self.x:
            r2 = (self.x[i] - x_cm).norm_sqr()
            ti.atomic_add(self.diag_sum_r2[None], r2)

    def compute_diagnostics(self) -> dict:
        """計算診斷指標"""
        self.compute_diagnostics_gpu()

        v_total_vec = self.diag_sum_v[None]
        sum_speed = self.diag_sum_speed[None]
        sum_r2 = self.diag_sum_r2[None]

        mean_speed = sum_speed / self.N
        v_total_norm = np.sqrt(
            v_total_vec[0] ** 2 + v_total_vec[1] ** 2 + v_total_vec[2] ** 2
        )
        polarization = v_total_norm / (sum_speed + 1e-12)
        rg = np.sqrt(sum_r2 / self.N)

        v_np = self.v.to_numpy()
        speed_np = np.linalg.norm(v_np, axis=1)
        std_speed = float(np.std(speed_np))

        return {
            "mean_speed": float(mean_speed),
            "std_speed": std_speed,
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

            if log_every > 0 and (n % log_every) == 0:
                diag = self.compute_diagnostics()
                print(
                    f"step {n:5d} | "
                    f"<|v|>={diag['mean_speed']:.3f} ± {diag['std_speed']:.3f}  "
                    f"Rg={diag['Rg']:.3f}  "
                    f"P={diag['polarization']:.3f}"
                )
