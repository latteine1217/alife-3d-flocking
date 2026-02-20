import sys
sys.path.insert(0, "src")
import time
import taichi as ti
from flocking_heterogeneous import HeterogeneousFlocking3D
from agents.types import AgentType
from flocking_3d import FlockingParams

ti.init(arch=ti.metal)

N = 10
system = HeterogeneousFlocking3D(
    N=N, params=FlockingParams(),
    agent_types=[AgentType.FOLLOWER]*N,
    enable_fov=False, max_agents=200
)
system.initialize(box_size=10.0, seed=42)
system.assign_agents_to_grid()

# 創建簡化版本的 Grid kernel
@ti.kernel
def compute_forces_simple_grid():
    """簡化版：只用 Grid 加速 Morse + Alignment，其他保持簡單"""
    # 清空
    for i in system.f:
        system.f[i] = ti.Vector([0.0, 0.0, 0.0])
    
    # 參數
    Ca, Cr = system.p[0], system.p[1]
    la, lr = system.p[2], system.p[3]
    rc = system.p[4]
    inv_la, inv_lr = 1.0 / la, 1.0 / lr
    rc2 = rc * rc
    
    # 主循環
    for i in system.x:
        if system.agent_alive[i] == 0:
            continue
        
        xi = system.x[i]
        force = ti.Vector([0.0, 0.0, 0.0])
        
        # 簡化：直接用 27 個鄰居 cell（避免深層巢狀）
        cell_id = system.agent_cell_id[i]
        if cell_id >= 0:
            res = system.grid_resolution
            iz = cell_id // (res * res)
            remainder = cell_id % (res * res)
            iy = remainder // res
            ix = remainder % res
            
            # 展開 27 個 cells（避免 3 層迴圈）
            # 只處理 Morse force（最內層計算）
            for cell_offset in ti.static(range(27)):
                dz = (cell_offset // 9) - 1
                dy = ((cell_offset % 9) // 3) - 1
                dx = (cell_offset % 3) - 1
                
                nx, ny, nz = ix + dx, iy + dy, iz + dz
                
                if 0 <= nx < res and 0 <= ny < res and 0 <= nz < res:
                    neighbor_cell = nx + ny*res + nz*res*res
                    n_agents = system.cell_count[neighbor_cell]
                    
                    # 限制最多檢查前 8 個 agents（避免 32 次迴圈）
                    max_check = ti.min(n_agents, 8)
                    for local_idx in range(max_check):
                        j = system.cell_agents[neighbor_cell, local_idx]
                        if i != j and system.agent_alive[j] == 1:
                            rij = system.pbc_dist(xi, system.x[j])
                            r2 = rij.dot(rij)
                            
                            if 1e-6 < r2 < rc2:
                                r = ti.sqrt(r2)
                                inv_r = 1.0 / r
                                exp_a = ti.exp(-r * inv_la)
                                exp_r = ti.exp(-r * inv_lr)
                                coeff = Ca * inv_la * exp_a - Cr * inv_lr * exp_r
                                force += coeff * rij * inv_r
        
        system.f[i] = force

print("測試簡化版 Grid kernel...")
print("編譯中...")
start = time.time()
compute_forces_simple_grid()
compile_time = time.time() - start
print(f"✅ 編譯成功: {compile_time:.2f} 秒")

start = time.time()
compute_forces_simple_grid()
exec_time = (time.time() - start) * 1000
print(f"執行時間: {exec_time:.2f} ms")

# 對比原始版本
system.compute_forces()  # warmup
start = time.time()
system.compute_forces()
orig_time = (time.time() - start) * 1000
print(f"原始版本: {orig_time:.2f} ms")

print(f"\n比例: {exec_time / orig_time:.2f}x")
